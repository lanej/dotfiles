//! Shared native I/O. No helper interprets user data as shell code.
use anyhow::{bail, Context, Result};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::env;
use std::fs::{self, File, OpenOptions};
use std::io::{Read, Write};
use std::os::fd::AsRawFd;
use std::os::unix::fs::{DirBuilderExt, MetadataExt, OpenOptionsExt};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};
use unicode_general_category::{get_general_category, GeneralCategory};

pub const PLUGIN: &str = "file:~/.config/zellij/plugins/lane-status.wasm";
pub fn home() -> Result<PathBuf> {
    env::var_os("HOME")
        .map(PathBuf::from)
        .context("HOME is not set")
}
pub fn state(name: &str) -> Result<PathBuf> {
    Ok(env::var_os("XDG_STATE_HOME")
        .map(PathBuf::from)
        .unwrap_or(home()?.join(".local/state"))
        .join(name))
}
pub fn hash(value: &str) -> String {
    format!("{:x}", Sha256::digest(value.as_bytes()))
}
pub fn now_ms() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis() as u64
}
pub fn now_ns() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_nanos() as u64
}
pub fn nonce() -> Result<String> {
    let mut bytes = [0u8; 16];
    File::open("/dev/urandom")?.read_exact(&mut bytes)?;
    bytes[6] = (bytes[6] & 15) | 64;
    bytes[8] = (bytes[8] & 63) | 128;
    Ok(bytes.iter().map(|b| format!("{b:02x}")).collect())
}
pub fn printable(c: char) -> bool {
    c == ' '
        || !matches!(
            get_general_category(c),
            GeneralCategory::Control
                | GeneralCategory::Format
                | GeneralCategory::Surrogate
                | GeneralCategory::PrivateUse
                | GeneralCategory::Unassigned
                | GeneralCategory::LineSeparator
                | GeneralCategory::ParagraphSeparator
                | GeneralCategory::SpaceSeparator
        )
}
pub fn clean(value: &str, limit: usize) -> String {
    value
        .chars()
        .filter(|c| printable(*c))
        .take(limit)
        .collect()
}
pub fn label(value: &str) -> String {
    value
        .chars()
        .map(|c| if printable(c) { c } else { ' ' })
        .collect()
}
pub fn quote(value: &str) -> String {
    format!("'{}'", value.replace('\'', "'\\''"))
}
pub fn root() -> Result<PathBuf> {
    // Release and debug binaries both live in <repo>/zellij/target/<profile>.
    let exe = env::current_exe()?;
    exe.ancestors()
        .nth(4)
        .map(Path::to_path_buf)
        .context("Cannot locate dotfiles checkout")
}
pub fn helper_command(subcommand: &str) -> Result<String> {
    Ok(format!(
        "{} {}",
        quote(&env::current_exe()?.to_string_lossy()),
        quote(subcommand)
    ))
}
pub fn exists(program: &str) -> bool {
    env::split_paths(&env::var_os("PATH").unwrap_or_default())
        .any(|p| fs::metadata(p.join(program)).is_ok_and(|m| m.is_file() && m.mode() & 0o111 != 0))
}
pub fn private_dir(path: &Path) -> Result<()> {
    fs::DirBuilder::new()
        .recursive(true)
        .mode(0o700)
        .create(path)?;
    let info = fs::symlink_metadata(path)?;
    // SAFETY: getuid has no preconditions.
    if !info.is_dir() || info.uid() != unsafe { libc::getuid() } || info.mode() & 0o077 != 0 {
        bail!(
            "Directory must be private and owned by this user: {}",
            path.display()
        );
    }
    Ok(())
}
pub fn atomic_write(path: &Path, data: &[u8]) -> Result<()> {
    let mut file = tempfile::NamedTempFile::new_in(path.parent().context("No parent directory")?)?;
    file.write_all(data)?;
    file.persist(path)?;
    Ok(())
}
pub fn read_json(path: &Path) -> Result<Value> {
    Ok(serde_json::from_slice(&fs::read(path)?)?)
}
pub fn save_json(path: &Path, value: &Value) -> Result<()> {
    atomic_write(path, format!("{value}\n").as_bytes())
}
pub struct Lock(File);
impl Lock {
    pub fn acquire(path: &Path, deadline: Instant) -> Result<Self> {
        let file = OpenOptions::new()
            .create(true)
            .append(true)
            .mode(0o600)
            .custom_flags(libc::O_NOFOLLOW | libc::O_NONBLOCK)
            .open(path)?;
        let metadata = file.metadata()?;
        if !metadata.is_file() || metadata.uid() != unsafe { libc::getuid() } {
            bail!("Unsafe lock file");
        }
        loop {
            // SAFETY: fd belongs to this open file; flock is released on Drop.
            if unsafe { libc::flock(file.as_raw_fd(), libc::LOCK_EX | libc::LOCK_NB) } == 0 {
                return Ok(Self(file));
            }
            let error = std::io::Error::last_os_error();
            if error.kind() != std::io::ErrorKind::WouldBlock {
                return Err(error.into());
            }
            if Instant::now() >= deadline {
                bail!("Another operation is busy");
            }
            std::thread::sleep(Duration::from_millis(20));
        }
    }
}
impl Drop for Lock {
    fn drop(&mut self) {
        unsafe {
            libc::flock(self.0.as_raw_fd(), libc::LOCK_UN);
        }
    }
}
pub fn run(program: &str, args: &[&str], deadline: Instant) -> Result<String> {
    crate::command::output(program, args, deadline).map_err(anyhow::Error::msg)
}
pub fn zellij(session: &str, args: &[&str], deadline: Instant) -> Result<String> {
    let selection = format!("--session={session}");
    let mut command = vec![selection.as_str()];
    command.extend_from_slice(args);
    run("zellij", &command, deadline)
}
pub fn native(session: &str, args: &[&str]) -> Result<String> {
    zellij(session, args, Instant::now() + Duration::from_secs(5))
}
pub fn snapshot(session: &str, kind: &str) -> Result<Vec<Value>> {
    Ok(serde_json::from_str(&native(
        session,
        &["action", &format!("list-{kind}"), "--json"],
    )?)?)
}
pub fn pipe(session: &str, name: &str, payload: &Value, deadline: Instant) -> Result<String> {
    zellij(
        session,
        &[
            "pipe",
            "--plugin",
            PLUGIN,
            "--name",
            name,
            "--",
            &payload.to_string(),
        ],
        deadline,
    )
}
pub fn status_pipe(session: &str, name: &str, payload: &Value) -> Result<String> {
    pipe(
        session,
        name,
        payload,
        Instant::now() + Duration::from_secs(5),
    )
}
pub fn text<'a>(value: &'a Value, key: &str) -> Result<&'a str> {
    value
        .get(key)
        .and_then(Value::as_str)
        .with_context(|| format!("Missing or invalid {key}"))
}
pub fn number(value: &Value, key: &str) -> Result<u64> {
    value
        .get(key)
        .and_then(Value::as_u64)
        .with_context(|| format!("Missing or invalid {key}"))
}
pub fn flag(value: &Value, key: &str) -> bool {
    value.get(key).and_then(Value::as_bool).unwrap_or(false)
}
pub fn session() -> Result<String> {
    env::var("ZELLIJ_SESSION_NAME")
        .ok()
        .filter(|s| !s.is_empty())
        .context("Run inside a Zellij session")
}
pub fn pane_id() -> Result<u64> {
    env::var("ZELLIJ_PANE_ID")?
        .parse()
        .context("Run inside a Zellij terminal pane")
}
pub fn origin_id() -> Result<u64> {
    env::var("ZELLIJ_ORIGIN_PANE_ID")?
        .strip_prefix("terminal_")
        .context("Requires the pinned Zellij runtime")?
        .parse()
        .context("Invalid origin pane")
}
pub fn legacy() -> bool {
    home()
        .ok()
        .and_then(|h| h.join(".config/zellij/config.kdl").canonicalize().ok())
        .is_some_and(|p| p.file_name().is_some_and(|n| n == "config-legacy.kdl"))
}
pub fn fzf(args: &[String], input: String) -> Result<Option<String>> {
    let mut child = Command::new("fzf")
        .args(args)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .spawn()?;
    // fzf may quit before consuming input; a cancelled picker is still success.
    let mut stdin = child.stdin.take().context("Missing fzf input")?;
    let writer = std::thread::spawn(move || {
        let _ = stdin.write_all(input.as_bytes());
    });
    let output = child.wait_with_output()?;
    let _ = writer.join();
    if matches!(output.status.code(), Some(1 | 130)) {
        return Ok(None);
    }
    if !output.status.success() {
        bail!("fzf exited with {}", output.status);
    }
    Ok(Some(
        String::from_utf8(output.stdout)?
            .split('\t')
            .next()
            .unwrap_or("")
            .trim()
            .to_owned(),
    ))
}
