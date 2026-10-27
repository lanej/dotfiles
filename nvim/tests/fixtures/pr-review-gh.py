# /// script
# dependencies = []
# ///
"""Controlled gh boundary for the workflow detector; never connects to GitHub."""
import json
import os
from pathlib import Path
import re
import sys
import time

root = Path(os.environ["PR_REVIEW_FIXTURE"])
args = sys.argv[1:]
payload = json.load(sys.stdin) if "--input" in args else {}
query = payload.get("query", "")
variables = payload.get("variables", {})
fields = {}
for i, arg in enumerate(args):
    if arg in ("-f", "-F", "--field", "--raw-field"):
        key, value = args[i + 1].split("=", 1)
        fields[key] = value
query = query or fields.get("query", "")
mode = (root / "mode").read_text().strip()
account = (root / "account").read_text().strip() if (root / "account").exists() else "reviewer"
head = (root / "head").read_text().strip() if (root / "head").exists() else "a" * 40
if mode == "repeat-review":
    head = "d" * 40
review_id = "REVIEW2" if mode == "repeat-review" else "REVIEW1"
base = "b" * 40
cursor = {"hasNextPage": False, "endCursor": None}
connection = lambda nodes: {"nodes": nodes, "pageInfo": cursor, "totalCount": len(nodes)}


def emit(value):
    print(json.dumps(value, ensure_ascii=False))
    sys.exit(0)


def fail(message):
    print(message, file=sys.stderr)
    sys.exit(1)


def pr(number, title, date="2020-01-01T00:00:00Z", author="other", draft=False):
    return {
        "id": f"PR{number}", "number": number, "title": title,
        "body": f"Description of {title}", "url": f"https://github.com/example/repo/pull/{number}",
        "createdAt": date, "headRefOid": head, "isDraft": draft, "state": "OPEN",
        "author": {"login": author}, "repository": {"nameWithOwner": "example/repo"},
    }


def check_node(number, after=None):
    checks = [{"name": "tests", "status": "COMPLETED", "conclusion": "SUCCESS", "checkSuite": None}]
    page = cursor
    if number == 1:
        if not after:
            checks += [{"name": "check-all-owners", "status": "COMPLETED", "conclusion": "FAILURE",
                        "checkSuite": {"workflowRun": {"workflow": {"name": "Require All Owners Approval"}}}}]
            page = {"hasNextPage": True, "endCursor": "checks2"}
        else:
            checks = [{"context": "external-ci", "state": "SUCCESS", "targetUrl": "https://example.invalid/ci"}]
    elif number == 2:
        checks = [{"name": "optional", "status": "COMPLETED", "conclusion": "SKIPPED", "checkSuite": None},
                  {"name": "lint", "status": "COMPLETED", "conclusion": "NEUTRAL", "checkSuite": None}]
    elif number == 3:
        checks[0].update(status="IN_PROGRESS", conclusion=None)
    elif number == 4:
        checks[0].update(name="check-all-owners", conclusion="FAILURE",
                         checkSuite={"workflowRun": {"workflow": {"name": "Other workflow"}}})
    elif number == 7:
        checks = []
    return {"headRefOid": head, "commits": {"nodes": [{"commit": {
        "statusCheckRollup": {"contexts": {"nodes": checks, "pageInfo": page}}}}]}}


def review_node(pr_id, after=None):
    nodes = []
    page = cursor
    if pr_id == "PR9" or (pr_id == "PR1" and (root / "submitted").exists()):
        reviewed_head = (root / "submitted").read_text().strip() if pr_id == "PR1" else head
        nodes = [{"state": "COMMENTED", "submittedAt": "2026-01-01T00:00:00Z", "commit": {"oid": reviewed_head}}]
    elif pr_id == "PR1" and not after:
        nodes = [{"state": "COMMENTED", "submittedAt": "2026-01-01T00:00:00Z", "commit": {"oid": base}}]
        page = {"hasNextPage": True, "endCursor": "reviews2"}
    return {"headRefOid": head, "reviews": {"nodes": nodes, "pageInfo": page}}


