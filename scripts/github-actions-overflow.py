#!/usr/bin/env python3
"""Start a matching Mac CI run when the hosted Pi check has waited too long."""

import argparse
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import fcntl
import json
from math import ceil, isfinite
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import quote

REPO = "lanej/dotfiles"
OWNER, _ = REPO.split("/")
HOSTED_WORKFLOW = "pi-resources.yml"
HOSTED_JOB = "resources (macos-latest)"
OVERFLOW_WORKFLOW = "mac-overflow.yml"
RUNNER = "dotfiles-mac-mini"
STATUS = "macOS overflow / Pi shared resources"
SHA = re.compile(r"[0-9a-f]{40}")
RETRY_DELAY = 300
RATE_RETRY_DELAY = 60
MAX_RATE_RETRY_DELAY = 1800
RATE_MESSAGE = re.compile(
    r"api rate limit exceeded|primary rate limit|secondary rate limit|"
    r"rate limit (?:exceeded|reached)|rate limit temporarily exceeded",
    re.IGNORECASE,
)
MAX_QUEUE = timedelta(minutes=10)
HOSTED_NODE = "W_kwDOACeEE84YD6uP"
QUEUE_QUERY = """query($hosted: ID!, $job: String!) {
  hosted: node(id: $hosted) {
    ... on Workflow {
      runs(first: 50, orderBy: {field: CREATED_AT, direction: DESC}) {
        pageInfo { hasNextPage }
        nodes {
          databaseId createdAt event
          checkSuite {
            checkRuns(first: 1, filterBy: {checkName: $job, statuses: [QUEUED]}) {
              nodes { id }
            }
          }
        }
      }
    }
  }
  rateLimit { cost }
}"""


class GitHubThrottled(RuntimeError):
    def __init__(self, reason, retry_at):
        super().__init__(reason)
        self.reason = reason
        self.retry_at = retry_at


class GitHubRequestError(subprocess.CalledProcessError):
    def __init__(self, result, status, body):
        super().__init__(result.returncode, result.args, body, result.stderr)
        self.status = status


def github_response(output):
    head, separator, body = output.replace("\r\n", "\n").partition("\n\n")
    match = re.match(r"HTTP/\S+ (\d{3})\b", head)
    if match is None or not separator:
        return None, {}, output
    headers = {}
    for line in head.splitlines()[1:]:
        name, _, value = line.partition(":")
        headers[name.lower()] = value.strip()
    return int(match[1]), headers, body


def retry_after(value, now):
    if not value:
        return 0
    try:
        if value.isascii() and value.isdecimal():
            return now + int(value)
        date = parsedate_to_datetime(value)
        return date.timestamp() if date.tzinfo else 0
    except (ValueError, OverflowError, OSError):
        return 0


def check_throttle(graphql, status, headers, body, stderr):
    if status not in {403, 429} and not (graphql and status == 200):
        return
    primary = headers.get("x-ratelimit-remaining") == "0"
    retry_header = headers.get("retry-after")
    rate_error = RATE_MESSAGE.search(stderr)
    if graphql and status == 200 and not rate_error:
        try:
            errors = json.loads(body).get("errors", [])
            rate_error = any(
                error.get("type") == "RATE_LIMITED"
                or RATE_MESSAGE.search(error.get("message", ""))
                for error in errors
            )
        except (AttributeError, TypeError, ValueError):
            pass
    elif status in {403, 429}:
        rate_error = rate_error or RATE_MESSAGE.search(body)
    if (
        status != 429
        and not rate_error
        and not (status == 403 and (primary or retry_header))
    ):
        return
    now = datetime.now(timezone.utc).timestamp()
    reset_header = headers.get("x-ratelimit-reset", "")
    reset = int(reset_header) + 1 if primary and reset_header.isdecimal() else 0
    retry_at = max(reset, retry_after(retry_header, now))
    source = "GraphQL" if graphql else "REST"
    reason = "primary rate limit" if primary else "rate limit"
    raise GitHubThrottled(f"GitHub {source} {reason}", ceil(retry_at) if retry_at > now else None)


