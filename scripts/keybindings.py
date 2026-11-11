#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Generate owned shortcuts and inventory explicit Kitty/skhd source bindings."""

import argparse
from dataclasses import asdict, dataclass
import itertools
import json
from pathlib import Path
import re
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {"kitty": "kitty/kittyconf", "skhd": "yabai/skhdrc"}
BEGIN = "# BEGIN generated keybindings (scripts/keybindings.py)"
END = "# END generated keybindings"
COVERAGE = {
    "included": ["Kitty explicit root-mode maps", "skhd explicit default-mode hotkeys"],
    "excluded": ["includes", "application defaults", "macOS system shortcuts", "tmux", "Zellij", "Neovim", "live runtime state"],
    "model": "desired registry bindings plus unmanaged source bindings; skhd may intercept Kitty",
}
ALIASES = {"super": "cmd", "command": "cmd", "opt": "alt", "option": "alt", "control": "ctrl"}
MODIFIERS = ("ctrl", "alt", "shift", "cmd")
KEY_ALIASES = {
    "return": "enter", "esc": "escape", "equal": "=", "minus": "-", "hyphen": "-",
    "pageup": "page_up", "pgup": "page_up", "pagedown": "page_down", "pgdn": "page_down",
    "arrowup": "up", "arrowdown": "down", "arrowleft": "left", "arrowright": "right",
    "del": "delete", "spc": "space",
}
NAMED_KEYS = {"enter", "tab", "space", "backspace", "escape", "delete", "home", "end",
              "page_up", "page_down", "insert", "left", "right", "up", "down"}
NAMED_KEYS.update(f"f{i}" for i in range(1, 21))
SKHD_KEYS = {"enter": "return", "page_up": "pageup", "page_down": "pagedown"}


@dataclass(frozen=True)
class Binding:
    app: str
    chord: str
    action: str
    source: str
    line: int
    id: str = ""
    description: str = ""


class Invalid(ValueError):
    pass


def chord(value):
    """Normalize supported physical key names; never infer layout-dependent shifts."""
    parts = [part.strip().lower() for part in value.split("+")]
    if not parts or not all(parts):
        raise Invalid(f"invalid chord {value!r}; use named keys such as plus")
    mods = [ALIASES.get(part, part) for part in parts[:-1]]
    if len(set(mods)) != len(mods) or any(mod not in MODIFIERS for mod in mods):
        raise Invalid(f"unsupported modifiers in {value!r}")
    key = KEY_ALIASES.get(parts[-1], parts[-1])
    if not re.fullmatch(r"[a-z0-9=\-]", key) and key not in NAMED_KEYS:
        raise Invalid(f"unsupported key in {value!r}")
    return "+".join([mod for mod in MODIFIERS if mod in mods] + [key])


def registry(text):
    data = tomllib.loads(text)
    if set(data) != {"version", "binding"} or data["version"] != 1:
        raise Invalid("registry requires version = 1 and [[binding]] records")
    bindings, ids = [], set()
    locations = [i for i, line in enumerate(text.splitlines(), 1)
                 if re.fullmatch(r"\s*\[\[\s*binding\s*\]\]\s*(?:#.*)?", line)]
    for record, line in zip(data["binding"], locations, strict=True):
        if set(record) != {"id", "app", "chord", "action", "description"}:
            raise Invalid(f"registry:{line}: expected id, app, chord, action, description")
        if any(not isinstance(value, str) or not value.strip() or any(ord(c) < 32 for c in value)
               for value in record.values()):
            raise Invalid(f"registry:{line}: fields must be nonempty single-line strings")
        if record["app"] not in SOURCES or record["id"] in ids:
            raise Invalid(f"registry:{line}: unsupported app or duplicate id")
        normalized = chord(record["chord"])
        if record["app"] == "skhd" and normalized.split("+")[-1] in {"=", "-"}:
            raise Invalid(f"registry:{line}: punctuation keys are outside the skhd adapter")
        if record["action"].endswith("\\"):
            raise Invalid(f"registry:{line}: actions cannot continue onto another generated line")
        ids.add(record["id"])
        bindings.append(Binding(**{**record, "chord": normalized},
                                source="config/keybindings.toml", line=line))
    return bindings


def block_span(text):
    lines = text.splitlines(keepends=True)
    starts = [i for i, line in enumerate(lines) if line.rstrip("\r\n") == BEGIN]
    ends = [i for i, line in enumerate(lines) if line.rstrip("\r\n") == END]
    if not starts and not ends:
        return lines, None
    if len(starts) != 1 or len(ends) != 1 or starts[0] >= ends[0]:
        raise Invalid("malformed or repeated generated keybinding markers")
    return lines, (starts[0], ends[0])


