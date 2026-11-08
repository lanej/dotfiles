#!/usr/bin/env python3
"""Compile shared theme roles into native files; never reload applications."""

import argparse
import json
from pathlib import Path
import re
import sys
import tomllib
import unicodedata
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "design-system"
HEX = re.compile(r"#[0-9a-fA-F]{6}\Z")


def read(path):
    return json.loads(path.read_text())


def resolve(theme, defaults=None):
    palette = theme["palette"]
    definitions = {**theme["roles"], **{name: definition for name, definition in (defaults or {}).items() if name not in theme["roles"]}}
    if not palette or any(not isinstance(v, str) or not HEX.fullmatch(v) for v in palette.values()):
        raise ValueError("palette values must be #RRGGBB colors")
    resolved, visiting = {}, set()

    def value(spec):
        if isinstance(spec, str):
            if spec.startswith("$"):
                return palette[spec[1:]].upper()
            if spec.startswith("@"):
                return role(spec[1:])
            if spec == "default":
                return spec
        if isinstance(spec, dict) and set(spec) == {"mix", "amount"}:
            if not isinstance(spec["mix"], list) or len(spec["mix"]) != 2:
                raise ValueError("mix requires two color references")
            amount = spec["amount"]
            if type(amount) not in (int, float) or not 0 <= amount <= 1:
                raise ValueError("mix amount must be between zero and one")
            colors = [value(s) for s in spec["mix"]]
            if "default" in colors:
                raise ValueError("cannot blend an inherited background")
            return "#" + "".join(f"{round(int(colors[0][i:i+2], 16) * (1-amount) + int(colors[1][i:i+2], 16) * amount):02X}" for i in (1, 3, 5))
        raise ValueError(f"invalid color definition: {spec!r}")

    def role(name):
        if name in visiting:
            raise ValueError(f"cyclic role: {name}")
        if name not in resolved:
            visiting.add(name)
            resolved[name] = value(definitions[name])
            visiting.remove(name)
        return resolved[name]

    for name in definitions:
        role(name)
    return resolved, value


class Presentation:
    def __init__(self, definitions, overrides):
        unknown = set(overrides) - set(definitions)
        if unknown:
            raise ValueError("unknown presentation overrides: " + ", ".join(sorted(unknown)))
        self.definitions, self.overrides = definitions, overrides
        self.values, self.visiting, self.consumers = {}, set(), {}
        for name in definitions:
            self.get(name)

    def get(self, name, consumer=None, expected=None, unit=None):
        definition = self.definitions[name]
        kind = definition["type"]
        if expected is not None and kind != expected:
            raise ValueError(f"{name}: expected {expected}, got {kind}")
        if unit is not None and definition.get("unit") != unit:
            raise ValueError(f"{name}: expected unit {unit}")
        if consumer:
            self.consumers.setdefault(name, set()).add(consumer)
            reference = self.overrides.get(name, definition["value"])
            if isinstance(reference, dict) and set(reference) == {"token"}:
                self.get(reference["token"], consumer, kind, definition.get("unit"))
        if name in self.visiting:
            raise ValueError(f"cyclic presentation token: {name}")
        if name not in self.values:
            self.visiting.add(name)
            result = self.overrides.get(name, definition["value"])
            if isinstance(result, dict) and set(result) == {"token"}:
                result = self.get(result["token"], consumer, kind, definition.get("unit"))
            if kind == "boolean":
                valid = type(result) is bool and "unit" not in definition
            elif kind == "string":
                valid = isinstance(result, str) and not any(unicodedata.category(c) in ("Cc", "Cs") for c in result) and "unit" not in definition
            elif kind == "dimension":
                valid = type(result) is int and result >= 0 and definition.get("unit") in ("cell", "row")
            else:
                valid = False
            if not valid:
                raise ValueError(f"invalid {kind} token {name}: {result!r}")
            self.values[name] = result
            self.visiting.remove(name)
        return self.values[name]

    def reference(self, reference, consumer):
        if set(reference) == {"token"}:
            return self.get(reference["token"], consumer)
        if set(reference) == {"token", "as"} and reference["as"] == "spaces":
            return " " * self.get(reference["token"], consumer, "dimension", "cell")
        raise ValueError(f"invalid token reference: {reference!r}")

    def catalog(self):
        return {name: {**definition, "resolved": self.values[name], "override": self.overrides.get(name), "consumers": sorted(self.consumers.get(name, set()))} for name, definition in self.definitions.items()}


