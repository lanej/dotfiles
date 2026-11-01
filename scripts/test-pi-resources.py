#!/usr/bin/env python3
"""One shared-resource installation workflow; --native also checks Pi discovery."""

import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest


ROOT = Path(__file__).resolve().parents[1]


def commands(home):
    pi = shutil.which("pi")
    if not pi:
        raise RuntimeError("Install Pi 1.4.0 before running --native")
    agent = home / ".pi/agent"
    (agent / "models.json").write_text(json.dumps({"providers": {"resource-fixture": {
        "baseUrl": "http://127.0.0.1:9/v1", "api": "openai-completions",
        "apiKey": "fixture", "models": [{"id": "tiny"}]}}}))
    env = dict(os.environ, HOME=str(home), PI_CODING_AGENT_DIR=str(agent),
               PI_SKIP_VERSION_CHECK="1", PI_TELEMETRY="0")
    with tempfile.TemporaryFile(mode="w+") as errors:
        process = subprocess.Popen(
            [pi, "--mode", "rpc", "--offline", "--no-session", "--no-extensions", "--no-mcp",
             "--model", "resource-fixture/tiny"],
            cwd=home, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=errors, text=True,
        )
        events = queue.Queue()
        def read():
            for line in process.stdout:
                events.put(line)
            events.put(None)
        threading.Thread(target=read, daemon=True).start()
        try:
            process.stdin.write('{"id":"catalog","type":"get_commands"}\n')
            process.stdin.flush()
            while True:
                line = events.get(timeout=20)
                if line is None:
                    errors.seek(0)
                    raise AssertionError("Pi exited before returning resources: " + errors.read())
                event = json.loads(line)
                if event.get("id") == "catalog":
                    if not event.get("success"):
                        raise AssertionError(event)
                    return event["data"]["commands"]
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            process.stdin.close()
            process.stdout.close()


class SharedResourceWorkflow(unittest.TestCase):
    def test_shared_roles_and_skills_survive_refresh_with_local_guidance(self):
        with tempfile.TemporaryDirectory(prefix="pi resources ") as temporary:
            home = Path(temporary).resolve()
            checkout = home / "checkout"
            for relative in ("bin/sync-codex-skills", "bin/sync-pi-resources",
                             "scripts/install-software-standard.py",
                             "ai/agents/code-reviewer.md", "ai/agents/reflection.md",
                             "ai/agents/github-pr-writer.md"):
                target = checkout / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, target)
            shutil.copytree(ROOT / "ai/skills/builder", checkout / "ai/skills/builder")
            agent = home / ".pi/agent"
            prompts = agent / "prompts"
            prompts.mkdir(parents=True)
            guidance = agent / "AGENTS.md"
            guidance.write_text("Keep my local project conventions.\n")
            local = prompts / "dotfiles-github-pr-writer.md"
            local.write_text("My personal PR prompt.\n")
            settings = agent / "settings.json"
            settings.write_text('{"theme":"dark"}\n')
            def install():
                result = subprocess.run(
                    ["make", "--no-print-directory", "-f", str(ROOT / "Makefile"),
                     "pi-config", f"DOTFILES={checkout}", f"HOME={home}", "IS_EASYPOST=false"],
                    cwd=checkout, capture_output=True, text=True, timeout=30,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            install()
            shared = home / ".agents/skills/dotfiles/builder/SKILL.md"
            self.assertEqual(shared.resolve(), home / ".local/share/software-standards/builder/SKILL.md")
            role = prompts / "dotfiles-code-reviewer.md"
            self.assertIn(str(checkout / "ai/agents/code-reviewer.md"), role.read_text())
            self.assertIn("$ARGUMENTS", role.read_text())
            self.assertTrue((prompts / "dotfiles-reflection.md").is_file())
            (checkout / "ai/agents/reflection.md").unlink()
            install()
            self.assertFalse((prompts / "dotfiles-reflection.md").exists())
            self.assertEqual(local.read_text(), "My personal PR prompt.\n")
            self.assertEqual(settings.read_text(), '{"theme":"dark"}\n')
            self.assertIn("Keep my local project conventions.", guidance.read_text())
            self.assertEqual(guidance.read_text().count("# Default software guidance: Builder"), 1)
            if NATIVE:
                catalog = commands(home)
                roles = [c for c in catalog if c["name"] == "dotfiles-code-reviewer"]
                self.assertEqual(len(roles), 1, catalog)
                self.assertEqual(roles[0]["source"], "prompt")
                self.assertEqual(Path(roles[0]["sourceInfo"]["path"]), role)
                skills = [c for c in catalog if c["name"] == "skill:builder"]
                self.assertEqual(len(skills), 1, catalog)
                self.assertEqual(skills[0]["source"], "skill")


if __name__ == "__main__":
    NATIVE = "--native" in sys.argv
    if NATIVE:
        sys.argv.remove("--native")
    unittest.main()
