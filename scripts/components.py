#!/usr/bin/env python3
"""Own repository inputs once, then use them for installation and CI selection."""

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import tomllib

from component_sandbox import sandbox_command, runtime_paths


ROOT = Path(__file__).resolve().parents[1]
TABLE = "config/components-install.tsv"
INFRA = {TABLE, "scripts/components.py", "scripts/component_sandbox.py",
         "scripts/test-components.py", "scripts/make/components-install.sh",
         ".github/workflows/components.yml"}
FIELDS = {"version", "dependencies", "legacy_inputs", "platforms", "tools", "install", "suites"}


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args])


def relative(value):
    if (not isinstance(value, str) or not value or
            any(character in value for character in "\t\r\n\\") or
            PurePosixPath(value).is_absolute() or
            any(part in ("", ".", "..") for part in value.split("/"))):
        raise ValueError(f"unsafe relative path: {value!r}")
    return value


class Tree:
    """Read a working tree or immutable Git revision without checking it out."""

    def __init__(self, root, ref=None):
        self.root, self.ref = Path(root).resolve(), ref
        if ref:
            entries = git(root, "ls-tree", "-r", "-z", ref).split(b"\0")
            self.modes = {}
            for entry in filter(None, entries):
                info, path = entry.split(b"\t", 1)
                self.modes[os.fsdecode(path)] = info.split()[0].decode()
        else:
            if (self.root / "components").is_symlink():
                raise ValueError("components directory cannot be a symlink")
            self.modes = {}
            # New component files inherit ownership before their first commit.
            for directory in sorted((self.root / "components").glob("*")):
                if directory.is_symlink():
                    raise ValueError(f"component directory cannot be a symlink: {directory}")
                for path in directory.rglob("*"):
                    if any(part in {".venv", "__pycache__", ".pytest_cache"} for part in path.parts):
                        continue
                    if path.is_file() or path.is_symlink():
                        self.modes[path.relative_to(self.root).as_posix()] = "120000" if path.is_symlink() else "100644"

    def exists(self, path):
        return path in self.modes if self.ref else (self.root / path).is_file()

    def read(self, path):
        if self.ref:
            return git(self.root, "show", f"{self.ref}:{path}").decode()
        return (self.root / path).read_text()

    def link(self, path):
        if self.ref:
            return self.read(path) if self.modes.get(path) == "120000" else None
        candidate = self.root / path
        return os.readlink(candidate) if candidate.is_symlink() else None


def load(tree):
    manifests = sorted(path for path in tree.modes
                       if re.fullmatch(r"components/[a-z][a-z0-9-]*/component\.toml", path))
    result = {}
    destinations = {}
    for path in manifests:
        name = path.split("/")[1]
        data = tomllib.loads(tree.read(path))
        if set(data) != FIELDS or type(data["version"]) is not int or data["version"] != 1:
            raise ValueError(f"{path}: expected version 1 fields {sorted(FIELDS)}")
        for field in ("dependencies", "legacy_inputs", "platforms", "tools"):
            values = data[field]
            if (not isinstance(values, list) or any(not isinstance(v, str) or not v for v in values)
                    or len(values) != len(set(values))):
                raise ValueError(f"{path}: {field} must contain unique strings")
        if not data["platforms"] or set(data["platforms"]) - {"linux", "darwin"}:
            raise ValueError(f"{path}: unsupported platforms")
        if any(not re.fullmatch(r"[a-zA-Z0-9_.+-]+", tool) for tool in data["tools"]):
            raise ValueError(f"{path}: tools must be executable names")
        for legacy in data["legacy_inputs"]:
            relative(legacy)
            if (legacy.startswith("components/") or not tree.exists(legacy) or
                    any(tree.link(str(parent)) for parent in (PurePosixPath(legacy), *PurePosixPath(legacy).parents))):
                raise ValueError(f"{path}: legacy input must be an existing regular legacy file: {legacy}")
        if not isinstance(data["install"], dict) or not isinstance(data["suites"], dict) or not data["suites"]:
            raise ValueError(f"{path}: install and nonempty suites must be tables")
        for source, destination in data["install"].items():
            relative(source)
            relative(destination)
            if not tree.exists(f"components/{name}/{source}"):
                raise ValueError(f"{path}: missing installation source {source}")
            if any(destination == old or destination.startswith(old + "/") or old.startswith(destination + "/") for old in destinations):
                raise ValueError(f"duplicate installation destination or parent: {destination}")
            destinations[destination] = name
        for suite, command in data["suites"].items():
            if (not re.fullmatch(r"[a-z][a-z0-9-]*", suite) or not isinstance(command, list) or
                    not command or any(not isinstance(arg, str) or not arg or "\0" in arg for arg in command)):
                raise ValueError(f"{path}: suite commands must be nonempty argument arrays")
        result[name] = data
    for name, data in result.items():
        for dependency in data["dependencies"]:
            if dependency not in result:
                raise ValueError(f"{name}: unknown dependency {dependency}")
        closure(result, name)
    for path in tree.modes:
        if not path.startswith("components/"):
            continue
        name = path.split("/")[1]
        if name not in result:
            raise ValueError(f"component file has no manifest: {path}")
        target = tree.link(path)
        if target is not None:
            if PurePosixPath(target).is_absolute():
                raise ValueError(f"absolute input symlink: {path}")
            current, visited = path, set()
            while tree.link(current) is not None:
                if current in visited:
                    raise ValueError(f"cyclic input symlink: {path}")
                visited.add(current)
                current = os.path.normpath(str(PurePosixPath(current).parent / tree.link(current)))
                if not any(current.startswith(f"components/{owner}/") for owner in closure(result, name)):
                    raise ValueError(f"undeclared input symlink: {path} -> {current}")
            if not tree.exists(current):
                raise ValueError(f"broken input symlink: {path}")
    return result