def expand(data, value, tokens=None, consumer=None):
    if isinstance(data, dict):
        if "token" in data:
            return tokens.reference(data, consumer)
        return {k: expand(v, value, tokens, consumer) for k, v in data.items()}
    if isinstance(data, list):
        return [expand(v, value, tokens, consumer) for v in data]
    if isinstance(data, str) and data.startswith(("@", "$")):
        return value(data)
    return data


def lua(value):
    if isinstance(value, dict):
        return "{\n" + "".join(f"[{json.dumps(k)}] = {lua(v)},\n" for k, v in value.items()) + "}"
    if isinstance(value, list):
        return "{" + ", ".join(lua(v) for v in value) + "}"
    if isinstance(value, bool):
        return "true" if value else "false"
    return json.dumps(value, ensure_ascii=False)


def validate_style(style):
    if not isinstance(style, dict):
        raise ValueError("style must be an object")
    for key, val in style.items():
        if key in ("fg", "bg", "sp"):
            if not isinstance(val, str) or (val != "default" and not HEX.fullmatch(val)):
                raise ValueError(f"invalid {key} color: {val!r}")
        elif key in ("bold", "italic", "underline", "undercurl", "strikethrough", "reverse"):
            if type(val) is not bool:
                raise ValueError(f"invalid {key} attribute: {val!r}")
        elif key != "link":
            raise ValueError(f"unsupported style attribute: {key}")


