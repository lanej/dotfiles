use std::collections::BTreeMap;
use zellij_tile::prelude::*;

pub const MESSAGE: &str = "clipboard-paste";
pub const PREPARE: &str = "clipboard-prepare";
pub const NOTICE: &str = "clipboard-notice";
pub const ROLE: &str = "clipboard-receiver";

pub fn prepare_receiver(panes: &PaneManifest) -> bool {
    // The configured background receiver is allocated before any visible
    // status bar. Address its known suppressed pane ID: native delivery can
    // cache this message while that plugin or a client instance is loading.
    let receiver = panes.panes.values().flatten()
        .filter(|pane| pane.is_plugin && pane.is_suppressed && !pane.exited
            && pane.plugin_url.as_deref().map(|url| url.ends_with("/lane-status.wasm")).unwrap_or(false))
        .map(|pane| pane.id).min();
    let Some(receiver) = receiver else { return false };
    let client = get_plugin_ids().client_id.to_string();
    // URL-directed plugin messages add caller_cwd to their configuration and
    // could launch a second receiver instead of matching the configured one.
    pipe_message_to_plugin(MessageToPlugin::new(PREPARE)
        .with_destination_plugin_id(receiver)
        .with_payload(client));
    true
}

pub fn is_own_client(message: &PipeMessage) -> bool {
    message.payload.as_deref() == Some(get_plugin_ids().client_id.to_string().as_str())
}

#[derive(Default)]
pub struct Clipboard {
    pending: Option<(PaneId, i32)>,
    notice: Option<(String, u8)>,
    binding_installed: bool,
}

impl Clipboard {
    pub fn route_binding(&mut self, bindings_changed: bool) {
        let ids = get_plugin_ids();
        if !bindings_changed && self.binding_installed { return; }
        // Native MessagePluginId routes to the actual invoking client. The
        // 0.45.1 typed Action API drops KeybindPipe metadata, so use its KDL
        // reconfiguration API. This changes only this client's runtime key.
        // This receiver is suppressed and survives tab closure, so its ID
        // never needs an asynchronous handoff between visible status bars.
        let config = format!(r#"keybinds {{
            tmux {{
                bind "p" {{
                    MessagePluginId {} {{ name "{MESSAGE}"; payload "{}"; }}
                    SwitchToMode "Locked"
                }}
            }}
        }}"#, ids.plugin_id, ids.client_id);
        reconfigure(config, false);
        self.binding_installed = true;
        // InitialKeybinds reaches inactive tabs after live config reload.
        // Reapply there; Zellij compares the native config and emits no update
        // when it is unchanged, so acknowledgements cannot create a loop.
    }

    pub fn receive_notice(&mut self, message: &PipeMessage) -> bool {
        let client = get_plugin_ids().client_id.to_string();
        if message.args.get("client") != Some(&client) { return false; }
        self.notice = message.payload.as_ref().filter(|text| !text.is_empty())
            .map(|text| (text.clone(), 8));
        true
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
                let context = BTreeMap::from([
                    ("action".into(), MESSAGE.into()),
                    ("client".into(), client),
                ]);
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
        self.publish_notice("");
    }

    fn report(&mut self, message: &str) {
        eprintln!("lane-status paste: {message}");
        let text = format!("paste: {message}");
        self.notice = Some((text.clone(), 8));
        self.publish_notice(&text);
    }

    fn publish_notice(&self, text: &str) {
        // The receiver has no visible pane. Existing ordinary bars select
        // their own client's notice; no URL lookup can launch an extra pane.
        pipe_message_to_plugin(MessageToPlugin::new(NOTICE)
            .with_args(BTreeMap::from([("client".into(), get_plugin_ids().client_id.to_string())]))
            .with_payload(text));
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