def github(path, *fields):
    result = subprocess.run(
        ["gh", "api", "--include", path, *fields], capture_output=True,
        text=True, timeout=25,
    )
    status, headers, body = github_response(result.stdout)
    if status is None:
        match = re.search(r"HTTP (\d{3})\b", result.stderr)
        status = int(match[1]) if match else None
    check_throttle(path == "graphql", status, headers, body, result.stderr)
    if result.returncode:
        raise GitHubRequestError(result, status, body)
    return json.loads(body) if body.strip() else None


def workflow_runs(workflow, query):
    return github(f"repos/{REPO}/actions/workflows/{workflow}/runs?{query}")["workflow_runs"]


def timestamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def pull(number):
    return github(f"repos/{REPO}/pulls/{number}")


def current_pull(number, head):
    pr = pull(number)
    if (
        pr["state"] == "open"
        and pr["user"]["login"] == OWNER
        and (pr["head"].get("repo") or {}).get("full_name") == REPO
        and pr["head"]["sha"] == head
        and pr["base"]["repo"]["full_name"] == REPO
        and SHA.fullmatch(pr.get("merge_commit_sha") or "")
    ):
        return pr
    return None


def queue_hint(minimum_age):
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=3)
    try:
        response = github(
            "graphql", "-f", f"query={QUEUE_QUERY}", "-f", f"hosted={HOSTED_NODE}",
            "-f", f"job={HOSTED_JOB}",
        )
        if response.get("errors"):
            raise ValueError("Incomplete GraphQL response")
        hosted = response["data"]["hosted"]["runs"]
        nodes = hosted["nodes"]
        if not isinstance(nodes, list) or any(
            not isinstance(run["checkSuite"]["checkRuns"]["nodes"], list) for run in nodes
        ):
            raise ValueError("Incomplete GraphQL check list")
        # A truncated window cannot rule out a queued pull request.
        if hosted["pageInfo"]["hasNextPage"] and (
            not nodes or timestamp(nodes[-1]["createdAt"]) >= cutoff
        ):
            return None
        candidates = {
            run["databaseId"] for run in nodes
            if run["event"] == "pull_request"
            and cutoff <= timestamp(run["createdAt"]) <= now - timedelta(seconds=minimum_age)
            and run["checkSuite"]["checkRuns"]["nodes"]
        }
        if not all(type(run_id) is int and run_id > 0 for run_id in candidates):
            raise ValueError("Missing workflow run ID")
        return candidates
    except (subprocess.SubprocessError, AttributeError, KeyError, TypeError, ValueError):
        print("GraphQL queue hint unavailable; checking REST.", file=sys.stderr)
        return None


def select_job(minimum_age, candidate_ids=None):
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    query = f"event=pull_request&created=%3E%3D{cutoff}&per_page=50"
    for run in reversed(workflow_runs(HOSTED_WORKFLOW, query)):
        if candidate_ids is not None and run["id"] not in candidate_ids:
            continue
        if (
            run["status"] not in {"queued", "in_progress"}
            or run["actor"]["login"] != OWNER
            or run["triggering_actor"]["login"] != OWNER
            or (run.get("head_repository") or {}).get("full_name") != REPO
            or len(run["pull_requests"]) != 1
        ):
            continue
        pr = current_pull(run["pull_requests"][0]["number"], run["head_sha"])
        if not pr:
            continue
        jobs = github(f"repos/{REPO}/actions/runs/{run['id']}/jobs")["jobs"]
        for job in jobs:
            if (
                job["name"] != HOSTED_JOB or job["status"] != "queued"
                or job["labels"] != ["macos-latest"] or job["runner_name"]
                or not job.get("created_at")
            ):
                continue
            if (now - timestamp(job["created_at"])).total_seconds() < minimum_age:
                continue
            commit = github(f"repos/{REPO}/commits/{pr['merge_commit_sha']}")
            base_ref = quote(pr["base"]["ref"], safe="/")
            base = github(f"repos/{REPO}/git/ref/heads/{base_ref}")["object"]["sha"]
            if [p["sha"] for p in commit["parents"]] == [base, pr["head"]["sha"]]:
                yield job, pr


