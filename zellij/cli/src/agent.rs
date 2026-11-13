//! Server-scoped forwarding. Only owned sockets and one-hop managed links are accepted.
use crate::util::*;
use anyhow::{bail, Context, Result};
use std::env;
use std::fs;
use std::io::Write;
use std::os::unix::fs::{
    symlink, DirBuilderExt, FileTypeExt, MetadataExt, OpenOptionsExt, PermissionsExt,
};
use std::path::{Path, PathBuf};
use std::time::{Duration, Instant};
fn owned(info: &fs::Metadata) -> bool {
    info.uid() == unsafe { libc::getuid() }
}
fn directory(path: &Path, create: bool, private: bool) -> Result<()> {
    if create && fs::symlink_metadata(path).is_err() {
        let _ = fs::DirBuilder::new().mode(0o700).create(path);
    }
    let info = fs::symlink_metadata(path)?;
    if !info.is_dir() || !owned(&info) || info.mode() & if private { 0o077 } else { 0o022 } != 0 {
        bail!("Unsafe directory: {}", path.display());
    }
    Ok(())
}
fn raw_socket(path: &Path) -> Result<()> {
    let info = fs::symlink_metadata(path)?;
    if !path.is_absolute() || !info.file_type().is_socket() || !owned(&info) {
        bail!("Invalid raw forwarded socket");
    }
    Ok(())
}
fn key(value: &str) -> bool {
    value.len() == 12
        && value
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}
fn managed_source(raw: &Path) -> Result<()> {
    let parent = home()?.join(".ssh");
    let dir = parent.join("dotfiles-agent");
    directory(&parent, false, false)?;
    directory(&dir, false, true)?;
    if raw.parent() != Some(dir.as_path()) {
        bail!("Invalid managed agent source");
    }
    let source = raw
        .file_name()
        .and_then(|v| v.to_str())
        .and_then(|s| s.strip_prefix("zellij-"))
        .and_then(|s| s.strip_suffix(".sock"))
        .context("Invalid managed agent name")?;
    let info = fs::symlink_metadata(raw)?;
    if !key(source) || !info.is_symlink() || !owned(&info) {
        bail!("Invalid managed agent source");
    }
    raw_socket(&fs::read_link(raw)?)
}
fn validate_link(link: &Path) -> Result<()> {
    if !fs::symlink_metadata(link)?.is_symlink() {
        bail!("Unsafe managed agent link");
    }
    match fs::metadata(link) {
        Ok(info) if info.file_type().is_socket() && owned(&info) => Ok(()),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(()),
        _ => bail!("Unsafe managed agent link"),
    }
}
fn owning_key() -> Result<String> {
    let mut pid = unsafe { libc::getppid() } as u32;
    let deadline = Instant::now() + Duration::from_secs(2);
    for _ in 0..16 {
        if pid <= 1 {
            break;
        }
        let args = run(
            "ps",
            &["-ww", "-p", &pid.to_string(), "-o", "command="],
            deadline,
        )?;
        if let Some((exe, address)) = args.trim().split_once(" --server ") {
            if Path::new(exe).file_name().is_some_and(|n| n == "zellij") {
                let path = Path::new(address.strip_suffix(" --debug").unwrap_or(address));
                raw_socket(path)?;
                let id = path
                    .file_name()
                    .and_then(|s| s.to_str())
                    .context("Invalid server socket")?;
                if !key(id) {
                    bail!("Invalid server socket ID");
                }
                return Ok(id.to_owned());
            }
        }
        let parent: u32 = run("ps", &["-p", &pid.to_string(), "-o", "ppid="], deadline)?
            .trim()
            .parse()?;
        if parent == pid {
            break;
        }
        pid = parent;
    }
    bail!("Cannot identify the owning pinned Zellij server")
}
pub fn enabled() -> bool {
    env::var("SSH_CONNECTION").is_ok_and(|s| !s.is_empty())
        && env::var("SSH_AUTH_SOCK").is_ok_and(|s| !s.is_empty())
}
pub fn can_refresh() -> bool {
    enabled()
        && env::var_os("SSH_AUTH_SOCK").is_some_and(|path| raw_socket(Path::new(&path)).is_ok())
}
pub fn publish(operation: &str, raw: &Path, request: Option<&Path>) -> Result<PathBuf> {
    if let Some(request) = request {
        if !request.is_absolute() {
            bail!("Request path must be absolute");
        }
        directory(request, false, true)?;
    }
    if operation == "publish-popup" && session()? != "pop-up" {
        bail!("Not the shared popup server");
    }
    let id = owning_key()?;
    let ssh = home()?.join(".ssh");
    let dir = ssh.join("dotfiles-agent");
    directory(&ssh, true, false)?;
    directory(&dir, true, false)?;
    fs::set_permissions(&dir, fs::Permissions::from_mode(0o700))?;
    let link = dir.join(format!("zellij-{id}.sock"));
    if operation == "init" && fs::symlink_metadata(&link).is_ok_and(|i| i.is_symlink()) {
        validate_link(&link)?;
        return Ok(link);
    }
    if fs::metadata(&link).is_ok_and(|i| i.is_dir())
        || fs::symlink_metadata(&link).is_ok_and(|i| !i.is_symlink())
    {
        bail!("Refusing unmanaged agent path");
    }
    if operation == "publish-popup"
        || (operation == "init" && fs::symlink_metadata(raw).is_ok_and(|i| i.is_symlink()))
    {
        if session()? != "pop-up" || raw == link {
            bail!("Only the shared popup may follow another managed agent");
        }
        managed_source(raw)?;
    } else {
        raw_socket(raw)?;
    }
    if operation == "init" {
        if symlink(raw, &link).is_err() {
            validate_link(&link)?;
        }
    } else {
        let staging = tempfile::Builder::new()
            .prefix(".refresh.")
            .permissions(fs::Permissions::from_mode(0o700))
            .tempdir_in(&dir)?;
        symlink(raw, staging.path().join("agent.sock"))?;
        let request = request.context("Missing request")?;
        directory(request, false, true)?;
        fs::rename(staging.path().join("agent.sock"), &link)?;
        let mut ack = fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .mode(0o600)
            .open(request.join("success"))?;
        writeln!(ack, "{}", link.display())?;
    }
    validate_link(&link)?;
    Ok(link)
}
pub fn refresh(session: &str, follow: bool) -> Result<()> {
    refresh_until(session, follow, Instant::now() + Duration::from_secs(2))
}
fn refresh_until(session: &str, follow: bool, deadline: Instant) -> Result<()> {
    if !enabled() {
        return Ok(());
    }
    let raw = PathBuf::from(env::var_os("SSH_AUTH_SOCK").context("Missing socket")?);
    if follow {
        managed_source(&raw)?;
    } else {
        raw_socket(&raw)?;
    }
    let request = tempfile::Builder::new()
        .prefix("zellij-agent-update.")
        .permissions(fs::Permissions::from_mode(0o700))
        .tempdir()?;
    let exe = executable()?;
    // The request directory expires on every return path. Late publications are rejected.
    let _ = zellij(
        session,
        &[
            "run",
            "--floating",
            "--no-focus",
            "--close-on-exit",
            "--blocking",
            "--",
            &exe.to_string_lossy(),
            "agent",
            if follow { "publish-popup" } else { "publish" },
            &raw.to_string_lossy(),
            &request.path().to_string_lossy(),
        ],
        deadline,
    );
    let info = fs::symlink_metadata(request.path().join("success"))
        .context("Agent update was not acknowledged")?;
    if !info.is_file() || !owned(&info) {
        bail!("Unsafe agent acknowledgement");
    }
    Ok(())
}
fn refresh_after_attach(session: &str) -> Result<()> {
    let deadline = Instant::now() + Duration::from_secs(5);
    while Instant::now() < deadline {
        std::thread::sleep(Duration::from_millis(200));
        if refresh_until(
            session,
            false,
            deadline.min(Instant::now() + Duration::from_secs(2)),
        )
        .is_ok()
        {
            return Ok(());
        }
    }
    bail!("forwarded SSH agent refresh failed; reconnect with agent forwarding enabled.")
}
pub fn main(args: &[String]) -> Result<()> {
    match args {
        [op] if op=="init"=>{if enabled(){println!("{}",publish("init",Path::new(&env::var("SSH_AUTH_SOCK")?),None)?.display());}},
        [op,session] if op=="refresh"=>refresh(session,false)?,
        [op,session] if op=="refresh-after-attach"=>refresh_after_attach(session)?,
        [op] if op=="follow-popup"=>refresh("pop-up",true)?,
        [op,raw,request] if matches!(op.as_str(),"publish"|"publish-popup")=>println!("{}",publish(op,Path::new(raw),Some(Path::new(request)))?.display()),
        _=>bail!("Usage: zellij-agent init | refresh SESSION | follow-popup | publish RAW_SOCKET PRIVATE_REQUEST_DIRECTORY"),
    }
    Ok(())
}
