"""Rebase authorized PR snapshots, verify publication and checks, then pin merges."""

import json
import os
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path


class Stop(RuntimeError):
    pass


class Usage(Stop):
    pass


def run(*args, env=None, allowed=(0,)):
    result = subprocess.run(
        args, check=False, text=True, capture_output=True, timeout=60, env=env
    )
    if result.returncode not in allowed:
        raise Stop(
            f"{args[0]} {args[1]} failed ({result.returncode}): {result.stderr.strip()}"
        )
    return result


def git(*args):
    return run("git", *args).stdout.strip()


def view(number, repo):
    fields = "state,headRefName,headRefOid,baseRefName,isDraft,isCrossRepository,reviewDecision,statusCheckRollup,mergeCommit"
    return json.loads(
        run("gh", "pr", "view", number, "-R", repo, "--json", fields).stdout
    )


def require_head(pr, branch, sha):
    if (
        pr.get("state"),
        pr.get("baseRefName"),
        pr.get("headRefName"),
        pr.get("headRefOid"),
    ) != ("OPEN", "main", branch, sha):
        raise Stop("PR state, target, branch, or head changed; inspect before retrying")
    if pr.get("isDraft") is not False or pr.get("isCrossRepository") is not False:
        raise Stop("draft and cross-repository PRs require manual handling")
    if pr.get("reviewDecision") == "CHANGES_REQUESTED":
        raise Stop("review changes remain requested")


def remote_head(branch):
    lines = git(
        "ls-remote", "--exit-code", "origin", f"refs/heads/{branch}"
    ).splitlines()
    if len(lines) != 1:
        raise Stop(f"cannot confirm remote {branch}")
    return lines[0].split()[0]


def checks_pass(pr):
    checks = pr.get("statusCheckRollup")
    if not isinstance(checks, list) or not checks:
        return False
    pending = False
    passed = False
    for check in checks:
        if check.get("__typename") == "StatusContext":
            state = check.get("state")
            if state == "SUCCESS":
                passed = True
            elif state in ("PENDING", "EXPECTED"):
                pending = True
            else:
                raise Stop(
                    f"unsuccessful commit status: {check.get('context')}: {state}"
                )
        elif check.get("__typename") == "CheckRun":
            status = check.get("status")
            if status in ("QUEUED", "IN_PROGRESS", "WAITING", "PENDING", "REQUESTED"):
                pending = True
            elif status == "COMPLETED":
                conclusion = check.get("conclusion")
                if conclusion == "SUCCESS":
                    passed = True
                elif conclusion not in ("NEUTRAL", "SKIPPED"):
                    raise Stop(f"unsuccessful check: {check.get('name')}: {conclusion}")
            else:
                raise Stop(f"unrecognized check status: {status}")
        else:
            raise Stop("unrecognized check result")
    return passed and not pending


def repository_identity(value):
    # Compare the configured push destination without printing URL credentials.
    from urllib.parse import urlsplit

    if value.startswith("git@") and ":" in value:
        value = "ssh://" + value.replace(":", "/", 1)
    parsed = urlsplit(value)
    path = parsed.path.rstrip("/")
    path = path.removesuffix(".git")
    return (parsed.hostname or "", path)