def save(path, state):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(state, indent=2) + "\n")
    temp.replace(path)


def backoff_path(state_path):
    return state_path.with_suffix(".backoff.json")


def load_backoff(state_path):
    try:
        backoff = json.loads(backoff_path(state_path).read_text())
    except FileNotFoundError:
        return {}
    if (
        not isinstance(backoff, dict)
        or type(backoff.get("retry_at")) not in {int, float}
        or not isfinite(backoff["retry_at"])
        or type(backoff.get("consecutive")) is not int
        or backoff["consecutive"] < 1
        or backoff.get("reason") not in {
            "GitHub REST primary rate limit", "GitHub REST rate limit",
            "GitHub GraphQL primary rate limit", "GitHub GraphQL rate limit",
        }
    ):
        raise ValueError("Invalid GitHub rate-limit backoff state")
    return backoff


def record_backoff(state_path, previous, error, now):
    consecutive = previous.get("consecutive", 0) + 1
    default_delay = min(RATE_RETRY_DELAY * 2 ** min(consecutive - 1, 5), MAX_RATE_RETRY_DELAY)
    retry_at = error.retry_at or ceil(now + default_delay)
    save(backoff_path(state_path), {
        "retry_at": retry_at, "consecutive": consecutive, "reason": error.reason,
    })
    return retry_at


def resolve_pending(state, runs):
    for pending in state.values():
        if pending.get("done"):
            continue
        run = next((
            r for r in runs
            if r["display_title"] == pending["title"]
            and ("run_id" not in pending or r["id"] == pending["run_id"])
            and r["head_branch"] == "master"
            and r["actor"]["login"] == OWNER
            and r["triggering_actor"]["login"] == OWNER
        ), None)
        now = datetime.now(timezone.utc)
        if not run:
            if (
                "retry_at" not in pending
                and not pending.get("reported")
                and now.timestamp() - pending["at"] >= RETRY_DELAY
            ):
                print(f"Unconfirmed dispatch: {pending['title']}", file=sys.stderr)
                pending["reported"] = True
            continue
        if run["status"] in {"queued", "requested", "pending"} and now - timestamp(run["created_at"]) >= MAX_QUEUE:
            jobs = github(f"repos/{REPO}/actions/runs/{run['id']}/jobs")["jobs"]
            if all(job["status"] == "queued" and not job["runner_name"] for job in jobs):
                github(f"repos/{REPO}/actions/runs/{run['id']}/cancel", "--method", "POST")
                print(f"Canceled unassigned overflow run {run['id']}", flush=True)
                pending["done"] = True
            continue
        if run["status"] != "completed":
            continue
        pr = current_pull(pending["pr"], pending["head"])
        if pr and pr["merge_commit_sha"] == pending["commit"]:
            jobs = github(f"repos/{REPO}/actions/runs/{run['id']}/jobs")["jobs"]
            if len(jobs) == 1 and jobs[0]["runner_name"] == RUNNER:
                result = jobs[0]["conclusion"]
                if result in {"success", "failure", "timed_out"}:
                    passed = result == "success" and any(
                        step["name"] == "Verify native Pi resources" and step["conclusion"] == "success"
                        for step in jobs[0]["steps"]
                    )
                    state_value = "success" if passed else "failure"
                    description = "Mac mini passed" if passed else "Mac mini did not pass"
                    github(
                        f"repos/{REPO}/statuses/{pending['head']}", "--method", "POST",
                        "-f", f"state={state_value}", "-f", f"context={STATUS}",
                        "-f", f"target_url={run['html_url']}",
                        "-f", f"description={description} at merge commit {pending['commit']}",
                    )
        pending["done"] = True


