use crate::util::*;
use anyhow::{bail, Context, Result};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::collections::HashSet;
use std::env;
use std::fs;
use std::io::Read;
use std::path::PathBuf;
use std::time::{Duration, Instant};
const LIMIT: usize = 500;
const MAX_BYTES: u64 = 2 * 1024 * 1024;
#[derive(Clone, Copy, Debug, Deserialize, Serialize)]
#[serde(rename_all = "lowercase")]
enum Level {
    Info,
    Success,
    Warn,
    Error,
}
impl Level {
    fn glyph(self) -> (&'static str, &'static str) {
        match self {
            Self::Info => ("·", "136;192;208"),
            Self::Success => ("✓", "163;190;140"),
            Self::Warn => ("!", "235;203;139"),
            Self::Error => ("×", "191;97;106"),
        }
    }
}
#[derive(Clone, Deserialize, Serialize)]
struct Notice {
    id: String,
    session: String,
    pane_id: String,
    title: String,
    message: String,
    level: Level,
    time_ms: u64,
    #[serde(default)]
    server_pid: Option<u64>,
    #[serde(default)]
    pane_pid: Option<u64>,
}
fn state_dir() -> Result<PathBuf> {
    Ok(env::var_os("XDG_STATE_HOME")
        .map(PathBuf::from)
        .filter(|p| p.is_absolute())
        .unwrap_or(home()?.join(".local/state"))
        .join("dotfiles/zellij"))
}
fn read_history() -> Result<Vec<Notice>> {
    let path = state_dir()?.join("notifications.json");
    let file = match fs::File::open(&path) {
        Ok(file) => file,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(vec![]),
        Err(e) => return Err(e.into()),
    };
    let mut bytes = Vec::new();
    file.take(MAX_BYTES + 1).read_to_end(&mut bytes)?;
    if bytes.len() as u64 > MAX_BYTES {
        bail!("Notification history exceeds its size limit");
    }
    let rows: Vec<Notice> = serde_json::from_slice(&bytes)?;
    if rows.iter().any(|r| r.time_ms > 253402300799000) {
        bail!("Notification history contains an invalid record");
    }
    Ok(rows)
}
fn record(payload: &str) -> Result<()> {
    if payload.len() > 128 * 1024 {
        bail!("Notification batch is too large");
    }
    let batch: Vec<Value> = serde_json::from_str(payload)?;
    if batch.len() > 64 {
        bail!("Expected at most 64 notifications");
    }
    let dir = state_dir()?;
    private_dir(&dir)?;
    let _lock = Lock::acquire(
        &dir.join("notifications.lock"),
        Instant::now() + Duration::from_secs(5),
    )?;
    let mut rows = read_history()?;
    let mut known: HashSet<_> = rows.iter().map(|r| r.id.clone()).collect();
    let mut changed = false;
    for value in batch {
        let level: Level = serde_json::from_value(value["level"].clone())?;
        if !value.is_object() {
            bail!("Invalid notification");
        }
        let field = |key: &str, size| {
            clean(
                value
                    .get(key)
                    .map(|v| {
                        v.as_str()
                            .map(str::to_owned)
                            .unwrap_or_else(|| v.to_string())
                    })
                    .unwrap_or_default()
                    .as_str(),
                size,
            )
        };
        let id = field("id", 1024);
        if id.is_empty() || !known.insert(id.clone()) {
            continue;
        }
        let integer = |key: &str| {
            value
                .get(key)
                .and_then(Value::as_u64)
                .filter(|n| *n <= i64::MAX as u64)
        };
        let time_ms = integer("time_ms")
            .filter(|n| *n != 0)
            .unwrap_or_else(now_ms);
        if time_ms > 253402300799000 {
            bail!("Notification time is out of range");
        }
        rows.push(Notice {
            id,
            session: field("session", 256),
            pane_id: field("pane_id", 32),
            title: field("title", 120),
            message: field("message", 512),
            level,
            time_ms,
            server_pid: integer("server_pid"),
            pane_pid: integer("pane_pid"),
        });
        changed = true;
    }
    if !changed {
        return Ok(());
    }
    rows.sort_by_key(|r| r.time_ms);
    if rows.len() > LIMIT {
        rows.drain(..rows.len() - LIMIT);
    }
    let mut encoded = serde_json::to_vec(&rows)?;
    while encoded.len() as u64 >= MAX_BYTES && !rows.is_empty() {
        rows.remove(0);
        encoded = serde_json::to_vec(&rows)?;
    }
    encoded.push(b'\n');
    atomic_write(&dir.join("notifications.json"), &encoded)
}
fn validate_source(row: &Notice) -> Result<()> {
    if row.pane_pid.is_none()
        || !row
            .pane_id
            .strip_prefix("terminal_")
            .is_some_and(|s| !s.is_empty() && s.bytes().all(|b| b.is_ascii_digit()))
    {
        bail!("This notification has no live source pane");
    }
    let reply = status_pipe(
        &row.session,
        "lane-notification-validate",
        &serde_json::to_value(row)?,
    )?;
    if !reply.lines().any(|l| l == "valid") {
        bail!("The source pane closed or changed; the notification remains in history");
    }
    Ok(())
}
fn show(id: &str) -> Result<()> {
    let rows = read_history()?;
    let result = (|| -> Result<String> {
        let row = rows.iter().find(|r| r.id == id).context("Missing notice")?;
        validate_source(row)?;
        let content = native(
            &row.session,
            &["action", "dump-screen", "--ansi", "--pane-id", &row.pane_id],
        )?;
        validate_source(row)?;
        Ok(content)
    })();
    println!(
        "{}",
        result.as_deref().unwrap_or("Pane unavailable").trim_end()
    );
    Ok(())
}
fn jump(row: &Notice) -> Result<()> {
    let origin = session()?;
    validate_source(row)?;
    if row.session == origin {
        native(&origin, &["action", "focus-pane-id", &row.pane_id])?;
    } else {
        native(
            &origin,
            &[
                "action",
                "switch-session",
                "--pane-id",
                &row.pane_id,
                "--",
                &row.session,
            ],
        )?;
    }
    Ok(())
}
fn stamp(ms: u64, format: &str) -> String {
    let time = (ms / 1000) as libc::time_t;
    let mut tm = std::mem::MaybeUninit::<libc::tm>::uninit();
    // SAFETY: localtime_r initializes tm; strftime writes within the fixed buffer.
    unsafe {
        if libc::localtime_r(&time, tm.as_mut_ptr()).is_null() {
            return String::new();
        }
        let mut out = [0u8; 64];
        let Ok(format) = std::ffi::CString::new(format) else {
            return String::new();
        };
        let n = libc::strftime(
            out.as_mut_ptr().cast(),
            out.len(),
            format.as_ptr(),
            tm.as_ptr(),
        );
        String::from_utf8_lossy(&out[..n]).into_owned()
    }
}
fn history() -> Result<()> {
    let mut rows = read_history()?;
    rows.reverse();
    let dates: HashSet<_> = rows.iter().map(|r| stamp(r.time_ms, "%Y-%m-%d")).collect();
    let times: HashSet<_> = rows.iter().map(|r| stamp(r.time_ms, "%H:%M")).collect();
    let years: HashSet<_> = rows.iter().map(|r| stamp(r.time_ms, "%Y")).collect();
    let format = if dates.len() > 1 {
        if years.len() > 1 {
            "%Y-%m-%d %H:%M"
        } else {
            "%m-%d %H:%M"
        }
    } else if times.len() > 1 {
        "%H:%M"
    } else {
        ""
    };
    let generated = regex::Regex::new(r"^(?:Pane #[0-9]+|(?:terminal|plugin)_[0-9]+)$")?;
    let mut input = String::new();
    for row in &rows {
        let time = stamp(row.time_ms, format);
        let prefix = if time.is_empty() {
            String::new()
        } else {
            format!("{time}  ")
        };
        let (glyph, color) = row.level.glyph();
        let message = if matches!(
            (row.level, row.message.as_str()),
            (Level::Success, "done") | (Level::Warn, "has a question")
        ) {
            ""
        } else {
            &row.message
        };
        let title = if generated.is_match(&row.title) {
            ""
        } else {
            &row.title
        };
        let summary = if title.is_empty() {
            message.to_owned()
        } else if message.is_empty() {
            title.to_owned()
        } else {
            format!("{title} — {message}")
        };
        input += &format!(
            "{}\t{prefix}\x1b[38;2;{color}m{glyph}\x1b[0m{}\n",
            row.id,
            if summary.is_empty() {
                String::new()
            } else {
                format!("  {summary}")
            }
        );
    }
    let mut args = vec![
        "--height=100%".into(),
        "--layout=reverse".into(),
        "--delimiter=\t".into(),
        "--with-nth=2..".into(),
        "--no-sort".into(),
        "--ansi".into(),
        "--prompt=› ".into(),
        "--bind=ctrl-/:toggle-preview".into(),
        "--preview".into(),
        format!("{} show {{1}}", helper_command("notify")?),
        format!(
            "--preview-window={}",
            if rows.is_empty() {
                "hidden"
            } else {
                "right:60%:border-left:wrap:<50(down:60%:border-top:wrap)"
            }
        ),
    ];
    if rows.is_empty() {
        args.push("--header=No notifications".into());
    }
    if let Some(id) = fzf(&args, input)? {
        if let Some(row) = rows.iter().find(|r| r.id == id) {
            jump(row)?;
        }
    }
    Ok(())
}
pub fn main(args: &[String]) -> Result<()> {
    match args {
        [cmd,payload] if cmd=="record"=>record(payload),
        [cmd,id] if cmd=="show"=>show(id),
        [cmd] if cmd=="list"=>{println!("{}",serde_json::to_string(&read_history()?)?);Ok(())},
        [cmd] if cmd=="history"=>history(),
        [cmd,rest @ ..] if cmd=="send"=>{
            let session=session()?;if env::var("ZELLIJ").is_err(){bail!("Run zellij-notify send inside Zellij");}
            let mut title="Notification".to_owned();let mut level="info".to_owned();let mut message=None;let mut i=0;
            while i<rest.len(){match rest[i].as_str(){
                "--title"|"--level"=>{let value=rest.get(i+1).context("Missing option value")?.clone();if rest[i]=="--title"{title=value;}else{level=value;}i+=2;},
                "--"=>{if rest.len()!=i+2||message.is_some(){bail!("Expected one message");}message=Some(rest[i+1].clone());break;},
                option if option.starts_with("--title=")=>{title=option[8..].to_owned();i+=1;},
                option if option.starts_with("--level=")=>{level=option[8..].to_owned();i+=1;},
                value=>{if value.starts_with('-')||message.is_some(){bail!("Expected one message");}message=Some(value.to_owned());i+=1;},
            }}
            let level:Level=serde_json::from_value(json!(level))?;
            let pane=env::var("ZELLIJ_PANE_ID").unwrap_or_default();let pane=if pane.parse::<u64>().is_ok(){format!("terminal_{pane}")}else{pane};
            let id=nonce()?;
            status_pipe(&session,"lane-notification",&json!({"id":id,"time_ms":now_ms(),"session":session,"pane_id":pane,"level":level,"title":title,"message":message.context("Expected a message")?}))?;Ok(())
        },
        _=>bail!("Usage: zellij-notify send [--level LEVEL] [--title TITLE] MESSAGE | history | list | record JSON | show ID"),
    }
}
