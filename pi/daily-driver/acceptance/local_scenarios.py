"""Independently runnable native Pi acceptance scenarios."""

from __future__ import annotations

import json
import re
import shlex
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, TypedDict

from local_fixture import Allocation, Fixture, Report, Scenario, TaskSnapshot
from local_provider import Provider
from socrates_fixture import ARCHIVE, RECEIPT
from zellij_terminal import Terminal


class RecordedAnswer(TypedDict):
    kind: str
    text: str


class ExchangeAnswer(TypedDict, total=False):
    answer: RecordedAnswer


class QuestionEvidence(TypedDict):
    decisionId: str


class PendingExchange(ExchangeAnswer):
    prompt: QuestionEvidence


class DecisionEvidence(TypedDict):
    evidence: str


class DraftEvidence(TypedDict):
    decisions: list[DecisionEvidence]
    blockingQuestions: list[str]


class Specification(TypedDict, total=False):
    draft: DraftEvidence | None
    exchange: PendingExchange
    acceptedRevision: str
    status: str


class ApprovedPlan(TypedDict):
    digest: str
    children: dict[str, str]


@dataclass(frozen=True)
class ResumedLead:
    id: str
    pane: int
    checkout: Allocation
    head: str


@dataclass(frozen=True)
class Case:
    harness: Fixture
    terminal: Terminal
    scenario: Scenario
    launcher: int
    bead: str
    pane: int
    before: TaskSnapshot
    start_command: str

    def capture(self, pane: int) -> str:
        return self.terminal.capture_pane(pane, full=True)

    def snapshot(self) -> TaskSnapshot:
        return self.harness.fresh(self.bead)

    def specification(self) -> Specification:
        spec: Specification = self.snapshot()["attempt"].get("specification", {})
        return spec

    def exit_pi(self, description: str) -> None:
        self.terminal.write_to_pane(self.pane, 4)
        self.terminal.until(description, lambda: all(
            p["id"] != self.pane or p["exited"] for p in self.terminal.terminals()
        ))


def launch(
    harness: Fixture, terminal: Terminal, launcher_pane: int, tab_id: int, scenario: Scenario,
) -> Case:
    work, repository = harness.options.work, harness.options.repository
    execute, driver = harness.execute, harness.driver

    created = json.loads(execute([
        harness.options.bd, "--sandbox", "create", "--title", f"Native Pi {scenario.value}",
        "--description", "Original bounded acceptance brief", "--type", "task", "--json",
        "--acceptance", "The agreed verifier must pass and preserve the accepted Git state",
    ]).stdout)
    bead = created["id"]
    exit_file = work / f"{scenario.value}.exit"
    verifier = ["/bin/sh", "-c", "printf 'native-check-evidence\\n'; exit " +
                ("7" if scenario == "failed-check" else "0")]
    placement = ["--tab-id", str(tab_id)] if scenario == "accepted" else []
    worker_flag = ["--worker"] if scenario in (Scenario.ACCEPTED, Scenario.FAILED_CHECK, Scenario.CHANGED_BRIEF) else []
    start_command = shlex.join([driver, "start", bead, "--profile", "personal", *worker_flag,
                                *placement, "--", *verifier])
    command = f"cd {shlex.quote(str(repository))} && {start_command}; printf '%s' $? > {shlex.quote(str(exit_file))}"
    assert any(p["id"] == launcher_pane for p in terminal.terminals()), "Owned launcher disappeared"
    terminal.send_to_pane(launcher_pane, command + "\r")
    try:
        terminal.until("start dispatch completes", exit_file.exists)
    except AssertionError as error:
        panes = {pane["id"]: terminal.capture_pane(pane["id"], full=True)
                 for pane in terminal.terminals()}
        raise AssertionError(f"Worker dispatch timed out. Pane output: {panes}") from error
    assert exit_file.read_text() == "0", terminal.capture_pane(launcher_pane, full=True)
    assert any(p["id"] == launcher_pane and p["is_focused"]
               for p in terminal.terminals()), terminal.terminals()
    before = harness.fresh(bead)
    assert before["attempt"]["phase"] == "running", before
    assert before["attempt"]["session"] == harness.name, before
    assert Path(before["attempt"]["checkout"]["path"]).resolve().is_relative_to(
        repository.resolve() / ".worktrees"), before
    harness.allocations.append(before["attempt"]["checkout"])
    pane = before["attempt"]["pane"]
    assert pane != launcher_pane, before
    return Case(harness, terminal, scenario, launcher_pane, bead, pane, before, start_command)


