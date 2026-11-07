//! Route native attention into quiet notices and a bounded, searchable journal.
//! Native Zellij remains the owner of unresolved attention and its inbox.
use serde_json::{json, Value};
use std::collections::{BTreeMap, VecDeque};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};
use zellij_tile::prelude::*;

pub const RECORD: &str = "lane-notification-record";
pub const SEND: &str = "lane-notification";
pub const VALIDATE: &str = "lane-notification-validate";
pub const ERROR: &str = "lane-notification-history-error";

fn clean(text: &str, limit: usize) -> String {
    text.chars()
        .filter(|c| !c.is_control())
        .take(limit)
        .collect()
}

fn level(status: AttentionStatus) -> Option<(&'static str, &'static str)> {
    match status {
        AttentionStatus::NeedsYou => Some(("warn", "!")),
        AttentionStatus::Failed => Some(("error", "×")),
        AttentionStatus::Done => Some(("success", "✓")),
        _ => None,
    }
}

pub struct Notifications {
    started_ms: u64,
    previous: BTreeMap<(String, PaneId), (AttentionStatus, String)>,
    queue: VecDeque<Value>,
    pending: bool,
    notice: Option<(String, String, Instant)>,
}

impl Default for Notifications {
    fn default() -> Self {
        Self {
            started_ms: SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .map(|time| time.as_millis() as u64)
                .unwrap_or(u64::MAX),
            previous: BTreeMap::new(),
            queue: VecDeque::new(),
            pending: false,
            notice: None,
        }
    }
}

impl Notifications {
    // Observe all statuses, including idle/working: returning to working makes
    // the next failure/completion a new event. Progress alone is not a notice.
    pub fn observe(
        &mut self,
        attention: &GlobalAttention,
        server: u32,
        focused: Option<PaneId>,
        visible: bool,
        recorder: bool,
    ) {
        let mut next = BTreeMap::new();
        for item in &attention.items {
            let state = &item.item.attention;
            let status = state.effective_status();
            let key = (item.session.clone(), item.item.pane_id);
            let title = clean(
                state
                    .detail
                    .title
                    .as_deref()
                    .unwrap_or(&item.item.pane_title),
                120,
            );
            let body = clean(state.detail.body.as_deref().unwrap_or(&state.text), 512);
            // OSC 7501 refreshes updated_ms even when the report is identical.
            // A timestamp change or progress update is not a new notification.
            let version = (
                status,
                format!("{:?}", (state.source, state.detail.kind, &title, &body)),
            );
            next.insert(key.clone(), version.clone());
            if self.previous.get(&key) == Some(&version) {
                continue;
            }
            let Some((severity, glyph)) = level(status) else {
                continue;
            };
            // Cached snapshots can arrive before permissions are ready. A
            // first observed snapshot may still contain a genuinely new
            // event; its timestamp, not arrival order, decides freshness.
            if state.since_ms >= self.started_ms
                && visible
                && !state.seen
                && !(item.is_current && focused == Some(item.item.pane_id))
            {
                self.show(
                    severity,
                    &format!("{glyph} {} · {}: {}", item.session, title, body),
                );
            }
            if recorder && item.is_current {
                self.queue.push_back(json!({
                    "id": format!("{server}:{}:{}:{}:{}", item.session,
                        item.item.pane_id, status.as_str(), state.since_ms),
                    "time_ms": state.since_ms, "level": severity,
                    "session": clean(&item.session, 256),
                    "pane_id": item.item.pane_id.to_string(),
                    "server_pid": server, "pane_pid": get_pane_pid(item.item.pane_id).ok(),
                    "title": title, "message": body,
                }));
            }
        }
        self.previous = next;
        self.queue.truncate(64);
        self.flush();
    }

    fn show(&mut self, severity: &str, message: &str) {
        // Keep a failure or question visible when several successes arrive in
        // the same burst. Subsequent notices replace, rather than stack.
        let priority = |level: &str| match level {
            "error" => 3,
            "warn" => 2,
            _ => 1,
        };
        if let Some((old, _, until)) = &self.notice {
            if *until > Instant::now() && priority(old) > priority(severity) {
                return;
            }
        }
        let seconds = if matches!(severity, "warn" | "error") {
            8
        } else {
            4
        };
        self.notice = Some((
            severity.to_owned(),
            clean(message, 240),
            Instant::now() + Duration::from_secs(seconds),
        ));
    }

    fn flush(&mut self) {
        if self.pending || self.queue.is_empty() {
            return;
        }
        let batch: Vec<_> = self.queue.drain(..16.min(self.queue.len())).collect();
        run_command(
            &["zellij-notify", "record", &json!(batch).to_string()],
            BTreeMap::from([
                ("action".into(), RECORD.into()),
                ("client".into(), get_plugin_ids().client_id.to_string()),
            ]),
        );
        self.pending = true;
    }

    pub fn finish(&mut self, code: Option<i32>, error: &[u8], context: &BTreeMap<String, String>) {
        if context.get("client") != Some(&get_plugin_ids().client_id.to_string()) {
            return;
        }
        self.pending = false;
        if code != Some(0) {
            eprintln!("notification history: {}", String::from_utf8_lossy(error));
            self.show("error", "× Notification history could not be saved");
            // The elected recorder may be on an inactive tab. Tell this
            // client's visible bars too, without recording the error again.
            pipe_message_to_plugin(
                MessageToPlugin::new(ERROR).with_payload(get_plugin_ids().client_id.to_string()),
            );
        }
        self.flush();
    }

