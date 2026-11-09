//! Cosmetic agent titles preserve explicit user names and reject delayed events.
use crate::util::*;
use anyhow::{bail, Context, Result};
use serde_json::{json, Value};
use std::fs;
use std::io::Read;
use std::path::PathBuf;
use std::time::{Duration, Instant};
struct Hook {
    identity: String,
    kind: String,
    event: Value,
    started: u64,
    deadline: Instant,
    directory: PathBuf,
    path: PathBuf,
    options: Value,
}
impl Hook {
    fn load(agent: &str, args: &[String]) -> Result<Self> {
        let started = match args {
            [] => now_ns(),
            [flag, value] if flag == "--timestamp" => value.parse()?,
            [value] if value.starts_with("--timestamp=") => value[12..].parse()?,
            _ => bail!("Usage: title hook [--timestamp NANOSECONDS]"),
        };
        let mut data = String::new();
        std::io::stdin()
            .take(1024 * 1024)
            .read_to_string(&mut data)?;
        let event: Value = serde_json::from_str(&data)?;
        if event.get("agent_id").is_some_and(truthy)
            || (agent == "codex" && event.get("agent_type").is_some_and(truthy))
        {
            bail!("Subagent event");
        }
        let identity = uuid(text(&event, "session_id")?)?;
        let kind = text(&event, "hook_event_name")?.to_owned();
        let directory = state(&format!("{agent}-zellij-titles"))?;
        private_dir(&directory)?;
        let path = directory.join(format!("{identity}.json"));
        Ok(Self {
            identity,
            kind,
            event,
            started,
            deadline: Instant::now() + Duration::from_millis(2500),
            directory,
            path,
            options: read_json(&root()?.join(format!("{agent}/zellij-title.json")))?,
        })
    }
    fn command(&self, args: &[&str]) -> Result<String> {
        run(
            "zellij",
            args,
            self.deadline
                .min(Instant::now() + Duration::from_millis(600)),
        )
    }
    fn panes(&self, session: &str) -> Result<Vec<Value>> {
        let rows: Vec<Value> = serde_json::from_str(&self.command(&[
            "--session",
            session,
            "action",
            "list-panes",
            "--json",
        ])?)?;
        Ok(rows
            .into_iter()
            .filter(|p| !flag(p, "is_plugin") && !flag(p, "exited"))
            .collect())
    }
    fn rename(&self, session: &str, pane: u64, title: &str) -> Result<()> {
        self.command(&[
            "--session",
            session,
            "action",
            "rename-pane",
            "--pane-id",
            &format!("terminal_{pane}"),
            title,
        ])?;
        Ok(())
    }
    fn save(&self, mut state: Value) -> Result<()> {
        state["updated_at"] = json!(self.started);
        save_json(&self.path, &state)
    }
    fn state(&self) -> Result<Value> {
        if self.path.exists() {
            read_json(&self.path)
        } else {
            Ok(json!({}))
        }
    }
    fn title(&self, status: &str) -> Result<String> {
        let format = text(&self.options, "format")?;
        let glyph = text(&self.options["states"], status)?;
        let project = std::path::Path::new(text(&self.event, "cwd")?)
            .file_name()
            .unwrap_or_default()
            .to_string_lossy();
        let project = clean(&project, usize::MAX);
        format_title(format, &self.identity, glyph, &project)
    }
}
fn truthy(v: &Value) -> bool {
    match v {
        Value::Null => false,
        Value::Bool(b) => *b,
        Value::String(s) => !s.is_empty(),
        Value::Number(n) => n.as_f64() != Some(0.),
        Value::Array(a) => !a.is_empty(),
        Value::Object(o) => !o.is_empty(),
    }
}
fn uuid(s: &str) -> Result<String> {
    let s = s
        .strip_prefix("urn:uuid:")
        .unwrap_or(s)
        .trim_matches(['{', '}'])
        .replace('-', "")
        .to_ascii_lowercase();
    if s.len() != 32 || !s.bytes().all(|b| b.is_ascii_hexdigit()) {
        bail!("Invalid session UUID");
    }
    Ok(format!(
        "{}-{}-{}-{}-{}",
        &s[..8],
        &s[8..12],
        &s[12..16],
        &s[16..20],
        &s[20..]
    ))
}
fn format_title(format: &str, id: &str, status: &str, project: &str) -> Result<String> {
    let mut out = String::new();
    let mut rest = format;
    while !rest.is_empty() {
        if let Some(next) = rest.strip_prefix("{{") {
            out.push('{');
            rest = next;
            continue;
        }
        if let Some(next) = rest.strip_prefix("}}") {
            out.push('}');
            rest = next;
            continue;
        }
        if let Some(next) = rest.strip_prefix('{') {
            let (field, next) = next.split_once('}').context("Invalid title format")?;
            let (name, precision) = if let Some((name, precision)) = field.split_once(":.") {
                (name, Some(precision.parse::<usize>()?))
            } else {
                (field, None)
            };
            let value = match name {
                "id" => id,
                "status" => status,
                "project" => project,
                _ => bail!("Unknown title format field: {name}"),
            };
            out.extend(value.chars().take(precision.unwrap_or(usize::MAX)));
            rest = next;
        } else {
            let c = rest.chars().next().context("Empty title")?;
            if c == '}' {
                bail!("Invalid title format");
            }
            out.push(c);
            rest = &rest[c.len_utf8()..];
        }
    }
    Ok(out)
}
fn current(h: &Hook, session: &str, pane: u64) -> Result<Option<String>> {
    let matches: Vec<_> = h
        .panes(session)?
        .into_iter()
        .filter(|p| p["id"] == pane)
        .collect();
    if matches.len() != 1 {
        return Ok(None);
    }
    Ok(Some(text(&matches[0], "title")?.to_owned()))
}
pub fn claude(args: &[String]) -> Result<()> {
    let mut h = Hook::load("claude", args)?;
    let session = session()?;
    let pane = pane_id()?;
    if crate::context::provider()? != "zellij" {
        return Ok(());
    }
    h.path = h
        .directory
        .join(format!("{}.json", hash(&format!("{session}\0{pane}"))));
    let _lock = Lock::acquire(&h.directory.join(".lock"), h.deadline)?;
    let mut state = h.state()?;
    if h.started < state["updated_at"].as_u64().unwrap_or(0) {
        return Ok(());
    }
    if h.kind != "SessionStart" && (state["identity"] != h.identity || flag(&state, "ended")) {
        return Ok(());
    }
    if h.kind == "SessionStart" && state["identity"] != h.identity {
        state = json!({"identity":h.identity,"title":state["title"]});
    }
    if h.kind == "SessionStart" {
        state["ended"] = json!(false);
        state["question"] = json!(false);
        state["approval"] = json!(false);
    }
    let Some(title) = current(&h, &session, pane)? else {
        return Ok(());
    };
    if h.kind == "SessionEnd" {
        if state["title"] == title {
            h.rename(&session, pane, "")?;
        }
        state["ended"] = json!(true);
        return h.save(state);
    }
    if flag(&state, "opted_out") {
        return Ok(());
    }
    if state["title"] != title {
        let native = (|| -> Result<Option<String>> {
            h.rename(&session, pane, "")?;
            current(&h, &session, pane)
        })();
        if native.as_ref().ok().and_then(|s| s.as_deref()) != Some(title.as_str()) {
            // Cleanup has its own bounded acknowledgement window.
            let _ = run(
                "zellij",
                &[
                    "--session",
                    &session,
                    "action",
                    "rename-pane",
                    "--pane-id",
                    &format!("terminal_{pane}"),
                    &title,
                ],
                Instant::now() + Duration::from_millis(600),
            );
        }
        let Some(native) = native? else {
            return Ok(());
        };
        if native != title {
            state["opted_out"] = json!(true);
            return h.save(state);
        }
    }
    if h.kind == "UserPromptSubmit" {
        state["question"] = json!(false);
        state["approval"] = json!(false);
    }
    let tool = h.event["tool_name"].as_str().unwrap_or("");
    if h.kind == "PreToolUse" && tool == "AskUserQuestion" {
        state["question"] = json!(true);
    }
    if h.kind == "PermissionRequest" {
        state["approval"] = json!(true);
    }
    if matches!(h.kind.as_str(), "PostToolUse" | "PostToolUseFailure") {
        state["approval"] = json!(false);
        if tool == "AskUserQuestion" {
            state["question"] = json!(false);
        }
    }
    if h.kind == "Notification" {
        match h.event["notification_type"].as_str() {
            Some("permission_prompt" | "elicitation_dialog") => state["approval"] = json!(true),
            Some("idle_prompt") => {}
            _ => return Ok(()),
        }
    }
    if matches!(h.kind.as_str(), "Stop" | "StopFailure") || flag(&h.event, "is_interrupt") {
        state["question"] = json!(false);
        state["approval"] = json!(false);
    }
    let status = if h.kind == "StopFailure" {
        "failed"
    } else if flag(&h.event, "is_interrupt") {
        "idle"
    } else if flag(&state, "question") || flag(&state, "approval") {
        "attention"
    } else if h.kind == "Stop"
        || (h.kind == "SessionStart" && h.event["source"] != "compact")
        || h.kind == "Notification"
    {
        "ready"
    } else {
        "working"
    };
    let title = h.title(status)?;
    h.rename(&session, pane, &title)?;
    state["title"] = json!(title);
    h.save(state)
}
fn owns(title: &str, identity: &str) -> bool {
    let mut fields = title
        .strip_prefix("[ ! ] Action Required | ")
        .unwrap_or(title)
        .split(" | ");
    if fields.next() != Some("codex") {
        return false;
    }
    let Some(prefix) = fields.next() else {
        return false;
    };
    let prefix = prefix.strip_suffix("...").unwrap_or(prefix);
    prefix.len() >= 16 && identity.starts_with(prefix)
}
fn records(h: &Hook) -> Result<Vec<(String, Value)>> {
    let mut rows = vec![];
    for entry in fs::read_dir(&h.directory)? {
        let path = entry?.path();
        if path.extension().is_some_and(|s| s == "json") {
            rows.push((
                path.file_stem()
                    .context("Invalid record name")?
                    .to_string_lossy()
                    .into_owned(),
                read_json(&path)?,
            ));
        }
    }
    Ok(rows)
}
fn reveal(
    h: &Hook,
    session: &str,
    pane: &Value,
    record: &Value,
    owner: &str,
) -> Result<Option<Value>> {
    if pane["title"] != record["title"] {
        return Ok(Some(pane.clone()));
    }
    let id = number(pane, "id")?;
    h.rename(session, id, "")?;
    let native = h.panes(session)?.into_iter().find(|p| p["id"] == id);
    if let Some(native) = &native {
        let title = text(native, "title")?;
        if owner != h.identity && owns(title, owner) {
            h.rename(session, id, text(record, "title")?)?;
        } else if !owns(title, &h.identity) {
            for (other, active) in records(h)? {
                if !flag(&active, "ended")
                    && active["session"] == session
                    && active["pane"] == id
                    && active["title"] == pane["title"]
                    && owns(title, &other)
                {
                    h.rename(session, id, text(&active, "title")?)?;
                    break;
                }
            }
        }
    }
    Ok(native)
}
pub fn codex(args: &[String]) -> Result<()> {
    let h = Hook::load("codex", args)?;
    let _lock = Lock::acquire(&h.directory.join(".lock"), h.deadline)?;
    let mut state = h.state()?;
    if h.started < state["updated_at"].as_u64().unwrap_or(0)
        || (flag(&state, "ended") && !matches!(h.kind.as_str(), "SessionStart" | "SessionEnd"))
    {
        return Ok(());
    }
    let mut target = None;
    if let Some(session) = state["session"].as_str() {
        let attempt = (|| -> Result<Option<Value>> {
            let candidate = h
                .panes(session)?
                .into_iter()
                .find(|p| p["id"] == state["pane"]);
            let candidate = match candidate {
                Some(p) => reveal(&h, session, &p, &state, &h.identity)?,
                None => None,
            };
            Ok(candidate.filter(|p| p["title"].as_str().is_some_and(|t| owns(t, &h.identity))))
        })();
        target = attempt.unwrap_or(None);
    }
    if h.kind == "SessionEnd" {
        state["ended"] = json!(true);
        return h.save(state);
    }
    if target.is_none() {
        let mut matches = vec![];
        let mut snapshots = std::collections::BTreeMap::new();
        for session in h.command(&["list-sessions", "--short"])?.lines() {
            let Ok(panes) = h.panes(session) else {
                continue;
            };
            for pane in &panes {
                if owns(text(pane, "title")?, &h.identity) {
                    matches.push((session.to_owned(), pane.clone()));
                }
            }
            snapshots.insert(session.to_owned(), panes);
        }
        if matches.is_empty() {
            let mut revealed = std::collections::BTreeSet::new();
            for (owner, record) in records(&h)? {
                let Some(session) = record["session"].as_str() else {
                    continue;
                };
                let Some(panes) = snapshots.get(session) else {
                    continue;
                };
                if flag(&record, "ended") {
                    continue;
                }
                let id = number(&record, "pane")?;
                if revealed.contains(&(session.to_owned(), id)) {
                    continue;
                }
                if let Some(pane) = panes
                    .iter()
                    .find(|p| p["id"] == id && p["title"] == record["title"])
                {
                    revealed.insert((session.to_owned(), id));
                    if let Ok(Some(candidate)) = reveal(&h, session, pane, &record, &owner) {
                        if owns(text(&candidate, "title")?, &h.identity) {
                            matches.push((session.to_owned(), candidate));
                        }
                    }
                }
            }
        }
        if matches.len() != 1 {
            return Ok(());
        }
        let (session, pane) = matches.remove(0);
        state = json!({"session":session,"pane":pane["id"]});
        target = Some(pane);
    }
    if h.kind == "SessionStart" {
        state["ended"] = json!(false);
        state["question"] = json!(false);
    }
    if h.kind == "UserPromptSubmit" {
        state["question"] = json!(false);
    }
    let tool = h.event["tool_name"]
        .as_str()
        .unwrap_or("")
        .rsplit('.')
        .next()
        .unwrap_or("");
    if h.kind == "PreToolUse" && matches!(tool, "request_user_input" | "request_user_input_async") {
        state["question"] = json!(true);
    }
    if h.kind == "PostToolUse" && tool == "request_user_input" {
        state["question"] = json!(false);
    }
    let status = if h.kind == "PermissionRequest" || flag(&state, "question") {
        "attention"
    } else if h.kind == "Interrupt" {
        "idle"
    } else if h.kind == "Stop" || (h.kind == "SessionStart" && h.event["source"] != "compact") {
        "ready"
    } else {
        "working"
    };
    let title = h.title(status)?;
    h.rename(
        text(&state, "session")?,
        number(&target.context("Missing target")?, "id")?,
        &title,
    )?;
    state["title"] = json!(title);
    h.save(state)
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn full_native_identity_is_required() {
        assert!(owns(
            "codex | 019a1234-abcd-7000... | work",
            "019a1234-abcd-7000-aaaa-bbbbbbbbbbbb"
        ));
        assert!(!owns(
            "codex | 019a1234... | work",
            "019a1234-abcd-7000-aaaa-bbbbbbbbbbbb"
        ));
    }
    #[test]
    fn format_keeps_custom_fields_and_precision() {
        assert_eq!(
            format_title(
                "✳ {id:.8} {status} | {project}",
                "12345678-abcd",
                "✓",
                "project"
            )
            .unwrap(),
            "✳ 12345678 ✓ | project"
        );
        assert!(format_title("{unknown}", "", "", "").is_err());
    }
}
