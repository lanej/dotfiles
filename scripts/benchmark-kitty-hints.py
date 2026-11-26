"""Informational benchmarks for the Kitty hint picker; no timing assertions."""
import json
import math
import os
from pathlib import Path
import platform
import signal
import socket as unix_socket
import statistics
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
REPS = 20


def summarize(values):
    ordered = sorted(values)
    return {"p50_ms": round(statistics.median(ordered), 2),
            "p95_ms": round(ordered[math.ceil(.95 * len(ordered)) - 1], 2),
            "n": len(ordered)}


def clock(fn):
    start = time.perf_counter_ns()
    value = fn()
    return value, (time.perf_counter_ns() - start) / 1e6


def report(data):
    print("HINT_BENCH " + json.dumps(data, sort_keys=True), flush=True)


def fixture(cols, rows, links, truecolor=False):
    lines = []
    for y in range(rows - 1):
        status = ("\x1b[32mPASS", "\x1b[33mWARN", "\x1b[31mFAIL")[y % 3]
        if y < links:
            line = status + "\x1b[0m  \x1b[36mhttps://example.org/\x1b[32mlink/\x1b[35m" + f"{y:03d}" + "\x1b[0m"
            visible_len = len("PASS  https://example.org/link/000")
        else:
            line = status + "\x1b[0m  build output / diagnostic context"
            visible_len = len("PASS  build output / diagnostic context")
        # Exercise dense rows and many independent foreground colors.
        remaining = max(0, cols - visible_len - 2)
        if truecolor:
            line += " " + "".join(
                f"\x1b[38;2;{(x*19+y*17)%256};{(x*71+y*29)%256};{(x*47+y*37)%256}m#"
                for x in range(max(0, remaining - 1))) + "\x1b[0m"
        else:
            line += "\x1b[90m " + ("review status information " * cols)[:max(0, remaining - 1)] + "\x1b[0m"
        lines.append(line)
    return "\n".join(lines)