    pub fn pipe(&mut self, message: &PipeMessage, session: Option<&str>, recorder: bool) -> bool {
        let PipeSource::Cli(pipe) = &message.source else {
            return false;
        };
        if message
            .payload
            .as_ref()
            .is_some_and(|text| text.len() > 8192)
        {
            return false;
        }
        let payload: Value =
            serde_json::from_str(message.payload.as_deref().unwrap_or("")).unwrap_or_default();
        if message.name == VALIDATE {
            // A retained history row must not navigate into a new session or
            // reused pane with the same display name/number.
            let pane = payload["pane_id"]
                .as_str()
                .and_then(|p| p.strip_prefix("terminal_").and_then(|p| p.parse().ok()))
                .map(PaneId::Terminal);
            let valid = payload["server_pid"].as_u64() == Some(get_plugin_ids().zellij_pid as u64)
                && payload["session"].as_str() == session
                && pane.and_then(|p| get_pane_pid(p).ok()).map(i64::from)
                    == payload["pane_pid"].as_i64()
                && payload["pane_pid"].is_i64();
            cli_pipe_output(pipe, if valid { "valid\n" } else { "stale\n" });
            return false;
        }
        if message.name != SEND || payload["session"].as_str() != session {
            return false;
        }
        let severity = payload["level"].as_str().unwrap_or("info");
        if !matches!(severity, "info" | "success" | "warn" | "error") {
            return false;
        }
        let title = clean(payload["title"].as_str().unwrap_or("Notification"), 120);
        let body = clean(payload["message"].as_str().unwrap_or(""), 512);
        self.show(severity, &format!("{title}: {body}"));
        if recorder && payload["id"].as_str().is_some_and(|id| id.len() <= 128) {
            let mut record = payload;
            record["server_pid"] = json!(get_plugin_ids().zellij_pid);
            record["title"] = json!(title);
            record["message"] = json!(body);
            let pane = record["pane_id"]
                .as_str()
                .and_then(|p| p.strip_prefix("terminal_").and_then(|p| p.parse().ok()))
                .map(PaneId::Terminal);
            record["pane_pid"] = json!(pane.and_then(|p| get_pane_pid(p).ok()));
            self.queue.push_back(record);
            self.queue.truncate(64);
            self.flush();
        }
        true
    }

    pub fn notice(&self) -> Option<(&str, &str)> {
        self.notice
            .as_ref()
            .filter(|(_, _, until)| *until > Instant::now())
            .map(|(level, message, _)| (level.as_str(), message.as_str()))
    }

    pub fn receive_error(&mut self, message: &PipeMessage) -> bool {
        if message.payload.as_deref() != Some(get_plugin_ids().client_id.to_string().as_str()) {
            return false;
        }
        self.show("error", "× Notification history could not be saved");
        true
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn late_initial_snapshots_do_not_replay_old_attention() {
        let mut notices = Notifications::default();
        let mut global = GlobalAttention {
            items: vec![GlobalAttentionItem {
                session: "main".into(),
                is_current: true,
                item: AttentionItem {
                    pane_id: PaneId::Terminal(1),
                    tab_id: 0,
                    tab_name: "work".into(),
                    pane_title: "Tests".into(),
                    attention: PaneAttention {
                        status: AttentionStatus::NeedsYou,
                        since_ms: notices.started_ms.saturating_sub(1),
                        text: "Question".into(),
                        ..Default::default()
                    },
                },
            }],
            ..Default::default()
        };
        notices.observe(&global, 1, None, true, false);
        assert!(notices.notice().is_none());
        global.items[0].item.attention.since_ms = notices.started_ms + 1;
        notices.observe(&global, 1, None, true, false);
        assert!(notices.notice().is_none());
        let mut first_snapshot = Notifications {
            started_ms: notices.started_ms,
            ..Default::default()
        };
        first_snapshot.observe(&global, 1, None, true, false);
        assert!(first_snapshot.notice().is_some());
        global.items[0].item.attention.status = AttentionStatus::Working;
        notices.observe(&global, 1, None, true, false);
        global.items[0].item.attention.status = AttentionStatus::NeedsYou;
        notices.observe(&global, 1, None, true, false);
        assert!(notices.notice().is_some());
        let deadline = notices.notice.as_ref().unwrap().2;
        global.items[0].item.attention.detail.progress = Some(80);
        global.items[0].item.attention.since_ms += 100;
        notices.observe(&global, 1, None, true, false);
        assert_eq!(notices.notice.as_ref().unwrap().2, deadline);
    }

    #[test]
    fn progress_is_quiet_and_failures_survive_success_bursts() {
        assert!(level(AttentionStatus::Working).is_none());
        assert!(level(AttentionStatus::NewOutput).is_none());
        let mut notices = Notifications::default();
        notices.show("error", "Tests failed");
        notices.show("success", "Build passed");
        assert_eq!(notices.notice(), Some(("error", "Tests failed")));
        notices.notice.as_mut().unwrap().2 = Instant::now() - Duration::from_secs(1);
        assert!(notices.notice().is_none());
        notices.show("success", "Build passed");
        assert_eq!(notices.notice(), Some(("success", "Build passed")));
    }
}
