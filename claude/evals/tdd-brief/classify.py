"""Classify one run by the order of its file writes.

Reads a Claude Code `--output-format stream-json` event log and reports whether
a test file was written before the implementation. The outcome is observed from
successful tool results, never from the agent's own account of what it did.
Reject streams whose mutations or ordering cannot be observed reliably.
"""
import argparse
import json
import os
import re
import sys

WRITE_TOOLS = {"Write", "Edit", "MultiEdit"}
READ_TOOLS = {"Read", "Grep", "Glob"}
# This is a small fixture-specific allowance, not a general shell safety parser.
TEST_COMMAND = re.compile(r"python3? -m pytest(?: -[qv]+)*")


def iter_tool_uses(event):
    """Yield completed tool_use blocks from one `assistant` event, in order.

    Only `assistant` events are read. The `stream_event` events in the same log
    also carry a tool_use block, but it is a `content_block_start` whose input
    has not been streamed in yet — counting those would double every write and
    read a file_path that is not there yet.
    """
    if event.get("type") != "assistant":
        return
    for block in (event.get("message") or {}).get("content") or []:
        if isinstance(block, dict) and block.get("type") == "tool_use":
            yield block


def is_test_path(relative):
    parts = relative.split(os.sep)
    if any(part in ("test", "tests") for part in parts[:-1]):
        return True
    name = parts[-1]
    return name.startswith("test_") or name.endswith("_test.py")


def classify(events_path, root):
    root = os.path.realpath(root)
    first = {"test": None, "impl": None}
    seen = {"test": [], "impl": []}
    index = 0
    model = None
    pending = {}
    tool_ids = set()
    completed = False
    with open(events_path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError("malformed or truncated event stream") from exc
            model = model or ((event.get("message") or {}).get("model")
                              if isinstance(event.get("message"), dict) else None)
            for block in iter_tool_uses(event):
                name = block.get("name")
                if name in READ_TOOLS:
                    continue
                if name == "Bash":
                    command = (block.get("input") or {}).get("command", "").strip()
                    if TEST_COMMAND.fullmatch(command):
                        continue
                    raise ValueError("unobserved Bash mutation possible; only python -m pytest is classifiable")
                if name not in WRITE_TOOLS:
                    raise ValueError(f"unobserved tool: {name}")
                tool_id = block.get("id")
                raw = (block.get("input") or {}).get("file_path")
                if not tool_id or tool_id in tool_ids or not raw:
                    raise ValueError("write is missing a unique id or file path")
                if pending:
                    raise ValueError("overlapping writes have ambiguous mutation order")
                tool_ids.add(tool_id)
                absolute = os.path.realpath(os.path.join(root, raw))
                pending[tool_id] = absolute
            if event.get("type") == "result":
                completed = event.get("subtype") == "success" and not event.get("is_error")
            if event.get("type") != "user":
                continue
            for block in (event.get("message") or {}).get("content") or []:
                if not isinstance(block, dict) or block.get("type") != "tool_result":
                    continue
                tool_id = block.get("tool_use_id")
                if tool_id not in pending:
                    continue
                absolute = pending.pop(tool_id)
                if block.get("is_error"):
                    raise ValueError("failed write; the stream cannot prove whether it partially mutated a file")
                if os.path.commonpath([absolute, root]) != root:
                    continue  # a write outside the fixture is not part of the task
                relative = os.path.relpath(absolute, root)
                kind = "test" if is_test_path(relative) else "impl"
                if first[kind] is None:
                    first[kind] = index
                if relative not in seen[kind]:
                    seen[kind].append(relative)
                index += 1

    if pending or not completed:
        raise ValueError("missing write result or successful run completion")
    if first["impl"] is None:
        outcome = "no_impl"
    elif first["test"] is None:
        outcome = "no_test"
    elif first["test"] < first["impl"]:
        outcome = "test_first"
    else:
        outcome = "impl_first"
    return outcome, first, seen, index, model


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", required=True)
    parser.add_argument("--root", required=True)
    parser.add_argument("--arm", required=True)
    parser.add_argument("--trial", required=True, type=int)
    parser.add_argument("--task", required=True, type=int)
    args = parser.parse_args(argv)

    try:
        outcome, first, seen, writes, model = classify(args.events, args.root)
    except ValueError as exc:
        parser.exit(1, f"Unclassifiable run: {exc}\n")
    json.dump({
        "arm": args.arm,
        "trial": args.trial,
        "task": args.task,
        "outcome": outcome,
        "first_test": first["test"],
        "first_impl": first["impl"],
        "writes": writes,
        "model": model,
        "test_paths": seen["test"],
        "impl_paths": seen["impl"],
    }, sys.stdout, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