first = pr(1, "first request")
team = pr(2, "team passing", "2019-01-01T00:00:00Z")
pending = pr(3, "pending request")
failed = pr(4, "failed request")
missing = pr(7, "missing checks")
unknown = pr(8, "unknown checks")
reviewed = pr(9, "already reviewed")
newer = pr(10, "newer personal", "2021-01-01T00:00:00Z")
foreign = dict(pr(11, "another repository", "2022-01-01T00:00:00Z"),
               repository={"nameWithOwner": "another/project"},
               url="https://github.com/another/project/pull/11")

comment = {
    "id": "COMMENT1", "body": "Inline feedback", "diffHunk": "@@ -1,3 +1,3 @@\n-old\n+new\n context\n context2",
    "createdAt": "2026-01-01T00:00:00Z", "lastEditedAt": None,
    "commit": {"oid": head, "abbreviatedOid": head[:7]},
    "originalCommit": {"oid": head, "abbreviatedOid": head[:7]},
    "author": {"login": "reviewer"}, "authorAssociation": "NONE",
    "viewerDidAuthor": True, "viewerCanUpdate": True, "viewerCanDelete": True,
    "state": "PENDING", "url": "https://github.com/example/repo/pull/1#discussion_r1",
    "replyTo": None, "pullRequestReview": {"id": "REVIEW1", "state": "PENDING"},
    "path": "sample.txt", "reactionGroups": [],
}
thread = {
    "id": "THREAD1", "originalStartLine": None, "originalLine": 1, "startLine": None,
    "line": 1, "startDiffSide": None, "diffSide": "RIGHT", "path": "sample.txt",
    "isOutdated": False, "isResolved": False, "isCollapsed": False,
    "comments": {"nodes": [comment]},
}
threads = [thread] if (root / "inline-saved").exists() else []
if mode == "repeat-review":
    threads = []

if args[:2] == ["auth", "status"]:
    print("Logged in to github.com account reviewer\nToken scopes: 'repo', 'read:org'")
    sys.exit(0)

if args[:2] == ["repo", "view"]:
    if args[2] != "https://github.com:443/example/repo.git":
        fail("Repository fallback did not select the explicit origin")
    if os.environ.get("GH_REPO"):
        fail("Repository fallback inherited GH_REPO")
    emit({"nameWithOwner": "example/repo", "url": "https://github.com/example/repo"})