def wait_for_lead(case: Case) -> None:
    terminal, bead, pane = case.terminal, case.bead, case.pane
    fresh, pane_text = case.harness.fresh, case.capture
    terminal.until("read-only lead drafts plan", lambda:
                   fresh(bead)["attempt"].get("leadPlan", {}).get("draft") is not None)
    assert "pi.plan" not in fresh(bead)["task"]["metadata"], fresh(bead)
    terminal.until("lead footer groups the bead, mode and model", lambda:
                   any(bead in line and "◇" in line and "▣" in line and "⊛ 6.1 \uE30D" in line and "personal" not in line
                       for line in pane_text(pane).splitlines()))
    terminal.until("footer observes the linked worktree", lambda:
                   any("▣ " in line and "⊛ 6.1 \uE30D" in line for line in pane_text(pane).splitlines()))
    terminal.focus_pane(pane)


def exercise_selector(case: Case) -> None:
    terminal, pane = case.terminal, case.pane
    artifacts = case.harness.artifacts

    def view() -> str:
        return terminal.capture_pane(pane)

    terminal.until("focused choice shows its explanation", lambda:
                   "│" in view() and "Retry in the same checkout" in view())
    terminal.send_to_pane(pane, "j")
    terminal.until("j moves focus and updates the explanation", lambda:
                   "→ Remove it" in view() and "Recover from the saved" in view())
    assert "answer" not in case.specification()["exchange"]
    terminal.send_to_pane(pane, "k")
    terminal.until("k restores the first choice and explanation", lambda:
                   f"→ {ARCHIVE.answer}" in view() and "Retry in the same checkout" in view())
    terminal.send_to_pane(pane, "l")
    terminal.until("choice details open with question context", lambda:
                   "Keeping the checkout preserves" in view() and "Octo has confirmed the merge" in view()
                   and "Run archive --retry" in view() and "retention check" in view())
    assert "**the exact worktree**" not in view() and "`archive --retry`" not in view()
    assert "https://example.com/retention" not in view()
    assert "h back" not in view() and "j/k scroll" not in view()
    (artifacts / "socrates-details.ansi").write_text(terminal.capture_pane(pane, ansi=True))
    terminal.send_to_pane(pane, "\r")
    assert "answer" not in case.specification()["exchange"]
    for _ in range(35):
        if "The retry fixture exited with status 7." in view():
            break
        terminal.send_to_pane(pane, "j")
    terminal.until("details scroll to evidence links", lambda:
                   "Recovery procedure" in view() and "Archive report" in view()
                   and "Fixture source · README.md:1" in view()
                   and "The retry fixture exited with status 7." in view())
    terminal.send_to_pane(pane, "h")
    terminal.until("h restores the original focused choice", lambda: f"→ {ARCHIVE.answer}" in view())

    terminal.send_to_pane(pane, ";")
    terminal.until("hints appear beside all three choices", lambda:
                   "a Keep the checkout ▸" in view() and "s Remove it" in view() and "d Type an answer" in view())
    assert all(line not in view() for line in ("j/k move", "Type hint to jump", "l details"))
    (artifacts / "socrates-hints.txt").write_text(view())
    (artifacts / "socrates-hints.ansi").write_text(terminal.capture_pane(pane, ansi=True))
    terminal.write_to_pane(pane, 27)
    terminal.until("Escape exits hint mode without dismissing the question", lambda:
                   f"→ {ARCHIVE.answer}" in view() and "d Type an answer" not in view())
    terminal.send_to_pane(pane, ";")
    terminal.until("hint mode reopens", lambda: "d Type an answer" in view())
    terminal.send_to_pane(pane, "d")
    terminal.until("completed hint jumps to free text", lambda: "→ Type an answer" in view())
    assert "answer" not in case.specification()["exchange"]
    terminal.send_to_pane(pane, "\r")
    terminal.until("Enter opens the free-text editor", lambda:
                   "submit" in view() and "Octo has confirmed the merge" in view())


