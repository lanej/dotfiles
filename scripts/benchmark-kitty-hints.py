"""Informational benchmarks for the Kitty hint picker; no timing assertions."""
import json
import math
import os
from pathlib import Path
import platform
import runpy
import signal
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


def micro():
    sys.path.insert(0, str(ROOT / "kitty"))
    from kitty.fast_data_types import Screen, set_options
    from kitty.config import load_config
    import hint_overlay as overlay
    from select_hint import capture

    set_options(load_config(str(ROOT / "design-system/generated/kitty.conf")))
    representative = runpy.run_path(str(ROOT / "scripts/fixtures/kitty-hint-review.py"))["fixture"]()
    for name, cols, rows, links, ansi in (
        ("representative", 82, 27, 4, representative),
        ("large_sparse", 160, 50, 4, fixture(160, 50, 4)),
        ("large_dense", 160, 50, 48, fixture(160, 50, 48)),
        ("stress_many_colors", 240, 80, 70, fixture(240, 80, 70, True)),
    ):
        screen = Screen(None, rows, cols, 0)
        data = memoryview(ansi.replace("\n", "\r\n").encode())
        while data:
            written = screen.test_commit_write_buffer(data, screen.test_create_write_buffer())
            data = data[written:]
            screen.test_parse_written_data()
        timings = {k: [] for k in ("capture", "snapshot", "match", "serialize", "deserialize",
                                    "cold_render", "warm_redraw", "total_cpu")}
        size = output_size = actual_links = 0
        for i in range(REPS):
            # Every invocation launches a new overlay process, hence cold contrast caches.
            for f in (overlay.mix, overlay.luminance, overlay.readable, overlay.dimmed):
                f.cache_clear()
            source, a = clock(lambda: capture(screen))
            model, b = clock(lambda: overlay.source_snapshot(screen, source))
            model["marks"], c = clock(lambda: overlay.raw_url_marks(source, model["wrapped"]))
            model["type"] = "url"
            payload, d = clock(lambda: json.dumps(model))
            loaded, e = clock(lambda: json.loads(payload))
            frame, f = clock(lambda: overlay.render(loaded))
            prefix = overlay.labels(len(loaded["marks"]))[0][:1] if len(loaded["marks"]) > 9 else ""
            _, g = clock(lambda: overlay.render(loaded, prefix))
            for key, v in zip(timings, (a, b, c, d, e, f, g, a+b+c+d+e+f)):
                timings[key].append(v)
            size, output_size, actual_links = len(payload.encode()), len(frame.encode()), len(loaded["marks"])
        report({"kind":"micro","case":name,"cols":cols,"rows":rows,"links":actual_links,
                "expected_links":links,"snapshot_bytes":size,"frame_bytes":output_size,
                "timings":{k:summarize(v) for k,v in timings.items()}})


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
            # Copy, rather than editing the symlink into the checked-out config.
            conf = home / ".config/kitty/kitty.conf"
            original = conf.read_text()
            conf.unlink()
            conf.write_text(original + "\nmap ctrl+shift+g kitten hints --type url --alphabet asdfghjkl --hints-offset 0 --ascending --prefix-free\n")
            socket = "unix:" + str(work / "kitty.sock")

            def run(*args):
                return subprocess.check_output(args, env=env, text=True,
                                               stderr=subprocess.DEVNULL, timeout=5)

            def remote(*args):
                return run("kitten", "@", "--to", socket, *args)

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
                return target in re.sub(r"\x1b\[[0-9;:]*m", "", out) and "mark:" in out

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
                    for shortcut in ("ctrl+shift+g", "ctrl+shift+e"):
                        key(shortcut)
                        ready(overlay_ready, "warm overlay " + shortcut)
                        key("Escape")
                        ready(source_ready, "warm cancellation")
                    values = {"native": [], "styled": []}
                    def observer():
                        remote("ls")
                        remote("get-text")
                    poll = [clock(observer)[1] for _ in range(REPS)]
                    for i in range(REPS):
                        cases = (("native", "ctrl+shift+g"), ("styled", "ctrl+shift+e"))
                        for label, shortcut in (cases if i%2==0 else reversed(cases)):
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
        micro()
