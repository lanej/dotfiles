# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Resolve an exact session or print a paged, source-referenced transcript digest."""

import argparse
import json
import os
from pathlib import Path
import re
import sys


def resolve(host, session_id, root):
    if not session_id or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", session_id):
        raise ValueError("a valid exact session ID is required; no newest-session fallback")
    matches = []
    for path in root.rglob(f"*{session_id}.jsonl"):
        with path.open() as stream:
            for _, line in zip(range(50), stream):
                event = json.loads(line)
                identity = (event.get("payload", {}).get("id")
                            if host == "codex" and event.get("type") == "session_meta"
                            else event.get("sessionId") if host == "claude" else None)
                if identity == session_id:
                    matches.append(path.resolve())
                    break
    matches = sorted(set(matches))
    if len(matches) != 1:
        raise ValueError(f"session {session_id}: expected one matching transcript, found {len(matches)}")
    return matches[0]


def clipped(value, length):
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    if len(text) > length:
        return text[:length] + " … [truncated; inspect source]"
    return text


def content_text(content):
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    return "\n".join(block["text"] for block in content
                     if isinstance(block, dict) and block.get("type") in
                     {"text", "input_text", "output_text"} and isinstance(block.get("text"), str))


def excerpts(event, host):
    if host == "codex":
        if event.get("type") != "response_item":
            return []
        item = event.get("payload", {})
        kind = item.get("type")
        if (kind == "message" and item.get("role") in {"user", "assistant"}
                and item.get("channel") in {None, "commentary", "final"}):
            text = content_text(item.get("content"))
            return [(item["role"], clipped(text, 6000))] if text else []
        if kind in {"function_call", "custom_tool_call"}:
            return [(f"tool {item.get('name', '?')}",
                     clipped(item.get("arguments", item.get("input", "")), 600))]
        if kind in {"function_call_output", "custom_tool_call_output"}:
            return [(f"tool-result {item.get('call_id', '?')}", clipped(item.get("output", ""), 600))]
        return []
    if event.get("type") not in {"user", "assistant"}:
        return []
    message = event.get("message", {})
    content = message.get("content", "")
    rows = []
    text = content_text(content)
    if text:
        rows.append((event["type"], clipped(text, 6000)))
    for block in content if isinstance(content, list) else []:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "tool_use":
            rows.append((f"tool {block.get('name', '?')}", clipped(block.get("input", ""), 600)))
        elif block.get("type") == "tool_result":
            rows.append((f"tool-result {block.get('tool_use_id', '?')}",
                         clipped(content_text(block.get("content", "")), 600)))
    return rows


def digest(path, host, start_line, limit):
    count = 0
    last = 0
    with path.open() as stream:
        for number, line in enumerate(stream, 1):
            if number < start_line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"{path}:{number}: malformed or incomplete JSON") from error
            rows = excerpts(event, host)
            if not rows:
                continue
            print(f"\n[{path}:{number}]")
            for label, text in rows:
                print(f"{label}: {text}")
            count += 1
            last = number
            if count >= limit:
                print(f"\n[page limit reached; continue with --start-line {last + 1}]")
                break
    if not count:
        print("[no conversation entries in this range]")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transcript", type=Path, nargs="?")
    parser.add_argument("--host", choices=["codex", "claude"], required=True)
    parser.add_argument("--session-id")
    parser.add_argument("--root", type=Path)
    parser.add_argument("--resolve", action="store_true", help="print only the exact resolved transcript path")
    parser.add_argument("--start-line", type=int, default=1)
    parser.add_argument("--limit", type=int, default=100, help="maximum source records per page")
    args = parser.parse_args()
    if args.start_line < 1 or not 1 <= args.limit <= 500:
        parser.error("start-line must be positive and limit must be between 1 and 500")
    try:
        if args.transcript:
            path = args.transcript.expanduser().resolve(strict=True)
        else:
            home = Path.home()
            root = args.root or (Path(os.environ.get("CODEX_HOME", home / ".codex")) / "sessions"
                                 if args.host == "codex" else home / ".claude/projects")
            identity = args.session_id or os.environ.get(
                "CODEX_THREAD_ID" if args.host == "codex" else "CLAUDE_CODE_SESSION_ID")
            path = resolve(args.host, identity, root)
        if args.resolve:
            print(path)
        else:
            digest(path, args.host, args.start_line, args.limit)
    except (OSError, ValueError, TypeError, AttributeError) as error:
        print(f"transcript: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