def render(text, app, bindings):
    owned = [binding for binding in bindings if binding.app == app]
    lines, span = block_span(text)
    if span is None:
        if owned:
            raise Invalid(f"{SOURCES[app]}: add a generated keybinding marker pair before migrating bindings")
        return text
    generated = [BEGIN + "\n"]
    for binding in owned:
        generated.append(f"# {binding.id}: {binding.description}\n")
        parts = binding.chord.split("+")
        if app == "kitty":
            parts = ["super" if part == "cmd" else part for part in parts[:-1]] + [
                {"=": "equal", "-": "minus"}.get(parts[-1], parts[-1])]
            key = "+".join(parts)
            generated.append(f"map {key} {binding.action}\n")
        else:
            parts[-1] = SKHD_KEYS.get(parts[-1], parts[-1])
            native = " + ".join(parts[:-1]) + " - " + parts[-1] if len(parts) > 1 else parts[0]
            generated.append(f"{native} : {binding.action}\n")
    generated.append(END + "\n")
    return "".join(lines[:span[0]] + generated + lines[span[1] + 1:])


def native(text, app):
    lines, span = block_span(text)
    bindings, pending, start = [], "", 0
    for number, raw in enumerate(lines, 1):
        if span and span[0] <= number - 1 <= span[1]:
            continue
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not pending:
            start = number
        pending += stripped.removesuffix("\\").rstrip() if stripped.endswith("\\") else stripped
        if stripped.endswith("\\"):
            pending += " "
            continue
        entry, pending = pending, ""
        try:
            if app == "kitty":
                if not re.match(r"(?:map|clear_all_shortcuts|action_alias|kitten_alias)\b", entry):
                    continue
                match = re.fullmatch(r"map\s+(\S+)\s+(.+)", entry)
                if not match:
                    raise Invalid("unsupported Kitty binding directive")
                key, action = match.groups()
                if key.startswith("--") or ">" in key:
                    raise Invalid("Kitty modes/options/sequences require a new adapter")
            else:
                match = re.fullmatch(r"([^:;<>\[\]]+)\s*:\s*(.+)", entry)
                if not match:
                    raise Invalid("skhd modes, process maps, includes and forwarding require a new adapter")
                key, action = match.groups()
                key = re.sub(r"\s*-\s*", "+", key.strip(), count=1)
                if re.search(r"(?:^|\+)\s*(?:[A-Z]|0x[0-9a-fA-F]+)\s*$", key):
                    raise Invalid("skhd uppercase literals and hardware keycodes require a new adapter")
                if key.strip().split("+")[-1].strip() in {"=", "-"}:
                    raise Invalid("punctuation keys are outside the skhd adapter")
            bindings.append(Binding(app, chord(key.strip()), action, SOURCES[app], start))
        except Invalid as error:
            raise Invalid(f"{SOURCES[app]}:{start}: {error}") from error
    if pending:
        raise Invalid(f"{SOURCES[app]}:{start}: unterminated continuation")
    return bindings


def conflicts(bindings):
    return [{"chord": a.chord, "kind": "duplicate" if a.app == b.app else "global-overlap",
             "bindings": [asdict(a), asdict(b)]}
            for a, b in itertools.combinations(bindings, 2) if a.chord == b.chord]


def inspect(root):
    owned = registry((root / "config/keybindings.toml").read_text())
    bindings, outputs = list(owned), {}
    for app, path in SOURCES.items():
        original = (root / path).read_text()
        outputs[path] = render(original, app, owned)
        bindings.extend(native(original, app))
    drift = [path for path, output in outputs.items() if (root / path).read_text() != output]
    return bindings, outputs, drift


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="dotfiles checkout to inspect")
    commands = parser.add_subparsers(dest="command", required=True)
    listing = commands.add_parser("list", help="inventory desired owned and existing unmanaged bindings")
    listing.add_argument("--chord", help="filter by chord, for example cmd+shift+l")
    listing.add_argument("--json", action="store_true")
    check = commands.add_parser("check", help="fail on conflicts or generated drift")
    check.add_argument("--json", action="store_true")
    generate = commands.add_parser("generate", help="update only marked owned sections; no runtime reload")
    generate.add_argument("--check", action="store_true", help="fail on drift without writing")
    args = parser.parse_args(argv)
    try:
        bindings, outputs, drift = inspect(args.root)
        overlaps = conflicts(bindings)
        if args.command == "generate":
            if overlaps:
                raise Invalid("resolve reported conflicts with 'check' before generating")
            if args.check:
                for path in drift:
                    print(f"stale generated bindings: {path}", file=sys.stderr)
                return int(bool(drift))
            for path in drift:
                (args.root / path).write_text(outputs[path])
                print(f"updated {path}")
            return 0
        if args.command == "list" and args.chord:
            wanted = chord(args.chord)
            bindings = [binding for binding in bindings if binding.chord == wanted]
            overlaps = conflicts(bindings)
        report = {"coverage": COVERAGE, "bindings": [asdict(binding) for binding in bindings],
                  "conflicts": overlaps, "drift": drift}
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print("Coverage: explicit Kitty/skhd source bindings (desired owned + unmanaged).")
            print("Excluded: " + ", ".join(COVERAGE["excluded"]) + ".")
            for binding in bindings:
                print(f"{binding.chord:24} {binding.app:6} {binding.source}:{binding.line}  {binding.action}")
            for overlap in overlaps:
                print(f"CONFLICT {overlap['chord']}: {overlap['kind']}")
            for path in drift:
                print(f"DRIFT {path}")
        return int(args.command == "check" and bool(overlaps or drift))
    except (Invalid, OSError, ValueError, TypeError, KeyError) as error:
        print(f"keybindings: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