if query:
    with (root / "requests").open("a") as log:
        log.write(json.dumps({"query": query, "variables": variables, "fields": fields}) + "\n")
    if "PRReviewSearch" in query:
        if (root / "slow-discovery").exists():
            time.sleep(0.5)
        personal = "user-review-requested:" in variables["query"]
        if not personal and "team-review-requested-user:" not in variables["query"]:
            fail("Unsupported review-request qualifier")
        restriction = re.search(r"repo:([^ ]+)", variables["query"])
        def restricted(nodes):
            return [node for node in nodes if not restriction
                    or node["repository"]["nameWithOwner"].lower() == restriction[1]]
        total = len(restricted([first, newer, reviewed, pending, foreign,
                               pr(5, "own request", author=account), pr(6, "draft request", draft=True)]))
        if personal and not variables.get("cursor"):
            nodes = restricted([first, newer, reviewed, foreign, pr(5, "own request", author=account), pr(6, "draft request", draft=True)])
            emit({"data": {"search": {"nodes": nodes, "issueCount": total,
                                      "pageInfo": {"hasNextPage": True, "endCursor": "page2"}}}})
        nodes = restricted([pending] if personal else [first, team, failed, missing, unknown])
        emit({"data": {"search": {"nodes": nodes, "issueCount": total if personal else len(nodes), "pageInfo": cursor}}})
    if "PRReviewBatch" in query:
        # Omit an unavailable node so fallback isolates its failed checks.
        nodes = [dict(check_node(int(pr_id[2:])), **review_node(pr_id), id=pr_id)
                 for pr_id in variables["ids"] if pr_id != "PR8"]
        emit({"data": {"nodes": nodes}})
    if "PRReviewChecks" in query:
        number = int(variables["id"][2:])
        if number == 8:
            fail("Checks unavailable")
        emit({"data": {"node": check_node(number, variables.get("cursor"))}})
    if "PRReviewHistory" in query:
        emit({"data": {"node": review_node(variables["id"], variables.get("cursor"))}})
    if "submitPullRequestReview(input:" in query:
        match = re.search(r'pullRequestReviewId:\s*"([^"]+)".*?event:\s*(\w+).*?body:\s*"""(.*?)"""', query, re.S)
        if not match:
            fail("Native Octo submission could not be decoded")
        review, event, body = match.groups()
        with (root / "attempts").open("a") as log:
            log.write(json.dumps({"review": review, "event": event, "body": body}) + "\n")
        if mode == "submit-rejected":
            fail("Review submission rejected")
        if review != review_id or not (root / "inline-saved").exists():
            fail("Submission lost the pending review or inline feedback")
        (root / "submitted").write_text(head)
        state = {"APPROVE": "APPROVED", "COMMENT": "COMMENTED", "REQUEST_CHANGES": "CHANGES_REQUESTED"}[event]
        emit({"data": {"submitPullRequestReview": {"pullRequestReview": {
            "id": review, "state": state}}}})
    if "addPullRequestReviewThread(" in query:
        (root / "inline-saved").write_text("yes")
        saved_thread = dict(thread, pullRequest={"reviewThreads": {"nodes": [thread]}})
        emit({"data": {"addPullRequestReviewThread": {"thread": saved_thread}}})
    if "addPullRequestReview(input:" in query:
        emit({"data": {"addPullRequestReview": {"pullRequestReview": {
            "id": review_id, "state": "PENDING", "pullRequest": {"reviewThreads": {"nodes": threads}}}}}})
    if "reviews(first: 100, states: PENDING)" in query:
        emit({"data": {"repository": {"pullRequest": {
            "reviews": {"nodes": []}, "reviewThreads": {"nodes": threads}}}}})
    if "expression:" in query or "$expression" in query:
        print(("old" if fields.get("expression", "").startswith(base) else "new") + "\ncontext\ncontext2")
        sys.exit(0)
    if "pullRequest(number:" in query and "timelineItems" in query:
        number = int(re.search(r"pullRequest\(number:\s*(\d+)", query)[1])
        node = first if number == 1 else newer
        node = dict(node, lastEditedAt=None, includesCreatedEdit=False, closedAt=None,
                    updatedAt=node["createdAt"], headRepository={"nameWithOwner": "example/repo"},
                    closingIssuesReferences=connection([]), files=connection([{"path": "sample.txt", "viewerViewedState": "UNVIEWED"}]),
                    merged=False, mergedBy=None, participants=connection([]), additions=1, deletions=1,
                    commits={"totalCount": 1}, changedFiles=1, headRefName="feature", headRef={"id": "REF1"},
                    baseRefName="main", baseRefOid=base, baseRepository={"name": "repo", "nameWithOwner": "example/repo"},
                    milestone=None, authorAssociation="NONE", viewerDidAuthor=False, viewerCanUpdate=False,
                    viewerCanSubscribe=True, viewerSubscription="UNSUBSCRIBED", reactionGroups=[],
                    timelineItems=connection([]), reviewDecision="REVIEW_REQUIRED", reviewThreads=connection(threads),
                    labels=connection([]), assignees=connection([]), reviewRequests=connection([]),
                    statusCheckRollup=None, isInMergeQueue=False, stackEntry=None)
        emit({"data": {"repository": {"pullRequest": node}}})
    if "issues(" in query or "issues (" in query:
        emit({"data": {"repository": {"issues": connection([])}}})
    fail("Unhandled GraphQL query: " + query[:160])

endpoint = next((arg for arg in args if arg == "user" or arg.startswith(("user/", "repos/", "/repos/"))), "")
if endpoint == "user":
    emit({"login": account})
if endpoint.startswith("user/teams"):
    fail("Discovery must use GitHub team-review-requested-user search")
if "/contributors" in endpoint:
    emit([])
if "/compare/" in endpoint:
    print(base)
    sys.exit(0)
if endpoint.endswith("/files"):
    files = [{"filename": "sample.txt", "patch": "@@ -1,3 +1,3 @@\n-old\n+new\n context\n context2", "status": "modified",
              "additions": 1, "deletions": 1, "changes": 2}]
    emit([files] if "--slurp" in args else files)
if "/pulls/" in endpoint:
    print("diff --git a/sample.txt b/sample.txt\nindex 0000000..1111111 100644\n--- a/sample.txt\n+++ b/sample.txt\n@@ -1,3 +1,3 @@\n-old\n+new\n context\n context2")
    sys.exit(0)
fail("Unhandled gh invocation: " + repr(args))
