use crate::{command, config};
use lane_zellij_protocol::{AttentionConfig, ReloadAck, ReloadRequest, RELOAD};
use serde::Deserialize;
use std::collections::BTreeSet;
use std::io::Read;
use std::time::{Duration, Instant};

#[derive(Deserialize)]
struct Pane {
    id: u32,
    #[serde(default)]
    is_plugin: bool,
    #[serde(default)]
    is_suppressed: bool,
    plugin_url: Option<String>,
}

#[derive(Deserialize)]
struct Tab {
    other_focused_clients: Vec<u32>,
}

struct Session<'a> {
    name: &'a str,
    deadline: Instant,
}

impl Session<'_> {
    fn cli(&self, args: &[&str]) -> Result<String, String> {
        let session = format!("--session={}", self.name);
        let args: Vec<&str> = std::iter::once(session.as_str())
            .chain(args.iter().copied())
            .collect();
        command::output("zellij", &args, self.deadline)
    }

    fn clients(&self) -> Result<BTreeSet<u32>, String> {
        let tabs: Vec<Tab> = serde_json::from_str(&self.cli(&["action", "list-tabs", "--json"])?)
            .map_err(|e| e.to_string())?;
        Ok(tabs
            .into_iter()
            .flat_map(|tab| tab.other_focused_clients)
            .collect())
    }
}

pub fn reload(name: Option<&str>, config: AttentionConfig) -> Result<String, String> {
    let name = name
        .filter(|name| !name.is_empty())
        .ok_or("Run inside Zellij or specify --session")?;
    let session = Session {
        name,
        deadline: Instant::now() + Duration::from_secs(5),
    };
    // Query only: never attach/start a session, or URL-pipe a replacement plugin.
    let panes: Vec<Pane> =
        serde_json::from_str(&session.cli(&["action", "list-panes", "--all", "--json"])?)
            .map_err(|e| e.to_string())?;
    let url = format!(
        "file:{}",
        config::home()?
            .join(".config/zellij/plugins/lane-status.wasm")
            .display()
    );
    let receivers: Vec<_> = panes
        .iter()
        .filter(|pane| {
            pane.is_plugin && pane.is_suppressed && pane.plugin_url.as_deref() == Some(url.as_str())
        })
        .collect();
    if receivers.len() != 1 {
        return Err("Expected one existing suppressed lane-status receiver; no reload sent".into());
    }
    let plugin_id = receivers[0].id;
    let before = session.clients()?;
    if before.is_empty() {
        return Err("No attached clients; no reload sent".into());
    }
    let mut nonce = [0u8; 16];
    std::fs::File::open("/dev/urandom")
        .and_then(|mut file| file.read_exact(&mut nonce))
        .map_err(|e| e.to_string())?;
    let request = ReloadRequest {
        request: nonce.iter().map(|byte| format!("{byte:02x}")).collect(),
        plugin_id,
        priority: serde_json::to_value(config.priority).map_err(|e| e.to_string())?,
    };
    let payload = serde_json::to_string(&request).map_err(|e| e.to_string())?;
    let send = || -> Result<usize, String> {
        let output = session.cli(&["pipe", "--name", RELOAD, "--", &payload])?;
        let mut confirmed = BTreeSet::new();
        for line in output.lines().filter(|line| !line.trim().is_empty()) {
            let ack: ReloadAck = serde_json::from_str(line)
                .map_err(|e| format!("Invalid reload acknowledgement: {e}"))?;
            if ack.request != request.request || ack.plugin_id != plugin_id {
                return Err("Unexpected reload acknowledgement identity".into());
            }
            if let Some(error) = ack.error.filter(|error| !error.is_empty()) {
                return Err(error);
            }
            if ack.ok != Some(true) {
                return Err("Invalid reload acknowledgement".into());
            }
            confirmed.insert(ack.client_id);
        }
        let expected: BTreeSet<_> = before.union(&session.clients()?).copied().collect();
        if confirmed.is_empty() || !expected.is_subset(&confirmed) {
            let missing: Vec<_> = expected
                .difference(&confirmed)
                .map(u32::to_string)
                .collect();
            return Err(format!(
                "Missing reload acknowledgements for clients: {}",
                missing.join(", ")
            ));
        }
        Ok(expected.len())
    };
    let count = send().map_err(|error| format!("Reload outcome may be partial: {error}"))?;
    Ok(format!(
        "Reloaded attention priority for {count} attached client(s) in {name}"
    ))
}