def exercise_question_exchange(case: Case) -> None:
    terminal, pane = case.terminal, case.pane
    artifacts = case.harness.artifacts

    spec = case.specification

    terminal.until("Socrates stops after saving the open decision", lambda:
                   (draft := spec().get("draft")) is not None and draft["blockingQuestions"] == [ARCHIVE.question]
                   and "ACK_TOOL_SUBMITTED" in terminal.capture_pane(pane))
    assert "exchange" not in spec()
    terminal.send_to_pane(pane, "/socrates\r")
    terminal.until("Socrates choice dialog", lambda:
                   ARCHIVE.question in " ".join(terminal.capture_pane(pane).split()) and ARCHIVE.answer in terminal.capture_pane(pane))
    first = spec()["exchange"]
    assert first["prompt"]["decisionId"] == ARCHIVE.id and "answer" not in first, first
    (artifacts / "socrates-question.txt").write_text(terminal.capture_pane(pane))
    (artifacts / "socrates-question.ansi").write_text(
        terminal.capture_pane(pane, ansi=True))
    exercise_selector(case)
    terminal.write_to_pane(pane, 27)
    terminal.until("question stays open after Escape", lambda:
                   "Question remains open" in case.capture(pane))
    assert spec()["exchange"] == first
    terminal.send_to_pane(pane, "/spec-freeze\r")
    terminal.until("open question blocks freeze", lambda:
                   "Resolve the blocking questions" in terminal.capture_pane(pane))
    terminal.send_to_pane(pane, "/socrates\r")
    terminal.until("same original choice reopened", lambda: ARCHIVE.answer in terminal.capture_pane(pane))
    terminal.send_to_pane(pane, "j")
    terminal.until("next choice retains focus until a hint jumps", lambda: "→ Remove it" in terminal.capture_pane(pane))
    terminal.send_to_pane(pane, ";")
    terminal.until("first choice has a visible hint", lambda: "a Keep the checkout" in terminal.capture_pane(pane))
    terminal.send_to_pane(pane, "a")
    terminal.until("preset jump restores focus without submitting", lambda: f"→ {ARCHIVE.answer}" in terminal.capture_pane(pane))
    assert "answer" not in spec()["exchange"]
    terminal.send_to_pane(pane, "\r")
    terminal.until("selected answer persisted without applying it", lambda:
                   (exchange := spec().get("exchange")) is not None and exchange.get("answer") ==
                   {"kind": "option", "text": ARCHIVE.answer}
                   and "ACK_ACCEPTED_CONTEXT" in terminal.capture_pane(pane))
    terminal.send_to_pane(pane, "/socrates\r")
    terminal.until("free-text question follows recovered answer", lambda:
                   RECEIPT.question in terminal.capture_pane(pane) and
                   "operator needs to know" in terminal.capture_pane(pane) and
                   "Receipt instructions" in terminal.capture_pane(pane) and
                   (exchange := spec().get("exchange")) is not None and exchange["prompt"]["decisionId"] == RECEIPT.id)
    case.harness.update_bead(case.bead, "--acceptance", "Verify the revised Socrates receipt")
    terminal.send_to_pane(pane, "An answer against the old brief.\r")
    terminal.until("stale answer is rejected", lambda:
                   "accepted brief, revision or owner changed" in " ".join(case.capture(pane).split()))
    assert "answer" not in spec()["exchange"], spec()
    old_revision = spec()["acceptedRevision"]
    terminal.send_to_pane(pane, "/plan-refresh\r")
    terminal.until("free-text question reevaluated against new revision", lambda:
                   RECEIPT.question in terminal.capture_pane(pane) and
                   spec()["acceptedRevision"] != old_revision and
                   (exchange := spec().get("exchange")) is not None and exchange["prompt"]["decisionId"] == RECEIPT.id)
    terminal.send_to_pane(pane, RECEIPT.answer + "\r")
    terminal.until("typed answer incorporated into the draft", lambda:
                   (current := spec()).get("exchange") is None and
                   (draft := current.get("draft")) is not None and not draft["blockingQuestions"] and
                   draft["decisions"][-1]["evidence"] == RECEIPT.answer)

    checkout = Path(case.before["attempt"]["checkout"]["path"]).resolve()
    for url in (
        (checkout / "README.md").as_uri() + "#L1",
        "https://example.com/recovery",
        "https://example.com/retention",
        "https://github.com/fixture/repo/issues/7",
        "https://github.com/fixture/repo/issues/8",
        "https://github.com/fixture/repo/issues/9",
    ):
        target = rb"\x1b\]8;[^;]*;" + re.escape(url.encode()) + rb"(?:\x07|\x1b\\)"
        assert re.search(target, terminal.output), f"Missing OSC 8 link for {url}"


def freeze_specification(case: Case, *, interview: bool) -> None:
    terminal, bead, pane = case.terminal, case.bead, case.pane

    spec = case.specification

    terminal.send_to_pane(pane, "/socrates\r")
    if interview:
        exercise_question_exchange(case)
    else:
        terminal.until("complete brief reaches a draft without a question", lambda:
                       (draft := spec().get("draft")) is not None and not draft["blockingQuestions"])
        assert "exchange" not in spec()
    assert "pi.plan" not in case.snapshot()["task"]["metadata"]
    terminal.send_to_pane(pane, "/spec-freeze\r")
    terminal.until("specification review opens", lambda:
                   "Freeze specification for " + bead in case.capture(pane))
    terminal.send_to_pane(pane, "\r")
    terminal.until("frozen specification has a plan", lambda:
                   spec().get("status") == "frozen" and
                   case.snapshot()["attempt"]["leadPlan"]["draft"] is not None)


