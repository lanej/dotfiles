use serde_json::{json, Value};
use std::time::{SystemTime, UNIX_EPOCH};
use zellij_tile::prelude::*;

pub const SNAPSHOT: &str = "lane-client-snapshot";
pub const DETACH: &str = "lane-client-detach";

#[derive(Default)]
pub struct Clients {
    nonce: String,
    epoch: u64,
    active: bool,
    session: String,
    pending: Option<(String, Value)>,
}

impl Clients {
    pub fn start(&mut self) {
        // A reload must invalidate old chooser entries too. A connection does
        // not imply a new plugin instance: 0.45.1 retains detached clones and
        // reuses their numeric client IDs when a new client attaches.
        self.nonce = SystemTime::now().duration_since(UNIX_EPOCH)
            .map(|time| time.as_nanos().to_string()).unwrap_or_default();
    }

    pub fn observe(&mut self, sessions: &[SessionInfo]) {
        let id = get_plugin_ids().client_id;
        let current = sessions.iter().find(|session| session.is_current_session);
        // SessionUpdate includes every active client in its tab snapshots,
        // including clients whose focused pane is a scrollback editor.
        let active = current.map(|session| session.tabs.iter()
            .any(|tab| tab.other_focused_clients.contains(&id))).unwrap_or(false);
        let session = current.map(|session| session.name.as_str()).unwrap_or("");
        if self.active != active || self.session != session {
            self.epoch += 1;
        }
        self.active = active;
        self.session = session.to_owned();
    }

    fn token(&self) -> Value {
        let ids = get_plugin_ids();
        json!({"client_id": ids.client_id, "plugin_id": ids.plugin_id,
            "server_pid": ids.zellij_pid, "session": self.session,
            "nonce": self.nonce, "epoch": self.epoch})
    }

    fn valid(&self, token: &Value) -> bool {
        self.active && !self.nonce.is_empty() && *token == self.token()
    }

    pub fn pipe(&mut self, message: &PipeMessage, panes: &PaneManifest) -> bool {
        let PipeSource::Cli(pipe) = &message.source else { return false };
        match message.name.as_str() {
            SNAPSHOT if self.active && get_plugin_ids().plugin_id == crate::leader(panes) => {
                let Ok((tab_id, pane_id)) = get_focused_pane_info() else { return false };
                let tab = get_tab_info(tab_id);
                let pane = get_pane_info(pane_id);
                let row = json!({"token": self.token(),
                    "tab": tab.map(|tab| format!("{}: {}", tab.position, tab.name)),
                    "pane": pane.map(|pane| pane.title)});
                cli_pipe_output(pipe, &(row.to_string() + "\n"));
            }
            DETACH => {
                let Ok(token) = serde_json::from_str::<Value>(message.payload.as_deref().unwrap_or("")) else {
                    return false;
                };
                let ids = get_plugin_ids();
                if token["plugin_id"].as_u64() != Some(ids.plugin_id as u64)
                    || token["client_id"].as_u64() != Some(ids.client_id as u64) {
                    return false;
                }
                if !self.valid(&token) {
                    cli_pipe_output(pipe, "The selected attachment changed; reopen the client chooser.\n");
                } else if self.pending.is_some() {
                    cli_pipe_output(pipe, "A detach request is already pending for this client.\n");
                } else {
                    // This async native query lets earlier lifecycle events
                    // reach this clone before the final check. Keep the CLI
                    // alive until its reply has been handled.
                    block_cli_pipe_input(pipe);
                    self.pending = Some((pipe.clone(), token));
                    list_clients();
                }
            }
            _ => return false,
        }
        false
    }

    pub fn finish(&mut self) {
        let Some((pipe, token)) = self.pending.take() else { return };
        // The focused-pane query reaches the screen directly and also covers
        // scrollback-editor clients omitted by native ListClients metadata.
        // Native detach still has a final client-ID check/action window; the
        // server does not accept an attachment-generation precondition.
        if self.valid(&token) && get_focused_pane_info().is_ok() {
            detach();
            cli_pipe_output(&pipe, "detached\n");
        } else {
            cli_pipe_output(&pipe, "The selected attachment changed; reopen the client chooser.\n");
        }
        unblock_cli_pipe_input(&pipe);
    }
}