def sequence(number, repo, metadata, attempts, interval):
    pr = view(number, repo)
    if pr.get("state") == "MERGED":
        print(f"#{number} already merged; skipped", flush=True)
        return
    fields = (metadata / f"{number}.tsv").read_text().strip().split("\t")
    if len(fields) != 5:
        raise Stop(
            "metadata must include branch, base, state, commits, and captured head SHA"
        )
    branch, base, state, replay, captured = fields
    commits = replay.split(",")
    if (
        base != "main"
        or state != "OPEN"
        or not all(re.fullmatch(r"[0-9a-f]{40}", sha) for sha in [captured, *commits])
    ):
        raise Stop("invalid metadata; capture an open PR targeting main")
    require_head(pr, branch, captured)
    git("check-ref-format", f"refs/heads/{branch}")
    git(
        "fetch",
        "--no-tags",
        "origin",
        "+refs/heads/main:refs/remotes/origin/main",
        f"+refs/heads/{branch}:refs/remotes/origin/{branch}",
    )
    if git("rev-parse", f"refs/remotes/origin/{branch}") != captured:
        raise Stop("fetched branch differs from captured metadata head")
    base_sha = git("rev-parse", "refs/remotes/origin/main")
    if git("rev-list", "--merges", f"{base_sha}..{captured}"):
        raise Stop("merge commits require manual replay planning")
    actual = git("rev-list", "--reverse", f"{base_sha}..{captured}").splitlines()
    if actual != commits:
        raise Stop("metadata does not contain the complete current PR commit sequence")
    scratch = f"coordinator-{number}-{uuid.uuid4().hex[:8]}"
    git("checkout", "-b", scratch, base_sha)
    helpers = Path(__file__).resolve().parent
    for commit in commits:
        result = run(
            "git",
            "-c",
            "merge.conflictstyle=diff3",
            "cherry-pick",
            "--allow-empty",
            "--keep-redundant-commits",
            commit,
            allowed=(0, 1, 128),
        )
        if result.returncode:
            conflicts = git("diff", "--name-only", "--diff-filter=U").splitlines()
            if conflicts != [".golangci.yml"]:
                raise Stop(
                    f"cherry-pick failed; inspect {scratch}: {result.stderr.strip()}"
                )
            run(sys.executable, str(helpers / "resolve-golangci.py"))
            if re.search(
                r"^(<{7}|={7}|>{7}|\|{7})",
                Path(".golangci.yml").read_text(),
                re.MULTILINE,
            ):
                raise Stop("lint conflict adapter left unresolved markers")
            git("add", ".golangci.yml")
            if (
                run("git", "diff", "--cached", "--quiet", allowed=(0, 1)).returncode
                == 0
            ):
                git("cherry-pick", "--skip")
            else:
                git("-c", "core.editor=true", "cherry-pick", "--continue")
    if Path(".golangci.yml").is_file():
        scopes = {
            "414": "dcrouter/",
            "415": "sentryread/",
            "417": "logsearch/",
            "419": "beanstalk/",
            "421": "announce/",
            "423": "",
            "426": "features/",
        }
        environment = dict(os.environ)
        environment.pop("SCOPE_ADD", None)
        if repo.lower() == "easypost-sandbox/epservicesctl" and number in scopes:
            environment["SCOPE_ADD"] = scopes[number]
        run(sys.executable, str(helpers / "normalize-golangci.py"), env=environment)
        if run(
            "git", "diff", "--quiet", "--", ".golangci.yml", allowed=(0, 1)
        ).returncode:
            git("add", ".golangci.yml")
            git("commit", "-m", "fix(lint): normalize typed-enum scope alternation")
    if git("status", "--porcelain"):
        raise Stop("replay left uncommitted changes")
    if run("git", "diff", "--quiet", base_sha, "HEAD", allowed=(0, 1)).returncode == 0:
        raise Stop("PR adds nothing over main; closing remains a human decision")
    expected = git("rev-parse", "HEAD")
    require_head(view(number, repo), branch, captured)
    if remote_head("main") != base_sha:
        raise Stop("main advanced during replay; inspect and recapture metadata")
    if expected != captured:
        run(
            "git",
            "push",
            f"--force-with-lease=refs/heads/{branch}:{captured}",
            "origin",
            f"HEAD:refs/heads/{branch}",
        )
    if remote_head(branch) != expected:
        raise Stop("publication not confirmed; no merge requested")
    print(f"#{number} published {expected}; waiting for checks", flush=True)
    for attempt in range(attempts):
        if remote_head(branch) != expected or remote_head("main") != base_sha:
            raise Stop("remote head or main advanced while waiting for checks")
        current = view(number, repo)
        # GitHub may briefly show the pre-push revision, never accept its checks.
        if current.get("headRefOid") == captured and captured != expected:
            require_head(current, branch, captured)
        else:
            require_head(current, branch, expected)
            if checks_pass(current):
                break
        if attempt + 1 == attempts:
            raise Stop("checks timed out or were unavailable; no merge requested")
        time.sleep(interval)
    run(
        "gh",
        "pr",
        "merge",
        number,
        "-R",
        repo,
        "--squash",
        "--match-head-commit",
        expected,
    )
    print(
        f"#{number} merge requested for {expected}; awaiting confirmation", flush=True
    )
    for attempt in range(attempts):
        current = view(number, repo)
        if (
            current.get("headRefOid") != expected
            or current.get("baseRefName") != "main"
        ):
            raise Stop("PR changed after merge request; outcome requires inspection")
        if current.get("state") == "MERGED":
            merged = current.get("mergeCommit") or {}
            sha = merged.get("oid", "")
            if not re.fullmatch(r"[0-9a-f]{40}", sha):
                raise Stop("merged state lacks a confirmed merge commit")
            git(
                "fetch",
                "--no-tags",
                "origin",
                "+refs/heads/main:refs/remotes/origin/main",
            )
            git("merge-base", "--is-ancestor", sha, "refs/remotes/origin/main")
            print(f"#{number} MERGED: {sha}", flush=True)
            return
        if current.get("state") != "OPEN":
            raise Stop("PR closed without a confirmed merge")
        if attempt + 1 < attempts:
            time.sleep(interval)
    raise Stop("merge accepted but not confirmed; inspect before retrying")


