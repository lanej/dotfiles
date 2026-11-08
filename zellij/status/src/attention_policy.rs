use serde_json::{json, Value};
use std::collections::BTreeMap;
use std::time::{SystemTime, UNIX_EPOCH};
use zellij_tile::prelude::*;

pub const LOAD: &str = "attention-config-load";
pub const RELOAD: &str = "lane-attention-reload";

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Policy(BTreeMap<String, usize>);

impl Default for Policy {
    fn default() -> Self {
        Self::parse(&json!([["marked", "needs_you", "failed"],
                           ["working", "new_output", "bell"]])).unwrap()
    }
}

impl Policy {
    pub fn parse(value: &Value) -> Result<Self, String> {
        let groups = value.as_array().filter(|groups| !groups.is_empty())
            .ok_or("attention.priority must be a nonempty list of groups")?;
        let mut ranks = BTreeMap::new();
        for (rank, group) in groups.iter().enumerate() {
            let classes = group.as_array().filter(|classes| !classes.is_empty())
                .ok_or("attention.priority groups must be nonempty lists")?;
            for class in classes {
                let name = class.as_str().ok_or("attention.priority classes must be strings")?;
                if !matches!(name, "marked" | "needs_you" | "failed" | "working"
                    | "new_output" | "bell" | "done" | "quiet") {
                    return Err(format!("Unknown attention class: {name}"));
                }
                if ranks.insert(name.to_owned(), rank).is_some() {
                    return Err(format!("Duplicate attention class: {name}"));
                }
            }
        }
        Ok(Self(ranks))
    }

    pub fn rank(&self, class: &str) -> Option<usize> { self.0.get(class).copied() }

    pub fn attention_rank(&self, attention: &PaneAttention) -> Option<usize> {
        let class = match attention.effective_status() {
            AttentionStatus::NeedsYou if attention.source.map(|source| source.as_str()) == Some("bell") => "bell",
            AttentionStatus::NeedsYou => "needs_you",
            AttentionStatus::Failed => "failed",
            AttentionStatus::Working => "working",
            AttentionStatus::NewOutput => "new_output",
            AttentionStatus::Done => "done",
            AttentionStatus::Quiet => "quiet",
            _ => return None,
        };
        self.rank(class)
    }

    pub fn tab_rank(&self, attention: Option<usize>, marked: bool, bell: bool) -> Option<usize> {
        [attention, marked.then(|| self.rank("marked")).flatten(),
         bell.then(|| self.rank("bell")).flatten()].into_iter().flatten().min()
    }
}

#[derive(Default)]
pub struct Config {
    pub policy: Policy,
    pub ready: bool,
    pending: Option<String>,
}

impl Config {
    pub fn load(&mut self) {
        let ids = get_plugin_ids();
        // Cached command results can be replayed to new plugin instances.
        // Bind this one read to the attachment, plugin, and load invocation.
        let stamp = SystemTime::now().duration_since(UNIX_EPOCH)
            .map(|time| time.as_nanos()).unwrap_or_default();
        let request = format!("{}:{}:{stamp}", ids.plugin_id, ids.client_id);
        self.pending = Some(request.clone());
        run_command(&["zellij-status", "config"], BTreeMap::from([
            ("action".into(), LOAD.into()), ("request".into(), request),
        ]));
    }

    pub fn apply(&mut self, priority: &Value) -> Result<(), String> {
        let policy = Policy::parse(priority)?;
        self.policy = policy;
        self.ready = true;
        // A completed reload supersedes an outstanding startup read.
        self.pending = None;
        Ok(())
    }

    pub fn finish(&mut self, code: Option<i32>, out: &[u8], error: &[u8],
                  context: &BTreeMap<String, String>) -> Option<String> {
        if self.pending.is_none() || context.get("request") != self.pending.as_ref() { return None; }
        self.pending = None;
        self.ready = true;
        let result = if code == Some(0) {
            serde_json::from_slice::<Value>(out).map_err(|error| error.to_string())
                .and_then(|value| self.apply(&value["priority"]))
        } else {
            let error = String::from_utf8_lossy(error);
            Err(if error.trim().is_empty() { "Could not load attention configuration".into() }
                else { error.trim().to_owned() })
        };
        // On first-load failure the documented defaults remain usable. Reload
        // validation is atomic and retains the last valid in-memory policy.
        result.err()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn defaults_preserve_bell_distinction_and_skip_quiet_completion() {
        let policy = Policy::default();
        let mut attention = PaneAttention { status: AttentionStatus::NeedsYou,
            source: serde_json::from_value(json!("ProgramStatus")).unwrap(), ..Default::default() };
        assert_eq!(policy.attention_rank(&attention), Some(0));
        attention.source = serde_json::from_value(json!("Bell")).unwrap();
        assert_eq!(policy.attention_rank(&attention), Some(1));
        attention.status = AttentionStatus::Done;
        assert_eq!(policy.attention_rank(&attention), None);
        attention.status = AttentionStatus::Quiet;
        assert_eq!(policy.attention_rank(&attention), None);
        attention.status = AttentionStatus::Failed;
        attention.muted = Some(MuteScope::Pane);
        assert_eq!(policy.attention_rank(&attention), None);
        assert_eq!(policy.tab_rank(Some(1), true, false), Some(0));
    }

    #[test]
    fn ordered_groups_control_eligibility_and_best_signal_wins() {
        let policy = Policy::parse(&json!([["working"], ["done", "needs_you"], ["marked"]])).unwrap();
        assert_eq!(policy.rank("working"), Some(0));
        assert_eq!(policy.rank("done"), Some(1));
        assert_eq!(policy.rank("needs_you"), Some(1));
        assert_eq!(policy.rank("failed"), None);
        assert_eq!(policy.tab_rank(Some(0), true, true), Some(0));
        assert_eq!(policy.tab_rank(None, false, true), None);
    }

    #[test]
    fn invalid_or_late_load_cannot_replace_a_valid_reload() {
        let mut config = Config::default();
        config.pending = Some("startup".into());
        config.apply(&json!([["done"]])).unwrap();
        for invalid in [json!([]), json!([[]]), json!([["done"], ["done"]]),
                        json!([["unknown"]]), json!([[4]]), json!("done")] {
            assert!(config.apply(&invalid).is_err());
            assert_eq!(config.policy.rank("done"), Some(0));
        }
        let context = BTreeMap::from([("request".into(), "startup".into())]);
        assert!(config.finish(Some(0), br#"{"priority":[["failed"]]}"#, b"", &context).is_none());
        assert_eq!(config.policy.rank("done"), Some(0));
        assert_eq!(config.policy.rank("failed"), None);
    }

    #[test]
    fn failed_startup_uses_defaults_and_ignores_another_clients_result() {
        let mut config = Config::default();
        config.pending = Some("this-client".into());
        let stale = BTreeMap::from([("request".into(), "other-client".into())]);
        assert!(config.finish(Some(0), br#"{"priority":[["done"]]}"#, b"", &stale).is_none());
        assert!(!config.ready);
        let current = BTreeMap::from([("request".into(), "this-client".into())]);
        assert_eq!(config.finish(Some(1), b"", b"invalid TOML", &current), Some("invalid TOML".into()));
        assert!(config.ready);
        assert_eq!(config.policy, Policy::default());
    }
}