def approve_lead_plan(case: Case) -> ApprovedPlan:
    terminal, bead, pane = case.terminal, case.bead, case.pane
    fresh, pane_text = case.harness.fresh, case.capture
    execute, driver = case.harness.execute, case.harness.driver
    terminal.send_to_pane(pane, "/diff\r")
    terminal.until("review extension renders", lambda: "Git diff" in pane_text(pane))
    terminal.write_to_pane(pane, 27)
    terminal.until("review viewer closes", lambda: "Git diff" not in
                   terminal.capture_pane(pane))
    terminal.send_to_pane(pane, "/plan-approve\r")
    terminal.until("operator approval prompt", lambda: "Approve the plan for " + bead in pane_text(pane))
    for _ in range(8):
        if "Enter start implementation" in terminal.capture_pane(pane):
            break
        terminal.send_to_pane(pane, "\r")
    else:
        raise AssertionError(pane_text(pane))
    terminal.send_to_pane(pane, "\r")
    terminal.until("approved task breakdown persisted", lambda:
                   fresh(bead)["attempt"]["leadPlan"]["mode"] == "implementing")
    approved = fresh(bead)
    plan: ApprovedPlan = approved["attempt"]["leadPlan"]
    assert approved["task"]["metadata"]["pi.plan"] == plan["digest"], approved
    assert len(set(plan["children"].values())) == 2, approved
    for key, child in plan["children"].items():
        task = fresh(child)["task"]
        assert task["metadata"]["pi.plan_key"] == key, task
        assert task["metadata"]["pi.plan"] == plan["digest"], task
    tree = json.loads(execute([driver, "tasks", "--json"]).stdout)["tasks"]
    views = {task["id"]: task for task in tree}
    for child in plan["children"].values():
        assert any(edge["id"] == bead and edge["dependency_type"] == "parent-child"
                   for edge in views[child]["dependencies"]), views[child]
    assert any(edge["id"] == plan["children"]["inspect"] and edge["dependency_type"] == "blocks"
               for edge in views[plan["children"]["verify"]]["dependencies"])
    terminal.send_to_pane(pane, "/plan-approve\r")
    terminal.until("second approval refused", lambda: "No draft to approve" in pane_text(pane))
    assert fresh(bead)["attempt"]["leadPlan"] == plan
    return plan


def verify_lead(case: Case) -> TaskSnapshot:
    terminal, bead, pane = case.terminal, case.bead, case.pane
    fresh, pane_text = case.harness.fresh, case.capture
    terminal.send_to_pane(pane, "/task-submit Acceptance lead verification at src/driver.ts:12 "
                    "https://github.com/fixture/repo/blob/main/src/driver.ts#L12\r")
    terminal.until("lead verification persisted", lambda:
                   fresh(bead)["attempt"]["phase"] == "verified")
    verified = fresh(bead)
    assert verified["task"]["status"] == "in_progress", verified
    assert verified["attempt"]["verification"]["exitCode"] == 0, verified
    terminal.until("verification event is collapsed", lambda:
                   f"▸ ● Verification passed · {bead}" in pane_text(pane))
    terminal.write_to_pane(pane, 15)
    terminal.until("verification expands typed code links", lambda:
                   "‹›" in pane_text(pane) and "driver.ts:12" in pane_text(pane) and
                   "▾ ● Verification passed" in pane_text(pane))
    terminal.write_to_pane(pane, 15)
    terminal.until("verification folds again", lambda:
                   f"▸ ● Verification passed · {bead}" in pane_text(pane))
    return verified


