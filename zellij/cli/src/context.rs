use crate::{titles, util::*};
use anyhow::{bail, Context, Result};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::{HashMap, HashSet};
use std::path::Path;
use std::time::{Duration, Instant};

#[derive(Serialize, Deserialize)]
pub(crate) struct Session {
    pub session: String,
    location: titles::Location,
    pub identity: Value,
}

impl Session {
    pub fn socket(&self) -> Result<&Path> {
        Ok(Path::new(
            self.identity[0]
                .as_str()
                .context("Missing session socket")?,
        ))
    }

    pub fn resolve(session: &str, deadline: Instant) -> Result<Self> {
        let location = location(deadline)?;
        let identity = titles::session_identity(session, &location).map_err(anyhow::Error::msg)?;
        Ok(Self {
            session: session.to_owned(),
            location,
            identity,
        })
    }

    pub fn validate(&self, session: &str) -> Result<()> {
        anyhow::ensure!(
            self.session == session,
            "Session context belongs to another session"
        );
        anyhow::ensure!(
            titles::session_identity(session, &self.location).map_err(anyhow::Error::msg)?
                == self.identity,
            "Session context belongs to a previous server"
        );
        Ok(())
    }
}

pub fn socket() -> Result<String> {
    let location = location(Instant::now() + Duration::from_secs(1))?;
    Ok(crate::titles::session_identity(&session()?, &location)
        .map_err(anyhow::Error::msg)?
        .to_string())
}

pub(crate) fn location(deadline: Instant) -> Result<crate::titles::Location> {
    let check = run("zellij", &["setup", "--check"], deadline)?;
    if !check.lines().any(|line| line == "[Version]: \"0.46.0\"") {
        bail!("Direct IPC requires the pinned Zellij 0.46.0 runtime");
    }
    let cache = check
        .lines()
        .find_map(|line| line.strip_prefix("[CACHE DIR]: "))
        .map(std::path::PathBuf::from)
        .filter(|path| path.is_absolute())
        .ok_or_else(|| anyhow::anyhow!("Cannot identify the session index"))?;
    let directory = std::env::var_os("ZELLIJ_SOCKET_DIR")
        .map(std::path::PathBuf::from)
        .or_else(|| {
            if cfg!(target_os = "linux") {
                std::env::var_os("XDG_RUNTIME_DIR")
                    .map(|path| std::path::PathBuf::from(path).join("zellij"))
            } else {
                None
            }
        })
        .unwrap_or_else(|| {
            std::env::temp_dir().join(format!("zellij-{}", unsafe { libc::getuid() }))
        })
        .join("contract_version_1");
    if !directory.is_absolute() {
        bail!("Zellij socket directory must be absolute");
    }
    Ok((
        directory,
        cache.join("contract_version_1/session_index.sqlite"),
    ))
}

pub fn provider() -> Result<&'static str> {
    let column = if cfg!(target_os = "macos") {
        "ucomm"
    } else {
        "comm"
    };
    let output = run(
        "ps",
        &["-axo", &format!("pid=,ppid=,{column}=")],
        Instant::now() + Duration::from_millis(500),
    )?;
    ancestry(&output, unsafe { libc::getppid() } as u32)
}
fn ancestry(output: &str, mut pid: u32) -> Result<&'static str> {
    let processes: HashMap<u32, (u32, &str)> = output
        .lines()
        .filter_map(|line| {
            let mut fields = line.split_whitespace();
            Some((
                fields.next()?.parse().ok()?,
                (fields.next()?.parse().ok()?, fields.next()?),
            ))
        })
        .collect();
    let mut visited = HashSet::new();
    while pid > 1 && visited.len() < 64 {
        if !visited.insert(pid) {
            bail!("Cannot establish the caller's process ancestry");
        }
        let (parent, name) = processes
            .get(&pid)
            .ok_or_else(|| anyhow::anyhow!("Cannot establish the caller's process ancestry"))?;
        let name = Path::new(name)
            .file_name()
            .and_then(|s| s.to_str())
            .unwrap_or("");
        if name == "zellij" {
            return Ok("zellij");
        }
        if name == "tmux" || name.starts_with("tmux:") {
            return Ok("tmux");
        }
        pid = *parent;
    }
    if pid > 1 {
        bail!("Multiplexer ancestry exceeds the inspection limit");
    }
    Ok("none")
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn nearest_owner_and_missing_ancestry() {
        assert_eq!(
            ancestry("30 20 sh\n20 10 tmux: server\n10 1 zellij", 30).unwrap(),
            "tmux"
        );
        assert_eq!(
            ancestry("30 20 sh\n20 10 zellij\n10 1 tmux", 30).unwrap(),
            "zellij"
        );
        assert!(ancestry("30 20 sh\n20 30 sh", 30).is_err());
        assert!(ancestry("", 30).is_err());
    }
}