def closure(graph, name, stack=()):
    if name in stack:
        raise ValueError("dependency cycle: " + " -> ".join((*stack, name)))
    found = {name}
    for dependency in graph[name]["dependencies"]:
        found.update(closure(graph, dependency, (*stack, name)))
    return found


def install_table(graph):
    return "".join(f"{name}\tcomponents/{name}/{source}\t{destination}\n"
                   for name, data in sorted(graph.items())
                   for source, destination in sorted(data["install"].items()))


def owners(graph, path):
    found = set()
    for name, data in graph.items():
        if path.startswith(f"components/{name}/") or path in data["legacy_inputs"]:
            found.add(name)
        for destination in data["install"].values():
            if destination.startswith(".local/bin/") and path == "bin/" + destination.removeprefix(".local/bin/"):
                found.add(name)
    return found


def select(graphs, changed):
    current = graphs[-1]
    reasons = {name: [] for name in current}
    for path in changed:
        recognized = False
        for graph in graphs:
            direct = owners(graph, path)
            recognized |= bool(direct)
            for name in graph:
                if name in reasons and closure(graph, name) & direct:
                    reasons[name].append(path)
        if path in INFRA or not recognized:
            for values in reasons.values():
                values.append(path)
    return {name: sorted(set(paths)) for name, paths in sorted(reasons.items()) if paths}


def plan(root, base, head, full=False):
    # Resolve refs once so concurrent branch movement cannot mix graph revisions.
    head = git(root, "rev-parse", "--verify", f"{head}^{{commit}}").decode().strip()
    base = git(root, "rev-parse", "--verify", f"{base}^{{commit}}").decode().strip()
    graphs = [load(Tree(root, ref)) for ref in (base, head)]
    changed = [os.fsdecode(path) for path in git(root, "diff", "--no-renames", "--name-only", "-z", base, head).split(b"\0") if path]
    selected = {name: ["full run"] for name in sorted(graphs[-1])} if full else select(graphs, changed)
    matrix = [{"component": name, "os": f"{platform}-latest"}
              for name in selected for platform in ("ubuntu", "macos")
              if ("linux" if platform == "ubuntu" else "darwin") in graphs[-1][name]["platforms"]]
    return {"base": base, "head": head, "selected": selected, "matrix": {"include": matrix}}


def project(tree, graph, name, stage):
    members = closure(graph, name)
    inputs = {path for path in tree.modes if any(path.startswith(f"components/{member}/") for member in members)}
    inputs.update(path for member in members for path in graph[member]["legacy_inputs"])
    for path in sorted(inputs):
        source, target = tree.root / path, stage / path
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_symlink():
            target.symlink_to(os.readlink(source))
        else:
            shutil.copy2(source, target)
    # Tests use the same generated Bash installer as real shell configuration.
    helper = stage / ".runner/install.sh"
    helper.parent.mkdir(parents=True)
    shutil.copy2(tree.root / "scripts/make/components-install.sh", helper)
    (stage / "config").mkdir(exist_ok=True)
    (stage / TABLE).write_text(install_table({member: graph[member] for member in members}))
    home = stage.parent / "home"
    subprocess.run(["bash", str(helper), str(stage), str(home)], check=True)
    # Compatibility paths resolve through the installation, so missing mappings fail tests.
    for member in members:
        for destination in graph[member]["install"].values():
            if destination.startswith(".local/bin/"):
                link = stage / "bin" / Path(destination).name
                link.parent.mkdir(exist_ok=True)
                link.symlink_to(home / destination)
    return home