def compile_theme(source, theme_name):
    if not re.fullmatch(r"[a-z][a-z0-9-]*", theme_name):
        raise ValueError("invalid theme name")
    theme = read(source / "themes" / f"{theme_name}.json")
    if theme["name"] != theme_name:
        raise ValueError("theme name disagrees with filename")
    shared = read(source / "tokens.json")
    tokens = Presentation(shared["presentation"], theme.get("presentation", {}))
    colors, value = resolve(theme, shared["roles"])
    components = expand(read(source / "components.json"), value, tokens, "components")
    for style in components.values():
        validate_style(style)
    ansi = [value(v) for v in theme["ansi"]]
    if len(ansi) != 16 or "default" in ansi:
        raise ValueError("ANSI palette requires sixteen literal colors")
    states = expand(read(source / "adapters/tmux-states.json"), value)
    for style in states.values():
        validate_style(style)
    outputs = {}

    def output(name, content):
        outputs[name] = content.rstrip() + "\n"

    c = colors
    output("colors.json", json.dumps({"theme": theme_name, "roles": c, "components": components, "ansi": ansi}, indent=2))
    output("theme.py", '# Generated by scripts/theme.py.\nCOLORS = ' + repr(c) + '\nCOMPONENTS = ' + repr(components) + '\nSTATE_STYLES = ' + repr(states) + '\nTOKENS = ' + repr(tokens.values))
    fzf = {"fg": "text", "bg": "surface", "fg+": "selection.fg", "bg+": "selection.bg", "hl": "match", "hl+": "match", "pointer": "accent", "marker": "status.success", "header": "heading", "prompt": "prompt", "info": "text.muted", "border": "border", "spinner": "status.info"}
    fzf_color = "dark," + ",".join(k + ":" + c[v] for k, v in fzf.items())
    output("fzf.txt", "--color=" + fzf_color)
    output("shell.sh", '# Generated by scripts/theme.py; source after application defaults.\nexport BAT_THEME=Dotfiles\nexport DOTFILES_FZF_COLOR=' + "'" + fzf_color + "'\ncase \" ${FZF_DEFAULT_OPTS-} \" in\n    *\" --color=$DOTFILES_FZF_COLOR \"*) ;;\n    *) export FZF_DEFAULT_OPTS=\"${FZF_DEFAULT_OPTS:+$FZF_DEFAULT_OPTS }--color=$DOTFILES_FZF_COLOR\" ;;\nesac")
    kitty = {"foreground": "text", "background": "surface", "selection_foreground": "selection.fg", "selection_background": "selection.bg", "cursor": "accent", "cursor_text_color": "surface", "active_tab_foreground": "tab.active.fg", "active_tab_background": "tab.active.bg", "inactive_tab_foreground": "tab.inactive.fg", "inactive_tab_background": "tab.inactive.bg", "active_border_color": "focus", "inactive_border_color": "border", "url_color": "link"}
    output("kitty.conf", "# Generated by scripts/theme.py.\n" + "\n".join(f"{k} {c[v]}" for k, v in kitty.items()) + "\n" + "\n".join(f"color{i} {v}" for i, v in enumerate(ansi)))

    highlights = read(source / "adapters/neovim.json")
    for name, style in highlights.items():
        if "component" in style:
            expand(read(source / "components.json")[style["component"]], value, tokens, "neovim")
            style = {**components[style["component"]], **{k: v for k, v in style.items() if k != "component"}}
        if "link" in style and style["link"] not in highlights:
            raise ValueError(f"unresolved highlight link: {name}")
        highlights[name] = {key: val if key == "link" else expand(val, value, tokens, "neovim") for key, val in style.items()}
        validate_style(highlights[name])
        for key in ("fg", "bg", "sp"):
            if key in highlights[name] and highlights[name][key] == "default":
                highlights[name][key] = "NONE"
    for name in highlights:
        visited, current = set(), name
        while "link" in highlights[current]:
            if current in visited:
                raise ValueError(f"cyclic highlight link: {name}")
            visited.add(current)
            current = highlights[current]["link"]
    for name in tokens.definitions:
        if name.startswith("symbol.git.") and not name.startswith("symbol.git.file."):
            tokens.get(name, "neovim", "string")
    separators = {kind: {side: tokens.get(f"symbol.separator.{kind}.{side}", "neovim", "string") for side in ("left", "right")} for kind in ("section", "component")}
    output("neovim.lua", "-- Generated by scripts/theme.py.\nreturn " + lua({"highlights": highlights, "ansi": ansi, "roles": c, "tokens": tokens.values, "separators": separators}))

    def rgb(role):
        return " ".join(str(int(c[role][i:i+2], 16)) for i in (1, 3, 5))

    styles = read(source / "adapters/zellij.json")
    kdl = ["// Generated by scripts/theme.py.", "themes {", "    dotfiles {"]
    for name, fields in styles.items():
        kdl += [f"        {name} {{"] + [f"            {field} {rgb(role)}" for field, role in fields.items()] + ["        }"]
    kdl += ["    }", "}"]
    output("zellij.kdl", "\n".join(kdl))
    template = (source / "adapters/tmux.conf.in").read_text()
    mappings = dict(c)
    for name in tokens.definitions:
        if "{{" + name + "}}" in template:
            if name == "space.inline":
                mappings[name] = " " * tokens.get(name, "tmux", "dimension", "cell")
            else:
                symbol = tokens.get(name, "tmux", "string")
                if any(c in symbol for c in '#[]{}",%\\'):
                    raise ValueError(f"{name}: tmux separator contains native format syntax")
                mappings[name] = symbol
    for field, fallback in {"bg": c["surface.raised"], "fg": c["text"]}.items():
        selected = fallback.replace("#", "##")
        for name, style in reversed(list(states.items())):
            selected = "#{?#{==:#{@claude-state}," + name + "}," + style[field].replace("#", "##") + "," + selected + "}"
        mappings["agent." + field] = selected
    rendered = re.sub(r"\{\{([a-z.]+)\}\}", lambda m: mappings[m[1]], template)
    if "{{" in rendered:
        raise ValueError("unresolved tmux template placeholder")
    output("tmux.conf", rendered)
    glow = expand(read(source / "adapters/glow.json"), value, tokens, "glow")
    if type(glow["heading"]["bold"]) is not bool or type(glow["h1"]["bold"]) is not bool:
        raise ValueError("Glow heading emphasis must be boolean")
    output("glow.json", json.dumps(glow, indent=2, ensure_ascii=False))
    starship = (source / "adapters/starship.toml.in").read_text()

    def starship_symbol(match):
        symbol = tokens.get(match[1], "starship", "string")
        escaped = re.sub(r"([\\$\[\]()])", r"\\\1", symbol)
        return json.dumps(escaped, ensure_ascii=False)[1:-1]

    starship = re.sub(r"\{\{([a-z.]+)\}\}", starship_symbol, starship)
    if "{{" in starship:
        raise ValueError("unresolved Starship template placeholder")
    tomllib.loads(starship)
    output("starship.toml", starship)
    output("delta.gitconfig", f'''# Generated by scripts/theme.py.
[delta "dotfiles"]
    syntax-theme = Dotfiles
    plus-style = syntax "{c['diff.add.bg']}"
    plus-non-emph-style = syntax "{c['diff.add.bg']}"
    plus-emph-style = bold syntax "{c['diff.add.emph.bg']}"
    plus-empty-line-marker-style = normal "{c['diff.add.bg']}"
    minus-style = syntax "{c['diff.delete.bg']}"
    minus-non-emph-style = syntax "{c['diff.delete.bg']}"
    minus-emph-style = bold syntax "{c['diff.delete.emph.bg']}"
    whitespace-error-style = "{c['status.error']}" reverse''')
    syntax = ET.Element("plist", version="1.0")
    dictionary = ET.SubElement(syntax, "dict")

    def entry(parent, key, val):
        ET.SubElement(parent, "key").text = key
        ET.SubElement(parent, "string").text = val

    entry(dictionary, "name", "Dotfiles")
    ET.SubElement(dictionary, "key").text = "settings"
    settings = ET.SubElement(dictionary, "array")
    scopes = read(source / "adapters/syntax.json")
    for scope, role in {"": "text", **scopes}.items():
        item = ET.SubElement(settings, "dict")
        if scope:
            entry(item, "scope", scope)
        ET.SubElement(item, "key").text = "settings"
        attributes = ET.SubElement(item, "dict")
        entry(attributes, "foreground", c[role])
        if not scope:
            entry(attributes, "background", c["surface"])
            entry(attributes, "selection", c["selection.bg"])
    ET.indent(syntax)
    output("Dotfiles.tmTheme", '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(syntax, encoding="unicode"))
    bottom = (source / "adapters/bottom.toml.in").read_text()
    rendered = re.sub(r"\{\{([a-z.]+)\}\}", lambda m: c[m[1]], bottom)
    if "{{" in rendered:
        raise ValueError("unresolved bottom template placeholder")
    output("bottom.toml", rendered)
    lualine = {}
    for mode, role in {"normal": "accent", "insert": "status.success", "visual": "syntax.number", "replace": "status.error", "command": "status.warning", "inactive": "text.muted"}.items():
        lualine[mode] = {"a": {"fg": c["text.inverse"], "bg": c[role], "gui": "bold"}, "b": {"fg": c["text"], "bg": c["surface.selected"]}, "c": {"fg": c["text.muted"], "bg": c["surface"]}}
    output("lualine.lua", "-- Generated by scripts/theme.py.\nreturn " + lua(lualine))
    output("tokens.json", json.dumps({"theme": theme_name, "presentation": tokens.catalog()}, indent=2, ensure_ascii=False))
    validate_catalog(source)
    return outputs


def validate_catalog(source):
    catalog = read(source / "catalog.json")
    levels = ["foundation", "atom", "molecule", "organism", "template", "interface"]
    by_id = {item["id"]: item for item in catalog}
    if len(by_id) != len(catalog):
        raise ValueError("duplicate catalog id")
    visiting, complete = set(), set()

    def visit(key):
        if key in visiting:
            raise ValueError(f"cyclic composition: {key}")
        if key in complete:
            return
        item = by_id[key]
        visiting.add(key)
        for child in item.get("composes", []):
            if levels.index(by_id[child]["level"]) >= levels.index(item["level"]):
                raise ValueError(f"invalid atomic dependency: {key} -> {child}")
            visit(child)
        for path in item.get("sources", []):
            if not (ROOT / path).is_file():
                raise ValueError(f"missing catalog source: {path}")
        visiting.remove(key)
        complete.add(key)

    for key in by_id:
        visit(key)
    for integration in read(source / "integrations.json"):
        for path in integration["sources"]:
            if not (ROOT / path).is_file():
                raise ValueError(f"missing integration source: {path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--theme", help="Override the preset selected by source/config.json")
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output-dir", type=Path, default=SOURCE / "generated")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        outputs = compile_theme(args.source, args.theme or read(args.source / "config.json")["theme"])
        stale = []
        for name, content in outputs.items():
            path = args.output_dir / name
            if args.check:
                if not path.exists() or path.read_text() != content:
                    stale.append(name)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
        if stale:
            raise ValueError("stale generated theme files: " + ", ".join(stale))
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(1, f"theme: {error}\n")


if __name__ == "__main__":
    main()