def check_refreshed_plan(case: Case, plan: ApprovedPlan, verified: TaskSnapshot) -> None:
    terminal, bead, pane = case.terminal, case.bead, case.pane
    fresh, pane_text = case.harness.fresh, case.capture
    execute, driver = case.harness.execute, case.harness.driver
    work = case.harness.options.work
    case.harness.update_bead(bead, "--acceptance", "Verify the revised criteria before delivery")
    terminal.send_to_pane(pane, "/plan-refresh\r")
    terminal.until("refreshed brief invalidates evidence", lambda:
                   fresh(bead)["attempt"]["verification"] is None)
    refreshed = fresh(bead)
    assert refreshed["attempt"]["phase"] == "running", refreshed
    assert refreshed["attempt"]["leadPlan"]["mode"] == "planning", refreshed
    assert refreshed["attempt"]["revision"] != verified["attempt"]["revision"], refreshed
    assert refreshed["attempt"]["revision"] == refreshed["task"]["revision"], refreshed
    terminal.send_to_pane(pane, "/task-submit The old result should not pass\r")
    terminal.until("unapproved verification refused", lambda:
                   "plan before submitting a result" in pane_text(pane))
    draft = work / "refresh-draft.md"
    draft.write_text("Delivery should require new verification.\n")
    publication = execute([driver, "publish", bead, "--title", "feat: verify refreshed brief",
                           "--body-file", str(draft), "--base", "main"], check=False)
    assert publication.returncode != 0 and "Verify the managed lead result" in publication.stderr, publication
    ready = execute([driver, "ready", bead, "--head",
                     verified["attempt"]["verification"]["gitHead"]], check=False)
    assert ready.returncode != 0 and "Verify and commit" in ready.stderr, ready
    assert fresh(bead)["attempt"]["verification"] is None
    terminal.send_to_pane(pane, "Draft a revised plan without new children.\r")
    terminal.until("revised plan drafted", lambda:
                   fresh(bead)["attempt"]["leadPlan"].get("draft") is not None)
    terminal.send_to_pane(pane, "/plan-approve\r")
    terminal.until("revised approval is visible", lambda:
                   "Enter start implementation" in pane_text(pane))
    terminal.send_to_pane(pane, "\r")
    terminal.until("revised plan approved", lambda:
                   fresh(bead)["attempt"]["leadPlan"]["mode"] == "implementing")
    assert fresh(bead)["attempt"]["leadPlan"]["children"] == plan["children"]
    terminal.send_to_pane(pane, "/task-submit Verified against the refreshed brief\r")
    terminal.until("fresh verification persisted", lambda:
                   fresh(bead)["attempt"]["phase"] == "verified")
    assert fresh(bead)["attempt"]["verification"]["summary"] == "Verified against the refreshed brief"


def resume_lead(case: Case) -> ResumedLead:
    terminal, bead, launcher_pane = case.terminal, case.bead, case.launcher
    work, driver = case.harness.options.work, case.harness.driver
    fresh, pane_text = case.harness.fresh, case.capture
    original = fresh(bead)["attempt"]
    resume_exit = work / "socrates-resume.exit"
    resume_command = shlex.join([driver, "resume", bead])
    terminal.focus_pane(launcher_pane)
    terminal.send_to_pane(launcher_pane, f"{resume_command}; printf '%s' $? > {shlex.quote(str(resume_exit))}\r")
    terminal.until("resume returns", resume_exit.exists)
    assert resume_exit.read_text() == "0", pane_text(launcher_pane)
    reopened = fresh(bead)["attempt"]
    for key in ("id", "checkout", "transcript", "phase", "specification", "leadPlan"):
        assert reopened[key] == original[key], reopened
    assert reopened["pid"] != original["pid"] and reopened["live"], reopened
    pane = reopened["pane"]
    terminal.until("verification entry survives resume", lambda:
                   f"● Verification passed · {bead}" in pane_text(pane))
    return ResumedLead(reopened["id"], pane, reopened["checkout"], reopened["verification"]["gitHead"])


def install_octo_stub(case: Case, reopened: ResumedLead, receipt_id: str, url: str) -> Path:
    execute, work = case.harness.execute, case.harness.options.work
    guard = case.harness.paths.guard
    head = reopened.head
    reference = work / "origin.git"
    execute(["git", "init", "--bare", str(reference)])
    execute(["git", "remote", "add", "origin", str(reference)])
    execute(["git", "push", "origin", "main"])
    description = work / "description.md"
    description.write_text("Deliver the fixture.\n")
    binding = {
        "id": "fixture-submission", "state": "published",
        "tracking": "active", "url": url,
    }
    octo = guard / "octo-manager"
    octo.write_text(
        "#!/usr/bin/env python3\nimport json, sys\n"
        "args=sys.argv[1:]\n"
        "answers=" + repr({
            ("submit-pr",): binding,
            ("submission",): binding,
            ("agent", "register"): {
                "agent": {"id": "fixture-agent", "harness": "pi",
                          "endpoint": "local", "sessionId": reopened.id},
            },
            ("pr", "show"): {
                "pr": {"id": "fixture-pr", "url": url, "ownerAgentId": "fixture-agent",
                       "observation": {"headSha": head, "lifecycle": "merged",
                                       "targetBase": {"ref": "main"}}},
            },
            ("agent", "inbox"): {
                "messages": [{"id": receipt_id, "recipientAgentId": "fixture-agent",
                              "workflowPrId": "fixture-pr", "actionId": "",
                              "applicable": True, "body": "Fixture ready https://github.com/fixture/repo/issues/7", "readyHead": head}],
                "nextSequence": 1, "hasMore": False,
            },
            ("acknowledge-message",): {"message": receipt_id, "applicable": True},
            ("merge",): {"state": "merged", "pr": url, "entry": "fixture-entry", "chain": "fixture-chain"},
            ("chain", "show"): {"entries": [{
                "id": "fixture-entry", "chainId": "fixture-chain", "prId": "fixture-pr",
                "state": "merged", "mergeCommit": head, "ready": {"head": head},
                "receiptId": f"pi-inbox:{receipt_id}:{head}",
            }]},
        }) + "\n"
        "if args[0] in ('submit-pr', 'merge'):\n"
        " assert args[args.index('--expected-head')+1] == " + repr(head) + "\n"
        "print(json.dumps(answers.get(tuple(args[:2])) or answers[(args[0],)]))\n"
    )
    octo.chmod(0o755)
    return description


