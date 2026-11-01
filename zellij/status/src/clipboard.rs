use std::collections::BTreeMap;
use zellij_tile::prelude::*;

pub const MESSAGE: &str = "clipboard-paste";

#[derive(Default)]
pub struct Clipboard {
    pending: Option<(PaneId, i32)>,
    notice: Option<(String, u8)>,
    receiver: Option<u32>,
}

impl Clipboard {
    pub fn route_binding(&mut self, panes: &PaneManifest, bindings_changed: bool) {
        let ids = get_plugin_ids();
        let leader = panes.panes.values().flatten()
            .filter(|p| p.is_plugin && !p.exited
                && p.plugin_url.as_deref().map(|url| url.ends_with("/lane-status.wasm")).unwrap_or(false))
            .map(|p| p.id).min().unwrap_or(ids.plugin_id);
        if ids.plugin_id != leader {
            self.receiver = None;
            return;
        }
        if !bindings_changed && self.receiver == Some(leader) { return; }
        // Native MessagePluginId routes to the actual invoking client. The
        // 0.45.1 typed Action API drops KeybindPipe metadata, so use its KDL
        // reconfiguration API. This changes only this client's runtime key.
        let config = format!(r#"keybinds {{
            tmux {{
                bind "p" {{
                    MessagePluginId {leader} {{ name "{MESSAGE}"; payload "{}"; }}
                    SwitchToMode "Locked"
                }}
            }}
        }}"#, ids.client_id);
        reconfigure(config, false);
        self.receiver = Some(leader);
        // InitialKeybinds reaches inactive tabs after live config reload.
        // Reapply there; Zellij compares the native config and emits no update
        // when it is unchanged, so acknowledgements cannot create a loop.
    }

    pub fn begin(&mut self, session: &str, message: &PipeMessage) -> bool {
        let client = get_plugin_ids().client_id.to_string();
        // Old URL bindings and broadcasts carry no client marker. Refuse
        // them rather than allowing each attached client to paste its focus.
        if !message.is_private || message.payload.as_deref() != Some(client.as_str()) {
            return false;
        }
        let Ok((_, pane @ PaneId::Terminal(_))) = get_focused_pane_info() else { return false };
        if self.pending.is_some() {
            self.report("A paste is already pending");
            return true;
        }
        match get_pane_pid(pane) {
            Ok(pid) => {
                self.pending = Some((pane, pid));
                let context = BTreeMap::from([("action".into(), MESSAGE.into())]);
                run_command(&["zellij-clipboard", "read", "--session", session], context);
            }
            Err(_) => self.report("The destination pane is no longer available"),
        }
        true
    }

    pub fn finish(&mut self, code: Option<i32>, bytes: Vec<u8>, error: Vec<u8>) {
        let Some((pane, pid)) = self.pending.take() else { return };
        if code != Some(0) {
            let error = String::from_utf8_lossy(&error);
            self.report(if error.trim().is_empty() { "Could not read the session buffer" } else { error.trim() });
            return;
        }
        if get_pane_pid(pane) != Ok(pid) {
            self.report("The destination pane changed; paste was cancelled");
            return;
        }
        // Match Zellij 0.45.1's native Paste action: separate framing writes
        // let the terminal layer honor the target application's paste mode.
        // The captured pane ID stays authoritative even if focus has moved.
        write_to_pane_id(b"\x1b[200~".to_vec(), pane);
        write_to_pane_id(bytes, pane);
        write_to_pane_id(b"\x1b[201~".to_vec(), pane);
        self.notice = None;
    }

    fn report(&mut self, message: &str) {
        eprintln!("lane-status paste: {message}");
        self.notice = Some((format!("paste: {message}"), 8));
    }

    pub fn tick(&mut self) {
        if let Some((_, seconds)) = self.notice.as_mut() {
            *seconds = seconds.saturating_sub(1);
            if *seconds == 0 { self.notice = None; }
        }
    }

    pub fn notice(&self) -> Option<&str> {
        self.notice.as_ref().map(|(message, _)| message.as_str())
    }
}