def gui():
    for name, cols, rows, links, target, command in (
        ("representative", 82, 27, 4, "github.com/lanej/dotfiles/pull/429",
         ["python3", str(ROOT / "scripts/fixtures/kitty-hint-review.py")]),
        ("large_dense", 160, 50, 48, "example.org/link/000",
         ["python3", str(Path(__file__).resolve()), "--fixture", "160", "50", "48"]),
    ):
        with tempfile.TemporaryDirectory(prefix="kitty-hint-bench-") as tmp:
            work = Path(tmp)
            home = work / "home"
            home.mkdir()
            env = {**os.environ, "HOME":str(home), "XDG_CONFIG_HOME":str(home / ".config"),
                   "XDG_CACHE_HOME":str(home / ".cache"), "XDG_DATA_HOME":str(home / ".local/share")}
            subprocess.run(["make", "-s", "kitty-config"], cwd=ROOT, env=env, check=True)
            helper = Path(os.environ["KITTY_NATIVE_HINTS_BIN"]).resolve()
            installed = home / ".local/bin/hint-native"
            installed.parent.mkdir(parents=True, exist_ok=True)
            installed.symlink_to(helper)
            env["PATH"] = str(installed.parent) + os.pathsep + env["PATH"]
            # Copy, rather than editing the symlink into the checked-out config.
            conf = home / ".config/kitty/kitty.conf"
            original = conf.read_text()
            conf.unlink()
            conf.write_text(original + "\nmap ctrl+shift+g kitten hints --type url --alphabet asdfghjkl --hints-offset 0 --ascending --prefix-free\n")
            socket = "unix:" + str(work / "kitty.sock")

            def run(*args):
                return subprocess.check_output(args, env=env, text=True,
                                               stderr=subprocess.DEVNULL, timeout=5)

            def remote(cmd, *args):
                # Use Kitty's actual socket protocol, not a new CLI process on
                # every observation. This removes tens of ms of measurement
                # overhead without changing the picker itself.
                payload = {}
                if cmd == "get-text":
                    payload = {"extent": "screen", "ansi": "--ansi" in args}
                    if "--match" in args:
                        payload["match"] = args[args.index("--match") + 1]
                request = {"cmd": cmd, "version": [0, 50, 0], "payload": payload}
                with unix_socket.socket(unix_socket.AF_UNIX, unix_socket.SOCK_STREAM) as client:
                    client.settimeout(2)
                    client.connect(socket.removeprefix("unix:"))
                    client.sendall(b"\x1bP@kitty-cmd" + json.dumps(request).encode("ascii") + b"\x1b\\")
                    client.shutdown(unix_socket.SHUT_WR)
                    parts = []
                    while chunk := client.recv(65536):
                        parts.append(chunk)
                raw = b"".join(parts)
                match = re.search(rb"\x1bP@kitty-cmd([^\x1b]+)\x1b\\", raw)
                if not match:
                    raise ValueError("No remote-control response")
                response = json.loads(match[1])
                if not response.get("ok"):
                    raise ValueError(response.get("error", "Kitty request failed"))
                return response.get("data", "")

            def ready(predicate, name):
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    try:
                        if predicate():
                            return
                    except (OSError, ValueError, subprocess.SubprocessError):
                        pass
                    time.sleep(.005)
                raise RuntimeError(f"Timed out waiting for {name}")

            def key(k):
                run("xdotool", "key", "--delay", "1", "--clearmodifiers", k)

            # ANSI transitions can appear within the target itself.
            import re
            def overlay_ready():
                windows = [w for ow in json.loads(remote("ls")) for tab in ow["tabs"] for w in tab["windows"]]
                overlay = next((w for w in windows if w["title"] == "Choose URL"), None)
                if overlay is None:
                    return False
                out = remote("get-text", "--ansi", "--match", f"id:{overlay['id']}")
                return target in re.sub(r"\x1b\[[0-9;:]*m", "", out) and ("mark:" in out or "59;66;82" in out or "59:66:82" in out)

            def source_ready():
                return all(w["title"] != "Choose URL" for ow in json.loads(remote("ls"))
                           for tab in ow["tabs"] for w in tab["windows"])

            with (work / "kitty.log").open("w") as log:
                app = subprocess.Popen(["kitty", "--listen-on", socket, "-o", "allow_remote_control=socket-only",
                    "-o", "linux_display_server=x11", "-o", f"initial_window_width={cols}c",
                    "-o", f"initial_window_height={rows}c", "-o", "remember_window_size=no",
                    "--directory", str(ROOT), *command], env=env, stdout=log, stderr=log)
                try:
                    ready(lambda: target in remote("get-text"), "source")
                    xid = run("xdotool", "search", "--onlyvisible", "--class", "kitty").splitlines()[-1]
                    run("xdotool", "windowfocus", "--sync", xid)
                    time.sleep(.2)
                    geometry = json.loads(remote("ls"))[0]["tabs"][0]["windows"][0]
                    # Warm filesystem/font caches; the picker child still starts each time.
                    cases = [("native", "ctrl+shift+g"), ("styled", "ctrl+shift+e")]
                    for _, shortcut in cases:
                        key(shortcut)
                        ready(overlay_ready, "warm overlay " + shortcut)
                        if shortcut == "ctrl+shift+e" and os.environ.get("KITTY_NATIVE_HINTS_BIN"):
                            current = next(w for ow in json.loads(remote("ls")) for tab in ow["tabs"]
                                           for w in tab["windows"] if w["title"] == "Choose URL")
                            if not current.get("cmdline") or Path(current["cmdline"][0]).resolve() != helper:
                                raise AssertionError(f"Native helper was not activated: {current.get('cmdline')}")
                        key("Escape")
                        ready(source_ready, "warm cancellation")
                    values = {label: [] for label, _ in cases}
                    def observer():
                        remote("ls")
                        remote("get-text")
                    poll = [clock(observer)[1] for _ in range(REPS)]
                    for i in range(REPS):
                        offset = i % len(cases)
                        for label, shortcut in cases[offset:] + cases[:offset]:
                            start = time.perf_counter_ns()
                            key(shortcut)
                            ready(overlay_ready, label)
                            values[label].append((time.perf_counter_ns() - start) / 1e6)
                            key("Escape")
                            ready(source_ready, "cancellation")
                    report({"kind":"gui","case":name,"cols":cols,"rows":rows,"links":links,
                            "actual_cols":geometry.get("columns"),"actual_rows":geometry.get("lines"),
                            "observer":summarize(poll),
                            "native":summarize(values["native"]), "styled":summarize(values["styled"])})
                except Exception:
                    print((work / "kitty.log").read_text()[-4000:], file=sys.stderr)
                    try:
                        print(remote("ls"), file=sys.stderr)
                        print(remote("get-text", "--ansi"), file=sys.stderr)
                    except subprocess.SubprocessError:
                        pass
                    raise
                finally:
                    app.terminate()
                    try:
                        app.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        app.kill()
                        app.wait()


if __name__ == "__main__":
    if "--fixture" in sys.argv:
        index = sys.argv.index("--fixture")
        print(fixture(*map(int, sys.argv[index+1:index+4])), flush=True)
        signal.pause()
    elif "--gui" in sys.argv:
        report({"kind":"environment","platform":platform.platform(),"cpu_count":os.cpu_count()})
        gui()
    else:
        raise SystemExit("Use --gui to measure activation")