def deliver_and_archive(case: Case, plan: ApprovedPlan) -> None:
    reopened = resume_lead(case)
    pane, checkout, head = reopened.pane, reopened.checkout, reopened.head
    receipt_id = "00000000-0000-4000-8000-000000000171"
    description = install_octo_stub(
        case, reopened, receipt_id, "https://github.com/fixture/repo/pull/1",
    )
    terminal, bead, pane_text = case.terminal, case.bead, case.capture
    fresh, execute, driver = case.harness.fresh, case.harness.execute, case.harness.driver
    artifacts, allocations = case.harness.artifacts, case.harness.allocations
    execute([driver, "publish", bead, "--title", "feat: deliver fixture",
             "--body-file", str(description), "--base", "main"])
    terminal.focus_pane(pane)
    for _ in range(2):
        terminal.send_to_pane(pane, "/octo-inbox\r")
        terminal.until("Octo inbox shows typed PR and issue links", lambda:
                       " fixture/repo#1" in pane_text(pane) and "! fixture/repo#7" in pane_text(pane))
        terminal.write_to_pane(pane, 27)
        terminal.until("Octo receipt renders in the transcript", lambda:
                       "Octo receipt ·  fixture/repo#1" in pane_text(pane))
    terminal.until("Octo inbox closes", lambda: "Fixture ready" not in
                   terminal.capture_pane(pane))
    terminal.until("footer shows the tracked PR", lambda:
                   any("▣ " in line and " #1" in line and "⊛ 6.1 \uE30D" in line
                       for line in pane_text(pane).splitlines()))
    terminal.write_to_pane(pane, 4)
    terminal.until("resumed Pi exits", lambda: all(p["id"] != pane or p["exited"] for p in terminal.terminals()))
    execute([driver, "merge", bead, "--head", head, "--notice", receipt_id])
    pending = execute([driver, "archive", bead], check=False)
    assert pending.returncode != 0 and "Settle child beads" in pending.stderr, pending
    assert Path(checkout["path"]).exists() and fresh(bead)["task"]["status"] == "in_progress"
    for child in (plan["children"]["inspect"], plan["children"]["verify"]):
        execute([case.harness.options.bd, "--sandbox", "close", child])
    archived = json.loads(execute([driver, "archive", bead]).stdout)
    assert archived["phase"] == "archived", archived
    assert not Path(checkout["path"]).exists(), archived
    assert fresh(bead)["task"]["status"] == "closed"
    manifest = Path(archived["archiveManifest"])
    transcript = manifest.with_name(reopened.id + ".jsonl")
    assert manifest.is_file() and transcript.is_file()
    entries = [json.loads(line) for line in transcript.read_text().splitlines()]
    events = [entry["data"] for entry in entries if entry["type"] == "custom" and
              entry.get("customType") == "pi-driver:transcript-event"]
    assert len(events) == 3, events
    assert [(event["kind"], event.get("notice")) for event in events] == [
        ("verification", None), ("octo", None), ("octo", receipt_id),
    ], events
    assert json.loads(execute([driver, "archive", bead]).stdout) == archived
    shutil.copytree(manifest.parent, artifacts / "archive")
    allocations.remove(checkout)


