"""Record a passing Pi macOS result on the associated owner PR merge commit."""
import json
import os
import re
import subprocess
from pathlib import Path

REPO = "lanej/dotfiles"
OWNER = "lanej"
MAIN = "master"
HOSTED = ".github/workflows/pi-resources.yml"
OVERFLOW = ".github/workflows/mac-overflow.yml"
HOSTED_JOB = "resources (macos-latest)"
NATIVE_STEP = "Discover the shared catalog through native Pi"
RUNNER = "dotfiles-mac-mini"
CONTEXT = "Pi macOS verification"
SHA = re.compile(r"[0-9a-f]{40}")
DISPATCH = re.compile(r"Mac overflow for hosted job ([1-9][0-9]*) at ([0-9a-f]{40})")


def github(endpoint, *args):
    result = subprocess.run(
        ["gh", "api", f"repos/{REPO}/{endpoint}", *args],
        check=True, capture_output=True, text=True,
    )
    return json.loads(result.stdout)


def owner_run(run):
    return (
        (run.get("head_repository") or {}).get("full_name") == REPO
        and run["actor"]["login"] == OWNER
        and run["triggering_actor"]["login"] == OWNER
    )


def successful_steps(job):
    return {step["name"] for step in job["steps"] if step["conclusion"] == "success"}


def current_pull(pull, head, branch, tested):
    return (
        pull["state"] == "open"
        and pull["user"]["login"] == OWNER
        and (pull["head"].get("repo") or {}).get("full_name") == REPO
        and pull["head"]["sha"] == head
        and pull["head"]["ref"] == branch
        and pull["merge_commit_sha"] == tested
        and pull["base"]["repo"]["full_name"] == REPO
        and pull["base"]["ref"] == MAIN
    )


def verification(run, api):
    if not owner_run(run) or run["status"] != "completed":
        return None

    workflow = run["path"]
    if workflow not in {HOSTED, OVERFLOW}:
        return None
    jobs = api(f"actions/runs/{run['id']}/attempts/{run['run_attempt']}/jobs")["jobs"]

    if workflow == HOSTED:
        if run["event"] != "pull_request":
            return None
        job = next((job for job in jobs if job["name"] == HOSTED_JOB), None)
        if (
            job is None
            or job["labels"] != ["macos-latest"]
            or job["conclusion"] != "success"
        ):
            return None
        steps = successful_steps(job)
        commits = {
            match.group(1) for step in steps
            if (match := re.fullmatch(r"Tested merge ([0-9a-f]{40})", step))
        }
        if NATIVE_STEP not in steps or len(commits) != 1:
            return None
        tested = commits.pop()
        hosted = run
    else:
        dispatch = DISPATCH.fullmatch(run["display_title"])
        if (
            run["event"] != "workflow_dispatch" or run["head_branch"] != MAIN
            or dispatch is None or len(jobs) != 1
        ):
            return None
        job = jobs[0]
        if (
            job["name"] != "pi-resources" or job["runner_name"] != RUNNER
            or job["conclusion"] != "success"
            or "Verify native Pi resources" not in successful_steps(job)
        ):
            return None
        hosted_job_id, tested = dispatch.groups()
        hosted_job = api(f"actions/jobs/{hosted_job_id}")
        if hosted_job["name"] != HOSTED_JOB or hosted_job["labels"] != ["macos-latest"]:
            return None
        hosted = api(f"actions/runs/{hosted_job['run_id']}")
        if hosted["path"] != HOSTED or hosted["event"] != "pull_request" or not owner_run(hosted):
            return None

    head = hosted["head_sha"]
    if not SHA.fullmatch(head):
        return None
    # Actions may omit pull_requests on its run record. Re-query candidates for
    # the recorded head; the matching pull must still point to the tested merge.
    pulls = hosted["pull_requests"] or api(f"commits/{head}/pulls?per_page=100")
    matching_pulls = [
        pull for association in pulls
        if current_pull(
            pull := api(f"pulls/{association['number']}"),
            head, hosted["head_branch"], tested,
        )
    ]
    if len(matching_pulls) != 1:
        return None
    commit = api(f"commits/{tested}")
    # A PR payload may still show an older base after the target branch moves.
    base = api(f"git/ref/heads/{MAIN}")["object"]["sha"]
    if [parent["sha"] for parent in commit["parents"]] != [base, head]:
        return None
    return head, base, tested, job["html_url"]


def main(event, api=github):
    result = verification(event["workflow_run"], api)
    if result is None:
        print("No passing Pi macOS job for a current owner PR merge commit.")
        return
    head, base, tested, url = result
    api(
        f"statuses/{tested}", "--method", "POST",
        "-f", "state=success", "-f", f"context={CONTEXT}",
        "-f", f"target_url={url}",
        "-f", f"description=base={base} merge={tested}",
    )
    print(f"Recorded Pi macOS verification for {head} at merge commit {tested}.")


if __name__ == "__main__":
    try:
        main(json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text()))
    except subprocess.CalledProcessError as error:
        raise SystemExit(error.stderr.strip()) from error

# Temporary offline Pi verification canary.
