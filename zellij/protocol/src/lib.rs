//! Host/plugin contracts. Keep this crate free of native I/O so the same
//! validation and wire types compile for the native CLI and WASI plugins.
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::BTreeMap;

pub const RELOAD: &str = "lane-attention-reload";
pub const READINESS: &str = "lane-attention-ready";
pub const MAX_CONFIG_BYTES: usize = 16 * 1024;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct AttentionConfig {
    pub priority: Vec<Vec<String>>,
}

impl Default for AttentionConfig {
    fn default() -> Self {
        Self {
            priority: vec![
                vec!["marked".into(), "needs_you".into(), "failed".into()],
                vec!["working".into(), "new_output".into(), "bell".into()],
            ],
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Policy(BTreeMap<String, usize>);

impl Default for Policy {
    fn default() -> Self {
        AttentionConfig::default().policy().unwrap()
    }
}

impl AttentionConfig {
    pub fn policy(&self) -> Result<Policy, String> {
        if self.priority.is_empty() {
            return Err("attention.priority must be a nonempty list of groups".into());
        }
        let mut ranks = BTreeMap::new();
        for (rank, group) in self.priority.iter().enumerate() {
            if group.is_empty() {
                return Err("attention.priority groups must be nonempty lists".into());
            }
            for name in group {
                if !matches!(
                    name.as_str(),
                    "marked"
                        | "needs_you"
                        | "failed"
                        | "working"
                        | "new_output"
                        | "bell"
                        | "done"
                        | "quiet"
                ) {
                    return Err(format!("Unknown attention class: {name}"));
                }
                if ranks.insert(name.clone(), rank).is_some() {
                    return Err(format!("Duplicate attention class: {name}"));
                }
            }
        }
        Ok(Policy(ranks))
    }
}

impl Policy {
    pub fn parse(priority: &Value) -> Result<Self, String> {
        let priority = serde_json::from_value(priority.clone()).map_err(|e| e.to_string())?;
        AttentionConfig { priority }.policy()
    }

    pub fn rank(&self, class: &str) -> Option<usize> {
        self.0.get(class).copied()
    }

    pub fn tab_rank(&self, attention: Option<usize>, marked: bool, bell: bool) -> Option<usize> {
        [
            attention,
            marked.then(|| self.rank("marked")).flatten(),
            bell.then(|| self.rank("bell")).flatten(),
        ]
        .into_iter()
        .flatten()
        .min()
    }
}

/// The established JSON protocol is intentionally unversioned. Adding required
/// fields would break already-running plugin clones during an incremental update.
#[derive(Debug, Serialize, Deserialize)]
pub struct ReloadRequest {
    pub request: String,
    pub plugin_id: u32,
    pub priority: Value,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ReloadAck {
    pub request: String,
    pub plugin_id: u32,
    pub client_id: u32,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub ok: Option<bool>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub error: Option<String>,
}

/// Read-only probe for a particular persistent receiver. It does not load or
/// replace policy, and replies independently for each attached client clone.
#[derive(Debug, Serialize, Deserialize)]
pub struct ReadinessRequest {
    pub request: String,
    pub plugin_id: u32,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ReadinessReply {
    pub request: String,
    pub plugin_id: u32,
    pub client_id: u32,
    pub config_ready: bool,
    pub attention_ready: bool,
    pub bindings_installed: bool,
}

#[derive(Debug, Default, Serialize, Deserialize)]
pub struct StatusView {
    pub session: Option<String>,
    pub auto_titles: BTreeMap<String, String>,
    pub host: String,
    pub clock: String,
    pub battery: String,
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn attention_config_preserves_order_and_omitted_classes() {
        let policy =
            Policy::parse(&json!([["working"], ["done", "needs_you"], ["marked"]])).unwrap();
        assert_eq!(policy.rank("working"), Some(0));
        assert_eq!(policy.rank("done"), Some(1));
        assert_eq!(policy.rank("needs_you"), Some(1));
        assert_eq!(policy.rank("failed"), None);
        assert_eq!(policy.tab_rank(Some(0), true, true), Some(0));
        assert_eq!(policy.tab_rank(None, false, true), None);
    }

    #[test]
    fn attention_config_rejects_invalid_priority() {
        for priority in [
            json!([]),
            json!([[]]),
            json!([["done"], ["done"]]),
            json!([["unknown"]]),
            json!([[4]]),
            json!("done"),
        ] {
            assert!(Policy::parse(&priority).is_err(), "{priority}");
        }
    }

    #[test]
    fn existing_plugin_wire_messages_round_trip_without_new_fields() {
        let config = json!({"priority": [["marked", "needs_you", "failed"], ["working", "new_output", "bell"]]});
        assert_eq!(
            serde_json::to_value(AttentionConfig::default()).unwrap(),
            config
        );
        let request = json!({"request":"nonce", "plugin_id":7, "priority":[["done"]]});
        assert_eq!(
            serde_json::to_value(serde_json::from_value::<ReloadRequest>(request.clone()).unwrap())
                .unwrap(),
            request
        );
        let ack = json!({"request":"nonce", "plugin_id":7, "client_id":1, "ok":true});
        assert_eq!(
            serde_json::to_value(serde_json::from_value::<ReloadAck>(ack.clone()).unwrap())
                .unwrap(),
            ack
        );
    }
}
