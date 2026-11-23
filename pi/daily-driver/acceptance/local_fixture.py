"""Configuration and resources shared by the native Pi acceptance cases."""

from __future__ import annotations

import json
import os
import runpy
import shlex
import shutil
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Sequence, TypedDict

from local_provider import ADMITTED_MODEL, ALTERNATE_MODEL
from zellij_terminal import Pane, Pty, Terminal


class Scenario(str, Enum):
    ACCEPTED = "accepted"
    FAILED_CHECK = "failed-check"
    CHANGED_BRIEF = "changed-brief"
    LEAD_PLAN = "lead-plan"
    SOCRATES = "socrates"
    SOCRATES_READY = "socrates-ready"


class BeadsSource(TypedDict):
    url: str
    projectId: str


@dataclass(frozen=True)
class RunOptions:
    root: Path
    work: Path
    repository: Path
    bd: str
    beads: BeadsSource
    scenario: Scenario | None
    output: Path | None

    @classmethod
    def read(cls, input_file: Path) -> RunOptions:
        raw = json.loads(input_file.read_text())
        return cls(
            root=Path(raw["root"]), work=Path(raw["directory"]), repository=Path(raw["workspace"]),
            bd=raw["bd"], beads=raw["beadsService"],
            scenario=Scenario(raw["scenario"]) if raw.get("scenario") else None,
            output=Path(raw["output"]) if raw.get("output") else None,
        )


@dataclass(frozen=True)
class FixturePaths:
    work: Path
    runtime: Path

    @property
    def home(self) -> Path:
        return self.work / "pi-home"

    @property
    def temporary(self) -> Path:
        return self.work / "tmp"

    @property
    def agent(self) -> Path:
        return self.work / "agent"

    @property
    def guard(self) -> Path:
        return self.work / "guard"

    @property
    def sentinels(self) -> dict[str, Path]:
        return {"paseo": self.work / "unexpected-paseo", "zellij": self.work / "unexpected-zellij-subprocess"}

    def prepare(self) -> None:
        for directory in (self.home, self.temporary, self.agent, self.guard):
            directory.mkdir(mode=0o700)
        config = self.home / ".config/zellij/config.kdl"
        config.parent.mkdir(parents=True)
        config.write_text('default_shell "/bin/sh"\nshow_startup_tips false\non_force_close "quit"\n')
        for command, sentinel in self.sentinels.items():
            executable = self.guard / command
            executable.write_text(f"#!/bin/sh\nprintf '%s\\n' \"$*\" >> {shlex.quote(str(sentinel))}\nexit 99\n")
            executable.chmod(0o755)

    def environment(self) -> dict[str, str]:
        # Only pass through the values the disposable run needs.
        return {
            **{key: os.environ[key] for key in (
                "LANG", "LC_ALL", "LC_CTYPE", "TZ", "DOLT_ROOT_PATH",
                "DOLT_CLI_NO_UPDATE_CHECK", "BD_DISABLE_METRICS", "GIT_CONFIG_GLOBAL",
                "GIT_CONFIG_NOSYSTEM", "PI_DRIVER_USE_SOURCE",
            ) if key in os.environ},
            "HOME": str(self.home),
            "SHELL": "/bin/sh",
            "PS1": "local-run-ready> ",
            "TERM": "xterm-256color",
            "COLORTERM": "truecolor",
            "XDG_CONFIG_HOME": str(self.home / ".config"),
            "XDG_CACHE_HOME": str(self.home / ".cache"),
            "XDG_DATA_HOME": str(self.home / ".local/share"),
            "XDG_STATE_HOME": str(self.home / ".local/state"),
            "XDG_RUNTIME_DIR": str(self.runtime),
            "ZELLIJ_SOCKET_DIR": str(self.runtime),
            "TMPDIR": str(self.temporary),
            "PATH": str(self.guard) + os.pathsep + os.environ["PATH"],
            "PI_CODING_AGENT_DIR": str(self.agent),
            "PI_DRIVER_CONFIG": str(self.work / "driver.json"),
            "PI_DRIVER_STATE_DIR": str(self.work / "journal"),
            "PI_SKIP_VERSION_CHECK": "1",
            "PI_TELEMETRY": "0",
            "PASEO_HOME": str(self.work / "paseo-unavailable"),
            "PASEO_URL": "http://127.0.0.1:9",
            "PASEO_ENDPOINT": "ws://127.0.0.1:9",
        }

    def configure_pi(self, options: RunOptions, port: int) -> None:
        models = (ADMITTED_MODEL, ALTERNATE_MODEL)
        providers = {model.provider: model.settings(port) for model in models}
        (self.agent / "models.json").write_text(json.dumps({"providers": providers}))
        settings: dict[str, object] = {"packages": [str(options.root)]}
        if options.scenario in (Scenario.SOCRATES, Scenario.SOCRATES_READY):
            settings.update({"theme": "dotfiles", "quietStartup": True})
            themes = self.agent / "themes"
            themes.mkdir()
            (themes / "dotfiles.json").symlink_to(options.root / "resources/theme.json")
        (self.agent / "settings.json").write_text(json.dumps(settings))
        role = {"provider": ADMITTED_MODEL.provider, "model": ADMITTED_MODEL.id, "reasoning": "off"}
        (self.work / "driver.json").write_text(json.dumps({
            "beadsService": options.beads,
            "integrations": {name: {"enabled": True} for name in ("zellij", "worktrees", "octo")},
            "profiles": {"personal": {name: role for name in ("lead", "worker", "reviewer", "explorer")}},
        }))


