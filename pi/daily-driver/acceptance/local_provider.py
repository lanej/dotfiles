"""Deterministic loopback provider for the native Pi acceptance harness."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from http.server import BaseHTTPRequestHandler
from typing import Literal, TypedDict

from socrates_fixture import CompletionRequest, message_text, specification_tool


class FunctionCall(TypedDict):
    name: str
    arguments: str


class ToolDeltaCall(TypedDict):
    index: int
    id: str
    type: Literal["function"]
    function: FunctionCall


class ToolDelta(TypedDict):
    role: Literal["assistant"]
    tool_calls: list[ToolDeltaCall]


class TextDelta(TypedDict):
    role: Literal["assistant"]
    content: str


class PlanTask(TypedDict, total=False):
    key: str
    title: str
    description: str
    acceptance: str
    requirements: list[str]
    owns: list[str]
    blockedBy: list[str]


@dataclass(frozen=True)
class PiModel:
    provider: str
    path: str
    api_key: str
    id: str
    name: str

    def settings(self, port: int) -> dict[str, object]:
        return {
            "baseUrl": f"http://127.0.0.1:{port}{self.path}",
            "api": "openai-completions",
            "apiKey": self.api_key,
            "models": [{
                "id": self.id, "name": self.name, "reasoning": False,
                "input": ["text"], "contextWindow": 32768, "maxTokens": 2048,
                "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
            }],
        }


ADMITTED_MODEL = PiModel(
    "openai-codex", "/v1", "fixture", "gpt-6.1-sol", "Local native acceptance fixture",
)
ALTERNATE_MODEL = PiModel(
    "alternate-fixture", "/alternate/v1", "alternate-fixture",
    "different-model", "Unapproved acceptance fixture",
)


def tool_delta(call_id: str, name: str, arguments: object) -> ToolDelta:
    return {
        "role": "assistant",
        "tool_calls": [{
            "index": 0, "id": call_id, "type": "function",
            "function": {"name": name, "arguments": json.dumps(arguments)},
        }],
    }


def plan_delta(names: set[str], *, refreshed: bool) -> ToolDelta:
    assert "draft_implementation_plan" in names and not names.intersection({"write", "edit", "bash"}), names
    tasks: list[PlanTask] = [
        {"key": "inspect", "title": "Inspect requirements", "description": "Read fixture",
         "acceptance": "Find marker", "requirements": ["R1"], "owns": ["README.md"]},
        {"key": "verify", "title": "Verify result", "description": "Run fixture check",
         "acceptance": "Fixture passes", "blockedBy": ["inspect"], "requirements": ["R1"]},
    ]
    return tool_delta("fixture-draft-plan", "draft_implementation_plan", {
        "summary": "Plan native fixture delivery", "tasks": [] if refreshed else tasks,
    })


def user_tool(request: CompletionRequest, text: str) -> ToolDelta | None:
    search = re.search(r"HL_FIXTURE_(SED|RG)", text)
    if search is not None:
        name = search.group(1)
        command = {"SED": "sed -n '1,3p' highlight-fixture.ts",
                   "RG": "rg -n --with-filename rgMarker highlight-fixture.ts"}[name]
        return tool_delta(f"fixture-search-{name}", "bash", {"command": command})
    names = {tool["function"]["name"] for tool in request["tools"]}
    refreshed = text == "Draft a revised plan without new children."
    if refreshed or text.startswith(("Draft a plan for ", "The operator froze")):
        return plan_delta(names, refreshed=refreshed)
    if "SUBMIT_WITH_TOOL_accepted" in text:
        assert "task_submit_result" in names, request
        return tool_delta("fixture-task-submit", "task_submit_result", {
            "summary": "Acceptance accepted evidence",
        })
    return None


def complete(request: CompletionRequest) -> ToolDelta | TextDelta:
    messages = request["messages"]
    last = messages[-1]
    text = message_text(last)
    spec = specification_tool(request)
    if spec is not None:
        calls = sum(bool(message.get("tool_calls")) for message in messages)
        arguments = asdict(spec.arguments, dict_factory=lambda fields: {
            name: value for name, value in fields if value is not None
        })
        return tool_delta(f"fixture-spec-{calls}", spec.name, arguments)
    if last["role"] == "user":
        tool = user_tool(request, text)
        if tool is not None:
            return tool
    if last["role"] == "tool":
        return {"role": "assistant", "content": "ACK_TOOL_SUBMITTED"}
    token = re.search(r"GUIDANCE_[a-z_]+", text)
    return {"role": "assistant", "content": "ACK_" + (token.group(0) if token else "ACCEPTED_CONTEXT")}


class Provider(BaseHTTPRequestHandler):
    requests: list[CompletionRequest] = []
    alternate_requests: list[CompletionRequest] = []

    def do_POST(self) -> None:
        request: CompletionRequest = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.requests.append(request)
        if self.path.startswith("/alternate/"):
            self.alternate_requests.append(request)
        delta = complete(request)
        finish = "tool_calls" if "tool_calls" in delta else "stop"
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Connection", "close")
        self.end_headers()
        self.write_chunk(delta, None)
        self.write_chunk({}, finish)
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()
        self.close_connection = True

    def write_chunk(self, delta: object, finish: str | None) -> None:
        chunk = {
            "id": "fixture-completion", "object": "chat.completion.chunk", "created": 1,
            "model": ADMITTED_MODEL.id,
            "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
        }
        self.wfile.write(("data: " + json.dumps(chunk) + "\n\n").encode())

    def log_message(self, _format: str, *args: object) -> None:
        pass