def prepare_runtime(component, temporary):
    config = component / "pyproject.toml"
    if not config.exists():
        return Path(sys.executable).resolve()
    runtime = temporary / "runtime"
    runtime.mkdir()
    for name in ("pyproject.toml", "uv.lock"):
        shutil.copy2(component / name, runtime / name)
    subprocess.run(["uv", "sync", "--locked", "--project", str(runtime), "--python", str(Path(sys.executable).resolve())], check=True)
    return runtime / ".venv/bin/python3"


@contextmanager
def workspace():
    path = Path(tempfile.mkdtemp(prefix="c-", dir="/tmp")).resolve()
    environments = []
    try:
        yield path, environments
    except BaseException:
        (path / "script-environments.json").write_text(json.dumps([str(item) for item in environments]))
        print(f"Component diagnostics retained at {path}", file=sys.stderr)
        destination = os.environ.get("COMPONENT_DIAGNOSTICS")
        if destination:
            shutil.copytree(path, Path(destination) / path.name)
        raise
    else:
        for environment in environments:
            shutil.rmtree(environment)
        shutil.rmtree(path)


def run_tests(root, names, suite=None):
    tree = Tree(root)
    graph = load(tree)
    if not names:
        raise ValueError("choose a component or --all")
    for name in names:
        if name not in graph:
            raise ValueError(f"unknown component: {name}")
        data = graph[name]
        if sys.platform not in data["platforms"]:
            raise ValueError(f"{name}: unsupported platform {sys.platform}")
        if suite and suite not in data["suites"]:
            raise ValueError(f"{name}: unknown suite {suite}")
        tools = {tool for member in closure(graph, name) for tool in graph[member]["tools"]} | {"python3"}
        for tool in tools:
            if not shutil.which(tool):
                raise ValueError(f"{name}: required tool unavailable: {tool}")
        with workspace() as (temporary, environments):
            stage = temporary / "source"
            stage.mkdir()
            home = project(tree, graph, name, stage)
            work = temporary / "t"
            work.mkdir()
            python = prepare_runtime(stage / "components" / name, temporary)
            cache = Path(subprocess.check_output(["uv", "cache", "dir"], text=True).strip()).resolve() if "uv" in tools else None
            environment = {"HOME": str(home), "PATH": os.defpath, "TMPDIR": str(work) + "/",
                           "LANG": "C", "LC_ALL": "C", "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1",
                           "PYTHONNOUSERSITE": "1", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
                           "PYTEST_ADDOPTS": "-p no:cacheprovider",
                           "COMPONENT_SOURCE_ROOT": str(stage), "COMPONENT_INSTALL_HOME": str(home),
                           "XDG_CONFIG_HOME": str(home / ".config"), "XDG_STATE_HOME": str(home / ".local/state"),
                           "XDG_CACHE_HOME": str(home / ".cache"), "GIT_CONFIG_NOSYSTEM": "1",
                           "GIT_CONFIG_GLOBAL": os.devnull, "UV_OFFLINE": "1", "UV_PYTHON_DOWNLOADS": "never",
                           "UV_PYTHON_PREFERENCE": "only-system", "UV_PYTHON": str(Path(sys.executable).resolve())}
            bins = temporary / "tools"
            bins.mkdir()
            for tool in sorted(tools):
                executable = python if tool == "python3" else Path(shutil.which(tool)).resolve()
                if sys.platform == "darwin" and tool == "git" and executable == Path("/usr/bin/git"):
                    executable = Path(subprocess.check_output(["xcrun", "--find", "git"], text=True).strip())
                if executable.stat().st_mode & (stat.S_ISUID | stat.S_ISGID):
                    # macOS refuses set-id executables inside a sandbox. Tests inspect their own processes.
                    shutil.copyfile(executable, bins / tool)
                    (bins / tool).chmod(0o755)
                    if sys.platform == "darwin":
                        subprocess.run(["codesign", "--force", "--sign", "-", str(bins / tool)], check=True)
                else:
                    (bins / tool).symlink_to(executable)
            environment["PATH"] = str(python.parent) + os.pathsep + str(bins) + os.pathsep + os.defpath
            git_exec = Path(subprocess.check_output([str(bins / "git"), "--exec-path"], text=True).strip())
            if sys.platform == "darwin" and not git_exec.is_dir():
                developer = Path(subprocess.check_output(["xcode-select", "-p"], text=True).strip())
                git_exec = developer / "usr/libexec/git-core"
            environment["GIT_EXEC_PATH"] = str(git_exec)
            templates = git_exec.parents[1] / "share/git-core/templates"
            if templates.is_dir():
                environment["GIT_TEMPLATE_DIR"] = str(templates)
            if cache:
                environment["UV_CACHE_DIR"] = str(cache)
                for script in (stage / "components" / name / "bin").iterdir():
                    if not script.is_symlink() and "# /// script" in script.read_text():
                        prepared = subprocess.run(
                            ["uv", "sync", "--script", str(script), "--python", str(Path(sys.executable).resolve())],
                            capture_output=True, text=True, env={**os.environ, "NO_COLOR": "1"})
                        sys.stderr.write(prepared.stderr)
                        prepared.check_returncode()
                        for line in prepared.stderr.splitlines():
                            if line.startswith("Creating script environment at: "):
                                location = Path(line.removeprefix("Creating script environment at: "))
                                if location.parent == cache / "environments-v2" and location.name.startswith(script.name + "-"):
                                    environments.append(location)
            read = runtime_paths(python, tools) + [temporary]
            write = [home, work]
            if cache:
                read.append(cache)
                write.append(cache)
            denied_roots = {root.resolve()}
            for entry in git(root, "worktree", "list", "--porcelain", "-z").split(b"\0"):
                if entry.startswith(b"worktree "):
                    denied_roots.add(Path(os.fsdecode(entry[9:])).resolve())
            denied_roots.add(Path(git(root, "rev-parse", "--path-format=absolute", "--git-common-dir").decode().strip()).resolve())
            command = sandbox_command(read, write, temporary, environment, sorted(denied_roots))
            (temporary / "environment.json").write_text(json.dumps(environment, indent=2))
            probe = temporary / "probe.py"
            probe.write_text('''import os, pathlib, subprocess, sys
assert pathlib.Path(sys.argv[1]).read_text() == "declared\\n"
reader = "import pathlib,sys; pathlib.Path(sys.argv[1]).read_bytes()"
subprocess.run([sys.executable, "-c", reader, sys.argv[1]], check=True, capture_output=True)
for denied in sys.argv[2:]:
    result = subprocess.run([sys.executable, "-c", reader, denied], capture_output=True)
    assert result.returncode != 0, "sandbox allowed undeclared read: " + denied
parent = pathlib.Path(sys.argv[1]).parent
immutable = [parent / "probe.py", parent / "source/.runner/install.sh"]
if (parent / "sandbox.sb").exists():
    immutable.append(parent / "sandbox.sb")
for path in immutable:
    result = subprocess.run([sys.executable, "-c", "import pathlib,sys; pathlib.Path(sys.argv[1]).write_text('unexpected write')", str(path)], capture_output=True)
    assert result.returncode != 0, "sandbox allowed input or policy mutation: " + str(path)
''')
            declared = temporary / "declared"
            declared.write_text("declared\n")
            alias = temporary / "undeclared-source"
            alias.symlink_to(root / "Makefile")
            denied = [str(root / "Makefile"), str(root / "sh/alias"), str(alias)]
            subprocess.run([*command, str(python), str(probe), str(declared), *denied], env=environment, check=True, cwd=temporary)
            for identifier, argv in data["suites"].items():
                if suite and identifier != suite:
                    continue
                print(f"== {name}/{identifier} ({sys.platform}, enforced inputs) ==", flush=True)
                subprocess.run([*command, *argv], cwd=stage / "components" / name, env=environment, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    commands = parser.add_subparsers(dest="operation", required=True)
    commands.add_parser("validate")
    generate = commands.add_parser("generate")
    generate.add_argument("--check", action="store_true")
    selector = commands.add_parser("plan")
    selector.add_argument("--base", required=True)
    selector.add_argument("--head", default="HEAD")
    selector.add_argument("--all", action="store_true")
    selector.add_argument("--json", action="store_true")
    test = commands.add_parser("test")
    test.add_argument("component", nargs="?")
    test.add_argument("--all", action="store_true")
    test.add_argument("--suite")
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        if args.operation == "plan":
            result = plan(root, args.base, args.head, args.all)
            if args.json:
                print(json.dumps(result))
            else:
                for name, reasons in result["selected"].items():
                    print(f"{name}: {', '.join(reasons)}")
            return
        graph = load(Tree(root))
        expected = install_table(graph)
        if args.operation == "generate" and not args.check:
            (root / TABLE).write_text(expected)
        elif args.operation in {"validate", "generate"}:
            if (root / TABLE).read_text() != expected:
                raise ValueError("installation table is stale; run python3 scripts/components.py generate")
            print(f"Validated {len(graph)} components and installation table")
        else:
            if args.all and (args.component or args.suite):
                raise ValueError("--all cannot be combined with a component or suite")
            run_tests(root, sorted(graph) if args.all else [args.component] if args.component else [], args.suite)
    except (ValueError, OSError, subprocess.CalledProcessError, tomllib.TOMLDecodeError) as error:
        parser.exit(1, f"components: {error}\n")


if __name__ == "__main__":
    main()
