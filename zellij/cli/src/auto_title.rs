use crate::{titles, util::*};
use anyhow::{Context, Result};
use serde_json::{json, Value};
use std::env;
use std::path::PathBuf;
use std::time::{Duration, Instant};
fn snapshot(session: &str, pane: u64, deadline: Instant) -> Result<Option<(u64, String)>> {
    let panes: Vec<Value> = serde_json::from_str(&zellij(
        session,
        &["action", "list-panes", "--json"],
        deadline,
    )?)?;
    panes
        .iter()
        .find(|p| {
            p["id"] == pane
                && !flag(p, "is_plugin")
                && flag(p, "is_focused")
                && !flag(p, "is_suppressed")
                && !flag(p, "exited")
        })
        .map(|p| Ok((number(p, "tab_id")?, text(p, "tab_name")?.to_owned())))
        .transpose()
}
pub fn main() -> Result<()> {
    let session = session()?;
    let pane = pane_id()?;
    let mut deadline = Instant::now() + Duration::from_millis(800);
    if crate::context::provider()? != "zellij" {
        return Ok(());
    }
    let location = titles::location_before(deadline).map_err(anyhow::Error::msg)?;
    let identity = titles::session_identity(&session, &location).map_err(anyhow::Error::msg)?;
    let directory = state("zellij-auto-titles")?;
    private_dir(&directory)?;
    let key = hash(&session);
    let _lock = Lock::acquire(&directory.join(format!("{key}.lock")), Instant::now())?;
    let Some((id, name)) = snapshot(&session, pane, deadline)? else {
        return Ok(());
    };
    let path = directory.join(format!("{key}-{id}.json"));
    let previous = titles::record_title(&path, &identity);
    let default = name.is_empty()
        || name
            .strip_prefix("Tab #")
            .is_some_and(|s| !s.is_empty() && s.bytes().all(|b| b.is_ascii_digit()));
    if !default && Some(name.as_str()) != previous.as_deref() {
        return Ok(());
    }
    let cwd = env::var_os("PWD")
        .map(PathBuf::from)
        .unwrap_or(env::current_dir()?);
    let mut title = cwd
        .file_name()
        .map(|n| n.to_string_lossy().into_owned())
        .unwrap_or("/".into());
    if let Ok(branch) = run("git", &["rev-parse", "--abbrev-ref", "HEAD"], deadline) {
        if !branch.trim().is_empty() {
            title += &format!(" [{}]", branch.trim());
        }
    }
    title = clean(&title, usize::MAX);
    if title == name {
        return Ok(());
    }
    if snapshot(&session, pane, deadline)? != Some((id, name)) {
        return Ok(());
    }
    if titles::session_identity(&session, &location).map_err(anyhow::Error::msg)? != identity {
        return Ok(());
    }
    if Instant::now() >= deadline {
        return Ok(());
    }
    deadline = deadline.max(Instant::now() + Duration::from_millis(500));
    zellij(
        &session,
        &[
            "action",
            "rename-tab",
            "--tab-id",
            &id.to_string(),
            "--",
            &title,
        ],
        deadline,
    )?;
    save_json(&path, &json!({"identity":identity,"title":title}))
        .context("Cannot retain automatic title ownership")
}

/// OSC emission is native; the shell only decides when its hooks should run.
pub fn shell_title() -> Result<()> {
    use std::io::{IsTerminal, Write};
    if !std::io::stdout().is_terminal() {
        return Ok(());
    }
    let cwd = env::var_os("PWD")
        .map(PathBuf::from)
        .unwrap_or(env::current_dir()?);
    let mut title = cwd
        .file_name()
        .map(|s| s.to_string_lossy().into_owned())
        .unwrap_or("/".into());
    if let Ok(branch) = run(
        "git",
        &["rev-parse", "--abbrev-ref", "HEAD"],
        Instant::now() + Duration::from_millis(500),
    ) {
        if !branch.trim().is_empty() {
            title += &format!(" [{}]", branch.trim());
        }
    }
    title = title
        .chars()
        .map(|c| if c.is_control() { ' ' } else { c })
        .collect();
    write!(std::io::stdout(), "\x1b]2;{title}\x07")?;
    Ok(())
}
