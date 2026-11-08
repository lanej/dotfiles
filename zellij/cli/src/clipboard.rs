use crate::util::*;
use anyhow::{bail, Context, Result};
use std::env;
use std::fs::{self, OpenOptions};
use std::io::{Read, Write};
use std::os::unix::fs::{MetadataExt, OpenOptionsExt};
const MAX_BYTES: u64 = 1024 * 1024;

pub fn main(args: &[String]) -> Result<()> {
    let (action, rest) = args
        .split_first()
        .context("Usage: zellij-clipboard copy|read|clear [--session SESSION]")?;
    let selected = match rest {
        [] => session()?,
        [flag, value] if flag == "--session" => value.clone(),
        [option] if option.starts_with("--session=") => option[10..].to_owned(),
        _ => bail!("Usage: zellij-clipboard copy|read|clear [--session SESSION]"),
    };
    if selected.is_empty() {
        bail!("Run inside Zellij or specify --session");
    }
    if !matches!(action.as_str(), "copy" | "read" | "clear") {
        bail!("Expected copy, read or clear");
    }
    let base = env::var_os("XDG_RUNTIME_DIR")
        .filter(|s| !s.is_empty())
        .map(std::path::PathBuf::from)
        .unwrap_or_else(env::temp_dir);
    let directory = base.join(format!("zellij-clipboard-{}", unsafe { libc::getuid() }));
    private_dir(&directory)?;
    let path = directory.join(hash(&selected));
    match action.as_str() {
        "clear" => match fs::remove_file(path) {
            Ok(()) => {}
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => {}
            Err(e) => return Err(e.into()),
        },
        "copy" => {
            let mut data = Vec::new();
            std::io::stdin()
                .take(MAX_BYTES + 1)
                .read_to_end(&mut data)?;
            if data.len() as u64 > MAX_BYTES {
                bail!("The selection exceeds the 1 MiB copy-buffer limit");
            }
            std::str::from_utf8(&data)?;
            atomic_write(&path, &data)?;
        }
        "read" => {
            let file = OpenOptions::new()
                .read(true)
                .custom_flags(libc::O_NOFOLLOW | libc::O_NONBLOCK)
                .open(path)
                .context(
                    "The session buffer is empty or unavailable; yank a selection in Neovim first",
                )?;
            let info = file.metadata()?;
            if !info.is_file()
                || info.uid() != unsafe { libc::getuid() }
                || info.mode() & 0o077 != 0
            {
                bail!("The copy buffer must be a private regular file");
            }
            let mut data = Vec::new();
            file.take(MAX_BYTES + 1).read_to_end(&mut data)?;
            if data.len() as u64 > MAX_BYTES {
                bail!("The copy buffer exceeds 1 MiB");
            }
            let text = std::str::from_utf8(&data)?;
            if text.chars().any(|c| {
                (c < ' ' && !matches!(c, '\t' | '\n' | '\r')) || ('\u{7f}'..'\u{a0}').contains(&c)
            }) {
                bail!("The selection contains terminal control characters; paste was cancelled");
            }
            std::io::stdout().write_all(&data)?;
        }
        _ => unreachable!(),
    }
    Ok(())
}