def check_worker_reuse(case: Case, report: Report) -> None:
    terminal, pane, launcher_pane = case.terminal, case.pane, case.launcher
    bead, before, start_command = case.bead, case.before, case.start_command
    pane_text, fresh, execute = case.capture, case.harness.fresh, case.harness.execute
    work, root = case.harness.options.work, case.harness.options.root
    manager, artifacts = case.harness.manager, case.harness.artifacts
    pi = root / "scripts/pi"
    extension = root / "extension.ts"
    browser = shlex.join([str(pi), "--offline", "--no-session", "--no-mcp",
                          "--extension", str(extension), "--model", "openai-codex/gpt-6.1-sol"])
    terminal.send_to_pane(launcher_pane, browser + "\r")
    terminal.until("task browser Pi starts", lambda: "clear/exit" in pane_text(launcher_pane))
    for name, marker in (("SED", "sedMarker"), ("RG", "rgMarker")):
        terminal.send_to_pane(launcher_pane, f"HL_FIXTURE_{name}\r")
        def highlighted_output() -> str | None:
            ansi = terminal.capture_pane(launcher_pane, full=True, ansi=True)
            executable, argument = ("sed", "1,3p") if name == "SED" else ("rg", "--with-filename")
            style = r"\x1b\[[0-9;]*m"
            if not any(
                executable in line and " -n " in re.sub(style, "", line) and argument in line and
                re.search(style, line[line.index(executable):line.index("-n")]) and
                re.search(style, line[line.index("-n"):line.index(argument)])
                for line in ansi.splitlines()
            ):
                return None
            for line in reversed(ansi.splitlines()):
                if marker not in line or "const" not in line:
                    continue
                code = line[line.index("const"):line.index(marker) + len(marker)]
                if re.search(r"\x1b\[[0-9;]*m", code):
                    return ansi
            return None
        terminal.until(f"{name.lower()} emits syntax colors", highlighted_output)
        highlighted = highlighted_output()
        assert highlighted is not None
        (artifacts / f"{name.lower()}-highlighted.ansi").write_text(highlighted)

    terminal.send_to_pane(launcher_pane, "/tasks\r")
    terminal.until("task overlay shows pane focus action", lambda: "Focus pane" in pane_text(launcher_pane))
    terminal.write_to_pane(launcher_pane, 27, 91, 67)
    terminal.until("task tree focuses the managed worker", lambda:
                   any(p["id"] == pane and p["is_focused"] for p in terminal.terminals()))
    terminal.write_to_pane(launcher_pane, 4)
    terminal.until("launcher shell returns", lambda: "local-run-ready>" in
                   terminal.capture_pane(launcher_pane))
    report["registered_process"] = execute(["ps", "-p", str(before["attempt"]["pid"]),
                                            "-o", "command="]).stdout.strip()
    report["registered_pane"] = next(p for p in
        terminal.pane_listing() if p["id"] == pane)
    terminal.focus_pane(launcher_pane)
    repeat_exit = work / "repeated-start.exit"
    repeat_command = f"{start_command}; printf '%s' $? > {shlex.quote(str(repeat_exit))}"
    terminal.send_to_pane(launcher_pane, repeat_command + "\r")
    terminal.until("identical start focuses existing worker", repeat_exit.exists)
    assert repeat_exit.read_text() == "0", pane_text(launcher_pane)
    repeated = fresh(bead)
    for key in ("id", "checkout", "pane", "pid", "transcript", "zellijSocket"):
        assert repeated["attempt"][key] == before["attempt"][key], repeated
    assert any(p["id"] == pane and p["is_focused"] for p in terminal.terminals()), terminal.terminals()
    inventory = json.loads(execute([manager, "status", "--json"]).stdout)
    assert len(inventory["result"]["tasks"]) == 1, inventory
    terminal.send_to_pane(pane, "/driver-profile personal\r")
    terminal.until("managed Pi refuses the lead profile command", lambda:
                   "Set the profile on pi-driver start." in pane_text(pane))
    terminal.send_to_pane(pane, "/model alternate-fixture/different-model\r")
    terminal.until("managed Pi refuses the alternate route", lambda:
                   "Managed Pi requires its admitted model" in pane_text(pane))