class Allocation(TypedDict):
    task_id: str
    path: str


# The CLI owns these JSON schemas. Each scenario asserts the fields it observes.
class TaskSnapshot(TypedDict):
    projectId: str
    task: dict[str, Any]
    attempt: dict[str, Any]


class CaseEvidence(TypedDict):
    scenario: str
    bead: str
    evidence: TaskSnapshot


class ReportObservations(TypedDict, total=False):
    registered_process: str
    registered_pane: Pane


class Report(ReportObservations):
    runtime: str
    submission: str
    paseo: str
    session: str
    cases: list[CaseEvidence]
    artifacts: str
    outcome: str
    cleanup: str


@dataclass
class Fixture:
    options: RunOptions
    paths: FixturePaths
    env: dict[str, str]
    binary: str
    manager: str
    name: str
    artifacts: Path
    allocations: list[Allocation] = field(default_factory=list)

    @property
    def driver(self) -> str:
        return str(self.options.root / "scripts/pi-driver")

    def execute(
        self, args: Sequence[str | Path], *, cwd: str | Path | None = None, check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            args, cwd=cwd or self.options.repository, env=self.env,
            capture_output=True, text=True, timeout=30,
        )
        assert not check or result.returncode == 0, {
            "argv": args, "code": result.returncode, "stdout": result.stdout, "stderr": result.stderr,
        }
        return result

    def fresh(self, bead: str) -> TaskSnapshot:
        result: TaskSnapshot = json.loads(self.execute([self.driver, "tasks", bead, "--json"]).stdout)
        return result

    def update_bead(self, bead: str, field: str, value: str) -> None:
        self.execute([self.options.bd, "--sandbox", "update", bead, field, value])

    def initialize_repository(self) -> None:
        repository = self.options.repository
        (repository / ".gitignore").write_text(".beads/\n.worktrees/\n")
        (repository / "README.md").write_text("Disposable native Pi acceptance repository.\n")
        (repository / "highlight-fixture.ts").write_text(
            'const sedMarker: number = 42;\nconst rgMarker: string = "fixture";\n',
        )
        self.execute(["git", "add", ".gitignore", "README.md", "highlight-fixture.ts"])
        self.execute(["git", "-c", "user.name=Acceptance", "-c", "user.email=acceptance@example.invalid",
                      "-c", "core.hooksPath=/dev/null", "commit", "-qm", "Initialize fixture"])
        self.execute(["git", "branch", "-M", "main"])

    def start_terminal(self) -> Terminal:
        workflow = runpy.run_path(str(self.options.root / "acceptance/zellij_pty.py"))
        pty: Pty = workflow["Terminal"](self.binary, self.env, self.name, install_navigation=False)
        try:
            return Terminal(pty, self.options.root, self.env, self.name)
        except OSError:
            pty.close()
            raise

    def check_sentinels(self) -> None:
        for sentinel in self.paths.sentinels.values():
            assert not sentinel.exists(), sentinel.read_text()

    def prune_worktrees(self) -> None:
        inventory = self.execute([self.manager, "status", "--json"])
        known = {checkout["task_id"] for checkout in self.allocations}
        checkout_root = self.options.repository.resolve() / ".worktrees"
        for task in json.loads(inventory.stdout)["result"]["tasks"]:
            task_path = Path(task["path"])
            if task["id"] not in known and task_path.exists() and task_path.resolve().is_relative_to(checkout_root):
                self.allocations.append({"task_id": task["id"], "path": task["path"]})
        for checkout in self.allocations:
            path = checkout["path"]
            self.execute([self.manager, "finish", checkout["task_id"], "--json"])
            assert not self.execute(["git", "status", "--porcelain", "--untracked-files=all"], cwd=path).stdout, checkout
            assert not self.execute(["git", "ls-files", "--others", "--ignored", "--exclude-standard"], cwd=path).stdout, checkout
            prune = [self.manager, "prune", "--worktree", path, "--accept-recent"]
            self.execute(prune)
            self.execute([*prune, "-y"])
            assert not Path(path).exists(), checkout


def make_fixture(options: RunOptions, runtime: Path) -> Fixture:
    binary, manager = shutil.which("zellij"), shutil.which("worktree")
    assert binary and manager, "Install native zellij and worktree before acceptance"
    paths = FixturePaths(options.work, runtime)
    paths.prepare()
    artifacts = options.output / options.work.name if options.output else options.work / "evidence"
    artifacts.mkdir(parents=True, exist_ok=True)
    return Fixture(options, paths, paths.environment(), binary, manager, "pi-local-" + options.work.name, artifacts)
