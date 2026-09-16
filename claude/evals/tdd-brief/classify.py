"""Classify one run by the order of its file writes.

Reads a Claude Code `--output-format stream-json` event log and reports whether
a test file was written before the implementation. The outcome is observed from
the tool-call stream, never from the agent's own account of what it did.
"""
import argparse
import json
import os
import sys

WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}


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
    with open(events_path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue  # a partial trailing line is not a write
            model = model or ((event.get("message") or {}).get("model")
                              if isinstance(event.get("message"), dict) else None)
            for block in iter_tool_uses(event):
                if block.get("name") not in WRITE_TOOLS:
                    continue
                raw = (block.get("input") or {}).get("file_path")
                if not raw:
                    continue
                absolute = os.path.realpath(os.path.join(root, raw))
                if os.path.commonpath([absolute, root]) != root:
                    continue  # a write outside the fixture is not part of the task
                relative = os.path.relpath(absolute, root)
                kind = "test" if is_test_path(relative) else "impl"
                if first[kind] is None:
                    first[kind] = index
                if relative not in seen[kind]:
                    seen[kind].append(relative)
                index += 1

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

    outcome, first, seen, writes, model = classify(args.events, args.root)
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
