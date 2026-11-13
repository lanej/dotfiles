use crate::{titles, util::*};
use anyhow::{bail, Context, Result};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
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
    pub fn persistent_identity(&self) -> Result<Value> {
        self.validate(&self.session)?;
        let connection = rusqlite::Connection::open_with_flags(
            &self.location.1,
            rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY,
        )?;
        connection.busy_timeout(Duration::from_millis(100))?;
        let (id, created): (String, i64) = connection.query_row(
            "SELECT COALESCE(id, name), created_at FROM sessions WHERE name = ?",
            [&self.session],
            |row| Ok((row.get(0)?, row.get(1)?)),
        )?;
        anyhow::ensure!(
            self.socket()?.file_name().and_then(|name| name.to_str()) == Some(id.as_str()),
            "Session changed while reading its persistent identity"
        );
        self.validate(&self.session)?;
        Ok(serde_json::json!([self.location.1, id, created]))
    }

    pub fn socket(&self) -> Result<&Path> {
        Ok(Path::new(
            self.identity[0]
                .as_str()
                .context("Missing session socket")?,
        ))
    }

    pub fn resolve(session: &str) -> Result<Self> {
        let location = location()?;
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
    Ok(Session::resolve(&session()?)?.identity.to_string())
}

pub(crate) fn location() -> Result<crate::titles::Location> {
    // rationale: Use the pinned runtime's ProjectDirs tuple and contract namespace directly.
    // Running `zellij setup --check` here costs far more than the actual IPC requests.
    let project = directories::ProjectDirs::from("org", "Zellij Contributors", "Zellij")
        .context("Cannot identify the Zellij directories")?;
    let socket_override = std::env::var("ZELLIJ_SOCKET_DIR").ok();
    let directory = socket_override
        .as_ref()
        .map(std::path::PathBuf::from)
        .or_else(|| project.runtime_dir().map(Path::to_path_buf))
        .unwrap_or_else(|| {
            std::env::temp_dir().join(format!("zellij-{}", unsafe { libc::getuid() }))
        })
        .join("contract_version_1");
    if !directory.is_absolute() {
        bail!("Zellij socket directory must be absolute");
    }
    // rationale: The runtime isolates indexes for overridden socket directories.
    let index_name = if socket_override.is_some() {
        let hash: String = Sha256::digest(directory.as_os_str().as_encoded_bytes())
            .iter()
            .take(6)
            .map(|byte| format!("{byte:02x}"))
            .collect();
        format!("session_index-{hash}.sqlite")
    } else {
        "session_index.sqlite".to_owned()
    };
    Ok((
        directory,
        project
            .cache_dir()
            .join("contract_version_1")
            .join(index_name),
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