def cycle(path, state, minimum_age, observe):
    runs = None
    if any(not entry.get("done") for entry in state.values()):
        runs = workflow_runs(OVERFLOW_WORKFLOW, "event=workflow_dispatch&per_page=100")
        if not observe:
            try:
                resolve_pending(state, runs)
            finally:
                save(path, state)
        if any(r["status"] != "completed" for r in runs):
            return

    candidate_ids = queue_hint(minimum_age)
    if candidate_ids == set():
        return
    for job, pr in select_job(minimum_age, candidate_ids):
        job_id = str(job["id"])
        commit, head = pr["merge_commit_sha"], pr["head"]["sha"]
        key = f"{job_id}:{commit}"
        title = f"Mac overflow for hosted job {job_id} at {commit}"
        previous = state.get(key, {})
        can_retry = previous.get("retry_at", float("inf")) <= datetime.now(timezone.utc).timestamp()
        if previous and not can_retry:
            continue
        if runs is None:
            runs = workflow_runs(OVERFLOW_WORKFLOW, "event=workflow_dispatch&per_page=100")
            if any(r["status"] != "completed" for r in runs):
                return
        if any(r["display_title"] == title for r in runs):
            continue
        runners = github(f"repos/{REPO}/actions/runners")["runners"]
        if not any(r["name"] == RUNNER and r["status"] == "online" and not r["busy"] for r in runners):
            return
        print(f"PR #{pr['number']} job {job_id} commits {head} / {commit}", flush=True)
        if observe:
            return
        # A reservation survives a lost API response so the next poll cannot
        # submit a second run for the same hosted job.
        entry = {
            "pr": pr["number"], "head": head, "commit": commit, "title": title,
            "at": datetime.now(timezone.utc).timestamp(),
            "attempts": previous.get("attempts", 0) + 1,
        }
        state[key] = entry
        save(path, state)
        try:
            result = github(
                f"repos/{REPO}/actions/workflows/{OVERFLOW_WORKFLOW}/dispatches",
                "--method", "POST", "-f", "ref=master", "-F", "return_run_details=true",
                "-f", f"inputs[hosted_job]={job_id}", "-f", f"inputs[commit]={commit}",
            )
        except GitHubThrottled as error:
            entry["attempts"] -= 1
            entry["retry_at"] = error.retry_at or ceil(entry["at"] + RATE_RETRY_DELAY)
            save(path, state)
            raise
        except GitHubRequestError as error:
            if error.status in {400, 401, 403, 404, 422} and entry["attempts"] < 3:
                entry["retry_at"] = entry["at"] + RETRY_DELAY
            print((error.stderr or "").strip(), file=sys.stderr)
        else:
            run_id = result.get("workflow_run_id") if isinstance(result, dict) else None
            if type(run_id) is int and run_id > 0:
                entry["run_id"] = run_id
                print(f"https://github.com/{REPO}/actions/runs/{entry['run_id']}", flush=True)
        save(path, state)
        return


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--wait-seconds", type=int, default=180)
    parser.add_argument("--observe", action="store_true")
    args = parser.parse_args()
    if args.wait_seconds < 1:
        parser.error("--wait-seconds must be positive")
    args.state.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with args.state.with_suffix(".lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        try:
            backoff = load_backoff(args.state)
        except ValueError as error:
            sys.exit(str(error))
        if backoff.get("retry_at", 0) > datetime.now(timezone.utc).timestamp():
            return
        state = json.loads(args.state.read_text()) if args.state.exists() else {}
        try:
            cycle(args.state, state, args.wait_seconds, args.observe)
        except GitHubThrottled as error:
            now = datetime.now(timezone.utc).timestamp()
            if args.observe:
                print(error.reason, file=sys.stderr)
                return
            retry_at = record_backoff(args.state, backoff, error, now)
            next_poll = datetime.fromtimestamp(retry_at, timezone.utc).isoformat()
            print(f"{error.reason}. Polling resumes after {next_poll}.", file=sys.stderr)
        except subprocess.CalledProcessError as error:
            print(error.stderr or f"GitHub CLI failed with exit {error.returncode}", file=sys.stderr)
            sys.exit(1)
        except subprocess.TimeoutExpired:
            print("GitHub CLI timed out. Any reserved dispatch will be reconciled.", file=sys.stderr)
            sys.exit(1)
        else:
            if not args.observe and backoff:
                backoff_path(args.state).unlink()


if __name__ == "__main__":
    main()
