use crate::util::*;
use anyhow::{bail, Context, Result};
use base64::{engine::general_purpose::STANDARD, Engine};
use rusqlite::{Connection, OpenFlags, OptionalExtension};
use serde_json::Value;
use std::env;
use std::fs;
use std::io::{self, IsTerminal, Write};
use std::os::unix::fs::{FileTypeExt, MetadataExt};
use std::os::unix::process::{CommandExt, ExitStatusExt};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::atomic::{AtomicI32, Ordering};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

const CLEAR_REMOTE_TITLE: &[u8] = b"\x1b]1337;SetUserVar=dotfiles_zellij\x07";
pub(crate) const ZSSH_ATTACH: &str =
    r#"exec "$SHELL" -lic 'exec "$HOME/.local/bin/zellij-attach" "$1"' zssh"#;
static REMOTE_TITLE_SIGNAL: AtomicI32 = AtomicI32::new(0);

extern "C" fn request_remote_title_exit(signal: libc::c_int) {
    // Forward and reap in the waiting thread, not inside the signal handler.
    REMOTE_TITLE_SIGNAL.store(signal, Ordering::SeqCst);
}

struct RemoteTitle {
    handlers: Vec<(libc::c_int, libc::sighandler_t)>,
}

impl RemoteTitle {
    fn announce() -> Result<Self> {
        let host = run("hostname", &["-s"], Instant::now() + Duration::from_secs(5))?;
        let nonce = SystemTime::now().duration_since(UNIX_EPOCH)?.as_nanos();
        let marker = STANDARD.encode(format!("{}/{}/{nonce}", host.trim(), std::process::id()));
        let mut title = Self { handlers: vec![] };
        for signal in [libc::SIGHUP, libc::SIGINT, libc::SIGTERM] {
            let previous = unsafe {
                libc::signal(
                    signal,
                    request_remote_title_exit as *const () as libc::sighandler_t,
                )
            };
            if previous == libc::SIG_ERR {
                return Err(io::Error::last_os_error().into());
            }
            title.handlers.push((signal, previous));
        }
        // Announce outside the mux, which consumes pane OSC messages.
        print!("\x1b]1337;SetUserVar=dotfiles_zellij={marker}\x07");
        io::stdout().flush()?;
        Ok(title)
    }
}

impl Drop for RemoteTitle {
    fn drop(&mut self) {
        let _ = io::stdout().write_all(CLEAR_REMOTE_TITLE);
        let _ = io::stdout().flush();
        for &(signal, previous) in &self.handlers {
            unsafe { libc::signal(signal, previous) };
        }
    }
}

