//! The Kitty picker uses the original client's terminal connection, including across SSH.
use crate::util::{flag, nonce, number, origin_id, pane_id, session, snapshot, text};
use anyhow::{ensure, Context, Result};
use base64::{engine::general_purpose::URL_SAFE_NO_PAD, Engine};
use serde::Deserialize;
use serde_json::Value;
use std::io::{self, BufRead, BufReader, Read, Write};
use std::os::fd::{AsFd, AsRawFd};
use std::path::{Path, PathBuf};
use std::process::Command;

struct RawInput(libc::termios);

impl RawInput {
    fn enter() -> Result<Self> {
        let mut original = std::mem::MaybeUninit::uninit();
        // stdin is the pseudo-terminal allocated for this command pane.
        if unsafe { libc::tcgetattr(0, original.as_mut_ptr()) } != 0 {
            return Err(io::Error::last_os_error().into());
        }
        let original = unsafe { original.assume_init() };
        let mut raw = original;
        unsafe { libc::cfmakeraw(&mut raw) };
        // A helper left behind by a disconnected Kitty client must release its pane.
        raw.c_cc[libc::VMIN] = 0;
        raw.c_cc[libc::VTIME] = 80;
        if unsafe { libc::tcsetattr(0, libc::TCSANOW, &raw) } != 0 {
            return Err(io::Error::last_os_error().into());
        }
        Ok(Self(original))
    }
}

impl Drop for RawInput {
    fn drop(&mut self) {
        unsafe { libc::tcsetattr(0, libc::TCSANOW, &self.0) };
    }
}

#[derive(Deserialize)]
struct Image {
    path: String,
    #[serde(default)]
    host: String,
}

fn resolve(image: &Image, cwd: &Path) -> Result<PathBuf> {
    if !image.host.is_empty() && !image.host.eq_ignore_ascii_case("localhost") {
        let output = Command::new("hostname").output()?;
        let host = std::str::from_utf8(&output.stdout)?.trim();
        ensure!(
            output.status.success()
                && (host.eq_ignore_ascii_case(&image.host)
                    || host
                        .split('.')
                        .next()
                        .is_some_and(|short| short.eq_ignore_ascii_case(&image.host))),
            "The file link belongs to a different host"
        );
    }
    ensure!(
        !image.path.chars().any(char::is_control),
        "Invalid image filename"
    );
    let path = match image.path.strip_prefix("~/") {
        Some(rest) => crate::util::home()?.join(rest),
        None => cwd.join(&image.path),
    };
    ensure!(
        path.is_file(),
        "Image does not exist in this worktree: {}",
        path.display()
    );
    Ok(path)
}

fn terminal(panes: &[Value], id: u64) -> Result<&Value> {
    panes
        .iter()
        .find(|p| p["id"].as_u64() == Some(id) && !flag(p, "is_plugin") && !flag(p, "exited"))
        .context("The terminal pane is unavailable")
}

pub fn run() -> Result<()> {
    let session = session()?;
    let origin = origin_id()?;
    let panes = snapshot(&session, "panes")?;
    let pane = terminal(&panes, origin)?;
    let receiver = terminal(&panes, pane_id()?)?;
    let cwd = Path::new(text(pane, "pane_cwd")?);
    ensure!(
        cwd.is_absolute(),
        "The source pane has no absolute working directory"
    );
    let ticket = nonce()?;
    let marker = format!(
        "dotfiles-hints://{ticket}/{}/{}/{}/{}/{}/{}",
        number(pane, "pane_content_x")?,
        number(pane, "pane_content_y")?,
        number(pane, "pane_content_columns")?,
        number(pane, "pane_content_rows")?,
        number(receiver, "pane_content_x")?,
        number(receiver, "pane_content_y")?
    );
    let raw = RawInput::enter()?;
    // The cursor stays over this link. Kitty checks it before writing to the receiver.
    print!("\x1b[H\x1b]8;;{marker}\x1b\\Choose a link or image\x1b]8;;\x1b\\\r");
    io::stdout().flush()?;
    // Consume exactly one byte before poll, even if the reply is already in the tty.
    let mut tty = std::fs::File::from(io::stdin().as_fd().try_clone_to_owned()?);
    let mut ack = [0; 1];
    if tty.read(&mut ack)? != 1 || ack != *b"!" {
        return Ok(());
    }
    // A detached client may leave the receiver open. Give the human picker five minutes,
    // then let this disposable pane close even when the original SSH connection survives.
    let mut descriptor = libc::pollfd {
        fd: tty.as_raw_fd(),
        events: libc::POLLIN,
        revents: 0,
    };
    if unsafe { libc::poll(&mut descriptor, 1, 300_000) } <= 0 {
        return Ok(());
    }
    let mut reply = Vec::new();
    let mut input = BufReader::new(tty);
    let mut limited = input.by_ref().take(16 * 1024);
    // The terminating period is outside the URL-safe base64 alphabet. No newline is sent.
    loop {
        let bytes = limited.fill_buf()?;
        if bytes.is_empty() || bytes.iter().any(|byte| matches!(byte, 3 | 27)) {
            return Ok(());
        }
        if let Some(end) = bytes.iter().position(|byte| *byte == b'.') {
            reply.extend_from_slice(&bytes[..end]);
            break;
        }
        reply.extend_from_slice(bytes);
        let count = bytes.len();
        limited.consume(count);
    }
    drop(raw);
    let reply = std::str::from_utf8(&reply)?
        .strip_prefix(&ticket)
        .context("This hint belongs to a different picker")?;
    if reply.is_empty() {
        return Ok(());
    }
    if let Err(error) = open(&session, origin, pane, cwd, reply) {
        eprintln!("Image preview: {error:#}\nPress Enter to close.");
        let _ = input.read_line(&mut String::new());
    }
    Ok(())
}

fn open(session: &str, origin: u64, pane: &Value, cwd: &Path, reply: &str) -> Result<()> {
    let image: Image = serde_json::from_slice(&URL_SAFE_NO_PAD.decode(reply)?)?;
    let path = resolve(&image, cwd)?;
    let panes = snapshot(session, "panes")?;
    let current = terminal(&panes, origin)?;
    ensure!(
        current["tab_id"] == pane["tab_id"] && current["pane_cwd"] == pane["pane_cwd"],
        "The source pane moved or changed directories"
    );
    ensure!(
        crate::util::exists("kitten"),
        "Install kitten on the host running this Zellij session"
    );
    let result = Command::new("zellij")
        .env("ZELLIJ_PANE_ID", origin.to_string())
        .arg(format!("--session={session}"))
        .args([
            "action",
            "new-pane",
            "--near-current-pane",
            "--direction",
            "right",
            "--close-on-exit",
            "--cwd",
        ])
        .arg(cwd)
        .args([
            "--",
            "kitten",
            "icat",
            "--hold",
            "--fit=both",
            "--transfer-mode=stream",
            "--",
        ])
        .arg(&path)
        .output()?;
    ensure!(
        result.status.success(),
        "Could not open image pane: {}",
        String::from_utf8_lossy(&result.stderr).trim()
    );
    Ok(())
}
