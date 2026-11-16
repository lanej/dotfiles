#!/usr/bin/env python3
"""One acceptance workflow: share a bootstrap, then retrofit and upgrade locally."""

import json
import importlib.util
import importlib.machinery
import sys
from concurrent.futures import ThreadPoolExecutor
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


# Fixture visibility must not inherit the workstation's global Git ignore rules.
os.environ["GIT_CONFIG_GLOBAL"] = os.devnull

SOURCE = Path(__file__).resolve().parents[1]
VALIDATOR = SOURCE / "ai/skills/skill-authoring/scripts/validate.py"


def run(command, cwd=None, expected=0, env=None):
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, env=env)
    assert result.returncode == expected, (command, result.stdout, result.stderr)
    return result.stdout + result.stderr


def git(root, *args):
    return run(["git", "-C", str(root), "-c", "core.hooksPath=/dev/null",
                "-c", "commit.gpgsign=false", "-c", "user.name=Bootstrap acceptance",
                "-c", "user.email=bootstrap@example.invalid", *args]).strip()


def tree(root):
    return {str(path.relative_to(root)): (os.readlink(path) if path.is_symlink() else path.read_bytes())
            for path in root.rglob("*") if path.is_symlink() or path.is_file()}


# Exercise the standalone workflow command with only its documented runner present.
with tempfile.TemporaryDirectory(prefix="go-standalone-workflow-") as temporary:
    standalone = Path(temporary)
    (standalone / "scripts").mkdir()
    (standalone / "scripts/check-go.sh").write_text("printf 'standalone-go-gate\\n'\n")
    workflow = (SOURCE / "ai/skills/go/assets/go-quality.yml").read_text()
    command = workflow.rsplit("- run: ", 1)[1].strip()
    assert "standalone-go-gate" in run(["bash", "-c", command], cwd=standalone)

