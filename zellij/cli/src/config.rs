use lane_zellij_protocol::{AttentionConfig, MAX_CONFIG_BYTES};
use serde::Deserialize;
use std::fs::OpenOptions;
use std::io::{ErrorKind, Read};
use std::os::unix::fs::OpenOptionsExt;
use std::path::PathBuf;

pub fn home() -> Result<PathBuf, String> {
    std::env::var_os("HOME")
        .filter(|home| !home.is_empty())
        .map(PathBuf::from)
        .ok_or_else(|| "HOME is not set".into())
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Document {
    attention: AttentionConfig,
}

pub fn load() -> Result<AttentionConfig, String> {
    let base = std::env::var_os("XDG_CONFIG_HOME")
        .map(PathBuf::from)
        .filter(|path| path.is_absolute());
    let base = match base {
        Some(base) => base,
        None => home()?.join(".config"),
    };
    let path = base.join("zellij/lane-status.toml");
    let read = || -> Result<AttentionConfig, String> {
        // O_NONBLOCK prevents a mistaken FIFO from stalling the command before
        // fstat can reject it. Bound the read even if the file grows meanwhile.
        let file = match OpenOptions::new()
            .read(true)
            .custom_flags(libc::O_NONBLOCK)
            .open(&path)
        {
            Ok(file) => file,
            Err(error) if error.kind() == ErrorKind::NotFound => {
                return Ok(AttentionConfig::default())
            }
            Err(error) => return Err(error.to_string()),
        };
        if !file.metadata().map_err(|e| e.to_string())?.is_file() {
            return Err("expected a regular file".into());
        }
        let mut bytes = Vec::new();
        file.take((MAX_CONFIG_BYTES + 1) as u64)
            .read_to_end(&mut bytes)
            .map_err(|e| e.to_string())?;
        if bytes.len() > MAX_CONFIG_BYTES {
            return Err("configuration exceeds 16 KiB".into());
        }
        let raw = std::str::from_utf8(&bytes).map_err(|e| e.to_string())?;
        let document: Document = toml::from_str(raw).map_err(|e| e.to_string())?;
        document.attention.policy()?;
        Ok(document.attention)
    };
    read().map_err(|error| format!("{}: {error}", path.display()))
}