pub fn attach(args: &[String]) -> Result<()> {
    if env::var("ZELLIJ").is_ok_and(|s| !s.is_empty()) {
        bail!("already inside Zellij; detach before attaching to another session.");
    }
    let defaults = vec!["main".to_owned()];
    let args = if args.is_empty() { &defaults } else { args };
    if !args[0].starts_with('-')
        && crate::agent::refresh(&args[0], false).is_err()
        && crate::agent::can_refresh()
    {
        // A restored server only starts during attach. Retry in a separate,
        // bounded process while this process becomes the interactive client.
        if let Ok(exe) = executable() {
            let _ = Command::new(exe)
                .args(["agent", "refresh-after-attach", &args[0]])
                .stdin(Stdio::null())
                .stdout(Stdio::null())
                .spawn();
        }
    }
    let mut command = Command::new("zellij");
    command.args(["attach", "--create"]).args(args);
    if env::var("SSH_CONNECTION").is_ok_and(|s| !s.is_empty())
        && env::var("TMUX").map_or(true, |s| s.is_empty())
        && io::stdout().is_terminal()
    {
        let title = RemoteTitle::announce()?;
        let mut child = command.spawn()?;
        let mut forwarded = 0;
        let status = loop {
            if let Some(status) = child.try_wait()? {
                break status;
            }
            let signal = REMOTE_TITLE_SIGNAL.load(Ordering::SeqCst);
            if signal != 0 && signal != forwarded {
                // This child has not been reaped, so its PID cannot be reused.
                unsafe { libc::kill(child.id() as libc::pid_t, signal) };
                forwarded = signal;
            }
            std::thread::sleep(Duration::from_millis(20));
        };
        let signal = REMOTE_TITLE_SIGNAL.load(Ordering::SeqCst);
        drop(title);
        std::process::exit(if signal != 0 {
            128 + signal
        } else {
            status.code().unwrap_or(128 + status.signal().unwrap_or(1))
        });
    }
    Err(command.exec().into())
}
pub fn ssh(args: &[String]) -> Result<()> {
    if args.is_empty() || args.len() > 2 || args[0].is_empty() || args[0].starts_with('-') {
        bail!("Usage: zssh host [session]");
    }
    let host = &args[0];
    let session = args
        .get(1)
        .filter(|s| !s.is_empty())
        .map(String::as_str)
        .unwrap_or("main");
    let remote = format!("{ZSSH_ATTACH} {}", quote(session));
    let nested = env::var("ZELLIJ").is_ok_and(|s| !s.is_empty());
    let kitty =
        !nested && env::var("KITTY_WINDOW_ID").is_ok_and(|s| !s.is_empty()) && exists("kitten");
    let mut ssh = if kitty {
        vec!["kitten", "ssh"]
    } else {
        vec!["ssh"]
    };
    ssh.extend(["-t", host, &remote]);
    let mut command = if nested {
        let mut c = Command::new("zellij");
        c.args(["action", "new-tab", "--name", host, "--"])
            .args(ssh);
        c
    } else {
        let mut c = Command::new(ssh[0]);
        c.args(&ssh[1..]);
        c
    };
    Err(command.exec().into())
}
pub fn popup() -> Result<()> {
    if session()? == "dotfiles-popup" {
        bail!("The popup is already open; Ctrl-f d detaches this view");
    }
    let default = home()?.join(".config/zellij");
    let default = if default.is_dir() {
        default
    } else {
        env::var_os("XDG_CONFIG_HOME")
            .map(PathBuf::from)
            .unwrap_or(home()?.join(".config"))
            .join("zellij")
    };
    let config = env::var_os("ZELLIJ_CONFIG_DIR")
        .map(PathBuf::from)
        .unwrap_or(default);
    let layout = fs::read_to_string(config.join("layouts/tmux.kdl"))
        .context("The installed tmux layout is missing; run make zellij")?;
    let layout=layout+"\n// Scratch processes survive detaching, but are never resurrected after exit.\nsession_serialization false\nkeybinds {\n    tmux {\n        bind \"P\" { SwitchToMode \"Locked\"; Detach; }\n    }\n}\n";
    let mut command = Command::new("zellij");
    if crate::agent::enabled() {
        if let Ok(raw) = env::var("SSH_AUTH_SOCK") {
            if let Ok(selected) = crate::agent::publish("init", Path::new(&raw), None) {
                command.env("SSH_AUTH_SOCK", &selected);
                // A subprocess gets the guest environment without mutating this process's environment.
                let exe = executable()?;
                let _ = Command::new(exe)
                    .args(["agent", "follow-popup"])
                    .env("SSH_AUTH_SOCK", &selected)
                    .env_remove("ZELLIJ")
                    .env_remove("ZELLIJ_SESSION_NAME")
                    .env_remove("ZELLIJ_PANE_ID")
                    .stdout(std::process::Stdio::null())
                    .stderr(std::process::Stdio::null())
                    .status();
            }
        }
    }
    Err(command
        .args([
            "--layout-string",
            &layout,
            "attach",
            "--create",
            "dotfiles-popup",
        ])
        .env_remove("ZELLIJ")
        .env_remove("ZELLIJ_SESSION_NAME")
        .env_remove("ZELLIJ_PANE_ID")
        .exec()
        .into())
}
fn socket_identity(path: &Path) -> Result<(u64, u64, i64, i64)> {
    let info = fs::symlink_metadata(path)?;
    if !info.file_type().is_socket() || info.uid() != unsafe { libc::getuid() } {
        bail!("The target is not a Unix socket owned by this user");
    }
    Ok((info.dev(), info.ino(), info.ctime(), info.ctime_nsec()))
}
fn require_owner(session: &str, path: &Path, index: &Path) -> Result<()> {
    let connection = Connection::open_with_flags(index, OpenFlags::SQLITE_OPEN_READ_ONLY)?;
    connection.busy_timeout(Duration::from_secs(2))?;
    let id: Option<String> = connection
        .query_row(
            "SELECT COALESCE(id, name) FROM sessions WHERE name = ?",
            [session],
            |r| r.get(0),
        )
        .optional()?;
    if id.as_deref() != path.file_name().and_then(|s| s.to_str()) {
        bail!("The session was renamed or replaced; reopen shutdown confirmation");
    }
    Ok(())
}
fn pane_identity(session: &str, id: u64) -> Result<Value> {
    let panes = snapshot(session, "panes")?;
    let pane = panes
        .iter()
        .find(|p| p["id"] == id && !flag(p, "is_plugin"))
        .context("The confirmation pane no longer belongs to the target session")?;
    Ok(serde_json::json!([
        number(pane, "tab_id")?,
        pane.get("terminal_command")
            .context("Missing terminal command")?,
        pane.get("pane_cwd")
    ]))
}
pub fn shutdown() -> Result<()> {
    let session = session()?;
    let pane = pane_id()?;
    let deadline = Instant::now() + Duration::from_secs(5);
    let process = run(
        "ps",
        &[
            "-ww",
            "-p",
            &unsafe { libc::getppid() }.to_string(),
            "-o",
            "command=",
        ],
        deadline,
    )?;
    let (exe, address) = process
        .trim()
        .split_once(" --server ")
        .context("Open shutdown with Ctrl-f Ctrl-q so its owning server can be identified")?;
    let address = address.strip_suffix(" --debug").unwrap_or(address);
    if Path::new(exe).file_name().is_none_or(|p| p != "zellij")
        || !Path::new(address).is_absolute()
        || session.contains('/')
        || matches!(session.as_str(), "." | "..")
    {
        bail!("Cannot identify the session socket safely");
    }
    let mut path = PathBuf::from(address);
    let check = run("zellij", &["setup", "--check"], deadline)?;
    let index = if check.lines().any(|l| l == "[Version]: \"0.45.1\"") {
        path = path.parent().context("Invalid socket")?.join(&session);
        None
    } else {
        let (directory, index) = crate::context::location()?;
        if path.parent() != Some(directory.as_path()) {
            bail!("The server socket does not belong to the configured socket directory");
        }
        require_owner(&session, &path, &index)?;
        Some(index)
    };
    let socket = socket_identity(&path)?;
    let original = pane_identity(&session, pane)?;
    println!("Shut down Zellij session {}\n\nCloses every pane in this session and disconnects all its clients.",serde_json::to_string(&session)?);
    println!(
        "{}",
        if session == "dotfiles-popup" {
            "Other sessions keep running."
        } else {
            "Other sessions, including the shared popup, keep running."
        }
    );
    print!("\nType SHUTDOWN to confirm; Enter or Ctrl-c cancels: ");
    io::stdout().flush()?;
    let mut answer = String::new();
    io::stdin().read_line(&mut answer)?;
    if answer.trim_end_matches(['\r', '\n']) != "SHUTDOWN" {
        return Ok(());
    }
    if pane_identity(&session, pane)? != original || socket_identity(&path)? != socket {
        bail!("The target changed; reopen shutdown confirmation");
    }
    if let Some(index) = index {
        require_owner(&session, &path, &index)?;
    }
    run(
        "zellij",
        &["kill-session", "--", &session],
        Instant::now() + Duration::from_secs(5),
    )?;
    Ok(())
}
