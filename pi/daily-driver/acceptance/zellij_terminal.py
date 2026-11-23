"""Drive the owned acceptance PTY with the generated TypeScript Zellij client."""

from __future__ import annotations

import json
import os
import select
import subprocess
import time
from pathlib import Path
from typing import Callable, Protocol, TypedDict


class Pty(Protocol):
    output: bytearray

    def drain(self, duration: float = 0.08) -> None: ...
    def until(self, description: str, predicate: Callable[[], object]) -> object: ...
    def close(self) -> None: ...


class Pane(TypedDict):
    id: int
    tab_id: int
    is_focused: bool
    is_plugin: bool
    is_suppressed: bool
    exited: bool


class Terminal:
    def __init__(self, pty: Pty, package: Path, env: dict[str, str], name: str) -> None:
        self.pty = pty
        self.client = subprocess.Popen(
            ["bun", "acceptance/zellij-control.ts", name],
            cwd=package, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=0,
        )

    @property
    def output(self) -> bytearray:
        return self.pty.output

    def until(self, description: str, predicate: Callable[[], object]) -> object:
        return self.pty.until(description, predicate)

    def pane_listing(self) -> list[Pane]:
        panes: list[Pane] = json.loads(self.request("panes"))
        return panes

    def terminals(self) -> list[Pane]:
        return [pane for pane in self.pane_listing() if not pane["is_plugin"] and not pane["is_suppressed"]]

    def capture_pane(self, pane: int, *, full: bool = False, ansi: bool = False) -> str:
        return self.request("capture", pane=pane, full=full, ansi=ansi)

    def send_to_pane(self, pane: int, text: str) -> None:
        self.request("text", pane=pane, text=text)

    def write_to_pane(self, pane: int, *keys: int) -> None:
        self.request("keys", pane=pane, bytes=keys)

    def focus_pane(self, pane: int) -> None:
        self.request("focus", pane=pane)

    def request(self, action: str, **arguments: object) -> str:
        writer, reader = self.client.stdin, self.client.stdout
        assert writer is not None and reader is not None
        writer.write((json.dumps({"action": action, **arguments}) + "\n").encode())
        deadline = time.monotonic() + 7
        response = bytearray()
        while time.monotonic() < deadline:
            # Keep consuming renders while a pane operation is in flight.
            self.pty.drain(0.01)
            if not select.select([reader], [], [], 0.05)[0]:
                continue
            chunk = os.read(reader.fileno(), 65536)
            if not chunk:
                raise RuntimeError("Zellij socket client exited without a reply")
            response.extend(chunk)
            if response.endswith(b"\n"):
                result = json.loads(response)
                if "error" in result:
                    raise subprocess.CalledProcessError(1, ["Zellij API", action], stderr=result["error"])
                output: str = result["output"]
                return output
        raise RuntimeError(f"Zellij socket client timed out during {action}")

    def close(self) -> None:
        try:
            if self.client.stdin is not None:
                self.client.stdin.close()
            try:
                self.client.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.client.kill()
                self.client.wait(timeout=5)
        finally:
            if self.client.stdout is not None:
                self.client.stdout.close()
            self.pty.close()
