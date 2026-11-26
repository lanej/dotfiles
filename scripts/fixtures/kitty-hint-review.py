"""Representative terminal fixture for the Kitty hint visual review."""
import signal
import sys

# Semantic segments: a review, CI diagnostics, a code diff and links with
# differently colored components. Raw URLs exercise Ctrl+Shift+E.
def c(code, text):
    return f"\x1b[{code}m{text}\x1b[0m"


def url(host, path, suffix=""):
    return c("36", "https://" + host + "/") + c("32", path) + c("35", suffix)


def fixture():
    return "\n".join([
        c("32", "$") + " " + c("1;37", "gh pr view 429 --comments"),
        "",
        c("1;37", "fix(kitty): preserve semantic colors in URL and file hints"),
        c("33", "DRAFT") + "  " + c("36", "lanej/dotfiles") + " #429  " + c("90", "fix/kitty-nord-hint-contrast"),
        "",
        "  Pull request  " + url("github.com", "lanej/dotfiles/pull/", "429"),
        "",
        c("1;37", "Checks"),
        "  " + c("32", "PASS") + "  Keybinding registry     " + c("90", "4s"),
        "  " + c("31", "FAIL") + "  Kitty visual regression " + c("90", "18s"),
        "  " + c("33", "WARN") + "  Contrast below 4.5:1 on two cells",
        "        " + url("github.com", "lanej/dotfiles/actions/runs/", "45754336810"),
        "",
        c("1;37", "Diff  ") + c("90", "kitty/hint_overlay.py"),
        "  " + c("36", "@@ -242,3 +242,3 @@"),
        c("38;2;191;97;106;48;2;61;43;52", "-    fg = palette['foreground']"),
        c("38;2;163;190;140;48;2;43;57;51", "+    fg = readable(fg, bg)"),
        "     " + c("35", "return") + " " + c("36", "sgr") + "(" + c("32", "fg") + ", bg)",
        "",
        c("33", "warning:") + " source colors must survive hint mode",
        "  Docs: " + url("sw.kovidgoyal.net", "kitty/kittens/hints/"),
        "  Issue: " + c("31", "https://github.com/") + c("35", "lanej/dotfiles/issues/428"),
        "",
        c("32", "$") + " " + c("36", "git") + " " + c("37", "diff --stat"),
        "  " + c("90", "4 files changed, ") + c("32", "86 insertions") + c("90", ", ") + c("31", "21 deletions"),
    ])


if __name__ == "__main__":
    print(fixture(), flush=True)
    signal.pause()
