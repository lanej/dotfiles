//! One stable forwarded-agent path per user. Only fresh remote logins publish.
use crate::util::home;
use anyhow::{bail, Context, Result};
use std::env;
use std::fs;
use std::os::unix::fs::{symlink, DirBuilderExt, FileTypeExt, MetadataExt, PermissionsExt};
use std::path::{Path, PathBuf};

fn owned(info: &fs::Metadata) -> bool {
    info.uid() == unsafe { libc::getuid() }
}

fn directory(path: &Path, private: bool) -> Result<()> {
    if !path.try_exists()? {
        let _ = fs::DirBuilder::new().mode(0o700).create(path);
    }
    let info = fs::symlink_metadata(path)?;
    if !info.is_dir() || !owned(&info) || info.mode() & if private { 0o077 } else { 0o022 } != 0 {
        bail!("Unsafe agent directory: {}", path.display());
    }
    Ok(())
}

/// Every remote process selects this path, even before an agent is forwarded.
/// Selection never publishes an inherited socket, including outside a mux.
pub fn select() -> Result<Option<PathBuf>> {
    if !env::var("SSH_CONNECTION").is_ok_and(|s| !s.is_empty()) {
        return Ok(None);
    }
    let ssh = home()?.join(".ssh");
    let dir = ssh.join("dotfiles-agent");
    let link = dir.join("forwarded.sock");
    directory(&ssh, false)?;
    directory(&dir, true)?;
    match fs::symlink_metadata(&link) {
        Ok(info) if !info.is_symlink() || !owned(&info) => {
            bail!("Refusing unmanaged agent path: {}", link.display());
        }
        Ok(_) => {}
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => {}
        Err(error) => return Err(error.into()),
    }
    Ok(Some(link))
}

/// Called by ~/.ssh/rc, before any user shell or command is launched.
fn publish_login() -> Result<()> {
    if let Some(link) = select()? {
        if let Some(raw) = env::var_os("DOTFILES_SSH_INCOMING_SOCK")
            .or_else(|| env::var_os("SSH_AUTH_SOCK"))
            .filter(|s| !s.is_empty())
            .map(PathBuf::from)
            .filter(|raw| *raw != link)
        {
            let info = fs::symlink_metadata(&raw)?;
            if !raw.is_absolute() || !info.file_type().is_socket() || !owned(&info) {
                bail!(
                    "Expected an owned raw forwarded SSH agent socket: {}",
                    raw.display()
                );
            }
            let staging = tempfile::Builder::new()
                .prefix(".refresh.")
                .permissions(fs::Permissions::from_mode(0o700))
                .tempdir_in(link.parent().context("Missing agent directory")?)?;
            let replacement = staging.path().join("agent.sock");
            symlink(raw, &replacement)?;
            fs::rename(replacement, &link)?;
        }
    }
    Ok(())
}

pub fn main(args: &[String]) -> Result<()> {
    match args {
        [op] if op == "init" => {
            if let Some(path) = select()? {
                println!("{}", path.display());
            }
        }
        [op] if op == "publish-login" => publish_login()?,
        // Compatibility for installed launchers from the session-scoped setup.
        [op, _session] if matches!(op.as_str(), "refresh" | "refresh-after-attach") => {
            select()?;
        }
        [op] if op == "follow-popup" => {}
        _ => bail!("Usage: zellij-agent init | publish-login"),
    }
    Ok(())
}
