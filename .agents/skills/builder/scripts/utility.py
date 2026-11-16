"""Print each distinct UTF-8 input line once, in encounter order.

Line endings normalize to LF; whitespace and blank lines remain meaningful.
Invalid UTF-8 produces an error and exit status 2, with no output.
"""
import sys


def unique_lines(lines: list[str]) -> list[str]:
    return list(dict.fromkeys(lines))


def main() -> int:
    try:
        text = sys.stdin.buffer.read().decode("utf-8")
    except UnicodeDecodeError:
        print("input must be UTF-8 text", file=sys.stderr)
        return 2
    lines = unique_lines(text.splitlines())
    sys.stdout.write("".join(line + "\n" for line in lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