with tempfile.TemporaryDirectory(prefix="repo-bootstrap-acceptance-") as temporary:
    run(["python3", str(VALIDATOR), *[str(SOURCE / "ai/skills" / name)
        for name in json.loads((SOURCE / "ai/skills/source-code-versions.json").read_text())["skills"]]])
    # macOS commonly exposes its temporary directory through /var -> /private/var.
    workspace = Path(temporary).resolve()
    # A private source copy lets the workflow exercise a real subsequent update.
    source = workspace / "dotfiles"
    (source / "bin").mkdir(parents=True)
    shutil.copy2(SOURCE / "bin/repo-bootstrap", source / "bin/repo-bootstrap")
    shutil.copy2(SOURCE / "bin/source-code", source / "bin/source-code")
    (source / "scripts").mkdir()
    shutil.copy2(SOURCE / "scripts/source_code_languages.py", source / "scripts/source_code_languages.py")
    shutil.copytree(SOURCE / "ai", source / "ai", symlinks=True)
    shutil.copytree(SOURCE / "docs", source / "docs", symlinks=True)
    cli = source / "bin/source-code"
    # Default setup is entirely local: clones inherit no settings or skill links.
    defaults = workspace / "default shadow setup"
    defaults.mkdir()
    git(defaults, "init", "--quiet")
    (defaults / "README.md").write_text("Application source.\n")
    git(defaults, "add", "README.md")
    git(defaults, "commit", "-qm", "Initial project")
    before = tree(defaults)
    view = json.loads(run([str(cli), "explain", "--repo", str(defaults), "--json"]))
    assert view["desired"]["mode"] == "local" and view["desired"]["skill_storage"] == "linked"
    run([str(cli), "setup", "--authority", "owned", "--adoption", "new", "--repo", str(defaults), "--dry-run"])
    assert tree(defaults) == before
    run([str(cli), "setup", "--authority", "owned", "--adoption", "new", "--repo", str(defaults)])
    assert (defaults / ".agents/skills/builder").is_symlink()
    assert (defaults / ".agents/skills/ship/SKILL.md").is_file()
    assert (defaults / ".claude/skills/ship/SKILL.md").is_file()
    assert (defaults / ".agents/templates/pull_request_template.md").is_file()
    assert not (defaults / ".github/pull_request_template.md").exists()
    assert not git(defaults, "status", "--porcelain", "--untracked-files=all")
    git(defaults, "add", ".")
    assert git(defaults, "ls-files").splitlines() == ["README.md"]
    assert "already current" in run([str(cli), "setup", "--authority", "owned", "--adoption", "new", "--repo", str(defaults)])
    run([str(cli), "validate", "--repo", str(defaults), "--strict"])
    default_clone = workspace / "default shadow clone"
    git(workspace, "clone", "--quiet", str(defaults), str(default_clone))
    assert not (default_clone / ".agents").exists()
    assert not (default_clone / "source-code.toml").exists()
    run([str(cli), "setup", "--authority", "owned", "--adoption", "new", "--repo", str(default_clone)])
    assert not git(default_clone, "status", "--porcelain", "--untracked-files=all")

    codex_only = workspace / "default Codex-only setup"
    run([str(cli), "setup", "--authority", "owned", "--adoption", "new", "--repo", str(codex_only), "--init", "--agents", "codex"])
    assert (codex_only / ".agents/skills/ship/SKILL.md").is_file()
    assert not (codex_only / ".claude").exists()
    assert not git(codex_only, "status", "--porcelain", "--untracked-files=all")

    # New projects share canonical packages; only portable settings are committed.
    linked_projects = [workspace / "linked one", workspace / "linked two"]
    for target in linked_projects:
        preview = run([str(cli), "setup", "--authority", "owned", "--adoption", "new", "--repo", str(target), "--init", "--mode", "tracked", "--no-detect-languages", "--pr-template", "none", "--dry-run"])
        assert not target.exists(), "linked preview created a repository"
        assert "Skill storage: linked" in preview
        run([str(cli), "setup", "--authority", "owned", "--adoption", "new", "--repo", str(target), "--init", "--mode", "tracked", "--no-detect-languages", "--pr-template", "none"])
        link = target / ".agents/skills/builder"
        assert link.is_symlink() and link.resolve() == source / "ai/skills/builder"
        assert (target / ".claude/skills/builder").resolve() == link.resolve()
        assert (target / ".agents/source-code-versions.json").is_symlink()
        before = tree(target)
        assert "already current" in run([str(cli), "setup", "--authority", "owned", "--adoption", "new", "--repo", str(target)])
        assert tree(target) == before
        run([str(cli), "validate", "--repo", str(target), "--strict"])
        git(target, "add", ".")
        tracked = git(target, "ls-files").splitlines()
        assert "source-code.toml" in tracked
        assert not any(path.startswith((".agents/skills/", ".claude/")) or path in {".agents/repo-bootstrap.json", ".agents/source-code-versions.json"} for path in tracked)
        assert str(source) not in (target / "source-code.toml").read_text()
        git(target, "commit", "-qm", "Configure canonical project skills")
    canonical = source / "ai/skills/builder/SKILL.md"
    original = canonical.read_bytes()
    registry_path = source / "ai/skills/source-code-versions.json"
    registry_bytes = registry_path.read_bytes()
    registry = json.loads(registry_bytes)
    registry["skills"]["builder"] = "1.9.0"
    canonical.write_bytes(original + b"\nCanonical change observed by both projects.\n")
    registry_path.write_text(json.dumps(registry))
    for target in linked_projects:
        assert (target / ".agents/skills/builder/SKILL.md").read_bytes() == canonical.read_bytes()
        assert "builder: 1.9.0 (live)" in run([str(cli), "validate", "--repo", str(target), "--strict"])
        view = json.loads(run([str(cli), "explain", "--repo", str(target), "--json"]))
        assert view["installed"]["skill_versions"]["builder"] == "1.9.0"
        assert not view["differences"]
        assert not git(target, "status", "--porcelain"), "canonical updates dirtied project configuration"
    # A cloned project recreates its ignored machine-local links from tracked intent.
    clone = workspace / "linked clone"
    git(workspace, "clone", "--quiet", str(linked_projects[0]), str(clone))
    run([str(cli), "setup", "--authority", "owned", "--adoption", "new", "--repo", str(clone)])
    assert (clone / ".agents/skills/builder").resolve() == source / "ai/skills/builder"
    run([str(cli), "validate", "--repo", str(clone), "--strict"])
    # Redirected and broken links fail validation instead of trusting metadata.
    builder_link = linked_projects[0] / ".agents/skills/builder"
    builder_link.unlink()
    builder_link.symlink_to(source / "ai/skills/architecture", target_is_directory=True)
    run([str(cli), "validate", "--repo", str(linked_projects[0])], expected=1)
    builder_link.unlink()
    builder_link.symlink_to(source / "ai/skills/builder", target_is_directory=True)
    canonical.rename(canonical.with_suffix(".saved"))
    run([str(cli), "validate", "--repo", str(linked_projects[0])], expected=1)
    canonical.with_suffix(".saved").rename(canonical)
    canonical.write_bytes(original)
    registry_path.write_bytes(registry_bytes)

    # Normal detection must not mistake generated runtimes in a clone for app code.
    detected_project = workspace / "linked default detection"
    run([str(cli), "setup", "--authority", "owned", "--adoption", "new", "--repo", str(detected_project), "--init", "--mode", "tracked", "--pr-template", "none"])
    git(detected_project, "add", ".")
    git(detected_project, "commit", "-qm", "Configure detected project")
    detected_clone = workspace / "default detection clone"
    git(workspace, "clone", "--quiet", str(detected_project), str(detected_clone))
    run([str(cli), "setup", "--authority", "owned", "--adoption", "new", "--repo", str(detected_clone)])
    assert not git(detected_clone, "status", "--porcelain")
    run([str(cli), "validate", "--repo", str(detected_clone), "--strict"])

    # Generated CI gates run from a fresh checkout without local skill links.
    gate_project = workspace / "linked gate"
    run([str(cli), "setup", "--authority", "owned", "--adoption", "new", "--repo", str(gate_project), "--init", "--mode", "tracked", "--go", "--go-rollout", "strict", "--no-detect-languages", "--pr-template", "none"])
    git(gate_project, "add", ".")
    git(gate_project, "commit", "-qm", "Configure a standalone lifecycle gate")
    gate_clone = workspace / "gate clone"
    git(workspace, "clone", "--quiet", str(gate_project), str(gate_clone))
    assert not (gate_clone / ".agents/skills").exists()
    gate = ["python3", str(gate_clone / "scripts/check-source-code.py"), "go"]
    assert '["bash", "scripts/check-go.sh", "all"]' in run([*gate, "--dry-run"])
    (gate_clone / "scripts/check-go.sh").write_text("printf 'fresh-clone-gate:%s\\n' \"$1\"\n")
    assert "fresh-clone-gate:all" in run(gate)

    # Copied installs remain portable and migrate only unchanged, untracked content.
    migration = workspace / "storage migration"
    run([str(cli), "setup", "--authority", "owned", "--adoption", "new", "--repo", str(migration), "--init", "--mode", "shadow", "--skill-storage", "copied", "--no-detect-languages", "--pr-template", "none"])
    assert "Skill storage: copied" in run([str(cli), "setup", "--authority", "owned", "--adoption", "new", "--repo", str(migration), "--dry-run"])
    extra = migration / ".agents/skills/builder/private-notes.txt"
    extra.write_text("Keep these local notes.\n")
    before = tree(migration)
    assert "unmanaged skill content" in run([str(cli), "setup", "--authority", "owned", "--adoption", "new", "--repo", str(migration), "--skill-storage", "linked"], expected=1)
    assert tree(migration) == before
    extra.unlink()
    installed_builder = migration / ".agents/skills/builder/SKILL.md"
    installed_bytes = installed_builder.read_bytes()
    installed_builder.write_bytes(installed_bytes + b"\nLocal customization.\n")
    before = tree(migration)
    run([str(cli), "setup", "--authority", "owned", "--adoption", "new", "--repo", str(migration), "--skill-storage", "linked"], expected=1)
    assert tree(migration) == before
    installed_builder.write_bytes(installed_bytes)
    git(migration, "add", "-f", ".agents/skills/builder/SKILL.md")
    before = tree(migration)
    assert "tracked files" in run([str(cli), "setup", "--authority", "owned", "--adoption", "new", "--repo", str(migration), "--skill-storage", "linked"], expected=1)
    assert tree(migration) == before
    git(migration, "rm", "--cached", ".agents/skills/builder/SKILL.md")
    before = tree(migration)
    run([str(cli), "setup", "--authority", "owned", "--adoption", "new", "--repo", str(migration), "--skill-storage", "linked", "--dry-run"])
    assert tree(migration) == before
    run([str(cli), "setup", "--authority", "owned", "--adoption", "new", "--repo", str(migration), "--skill-storage", "linked"])
    assert (migration / ".agents/skills/builder").is_symlink()
    run([str(cli), "validate", "--repo", str(migration), "--strict"])
    source_before = tree(source / "ai/skills")
    run([str(cli), "setup", "--authority", "owned", "--adoption", "new", "--repo", str(migration), "--skill-storage", "copied"])
    assert not (migration / ".agents/skills/builder").is_symlink()
    assert tree(source / "ai/skills") == source_before, "copy migration changed canonical packages"
    # The authored configuration remains linked; CLI override does not rewrite it.
    assert 'skill_storage = "linked"' in (migration / "source-code.toml").read_text()

    # Retired skill selections migrate without retaining duplicate entrypoints.
    for old_name, new_name in (("pr-writer", "pull-request"), ("pr-merge", "ship")):
        retired = workspace / ("retired " + old_name)
        retired.mkdir()
        git(retired, "init", "--quiet")
        entrypoint = retired / ".agents/skills" / old_name / "SKILL.md"
        entrypoint.parent.mkdir(parents=True)
        entrypoint.write_text("---\nname: " + old_name + "\ndescription: Use when handling the old pull request workflow.\n---\nOld guidance.\n")
        relative = entrypoint.relative_to(retired).as_posix()
        state = {"version": 1, "mode": "local", "skills": [old_name],
                 "skill_versions": {old_name: "1.0.0"}, "files": {relative:
                 {"kind": "file", "sha256": hashlib.sha256(entrypoint.read_bytes()).hexdigest(), "executable": False}}}
        (retired / ".agents/repo-bootstrap.json").write_text(json.dumps(state))
        extra = entrypoint.parent / "local-notes.txt"
        extra.write_text("Keep my notes.\n")
        before = tree(retired)
        run([str(cli), "setup", "--authority", "owned", "--adoption", "new", "--repo", str(retired), "--no-detect-languages"], expected=1)
        assert tree(retired) == before
        extra.unlink()
        run([str(cli), "setup", "--authority", "owned", "--adoption", "new", "--repo", str(retired), "--skills", "just", "--no-detect-languages"])
        assert not entrypoint.parent.exists()
        assert (retired / ".agents/skills" / new_name / "SKILL.md").is_file()
        assert not (retired / ".claude/skills" / old_name).exists()
        run([str(cli), "validate", "--repo", str(retired), "--strict"])

    # Agents can discover the tool before choosing or creating a project.
    assert run([str(cli), "skill"], cwd=workspace) == (source / "ai/skills/source-code/SKILL.md").read_text()
    assert "skill" in run([str(cli), "--help"])
    invalid_context = workspace / "discovery-only"
    invalid_context.mkdir()
    (invalid_context / "source-code.toml").write_text("not valid TOML [[[\n")
    before = tree(invalid_context)
    run([str(cli), "skill"], cwd=invalid_context)
    assert tree(invalid_context) == before
    management = source / "ai/skills/source-code/SKILL.md"
    management.rename(management.with_suffix(".saved"))
    assert "management skill is unavailable" in run([str(cli), "skill"], cwd=workspace, expected=1)
    management.with_suffix(".saved").rename(management)

    # Explain shares setup's resolver and never initializes Git or installs artifacts.
    inspection = workspace / "inspection without Git"
    inspection.mkdir()
    intent = inspection / "source-code.toml"
    intent.write_text('schema_version = 1\nstage = "alpha"\nauthority = "owned"\nadoption = "new"\nkind = "library"\nmode = "shadow"\npr_template = "none"\n[checks.go]\nenabled = false\n[checks.typescript]\nenabled = false\n')
    before = tree(inspection)
    source_scripts_before = tree(source / "scripts")
    explained = json.loads(run([str(cli), "explain", "--skill-storage", "copied", "--repo", str(inspection), "--json"]))
    assert tree(source / "scripts") == source_scripts_before, "inspection wrote bytecode into its source checkout"
    assert explained["schema_version"] == 1 and explained["installed"] is None
    assert explained["desired"]["stage"] == "alpha" and explained["desired"]["kind"] == "library"
    assert explained["origins"]["stage"]["source"] == "toml"
    assert "library-code-comments" in explained["desired"]["skills"]
    overridden = json.loads(run([str(cli), "explain", "--skill-storage", "copied", "--repo", str(inspection), "--stage", "research", "--json"]))
    assert overridden["desired"]["stage"] == "research" and overridden["origins"]["stage"]["source"] == "cli"
    preview = run([str(cli), "setup", "--skill-storage", "copied", "--repo", str(inspection), "--init", "--dry-run"])
    effective = json.loads(next(line.split(": ", 1)[1] for line in preview.splitlines() if "Effective configuration:" in line))
    assert explained["desired"] == effective
    assert tree(inspection) == before, "inspection or preview changed authored content/Git metadata"
    run([str(cli), "setup", "--skill-storage", "copied", "--repo", str(inspection), "--init"])
    before = tree(inspection)
    installed_view = json.loads(run([str(cli), "explain", "--skill-storage", "copied", "--repo", str(inspection), "--json"]))
    assert installed_view["differences"] == []
    subset = json.loads(run([str(cli), "explain", "--skill-storage", "copied", "--repo", str(inspection), "--skills", "pull-request", "--json"]))
    assert subset["selection"]["skills"] == ["pull-request"]
    assert "source-code-lifecycle" in subset["selection"]["retained_skills"]
    assert "source-code-lifecycle" in subset["desired"]["skills"]
    human = run([str(cli), "explain", "--skill-storage", "copied", "--repo", str(inspection)])
    assert "Recorded installation" in human and "Skills retained" in human
    assert tree(inspection) == before, "explain changed an installed project or Git metadata"
    intent.write_text('schema_version = 1\nstage = "research"\n')
    drift = json.loads(run([str(cli), "explain", "--skill-storage", "copied", "--repo", str(inspection), "--json"]))
    assert any(item["field"] == "stage" and item["installed"] == "alpha" for item in drift["differences"])
    intent.write_text('schema_version = true\n')
    before = tree(inspection)
    invalid = subprocess.run([str(cli), "explain", "--skill-storage", "copied", "--repo", str(inspection), "--json"], text=True, capture_output=True)
    assert invalid.returncode == 1 and not invalid.stdout and "Traceback" not in invalid.stderr
    assert tree(inspection) == before

    # Go rollout inspection does not parse legacy YAML or provision its parser.
    inspect_go = workspace / "inspection legacy Go"
    inspect_go.mkdir()
    (inspect_go / "go.mod").write_text("module example.com/inspection\n\ngo 1.26\n")
    (inspect_go / ".golangci.yaml").write_text("invalid YAML [[[:\n")
    before = tree(inspect_go)
    legacy_view = json.loads(run([str(cli), "explain", "--skill-storage", "copied", "--repo", str(inspect_go), "--json"]))
    assert legacy_view["desired"]["checks"]["go"]["rollout"] == "ratchet"
    assert tree(inspect_go) == before

    legacy_install = workspace / "inspection pre-pin installation"
    legacy_skill = legacy_install / ".agents/skills/pull-request/SKILL.md"
    legacy_skill.parent.mkdir(parents=True)
    legacy_skill.write_text("---\nname: pr-writer\ndescription: Use when drafting pull requests with clear review context.\n---\n")
    legacy_state = {"version": 1, "mode": "tracked", "files": {".agents/skills/pull-request/SKILL.md":
        {"kind": "file", "sha256": hashlib.sha256(legacy_skill.read_bytes()).hexdigest(), "executable": False}}}
    (legacy_install / ".agents/repo-bootstrap.json").write_text(json.dumps(legacy_state))
    legacy_view = json.loads(run([str(cli), "explain", "--skill-storage", "copied", "--repo", str(legacy_install), "--json"]))
    assert legacy_view["installed"]["skills"] == ["pull-request"]
    assert legacy_view["installed"]["skill_versions"]["pull-request"] is None

    project = workspace / "new repository"

    def install(target, *args, expected=0):
        # Portable legacy scenarios choose tracked visibility explicitly on first setup.
        visibility = []
        if not (target / ".agents/repo-bootstrap.json").exists() and not (target / "source-code.toml").exists() and "--config" not in args and "--mode" not in args:
            visibility = ["--mode", "tracked"]
        return run([str(cli), "setup", "--skill-storage", "copied", *visibility, "--repo", str(target), *args], expected=expected)

    def owned_install(target, *args, expected=0):
        return install(target, "--authority", "owned", "--adoption", "new", *args, expected=expected)

    # Two concurrent seed publishers retain one complete winner and never replace it.
    loader = importlib.machinery.SourceFileLoader("source_code_seed_test", str(cli))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[loader.name] = module
    loader.exec_module(module)
    seed = workspace / "concurrent-octo.toml"
    candidates = [b"first complete seed\n", b"second complete seed\n"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda data: module.seed_file(seed, data), candidates))
    winner = seed.read_bytes()
    assert winner in candidates
    module.seed_file(seed, b"replacement")
    assert seed.read_bytes() == winner

    # Repository automation is seeded only for selected Octo projects and remains authored.
    for mode in ("tracked", "shadow"):
        target = workspace / ("octo-" + mode)
        flags = ("--skills", "octo-manager", "--no-go", "--no-typescript", "--no-detect-languages", "--pr-template", "none")
        owned_install(target, "--init", "--stage", "research", "--mode", mode, *flags)
        config = target / "octo-manager.toml"
        assert 'auto_merge = "project_stage"' in config.read_text()
        authored = config.read_bytes() + b"\n# Keep this repository's follow-up.\n"
        config.write_bytes(authored)
        owned_install(target, "--stage", "beta", *flags)
        assert config.read_bytes() == authored
        state = json.loads((target / ".source-code.json").read_text())
        assert state["stage"] == "beta"
        manifest = json.loads((target / ".agents/repo-bootstrap.json").read_text())
        assert "octo-manager.toml" not in manifest["files"]
        if mode == "shadow":
            assert "octo-manager.toml" in git(target, "check-ignore", "octo-manager.toml")
            git(target, "add", "-f", "octo-manager.toml")
            owned_install(target, *flags)
            assert config.read_bytes() == authored
        before = tree(target)
        run([str(cli), "upgrade", "--repo", str(target), "--dry-run"])
        assert tree(target) == before
    unrelated = workspace / "without-octo"
    owned_install(unrelated, "--init", "--skills", "builder", "--no-go", "--no-typescript", "--no-detect-languages", "--pr-template", "none")
    assert not (unrelated / "octo-manager.toml").exists()

    # Missing policy choices fail before Git initialization or installation writes.
    authority_project = workspace / "explicit authority"
    for flags, missing in (([], "authority"), (["--authority", "owned"], "adoption")):
        assert missing + " must be selected explicitly" in install(authority_project, "--init", *flags, expected=1)
        assert not authority_project.exists()
    authority_project.mkdir()
    empty_view = json.loads(run([str(cli), "explain", "--repo", str(authority_project), "--json"]))
    assert empty_view["desired"]["authority"] is None and empty_view["desired"]["adoption"] is None
    assert not (authority_project / ".git").exists()
    for authority, adoption in (("owned", "new"), ("shared", "hold"), ("upstream", "backfill")):
        install(authority_project, "--init", "--authority", authority, "--adoption", adoption,
                "--stage", "research", "--agents", "codex", "--pr-template", "none")
        policy = json.loads((authority_project / ".source-code.json").read_text())
        assert policy["authority"] == authority and policy["adoption"] == adoption
        assert (authority_project / ".agents/skills/source-code-lifecycle/references/tool-choices.md").is_file()
        run([str(cli), "upgrade", "--repo", str(authority_project)])
        view = json.loads(run([str(cli), "explain", "--repo", str(authority_project), "--json"]))
        assert view["differences"] == []
        assert view["origins"]["authority"]["source"] == "saved"
        assert view["installed"]["adoption"] == adoption
        run([str(cli), "validate", "--repo", str(authority_project), "--strict"])
    authored_authority = authority_project / "source-code.toml"
    authored_authority.write_text('schema_version = 1\nauthority = "shared"\nadoption = "hold"\n')
    before = tree(authority_project)
    view = json.loads(run([str(cli), "explain", "--repo", str(authority_project), "--json"]))
    assert view["desired"]["authority"] == "shared" and view["origins"]["adoption"]["source"] == "toml"
    assert "configuration authority differs" in run([str(cli), "validate", "--repo", str(authority_project)], expected=0)
    override = json.loads(run([str(cli), "explain", "--repo", str(authority_project),
                              "--authority", "owned", "--adoption", "new", "--json"]))
    assert override["desired"]["authority"] == "owned" and override["desired"]["adoption"] == "new"
    assert override["origins"]["adoption"]["source"] == "cli"
    assert tree(authority_project) == before
    install(authority_project)
    assert authored_authority.read_text() == 'schema_version = 1\nauthority = "shared"\nadoption = "hold"\n'
    for key in ("authority", "adoption"):
        authored_authority.write_text(f'schema_version = 1\n{key} = "unknown"\n')
        before = tree(authority_project)
        assert "invalid configuration " + key in install(authority_project, expected=1)
        assert tree(authority_project) == before
    authored_authority.unlink()
    # A legacy policy remains inspectable and runnable until an explicit upgrade.
    legacy_policy_path = authority_project / ".source-code.json"
    legacy_manifest_path = authority_project / ".agents/repo-bootstrap.json"
    legacy_pins_path = authority_project / ".agents/source-code-versions.json"
    legacy_plans_path = authority_project / ".agents/skills/source-code-lifecycle/references/stages.json"
    for path in (legacy_policy_path, legacy_manifest_path, legacy_pins_path, legacy_plans_path):
        legacy = json.loads(path.read_text())
        legacy.pop("authority", None)
        legacy.pop("adoption", None)
        legacy["policy_version"] = "1.0.0"
        path.write_text(json.dumps(legacy))
    before = tree(authority_project)
    view = json.loads(run([str(cli), "explain", "--repo", str(authority_project), "--json"]))
    assert view["installed"]["authority"] is None and view["installed"]["adoption"] is None
    assert "authority must be selected explicitly" in run([str(cli), "upgrade", "--repo", str(authority_project)], expected=1)
    assert tree(authority_project) == before
    install(authority_project, "--authority", "owned", "--adoption", "new", "--conflict", "replace")
    run([str(cli), "validate", "--repo", str(authority_project), "--strict"])

    configured = workspace / "toml project"
    configured.mkdir()
    git(configured, "init", "--quiet")
    config = configured / "source-code.toml"
    config_text = ("# Authored choices stay byte-for-byte intact.\nschema_version = 1\n"
                   'stage = "research"\nauthority = "owned"\nadoption = "new"\nmode = "shadow"\nskills = ["pull-request"]\n'
                   'agents = "codex"\npr_template = "none"\ndetect_languages = false\n'
                   '[checks.go]\nenabled = false\n[checks.typescript]\nenabled = false\n')
    config.write_text(config_text)
    assert "TOML configuration only" in run([str(cli), "validate", "--repo", str(configured)])
    config.write_text(config_text.replace('stage = "research"', 'stage = "research"\npolicy_version = "99.0.0"'))
    before = tree(configured)
    run([str(cli), "validate", "--repo", str(configured)], expected=1)
    assert tree(configured) == before, "unsupported config-only policy validation wrote files"
    config.write_text(config_text)
    before = tree(configured)
    preview = install(configured, "--dry-run")
    assert "Effective configuration" in preview and '"enabled": false' in preview
    assert tree(configured) == before, "TOML preview wrote files"
    install(configured)
    assert config.read_text() == config_text
    config_policy = json.loads((configured / ".source-code.json").read_text())
    assert config_policy["stage"] == "research" and config_policy["languages"] == []
    assert not (configured / "scripts/check-go.sh").exists()
    assert git(configured, "check-ignore", "source-code.toml") == "source-code.toml"
    state = json.loads((configured / ".agents/repo-bootstrap.json").read_text())
    assert str(config) not in json.dumps(state) and "source-code.toml" not in state["files"]
    assert "already current" in install(configured)
    install(configured, "--stage", "alpha")
    assert config.read_text() == config_text
    assert json.loads((configured / ".source-code.json").read_text())["stage"] == "alpha"
    assert "configuration stage differs" in run([str(cli), "validate", "--repo", str(configured), "--strict"], expected=1)
    run([str(cli), "upgrade", "--repo", str(configured)])
    assert json.loads((configured / ".source-code.json").read_text())["stage"] == "research"
    run([str(cli), "validate", "--repo", str(configured), "--strict"])
    for invalid in ["schema_version = true\n", "schema_version = 2\n", 'schema_version = 1\nunknown = true\n',
                    'schema_version = 1\ndetect_languages = "false"\n', 'schema_version = 1\n[checks.go]\nenabled = 0\n',
                    'schema_version = 1\n[checks.typescript]\nenabled = false\nprojects = ["tsconfig.json"]\n',
                    'schema_version = 1\n[checks.go]\nunknown = true\n', 'schema_version = 1\nstage = [\n']:
        config.write_text(invalid)
        before = tree(configured)
        install(configured, expected=1)
        run([str(cli), "validate", "--repo", str(configured)], expected=1)
        assert tree(configured) == before, "invalid configuration changed installation"
    config.write_text(config_text.replace('stage = "research"', 'stage = "research"\npolicy_version = "99.0.0"'))
    before = tree(configured)
    install(configured, "--dry-run", expected=1)
    run([str(cli), "validate", "--repo", str(configured)], expected=1)
    overridden_pin = install(configured, "--policy-version", "1.1.0", "--dry-run")
    assert '"policy_version": "1.1.0"' in overridden_pin
    assert tree(configured) == before, "CLI policy override changed authored configuration"
    config.write_text(config_text.replace('[checks.go]\nenabled = false', '[checks.go]\nenabled = true\nrollout = "strict"'))
    before = tree(configured)
    override = install(configured, "--no-go", "--dry-run")
    assert not json.loads(next(line.split(": ", 1)[1] for line in override.splitlines() if "Effective configuration:" in line))["checks"]["go"]["selected"]
    assert tree(configured) == before, "CLI override preview changed authored TOML"
    run([str(cli), "validate", "--skills-dir", str(source / "ai/skills/pull-request"),
         "--config", str(config)], expected=1)
    config.write_text(config_text.replace('stage = "research"', 'stage = "beta"'))
    local_guide = configured / ".agents/skills/pull-request/SKILL.md"
    local_guide.write_text(local_guide.read_text() + "\nLocal customization.\n")
    before = tree(configured)
    assert "preserving existing" in run([str(cli), "upgrade", "--repo", str(configured)], expected=1)
    assert tree(configured) == before, "TOML upgrade overwrote customization"

    alternate = workspace / "alternate project"
    alternate.mkdir()
    git(alternate, "init", "--quiet")
    private_config = alternate / "private settings.toml"
    private_config.write_text(config_text)
    # Explicit relative paths resolve from the invocation directory, not --repo.
    relative_config = str(private_config.relative_to(workspace))
    run([str(cli), "setup", "--skill-storage", "copied", "--repo", str(alternate), "--config", relative_config], cwd=workspace)
    assert git(alternate, "check-ignore", private_config.name) == private_config.name
    run([str(cli), "validate", "--repo", str(alternate), "--config", relative_config, "--strict"], cwd=workspace)
    run([str(cli), "upgrade", "--repo", str(alternate), "--config", relative_config], cwd=workspace)
    private_config.write_text(config_text.replace('mode = "shadow"', 'mode = "tracked"'))
    run([str(cli), "setup", "--skill-storage", "copied", "--repo", str(alternate), "--config", relative_config], cwd=workspace)
    assert not run(["git", "-C", str(alternate), "check-ignore", "--no-index", private_config.name], expected=1)
    before = tree(alternate)
    run([str(cli), "setup", "--skill-storage", "copied", "--repo", str(alternate), "--config", "missing.toml"], cwd=workspace, expected=1)
    assert tree(alternate) == before

    # Domain guidance is opt-in, portable, and separate from workstation tools.
    for mode in ("tracked", "shadow"):
        domain = workspace / ("domain guidance " + mode)
        owned_install(domain, "--init", "--mode", mode, "--stage", "research",
                      "--skills", "data-pipeline,ui-acceptance", "--no-detect-languages", "--pr-template", "none")
        policy = json.loads((domain / ".source-code.json").read_text())
        assert {"data-pipeline", "ui-acceptance", "architecture", "testing", "git"} <= policy["skills"].keys()
        assert policy["languages"] == []
        assert not (domain / ".agents/skills/ui-review").exists()
        assert (domain / ".agents/skills/data-pipeline/references/medallion-architecture.md").is_file()
        assert (domain / ".agents/skills/ui-acceptance/references/visual-review.md").is_file()
        run([str(cli), "validate", "--repo", str(domain), "--strict"])
        if mode == "tracked":
            git(domain, "add", ".")
            git(domain, "commit", "-qm", "Select project domain guidance")
            clone = workspace / "portable domain clone"
            run(["git", "clone", "--quiet", str(domain), str(clone)])
            run([str(cli), "validate", "--repo", str(clone), "--strict"])
            run(["python3", str(VALIDATOR), *[str(clone / ".agents/skills" / name) for name in policy["skills"]]])
        else:
            assert not git(domain, "status", "--porcelain"), "private domain guidance escaped shadow exclusions"
        run([str(cli), "upgrade", "--repo", str(domain)])
        assert json.loads((domain / ".source-code.json").read_text())["skills"].keys() == policy["skills"].keys()

    profile_intent = workspace / "inferred profiles"
    profile_intent.mkdir()
    git(profile_intent, "init", "--quiet")
    (profile_intent / "go.mod").write_text("module example.com/intent\n\ngo 1.26\n")
    (profile_intent / "package.json").write_text('{"name":"intent","scripts":{"test":"echo ok"}}\n')
    (profile_intent / "tsconfig.json").write_text('{"compilerOptions":{"strict":true}}\n')
    owned_install(profile_intent, "--stage", "research", "--no-go", "--no-typescript", "--no-detect-languages", "--pr-template", "none")
    (profile_intent / "source-code.toml").write_text('schema_version = 1\n[checks.go]\nrollout = "strict"\n[checks.typescript]\nprojects = ["tsconfig.json"]\n')
    setup_preview = owned_install(profile_intent, "--dry-run")
    upgrade_preview = run([str(cli), "upgrade", "--repo", str(profile_intent), "--dry-run"])
    for preview in (setup_preview, upgrade_preview):
        effective = json.loads(next(line.split(": ", 1)[1] for line in preview.splitlines() if "Effective configuration:" in line))
        assert effective["checks"]["go"]["selected"] and effective["checks"]["typescript"]["selected"]
    run([str(cli), "upgrade", "--repo", str(profile_intent)])
    assert json.loads((profile_intent / ".source-code.json").read_text())["languages"] == ["go", "typescript"]
    run([str(cli), "validate", "--repo", str(profile_intent), "--strict"])
    original_intent = (profile_intent / "source-code.toml").read_text()
    (profile_intent / "source-code.toml").write_text('schema_version = 1\n[checks.go]\nrollout = "ratchet"\n[checks.typescript]\nprojects = ["ignored.json"]\n')
    before = tree(profile_intent)
    retained = json.loads(run([str(cli), "explain", "--skill-storage", "copied", "--repo", str(profile_intent), "--no-go", "--no-typescript", "--json"]))
    assert retained["desired"]["checks"]["go"]["action"] == "retain"
    assert retained["desired"]["checks"]["go"]["enabled"] and not retained["desired"]["checks"]["go"]["selected"]
    assert retained["desired"]["checks"]["go"]["rollout"] == "strict"
    assert retained["origins"]["checks.go.rollout"]["source"] == "saved"
    assert retained["desired"]["checks"]["typescript"]["projects"] == ["tsconfig.json"]
    assert retained["origins"]["checks.typescript.projects"]["source"] == "saved"
    assert tree(profile_intent) == before
    (profile_intent / "source-code.toml").write_text(original_intent)

    portable_config = workspace / "tracked configuration"
    portable_config.mkdir()
    git(portable_config, "init", "--quiet")
    tracked_config = portable_config / "source-code.toml"
    tracked_config.write_text(config_text)
    git(portable_config, "add", "source-code.toml")
    git(portable_config, "commit", "-qm", "Track authored policy")
    owned_install(portable_config)
    # A tracked authored policy must not be hidden even with a shadow installation.
    assert not run(["git", "-C", str(portable_config), "check-ignore", "--no-index", "source-code.toml"], expected=1)
    assert tracked_config.read_text() == config_text
    # Share a tracked installation and prove the file works from a different checkout.
    tracked_config.write_text(config_text.replace('mode = "shadow"', 'mode = "tracked"'))
    owned_install(portable_config)
    git(portable_config, "add", ".")
    git(portable_config, "commit", "-qm", "Share project profile")
    config_clone = workspace / "configuration clone"
    run(["git", "clone", "--quiet", str(portable_config), str(config_clone)])
    run([str(cli), "validate", "--repo", str(config_clone), "--strict"])
    run([str(cli), "upgrade", "--repo", str(config_clone)])
    assert (config_clone / "source-code.toml").read_text() == tracked_config.read_text()

    # Python profiles are explicit, preserve project config, and participate in lifecycle/upgrade metadata.
    python_project = workspace / "strict Python project"
    python_project.mkdir()
    git(python_project, "init", "--quiet")
    (python_project / "app.py").write_text("def answer() -> int:\n    return 42\n")
    pyproject = python_project / "pyproject.toml"
    pyproject.write_text('[project]\nname = "existing"\nversion = "1.0.0"\n[tool.ruff]\nline-length = 99\n')
    original_project = pyproject.read_bytes()
    owned_install(python_project, "--stage", "alpha", "--pr-template", "none")
    assert "python" in json.loads((python_project / ".source-code.json").read_text())["skills"]
    assert not (python_project / "scripts/check-python.py").exists(), "detection installed Python checks implicitly"
    (python_project / "source-code.toml").write_text('schema_version = 1\nstage = "beta"\n[checks.python]\nenabled = true\npaths = ["app.py"]\n')
    before = tree(python_project)
    inspected = json.loads(run([str(cli), "explain", "--skill-storage", "copied", "--repo", str(python_project), "--json"]))
    assert inspected["desired"]["checks"]["python"]["selected"]
    assert inspected["desired"]["checks"]["python"]["paths"] == ["app.py"]
    assert tree(python_project) == before
    owned_install(python_project)
    assert pyproject.read_bytes() == original_project
    assert json.loads((python_project / ".source-code.json").read_text())["languages"] == ["python"]
    assert json.loads((python_project / ".python-quality.json").read_text())["paths"] == ["app.py"]
    run([str(cli), "validate", "--repo", str(python_project), "--strict"])
    for stage, mode in (("research", "typecheck"), ("alpha", "alpha"), ("beta", "all"), ("production", "all")):
        owned_install(python_project, "--stage", stage)
        plan = run(["python3", str(python_project / "scripts/check-source-code.py"), "python", "--dry-run"])
        assert json.dumps(["python3", "scripts/check-python.py", mode]) in plan
    run([str(cli), "upgrade", "--repo", str(python_project)])
    assert json.loads((python_project / ".source-code.json").read_text())["stage"] == "beta"
    retained_python = json.loads(run([str(cli), "explain", "--skill-storage", "copied", "--repo", str(python_project), "--no-python", "--json"]))
    assert retained_python["desired"]["checks"]["python"]["action"] == "retain"
    local_python = workspace / "private Python profile"
    owned_install(local_python, "--init", "--python", "--mode", "shadow", "--pr-template", "none")
    assert not git(local_python, "status", "--porcelain", "--untracked-files=all")

    # Protobuf schemas select the profile automatically; explicit opt-outs remain authoritative.
    proto_project = workspace / "strict Protobuf project"
    proto_project.mkdir()
    git(proto_project, "init", "--quiet")
    (proto_project / "example.proto").write_text('syntax = "proto3";\npackage example.v1;\n')
    install(proto_project, "--authority", "owned", "--adoption", "new", "--pr-template", "none")
    assert "protobuf" in json.loads((proto_project / ".source-code.json").read_text())["skills"]
    assert (proto_project / "scripts/check-protobuf.py").is_file()
    assert json.loads((proto_project / ".source-code.json").read_text())["languages"] == ["protobuf"]
    intent = proto_project / "source-code.toml"
    intent.write_text('schema_version = 1\n[checks.protobuf]\nenabled = true\n')
    before = tree(proto_project)
    inspected = json.loads(run([str(cli), "explain", "--repo", str(proto_project), "--json"]))
    assert inspected["desired"]["checks"]["protobuf"]["action"] == "update"
    assert tree(proto_project) == before
    install(proto_project, "--dry-run")
    assert tree(proto_project) == before
    install(proto_project)
    assert json.loads((proto_project / ".source-code.json").read_text())["languages"] == ["protobuf"]
    run([str(cli), "validate", "--repo", str(proto_project), "--strict"])
    for stage, mode in (("research", "build"), ("alpha", "alpha"), ("beta", "all"), ("production", "all")):
        install(proto_project, "--stage", stage)
        plan = run(["python3", str(proto_project / "scripts/check-source-code.py"), "protobuf", "--dry-run"])
        assert json.dumps(["python3", "scripts/check-protobuf.py", mode]) in plan
    settings = proto_project / ".protobuf-quality.json"
    settings.write_text(json.dumps({"version": 1, "against": ".git#ref=origin/main"}))
    original = settings.read_bytes()
    run([str(cli), "upgrade", "--repo", str(proto_project)])
    assert settings.read_bytes() == original
    retained = json.loads(run([str(cli), "explain", "--repo", str(proto_project), "--no-protobuf", "--json"]))
    assert retained["desired"]["checks"]["protobuf"]["action"] == "retain"
    private_proto = workspace / "private Protobuf profile"
    install(private_proto, "--init", "--authority", "owned", "--adoption", "new", "--skills", "protobuf", "--protobuf", "--mode", "shadow", "--pr-template", "none")
    assert not git(private_proto, "status", "--porcelain", "--untracked-files=all")
    git(proto_project, "add", ".")
    git(proto_project, "commit", "--quiet", "-m", "Install portable Protobuf policy")
    proto_clone = workspace / "portable Protobuf clone"
    run(["git", "clone", "--quiet", str(proto_project), str(proto_clone)])
    run([str(cli), "validate", "--repo", str(proto_clone), "--strict"])

    # Nested Buf workspaces also select checks; ignored/vendor schemas do not classify the project.
    auto_proto = workspace / "nested Buf workspace"
    auto_proto.mkdir()
    git(auto_proto, "init", "--quiet")
    (auto_proto / "api").mkdir()
    (auto_proto / "api/buf.yaml").write_text("version: v2\n")
    before = tree(auto_proto)
    view = json.loads(run([str(cli), "explain", "--repo", str(auto_proto), "--json"]))
    assert view["desired"]["checks"]["protobuf"]["selected"]
    assert view["origins"]["checks.protobuf.selected"]["source"] == "detection"
    assert view["origins"]["checks.protobuf.selected"]["evidence"] == ["api/buf.yaml"]
    assert tree(auto_proto) == before
    for number in range(6):
        folder = auto_proto / f"workspace{number}"
        folder.mkdir()
        (folder / "buf.yaml").write_text("version: v2\n")
    install(auto_proto, "--authority", "owned", "--adoption", "new", "--no-protobuf", "--pr-template", "none")
    assert not (auto_proto / "scripts/check-protobuf.py").exists()
    install(auto_proto)
    run([str(cli), "upgrade", "--repo", str(auto_proto)])
    assert not (auto_proto / "scripts/check-protobuf.py").exists(), "saved explicit opt-out was lost"
    install(auto_proto, "--protobuf")
    assert (auto_proto / "scripts/check-protobuf.py").is_file()
    roots = json.loads((auto_proto / ".source-code.json").read_text())["detection"]["protobuf_roots"]
    assert roots == ["api", *[f"workspace{number}" for number in range(6)]]
    install(auto_proto, "--no-detect-languages")
    assert json.loads((auto_proto / ".source-code.json").read_text())["detection"]["protobuf_roots"] == roots
    no_detection = workspace / "disabled schema detection"
    no_detection.mkdir()
    git(no_detection, "init", "--quiet")
    (no_detection / "example.proto").write_text('syntax = "proto3";\n')
    install(no_detection, "--authority", "owned", "--adoption", "new", "--no-detect-languages", "--pr-template", "none")
    assert not (no_detection / "scripts/check-protobuf.py").exists()
    install(no_detection, "--protobuf")
    assert (no_detection / "scripts/check-protobuf.py").is_file()
    late_proto = workspace / "schemas added after initial setup"
    install(late_proto, "--init", "--authority", "owned", "--adoption", "new", "--pr-template", "none")
    (late_proto / "vendor").mkdir()
    (late_proto / "vendor/external.proto").write_text('syntax = "proto3";\n')
    (late_proto / ".gitignore").write_text("ignored.proto\n")
    (late_proto / "ignored.proto").write_text('syntax = "proto3";\n')
    install(late_proto)
    assert not (late_proto / "scripts/check-protobuf.py").exists()
    (late_proto / "api").mkdir()
    (late_proto / "api/owned.proto").write_text('syntax = "proto3";\n')
    run([str(cli), "upgrade", "--repo", str(late_proto)])
    assert (late_proto / "scripts/check-protobuf.py").is_file(), "upgrade missed newly added schemas"

    # Kind selects usage guidance independently from lifecycle and language gates.
    for kind in ("service", "library", "tool"):
        target = workspace / ("kind-" + kind)
        owned_install(target, "--init", "--kind", kind, "--stage", "research", "--no-detect-languages",
                "--no-go", "--no-typescript", "--pr-template", "none")
        policy = json.loads((target / ".source-code.json").read_text())
        assert policy["kind"] == kind and policy["stage"] == "research" and policy["languages"] == []
        assert ("library-code-comments" in policy["skills"]) == (kind == "library")
        assert f"Project kind: **{kind}**" in (target / ".agents/source-code.md").read_text()
        assert (target / ".agents/skills/source-code-lifecycle/references/kinds.md").is_file()
        run([str(cli), "validate", "--repo", str(target), "--strict"])
        run([str(cli), "upgrade", "--repo", str(target)])
        assert json.loads((target / ".source-code.json").read_text())["kind"] == kind

    kind_target = workspace / "kind-config"
    git(kind_target.parent, "init", "-q", str(kind_target))
    kind_config = kind_target / "source-code.toml"
    kind_text = ('schema_version = 1\nstage = "alpha"\nkind = "library"\n'
                 'detect_languages = false\npr_template = "none"\n'
                 '[checks.go]\nenabled = false\n[checks.typescript]\nenabled = false\n')
    kind_config.write_text(kind_text)
    owned_install(kind_target)
    assert kind_config.read_text() == kind_text
    owned_install(kind_target, "--kind", "tool")
    assert json.loads((kind_target / ".source-code.json").read_text())["kind"] == "tool"
    assert "configuration kind differs" in run([str(cli), "validate", "--repo", str(kind_target), "--strict"], expected=1)
    run([str(cli), "upgrade", "--repo", str(kind_target)])
    assert json.loads((kind_target / ".source-code.json").read_text())["kind"] == "library"
    kind_config.write_text(kind_text.replace('kind = "library"\n', ''))
    run([str(cli), "upgrade", "--repo", str(kind_target)])
    assert json.loads((kind_target / ".source-code.json").read_text())["kind"] == "library"
    for bad in ('true', '"application"'):
        kind_config.write_text(kind_text.replace('kind = "library"', 'kind = ' + bad))
        before = tree(kind_target)
        owned_install(kind_target, expected=1)
        run([str(cli), "validate", "--repo", str(kind_target)], expected=1)
        assert tree(kind_target) == before, "invalid kind changed installation"

    owned_install(project, "--init", "--dry-run")
    assert not project.exists(), "preview initialized the target"
    run([str(source / "bin/repo-bootstrap"), "--skill-storage", "copied", "--repo", str(project), "--authority", "owned", "--adoption", "new", "--init", "--mode", "tracked"])
    nested = project / "not-yet-created"
    assert "nested repository" in owned_install(nested, "--init", "--dry-run", expected=1)
    assert not nested.exists()
    assert (project / ".github/pull_request_template.md").is_file()
    assert (project / ".agents/skills/architecture/SKILL.md").is_file()
    assert (project / ".agents/skills/ship/SKILL.md").is_file()
    assert not (project / ".agents/skills/ship").is_symlink()
    default_policy = json.loads((project / ".source-code.json").read_text())
    assert "git" in default_policy["skills"] and "pull-request" in default_policy["skills"]
    router = project / "AGENTS.override.md"
    generated_guide = project / ".agents/source-code.md"
    router_text = router.read_text()
    assert "`AGENTS.md`" in router_text
    assert re.findall(r"\]\(([^)]+)\)", router_text) == [".agents/source-code.md"]
    assert generated_guide.is_file()
    authored = project / "AGENTS.md"
    authored_text = "# Project instructions\n\nPreserve the public CLI contract.\n"
    authored.write_text(authored_text)
    saved_router = router.read_bytes()
    install(project, "--stage", "research")
    assert authored.read_text() == authored_text and router.read_bytes() == saved_router
    assert "Lifecycle stage: **research**" in generated_guide.read_text()
    install(project, "--stage", "beta")
    assert authored.read_text() == authored_text and router.read_bytes() == saved_router
    assert "Lifecycle stage: **beta**" in generated_guide.read_text()
    run([str(cli), "validate", "--repo", str(project), "--strict"])
    # The default Git package must resolve its references without an optional writer skill.
    run(["python3", str(VALIDATOR), str(project / ".agents/skills/git")])
    owned_install(project, "--skills", "octo-manager")
    assert (project / ".agents/skills/octo-manager/SKILL.md").is_file()
    assert (project / ".claude/skills/octo-manager/SKILL.md").is_file()
    assert (project / ".agents/skills/octo-manager/references/submission.md").is_file()
    assert (project / ".claude/skills/builder").resolve() == project / ".agents/skills/builder"
    before = tree(project)
    assert "already current" in owned_install(project)
    assert tree(project) == before
    assert "already current" in run([str(source / "bin/repo-bootstrap"), "--repo", str(project)])
    assert tree(project) == before
    owned_install(project, "--skills", "builder,architecture,pull-request,library-code-comments")
    assert not git(project, "diff", "--cached", "--name-only"), "installer staged files"
    git(project, "add", ".")
    git(project, "commit", "-qm", "Adopt repository guidance")
    shared = workspace / "colleague checkout"
    run(["git", "clone", "--quiet", str(project), str(shared)])
    assert (shared / ".claude/skills/pull-request/SKILL.md").is_file()
    assert (shared / ".claude/skills/library-code-comments/SKILL.md").is_file()
    assert (shared / ".agents/skills/code-comments/references/standard.md").is_file()
    before = tree(shared)
    run([str(cli), "validate", "--repo", str(shared), "--strict"])
    assert tree(shared) == before, "validation wrote project files"
    installed_skills = [str(shared / ".agents/skills" / name)
                        for name in ("code-comments", "library-code-comments")]
    run(["python3", str(VALIDATOR), *installed_skills])
    library_guide = shared / ".agents/skills/library-code-comments/SKILL.md"
    guide = library_guide.read_bytes()
    library_guide.write_bytes(guide + b"\nRead [missing guidance](missing.md).\n")
    run(["python3", str(VALIDATOR), *installed_skills], expected=1)
    run([str(cli), "validate", "--repo", str(shared)], expected=1)
    library_guide.write_bytes(guide)
    # Follow actual local Markdown resource links after cloning, without dotfiles.
    for path in (shared / ".agents/skills").rglob("*.md"):
        text = path.read_text()
        assert "~/.files/" not in text and "~/.local/share/software-standards/" not in text, path
        for link in re.findall(r"\]\(([^)]+)\)", text):
            if "://" not in link and not link.startswith("#"):
                assert (path.parent / link.split("#", 1)[0]).exists(), (path, link)
    run(["python3", "scripts/check_examples.py"], cwd=shared / ".agents/skills/builder")

    library = workspace / "private library"
    owned_install(library, "--init", "--skills", "library-code-comments", "--mode", "shadow", "--pr-template", "none")
    assert not git(library, "status", "--porcelain", "--untracked-files=all")
    assert not (library / "AGENTS.md").exists()
    assert not (library / ".gitignore").exists()
    assert (library / ".claude/skills/library-code-comments/SKILL.md").is_file()
    before = tree(library)
    assert "already current" in owned_install(library, "--skills", "library-code-comments", "--pr-template", "none")
    assert tree(library) == before
    run([str(cli), "validate", "--repo", str(library), "--strict"])
    override = library / "AGENTS.override.md"
    assert override.is_file()
    assert json.loads((library / ".source-code.json").read_text())["skills"]["testing"] == "1.0.0"
    registry = source / "ai/skills/source-code-versions.json"
    registry_bytes = registry.read_bytes()
    versions = json.loads(registry_bytes)
    versions["skills"]["testing"] = "1.1.0"
    registry.write_text(json.dumps(versions))
    testing_guide = source / "ai/skills/testing/SKILL.md"
    testing_bytes = testing_guide.read_bytes()
    testing_guide.write_bytes(testing_bytes + b"\nAdditional project verification guidance.\n")
    before = tree(library)
    preview = run([str(cli), "upgrade", "--repo", str(library), "--dry-run"])
    assert "1.0.0 -> 1.1.0" in preview
    release_view = json.loads(run([str(cli), "explain", "--skill-storage", "copied", "--repo", str(library), "--json"]))
    assert any(item["field"] == "skill_versions.testing" and item["installed"] == "1.0.0" and item["desired"] == "1.1.0" for item in release_view["differences"])
    assert tree(library) == before, "upgrade preview wrote files"
    run([str(cli), "upgrade", "--repo", str(library)])
    upgraded = json.loads((library / ".source-code.json").read_text())
    assert upgraded["skills"]["testing"] == "1.1.0" and upgraded["stage"] == "beta"
    assert not (library / ".github").exists(), "upgrade added an unselected PR template"
    assert not git(library, "status", "--porcelain", "--untracked-files=all")
    run([str(cli), "validate", "--repo", str(library), "--strict"])
    assert "already current" in run([str(cli), "upgrade", "--repo", str(library)])
    saved_override = override.read_bytes()
    override.write_bytes(saved_override + b"\nPersonal local instructions.\n")
    before = tree(library)
    run([str(cli), "upgrade", "--repo", str(library)], expected=1)
    run([str(cli), "upgrade", "--repo", str(library), "--conflict", "skip"], expected=1)
    assert tree(library) == before, "conflicting override partially upgraded the project"
    override.write_bytes(saved_override)
    generated = library / ".agents/source-code.md"
    saved_generated = generated.read_bytes()
    generated.write_bytes(saved_generated + b"\nLocally edited generated policy.\n")
    before = tree(library)
    run([str(cli), "validate", "--repo", str(library)], expected=1)
    run([str(cli), "upgrade", "--repo", str(library), "--conflict", "skip"], expected=1)
    assert tree(library) == before, "customized generated policy was overwritten"
    generated.write_bytes(saved_generated)
    registry.write_bytes(registry_bytes)

    detected = workspace / "detected project"
    detected.mkdir()
    (detected / "app.py").write_text("print('project')\n")
    (detected / "vendor").mkdir()
    (detected / "vendor/fake.rs").write_text("// Third-party fixture.\n")
    (detected / "node_modules").mkdir()
    (detected / "node_modules/fake.ts").write_text("export {};\n")
    before = tree(detected)
    found = json.loads(run([str(cli), "detect", "--repo", str(detected), "--json"]))
    assert found["languages"] == ["python"] and found["evidence"]["python"] == ["app.py"]
    assert tree(detected) == before and not (detected / ".git").exists()
    git(detected, "init", "--quiet")
    git(detected, "add", "vendor/fake.rs")
    (detected / ".gitignore").write_text("/Cargo.toml\n/package.json\n/pyproject.toml\n")
    (detected / "Cargo.toml").write_text('[package]\nname="scratch"\n')
    (detected / "package.json").write_text('{"devDependencies":{"typescript":"5.9.3"}}\n')
    (detected / "pyproject.toml").write_text("[project]\nname='scratch'\n")
    assert json.loads(run([str(cli), "detect", "--repo", str(detected), "--json"]))["languages"] == ["python"]
    owned_install(detected, "--skills", "builder", "--no-go", "--no-typescript", "--mode", "shadow", "--pr-template", "none")
    policy = json.loads((detected / ".source-code.json").read_text())
    assert "python" in policy["skills"] and policy["languages"] == []
    assert policy["detection"]["languages"] == ["python"]
    assert "already current" in owned_install(detected, "--no-go", "--no-typescript")
    assert json.loads(run([str(cli), "detect", "--repo", str(detected), "--json"]))["languages"] == ["python"]
    for name, contents in {"backend/go.mod": "module example.invalid/detected\n", "web/package.json": '{"devDependencies":{"typescript":"5.9.3"}}\n',
                           "native/Cargo.toml": '[package]\nname="detected"\nversion="0.1.0"\n'}.items():
        path = detected / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents)
    found = json.loads(run([str(cli), "detect", "--repo", str(detected), "--json"]))
    assert found["languages"] == ["go", "javascript", "python", "rust", "typescript"]
    owned_install(detected, "--no-go", "--no-typescript")
    policy = json.loads((detected / ".source-code.json").read_text())
    assert set(found["skills"]) <= set(policy["skills"]) and policy["languages"] == []
    assert not (detected / "scripts/check-go.sh").exists() and not (detected / "scripts/check-typescript.mjs").exists()
    run([str(cli), "validate", "--repo", str(detected), "--strict"])
    opted_out = workspace / "manual language selection"
    opted_out.mkdir()
    (opted_out / "main.py").write_text("pass\n")
    owned_install(opted_out, "--init", "--skills", "builder", "--no-detect-languages", "--pr-template", "none")
    assert "python" not in json.loads((opted_out / ".source-code.json").read_text())["skills"]
    assert "already current" in run([str(cli), "upgrade", "--repo", str(opted_out)])
    before = tree(library)
    assert "downgrade" in run([str(cli), "upgrade", "--repo", str(library)], expected=1)
    assert tree(library) == before
    testing_guide.write_bytes(testing_bytes)
    standalone = workspace / "standalone-skill"
    standalone.mkdir()
    (standalone / "SKILL.md").write_text("---\nname: standalone-skill\ndescription: Helpful details.\n---\nUseful instructions.\n")
    assert "WARNING" in run([str(cli), "validate", "--skills-dir", str(standalone)])
    run([str(cli), "validate", "--skills-dir", str(standalone), "--strict"], expected=1)

    # Retrofit an existing linked worktree, retaining its instructions/template.
    existing = workspace / "existing repository"
    existing.mkdir()
    git(existing, "init", "--quiet")
    (existing / "AGENTS.md").write_text("Keep this project's own instructions.\n")
    (existing / "PULL_REQUEST_TEMPLATE.txt").write_text("Required project review fields.\n")
    git(existing, "add", ".")
    git(existing, "commit", "-qm", "Existing project policy")
    worktree = workspace / "retrofit worktree"
    git(existing, "worktree", "add", "--quiet", "--detach", str(worktree))
    before = tree(worktree)
    assert "existing PR template" in owned_install(worktree, expected=1)
    assert tree(worktree) == before, "conflicting retrofit partially wrote files"
    exclude = existing / ".git/info/exclude"
    exclude.write_text(exclude.read_text() + "\n/scratch-notes\n")
    original_exclude = exclude.read_text()
    owned_install(worktree, "--mode", "local")
    run(["python3", "scripts/check_examples.py"], cwd=worktree / ".agents/skills/builder")
    # A smaller local install in a sibling must not expose this one's packages.
    owned_install(existing, "--mode", "local", "--skills", "builder", "--agents", "codex", "--pr-template", "none")
    assert not git(worktree, "status", "--porcelain", "--untracked-files=all")
    assert (worktree / "AGENTS.md").read_text() == "Keep this project's own instructions.\n"
    assert (worktree / "PULL_REQUEST_TEMPLATE.txt").read_text() == "Required project review fields.\n"
    assert exclude.read_text().startswith(original_exclude)
    assert (worktree / ".agents/templates/pull_request_template.md").is_file()

    # An update refreshes unchanged files but protects a locally customized skill.
    builder = worktree / ".agents/skills/builder/SKILL.md"
    builder.write_text(builder.read_text() + "\nLocal construction guidance.\n")
    local_builder = builder.read_bytes()
    upstream = source / "ai/skills/builder/references/construction.md"
    upstream.write_text(upstream.read_text() + "\nUpdated construction clarification.\n")
    before = tree(worktree)
    assert "preserving existing or locally modified" in owned_install(worktree, expected=1)
    assert tree(worktree) == before
    owned_install(worktree, "--conflict", "skip")
    assert builder.read_bytes() == local_builder
    assert (worktree / ".agents/skills/builder/references/construction.md").read_bytes() == upstream.read_bytes()
    owned_install(worktree, "--conflict", "replace")
    backups = list((existing / ".git/repo-bootstrap/backups").glob("replace-*/.agents/skills/builder/SKILL.md"))
    assert len(backups) == 1 and backups[0].read_bytes() == local_builder
    assert "already current" in owned_install(worktree)
    assert not git(worktree, "status", "--porcelain", "--untracked-files=all")

    # Local exclusions must really win; negation must fail before new writes.
    (worktree / ".gitignore").write_text("!/.agents/repo-bootstrap.json\n")
    before = tree(worktree)
    assert "prevent local exclusion" in owned_install(worktree, expected=1)
    assert tree(worktree) == before
    (worktree / ".gitignore").unlink()
    owned_install(worktree, "--mode", "tracked", "--pr-template", "none")
    assert exclude.read_text() == original_exclude
    assert ".agents/" in git(worktree, "status", "--porcelain")
    git(worktree, "add", ".agents", ".claude")
    before = tree(worktree)
    assert "cannot hide tracked" in owned_install(worktree, "--mode", "local", expected=1)
    assert tree(worktree) == before

    # Go modules inherit the portable checks, while existing policies stay safe.
    go_project = workspace / "Go project"
    go_project.mkdir()
    git(go_project, "init", "--quiet")
    (go_project / "go.mod").write_text("module example.invalid/project\n\ngo 1.26.2\n")
    alternate = go_project / ".golangci.yaml"
    original_go_policy = '# Existing project policy.\nversion: "2"\nlinters:\n  default: none\n  enable: [unused]\n'
    alternate.write_text(original_go_policy)
    go_exclude = go_project / ".git/info/exclude"
    original_go_exclude = go_exclude.read_text()
    go_exclude.write_text(original_go_exclude + "\n/.golangci.yaml\n")
    before = tree(go_project)
    assert "tracked installation is ignored" in owned_install(go_project, expected=1)
    assert tree(go_project) == before, "hidden legacy dependency was installed into tracked mode"
    go_exclude.write_text(original_go_exclude)
    before = tree(go_project)
    owned_install(go_project, "--dry-run")
    assert tree(go_project) == before, "Go merge preview wrote target files"
    owned_install(go_project, "--skills", "go")
    assert alternate.read_text() == original_go_policy
    assert not (go_project / ".golangci.yml").exists()
    assert (go_project / ".golangci.strict.json").is_file()
    settings = json.loads((go_project / ".go-quality.json").read_text())
    assert settings["rollout"] == "ratchet" and settings["legacy"]["path"] == ".golangci.yaml"
    assert os.access(go_project / "scripts/check-go.sh", os.X_OK)
    assert (go_project / ".github/workflows/go-quality.yml").is_file()
    assert (go_project / ".claude/skills/go").resolve() == go_project / ".agents/skills/go"
    assert (go_project / ".claude/skills/library-code-comments/SKILL.md").is_file()
    assert (go_project / ".agents/skills/code-comments/references/standard.md").is_file()
    # Remember explicit adoption even before a new project has its module file.
    (go_project / "go.mod").unlink()
    owned_install(go_project, "--skills", "go")
    assert json.loads((go_project / ".source-code.json").read_text())["languages"] == ["go"]
    assert "already current" in owned_install(go_project, "--skills", "go")
    explicit_go = workspace / "future Go module"
    owned_install(explicit_go, "--init", "--go", "--skills", "go", "--pr-template", "none")
    assert (explicit_go / "scripts/check-go.sh").is_file()
    assert (explicit_go / ".agents/skills/library-code-comments/SKILL.md").is_file()
    assert json.loads((explicit_go / ".source-code.json").read_text())["stage"] == "beta"
    fake = workspace / "controlled lifecycle commands"
    fake.mkdir()
    boundary = fake / "bash"
    boundary.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$LIFECYCLE_TRACE"\nexit "${LIFECYCLE_FAIL:-0}"\n')
    boundary.chmod(0o755)
    trace = workspace / "lifecycle trace"
    environment = {**os.environ, "PATH": str(fake) + os.pathsep + os.environ["PATH"], "LIFECYCLE_TRACE": str(trace)}
    runner = explicit_go / "scripts/check-source-code.py"
    for stage, mode in (("research", "compile"), ("alpha", "alpha"), ("beta", "all"), ("production", "all")):
        before = tree(explicit_go)
        assert stage in owned_install(explicit_go, "--skills", "go", "--stage", stage, "--dry-run")
        assert tree(explicit_go) == before
        owned_install(explicit_go, "--skills", "go", "--stage", stage)
        run(["python3", str(runner), "go"], env=environment)
        assert trace.read_text().splitlines()[-1] == f"scripts/check-go.sh {mode}"
        assert "already current" in owned_install(explicit_go, "--skills", "go")
    run(["python3", str(runner), "go"], env={**environment, "LIFECYCLE_FAIL": "7"}, expected=7)
    policy_path = explicit_go / ".source-code.json"
    original = policy_path.read_text()
    for key, invalid in (("stage", "unknown"), ("schema_version", 99), ("policy_version", "99.0.0")):
        policy = json.loads(original)
        policy[key] = invalid
        policy_path.write_text(json.dumps(policy))
        trace_before = trace.read_bytes()
        run(["python3", str(runner), "go"], env=environment, expected=1)
        assert trace.read_bytes() == trace_before
    assert "locally modified lifecycle policy" in owned_install(explicit_go, "--skills", "go", "--stage", "research", "--conflict", "skip", expected=1)
    policy_path.write_text(original)
    legacy_runner = explicit_go / "scripts/check-go.sh"
    legacy_bytes = legacy_runner.read_bytes()
    legacy_runner.write_bytes(b"#!/bin/sh\nexit 0\n")
    manifest_path = explicit_go / ".agents/repo-bootstrap.json"
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    manifest["files"]["scripts/check-go.sh"]["sha256"] = hashlib.sha256(legacy_runner.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest))
    before = tree(explicit_go)
    assert "requires an updated go runner" in owned_install(explicit_go, "--skills", "go", "--no-go", "--stage", "research", expected=1)
    assert tree(explicit_go) == before
    legacy_runner.write_bytes(legacy_bytes)
    manifest_path.write_bytes(manifest_bytes)
    versions = json.loads(registry_bytes)
    versions["skills"]["go"] = "1.2.0"
    registry.write_text(json.dumps(versions))
    legacy_runner.write_bytes(legacy_bytes + b"\n# Local runner customization.\n")
    before = tree(explicit_go)
    assert "scripts/check-go.sh" in run([str(cli), "upgrade", "--repo", str(explicit_go), "--conflict", "skip"], expected=1)
    assert tree(explicit_go) == before, "version upgrade retained a modified runtime with a newer pin"
    legacy_runner.write_bytes(legacy_bytes)
    before = tree(explicit_go)
    assert "retained runtime" in run([str(cli), "upgrade", "--repo", str(explicit_go), "--no-go"], expected=1)
    assert tree(explicit_go) == before
    registry.write_bytes(registry_bytes)
    versions = json.loads(registry_bytes)
    versions["policy_version"] = "1.2.0"
    registry.write_text(json.dumps(versions))
    plans_path = source / "ai/skills/source-code-lifecycle/references/stages.json"
    plans_bytes = plans_path.read_bytes()
    plans = json.loads(plans_bytes)
    plans["policy_version"] = "1.2.0"
    plans_path.write_text(json.dumps(plans))
    before = tree(shared)
    assert "complete upgrade" in run([str(cli), "upgrade", "--repo", str(shared), "--skills", "pull-request"], expected=1)
    assert tree(shared) == before
    registry.write_bytes(registry_bytes)
    plans_path.write_bytes(plans_bytes)
    testing_guide.write_bytes(testing_bytes.replace(b"name: testing", b"name: testing\nname: testing"))
    before = tree(shared)
    assert "duplicate frontmatter key" in run([str(cli), "upgrade", "--repo", str(shared)], expected=1)
    assert tree(shared) == before, "invalid source instructions partially upgraded the project"
    testing_guide.write_bytes(testing_bytes)
    versions = json.loads(registry_bytes)
    versions["skills"].update({"source-code-lifecycle": "1.3.0", "pull-request": "1.1.0"})
    registry.write_text(json.dumps(versions))
    runner_asset = source / "ai/skills/source-code-lifecycle/assets/check-source-code.py"
    runner_bytes = runner_asset.read_bytes()
    runner_asset.write_bytes(runner_bytes + b"\n# New lifecycle runtime release.\n")
    for target in (shared, *(workspace / ("kind-" + name) for name in ("service", "library", "tool"))):
        if target != shared:
            saved_kind = json.loads((target / ".source-code.json").read_text())["kind"]
            (target / "source-code.toml").write_text('schema_version = 1\nstage = "research"\nkind = "' + saved_kind + '"\n')
        installed_runner = (target / "scripts/check-source-code.py").read_bytes()
        subset_view = json.loads(run([str(cli), "explain", "--skill-storage", "copied", "--repo", str(target), "--skills", "pull-request", "--json"]))
        assert subset_view["desired"]["skill_versions"]["source-code-lifecycle"] == json.loads(registry_bytes)["skills"]["source-code-lifecycle"]
        assert subset_view["desired"]["skill_versions"]["pull-request"] == "1.1.0"
        run([str(cli), "upgrade", "--repo", str(target), "--skills", "pull-request"])
        pins = json.loads((target / ".source-code.json").read_text())["skills"]
        assert pins["pull-request"] == "1.1.0" and pins["source-code-lifecycle"] == json.loads(registry_bytes)["skills"]["source-code-lifecycle"]
        assert (target / "scripts/check-source-code.py").read_bytes() == installed_runner
        run([str(cli), "validate", "--repo", str(target), "--strict"])
    runner_asset.write_bytes(runner_bytes)
    registry.write_bytes(registry_bytes)

print("PASS: portable repository and Go bootstrap with safe retrofit/update through the real CLI")
