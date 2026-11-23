//! The Kitty picker uses the original client's terminal connection, including across SSH.
use crate::util::{flag, native, nonce, number, origin_id, pane_id, session, snapshot, text};
use anyhow::{ensure, Context, Result};
use base64::{engine::general_purpose::URL_SAFE_NO_PAD, Engine};
use serde_json::Value;
use std::io::{self, BufRead, BufReader, Read, Write};
use std::os::fd::{AsFd, AsRawFd};
use std::path::Path;

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

fn terminal(panes: &[Value], id: u64) -> Result<&Value> {
    panes
        .iter()
        .find(|p| p["id"].as_u64() == Some(id) && !flag(p, "is_plugin") && !flag(p, "exited"))
        .context("The terminal pane is unavailable")
}

pub fn run() -> Result<()> {
    let session = session()?;
    let server = crate::context::Session::resolve(&session)?;
    let origin = origin_id()?;
    let panes = snapshot(&session, "panes")?;
    let pane = terminal(&panes, origin)?;
    // zssh started inside Zellij creates a tab running this SSH command. Forward
    // the shortcut through its PTY so the remote session resolves its own files.
    if pane["terminal_command"]
        .as_str()
        .is_some_and(|cmd| cmd.starts_with("ssh -t ") && cmd.contains(crate::session::ZSSH_ATTACH))
    {
        native(
            &session,
            &[
                "action",
                "write-chars",
                "--pane-id",
                &origin.to_string(),
                "\x1b[24;7~",
            ],
        )?;
        return Ok(());
    }
    let receiver = terminal(&panes, pane_id()?)?;
    let cwd = Path::new(text(pane, "pane_cwd")?);
    ensure!(
        cwd.is_absolute(),
        "The source pane has no absolute working directory"
    );
    let ticket = nonce()?;
    let marker = format!(
        "dotfiles-hints-v2://{ticket}/{}/{}/{}/{}/{}/{}",
        number(pane, "pane_content_x")?,
        number(pane, "pane_content_y")?,
        number(pane, "pane_content_columns")?,
        number(pane, "pane_content_rows")?,
        number(receiver, "pane_content_x")?,
        number(receiver, "pane_content_y")?
    );
    let raw = RawInput::enter()?;
    // The cursor stays over this link. Kitty checks it before writing to the receiver.
    print!("\x1b[H\x1b]8;;{marker}\x1b\\Choose a link or file\x1b]8;;\x1b\\\r");
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
    if let Err(error) = server
        .validate(&session)
        .and_then(|()| open(&session, origin, pane, cwd, reply))
    {
        // A failed tiled split may have hidden this receiver. Bring its message back.
        let _ = native(
            &session,
            &["action", "focus-pane-id", &pane_id()?.to_string()],
        );
        eprintln!("\x1b[2J\x1b[HOpen file: {error:#}\nPress Enter to close.");
        let _ = input.read_line(&mut String::new());
    }
    Ok(())
}

fn open(session: &str, origin: u64, pane: &Value, cwd: &Path, reply: &str) -> Result<()> {
    let target: crate::file_routes::Target =
        serde_json::from_slice(&URL_SAFE_NO_PAD.decode(reply)?)?;
    let panes = snapshot(session, "panes")?;
    let current = terminal(&panes, origin)?;
    ensure!(
        current["tab_id"] == pane["tab_id"] && current["pane_cwd"] == pane["pane_cwd"],
        "The source pane moved or changed directories"
    );
    crate::file_routes::open(session, origin, pane, cwd, target)
}

pub fn view(path: &str) -> Result<()> {
    // Keep the pane's normal line discipline. Enter works even when the mux
    // and icat negotiate different extended-keyboard modes for the hold prompt.
    let result = std::process::Command::new("kitten")
        .args(["icat", "--fit=both", "--transfer-mode=stream", "--", path])
        .status()?;
    if !result.success() {
        eprintln!("icat exited with {result}");
    }
    println!("Press Enter to close.");
    io::stdin().read_line(&mut String::new())?;
    Ok(())
}