def main():
    numbers = sys.argv[1:]
    if not numbers or any(not re.fullmatch(r"[1-9][0-9]*", n) for n in numbers):
        raise Usage("usage: merge-seq.sh PR [PR...]")
    repo = os.environ.get("EPSCTL_REPO", "easypost-sandbox/epservicesctl")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise Stop("EPSCTL_REPO must identify owner/repository")
    work = Path(os.environ.get("EPSCTL_MERGE_DIR", "/tmp/epsctl-merge")).resolve()
    metadata = Path(
        os.environ.get("EPSCTL_MERGE_META", "/tmp/epsctl-merge-meta")
    ).resolve()
    attempts = int(os.environ.get("EPSCTL_MERGE_ATTEMPTS", "90"))
    interval = float(os.environ.get("EPSCTL_MERGE_INTERVAL", "45"))
    if attempts < 1 or not 0 <= interval <= 300:
        raise Stop(
            "attempts must be positive and interval must be between 0 and 300 seconds"
        )
    os.chdir(work)
    if Path(git("rev-parse", "--show-toplevel")).resolve() != work or git(
        "status", "--porcelain"
    ):
        raise Stop("use a clean, dedicated repository root")
    for marker in (
        "MERGE_HEAD",
        "CHERRY_PICK_HEAD",
        "REBASE_HEAD",
        "rebase-merge",
        "rebase-apply",
    ):
        if Path(git("rev-parse", "--git-path", marker)).exists():
            raise Stop("finish the existing Git operation first")
    identity = json.loads(
        run("gh", "repo", "view", repo, "--json", "url,sshUrl").stdout
    )
    push = git("remote", "get-url", "--push", "--all", "origin").splitlines()
    fetch = git("remote", "get-url", "--all", "origin").splitlines()
    allowed = [repository_identity(identity[key]) for key in ("url", "sshUrl")]
    if (
        len(push) != 1
        or len(fetch) != 1
        or any(repository_identity(url) not in allowed for url in push + fetch)
    ):
        raise Stop(
            "origin must have one fetch and push destination matching EPSCTL_REPO"
        )
    for number in numbers:
        sequence(number, repo, metadata, attempts, interval)


if __name__ == "__main__":
    try:
        main()
    except Usage as error:
        print(f"merge-seq: {error}", file=sys.stderr)
        sys.exit(64)
    except (Stop, OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"merge-seq: {error}", file=sys.stderr)
        sys.exit(1)
