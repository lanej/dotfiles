"""Scripted provider responses for the native Socrates acceptance cases."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypedDict, Union


class ContentBlock(TypedDict, total=False):
    text: str


class ToolCallingMessage(TypedDict, total=False):
    tool_calls: list[object]


class Message(ToolCallingMessage):
    role: str
    content: str | list[ContentBlock] | None


class Function(TypedDict):
    name: str


class Tool(TypedDict):
    function: Function


class CompletionRequest(TypedDict):
    model: str
    messages: list[Message]
    tools: list[Tool]


@dataclass(frozen=True)
class WebEvidence:
    label: str
    url: str


@dataclass(frozen=True)
class SourceEvidence:
    label: str
    path: str
    line: int


@dataclass(frozen=True)
class ObservationEvidence:
    label: str
    observation: str


Evidence = Union[WebEvidence, SourceEvidence, ObservationEvidence]


@dataclass(frozen=True)
class Choice:
    label: str
    description: str
    details: str | None = None
    evidence: tuple[Evidence, ...] | None = None


@dataclass(frozen=True)
class Decision:
    id: str
    decision: str
    basis: Literal["observed", "decided"]
    evidence: str
    disposition: Literal["open", "resolved"]
    uncertainty: str


@dataclass(frozen=True)
class AskArguments:
    decisionId: str
    question: str
    options: list[Choice]
    context: str | None = None
    evidence: tuple[Evidence, ...] | None = None


@dataclass(frozen=True)
class Requirement:
    id: str
    outcome: str
    acceptance: str


@dataclass(frozen=True)
class DraftArguments:
    objective: str
    scope: list[str]
    requirements: list[Requirement]
    decisions: list[Decision]
    blockingQuestions: list[str]


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: AskArguments | DraftArguments


@dataclass(frozen=True)
class Exchange:
    id: str
    decision: str
    question: str
    answer: str
    choices: tuple[Choice, ...] = ()
    context: str | None = None
    evidence: tuple[Evidence, ...] | None = None

    def ask(self) -> ToolCall:
        return ToolCall(
            "ask_user_question",
            AskArguments(
                decisionId=self.id, question=self.question, options=list(self.choices),
                context=self.context, evidence=self.evidence,
            ),
        )

    def open_decision(self) -> Decision:
        return Decision(
            id=self.id,
            decision=self.decision,
            basis="observed",
            evidence="Beads acceptance criteria",
            disposition="open",
            uncertainty="The missing choice changes the acceptance check",
        )

    def resolved_decision(self) -> Decision:
        return Decision(
            id=self.id,
            decision=self.decision,
            basis="decided",
            evidence=self.answer,
            disposition="resolved",
            uncertainty="None",
        )


KEEP_CHECKOUT = "Keep the checkout"
ARCHIVE = Exchange(
    "D1", "Choose recovery behavior after an archive failure",
    "If the archive fails, what should happen to the checkout?", KEEP_CHECKOUT,
    (
        Choice(
            KEEP_CHECKOUT, "Retry in the same checkout",
            "Keeping the checkout preserves **the exact worktree** for a retry.\n\n"
            "- Run `archive --retry` after the [retention check](https://example.com/retention).\n\n"
            + "\n".join(f"Recovery log entry {i}" for i in range(1, 33)),
            (
                WebEvidence("Recovery procedure", "https://github.com/fixture/repo/issues/7"),
                SourceEvidence("Fixture source", "README.md", 1),
                ObservationEvidence("Observed outcome", "The retry fixture exited with status 7."),
            ),
        ),
        Choice("Remove it", "Recover from the saved transcript"),
    ),
    context=(
        "Octo has confirmed the merge, and the transcript archive failed. "
        "See the [recovery log](https://example.com/recovery)."
    ),
    evidence=(WebEvidence("Archive report", "https://github.com/fixture/repo/issues/8"),),
)
RECEIPT = Exchange(
    "D2", "Choose the operator receipt", "What receipt should the operator see?",
    "Show the archived transcript path.",
    context="The operator needs to know where to find the transcript.",
    evidence=(WebEvidence("Receipt instructions", "https://github.com/fixture/repo/issues/9"),),
)
RESUME_DRAFT = "Resume Socrates discovery for the accepted bead."
RESUME_ANSWER = "Resume Socrates discovery using the recorded operator answer."
REFRESH_SPEC = "Reassess Socrates discovery against the refreshed Beads brief."
DRAFT_TOOL = "draft_socrates_specification"


def message_text(message: Message) -> str:
    content = message["content"]
    if isinstance(content, list):
        return "".join(item.get("text", "") for item in content)
    return content or ""


def draft(resolved: list[Decision], *, pending: Exchange | None = None) -> ToolCall:
    return ToolCall(
        DRAFT_TOOL,
        DraftArguments(
            objective="Verify the native lead handoff",
            scope=["Disposable Beads checkout"],
            requirements=[
                Requirement("R1", "Preserve approval evidence", "Verify the Beads graph"),
            ],
            decisions=resolved if pending is None else [*resolved, pending.open_decision()],
            blockingQuestions=[] if pending is None else [pending.question],
        ),
    )


def user_turn(text: str, prompt: str, history: list[str]) -> ToolCall | None:
    if text.startswith("Begin Socrates discovery"):
        if "Native Pi socrates-ready" in prompt:
            return draft([ARCHIVE.resolved_decision()])
        return draft([], pending=ARCHIVE)
    if text == RESUME_DRAFT:
        return ARCHIVE.ask()
    if text == RESUME_ANSWER:
        assert f"Operator answer · {ARCHIVE.answer}" in prompt, prompt
        # Leave the first recorded answer unapplied to exercise recovery on resume.
        if history.count(RESUME_ANSWER) == 1:
            return None
        return draft([ARCHIVE.resolved_decision()], pending=RECEIPT)
    if text.startswith(REFRESH_SPEC):
        assert "Verify the revised Socrates receipt" in prompt, prompt
        return draft([ARCHIVE.resolved_decision()], pending=RECEIPT)
    return None


def tool_turn(text: str, history: list[str]) -> ToolCall | None:
    if text == f"Operator answer for {RECEIPT.id}: {RECEIPT.answer}":
        return draft([ARCHIVE.resolved_decision(), RECEIPT.resolved_decision()])
    # The initial draft waits for /socrates; later drafts continue to the receipt dialog.
    if text.startswith("Draft saved. Resolve") and RESUME_DRAFT in history:
        return RECEIPT.ask()
    return None


def specification_tool(request: CompletionRequest) -> ToolCall | None:
    names = {tool["function"]["name"] for tool in request["tools"]}
    if DRAFT_TOOL not in names:
        return None
    assert "ask_user_question" in names and "draft_implementation_plan" not in names, names

    messages = request["messages"]
    prompt = "\n".join(message_text(message) for message in messages if message["role"] == "system")
    assert all(rule in prompt for rule in ("Harmony", "Parsimony", "Readiness gate")), prompt
    last = messages[-1]
    history = [message_text(message) for message in messages if message["role"] == "user"]
    if last["role"] == "user":
        return user_turn(message_text(last), prompt, history)
    if last["role"] == "tool":
        return tool_turn(message_text(last), history)
    return None