def check_worker_submission(case: Case) -> TaskSnapshot:
    terminal, pane, bead = case.terminal, case.pane, case.bead
    scenario = case.scenario.value
    pane_text, fresh = case.capture, case.harness.fresh
    artifacts = case.harness.artifacts
    guidance = f"GUIDANCE_{scenario.replace('-', '_')} for accepted bead {bead}"
    terminal.send_to_pane(pane, guidance + "\r")
    terminal.until("Pi responds to guidance in its original pane", lambda:
                   "ACK_GUIDANCE_" + scenario.replace("-", "_") in pane_text(pane))
    observed = json.dumps(Provider.requests)
    assert bead in observed and "Original bounded acceptance brief" in observed and guidance in observed, observed
    if scenario == "changed-brief":
        case.harness.update_bead(bead, "--description", "Changed acceptance scope while Pi owns the old brief")
    # Both native submission surfaces reach the same guarded verification path.
    terminal.send_to_pane(pane, "SUBMIT_WITH_TOOL_accepted\r" if scenario == "accepted" else
                    f"/task-submit Acceptance {scenario} evidence\r")
    terminal.until("submission persisted", lambda:
                   fresh(bead)["attempt"]["phase"] not in ("running", "checking"))
    submitted = fresh(bead)
    expected = {"accepted": "closed", "failed-check": "check_failed", "changed-brief": "needs_review"}
    assert submitted["projectId"] == case.harness.options.beads["projectId"], submitted
    assert submitted["task"]["id"] == bead == submitted["attempt"]["bead"]["id"], submitted
    assert submitted["attempt"]["phase"] == expected[scenario], submitted
    assert (submitted["task"]["status"] == "closed") == (scenario == "accepted"), submitted
    verification = submitted["attempt"]["verification"]
    if scenario == "changed-brief":
        assert any(word in submitted["attempt"]["message"].lower()
                   for word in ("brief", "revision", "changed")), submitted
        assert submitted["task"]["description"] != submitted["attempt"]["bead"]["description"], submitted
    if scenario != "changed-brief":
        assert verification["exitCode"] == (7 if scenario == "failed-check" else 0), verification
        assert "native-check-evidence" in verification["output"], verification
        assert verification["gitHead"], verification
    if scenario == "accepted":
        assert submitted["task"]["metadata"]["pi.result"] == verification, submitted
        assert submitted["task"]["metadata"]["pi.result_attempt"] == submitted["attempt"]["id"], submitted
        terminal.until("Pi receives native tool result", lambda: "ACK_TOOL_SUBMITTED" in pane_text(pane))
    else:
        assert "pi.result" not in submitted["task"]["metadata"], submitted
    (artifacts / f"{scenario}.screen.txt").write_text(pane_text(pane))
    (artifacts / f"{scenario}.screen.ansi").write_text(
        terminal.capture_pane(pane, full=True, ansi=True))
    # Empty-editor Ctrl-D exits Pi; retain its caller shell for the next independent bead.
    case.exit_pi("Pi exit")
    after_exit = fresh(bead)
    assert after_exit["attempt"]["verification"] == verification, after_exit
    assert after_exit["attempt"]["phase"] == expected[scenario], after_exit
    return after_exit


def wait_for_worker(case: Case) -> None:
    case.terminal.until("the admitted provider responded", lambda:
                        "ACK_ACCEPTED_CONTEXT" in case.capture(case.pane))


def accepted(case: Case, report: Report) -> TaskSnapshot:
    wait_for_worker(case)
    check_worker_reuse(case, report)
    return check_worker_submission(case)


def failed_check(case: Case, _report: Report) -> TaskSnapshot:
    wait_for_worker(case)
    after_exit = check_worker_submission(case)
    stale_exit = case.harness.options.work / "stale-start.exit"
    stale_start = f"{case.start_command}; printf '%s' $? > {shlex.quote(str(stale_exit))}"
    case.terminal.send_to_pane(case.launcher, stale_start + "\r")
    case.terminal.until("exited worker rejects refocus", stale_exit.exists)
    assert stale_exit.read_text() != "0", case.capture(case.launcher)
    assert "registered Pi process or pane has exited or changed" in case.capture(case.launcher)
    assert case.snapshot()["attempt"] == after_exit["attempt"]
    return after_exit


def changed_brief(case: Case, _report: Report) -> TaskSnapshot:
    wait_for_worker(case)
    return check_worker_submission(case)


def lead_plan(case: Case, _report: Report) -> TaskSnapshot:
    wait_for_lead(case)
    plan = approve_lead_plan(case)
    verified = verify_lead(case)
    check_refreshed_plan(case, plan, verified)
    case.exit_pi("lead Pi exit")
    return case.snapshot()


def socrates(case: Case, _report: Report) -> TaskSnapshot:
    wait_for_lead(case)
    freeze_specification(case, interview=True)
    plan = approve_lead_plan(case)
    verify_lead(case)
    case.exit_pi("lead Pi exit")
    deliver_and_archive(case, plan)
    return case.snapshot()


def socrates_ready(case: Case, _report: Report) -> TaskSnapshot:
    wait_for_lead(case)
    freeze_specification(case, interview=False)
    approve_lead_plan(case)
    verify_lead(case)
    case.exit_pi("lead Pi exit")
    return case.snapshot()


SCENARIOS: dict[Scenario, Callable[[Case, Report], TaskSnapshot]] = {
    Scenario.ACCEPTED: accepted,
    Scenario.FAILED_CHECK: failed_check,
    Scenario.CHANGED_BRIEF: changed_brief,
    Scenario.LEAD_PLAN: lead_plan,
    Scenario.SOCRATES: socrates,
    Scenario.SOCRATES_READY: socrates_ready,
}
