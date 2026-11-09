use crate::util::*;
use anyhow::{bail, Result};
use std::collections::{HashMap, HashSet};
use std::path::Path;
use std::time::{Duration, Instant};

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
