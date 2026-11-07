use serde_json::{json, Value};
use std::collections::{BTreeMap, BTreeSet};
use std::time::{SystemTime, UNIX_EPOCH};
use zellij_tile::prelude::*;

pub const SNAPSHOT: &str = "lane-client-snapshot";
pub const DETACH: &str = "lane-client-detach";
const SUPPORTED_RUNTIME: &str = "0.46.0";
const UNSUPPORTED_RUNTIME: &str = "The client chooser requires the pinned Zellij 0.46.0 server. Run make zellij-runtime and restart this session.";

// Routing is independent of plugin calls: an addressed read belongs to the
// captured receiver even when another bar is now the discovery leader.
fn snapshot_route(token: Option<&Value>, receiver: &Value, leader: u32,
                  supported_runtime: bool) -> Result<bool, &'static str> {
    let Some(token) = token else {
        return Ok(receiver["plugin_id"].as_u64() == Some(leader as u64));
    };
    if token["plugin_id"] != receiver["plugin_id"] || token["client_id"] != receiver["client_id"] {
        return Ok(false);
    }
    if !valid_identity(token, receiver, supported_runtime) {
        return Err("The captured attachment or status plugin changed");
    }
    Ok(true)
}

fn valid_identity(token: &Value, receiver: &Value, supported_runtime: bool) -> bool {
    supported_runtime && receiver["nonce"].as_str().map(|nonce| !nonce.is_empty()).unwrap_or(false)
        && token == receiver
}

#[derive(Default)]
pub struct Clients {
    nonce: String,
    supported_runtime: bool,
    pending: Option<(String, Value)>,
    completed_moves: BTreeMap<String, (u64, String)>,
}

impl Clients {
    pub fn start(&mut self) {
        // Query the server hosting this plugin, not a possibly newer binary
        // on PATH while the current session still runs an older server.
        self.supported_runtime = get_zellij_version() == SUPPORTED_RUNTIME;
        // The pinned runtime allocates a fresh native ID for every attachment
        // and removes detached plugin instances. A nonce also invalidates a
        // chooser entry if this still-connected client's plugin is reloaded.
        self.nonce = SystemTime::now().duration_since(UNIX_EPOCH)
            .map(|time| time.as_nanos().to_string()).unwrap_or_default();
    }

    fn token(&self) -> Value {
        let ids = get_plugin_ids();
        json!({"client_id": ids.client_id, "plugin_id": ids.plugin_id,
            "server_pid": ids.zellij_pid, "nonce": self.nonce})
    }

    fn valid(&self, token: &Value) -> bool {
        valid_identity(token, &self.token(), self.supported_runtime)
    }

    pub fn pipe(&mut self, message: &PipeMessage, panes: &PaneManifest) -> bool {
        let PipeSource::Cli(pipe) = &message.source else { return false };
        match message.name.as_str() {
            SNAPSHOT => {
                // Discovery elects a bar from its cached pane manifest. Once a
                // caller captures a token, read from that exact instance even
                // if later PaneUpdates elect another leader.
                let Some(payload) = message.payload.as_deref() else { return false };
                let request: Value = serde_json::from_str(payload).unwrap_or_default();
                match snapshot_route(request.get("token"), &self.token(), crate::leader(panes),
                                     self.supported_runtime) {
                    Ok(true) => {},
                    Ok(false) => return false,
                    Err(error) => {
                        cli_pipe_output(pipe, &(json!({"error": error}).to_string() + "\n"));
                        return false;
                    },
                }
                if !self.supported_runtime {
                    cli_pipe_output(pipe, &(json!({"error": UNSUPPORTED_RUNTIME}).to_string() + "\n"));
                    return false;
                }
                // The picker reads lifecycle-checked ownership once per
                // snapshot; hidden plugin clones do not poll host metadata.
                // A non-TTY CLI sends a trailing EOF message without payload.
                // It must not overwrite the ownership-aware snapshot rows.
                let owned = &request["auto_titles"];
                let Ok((tab_id, pane_id)) = get_focused_pane_info() else { return false };
                let tab = get_tab_info(tab_id);
                let Some(pane) = get_pane_info(pane_id) else { return false };
                let row = json!({"token": self.token(),
                    "tab": tab.map(|tab| format!("{}: {}", tab.position, crate::tab_name(&tab, panes, Some(&pane), owned))),
                    "pane_id": pane_id.to_string(),
                    "pane": pane.title});
                cli_pipe_output(pipe, &(row.to_string() + "\n"));
            }
            "lane-move-pane" | "lane-move-status" | "lane-move-ack" => {
                let Ok(request) = serde_json::from_str::<Value>(message.payload.as_deref().unwrap_or("")) else {
                    return false;
                };
                let token = &request["token"];
                let ids = get_plugin_ids();
                if token["plugin_id"].as_u64() != Some(ids.plugin_id as u64)
                    || token["client_id"].as_u64() != Some(ids.client_id as u64) {
                    return false;
                }
                if message.name == "lane-move-ack" {
                    if self.valid(token) {
                        if let Some(operation) = request["operation"].as_str() {
                            self.completed_moves.remove(operation);
                        }
                    }
                    return false;
                }
                if message.name == "lane-move-status" {
                    if !self.valid(token) { return false; }
                    let operation = request["operation"].as_str().unwrap_or("");
                    let completed = self.completed_moves.get(operation).map(|(_, result)| result.clone());
                    if completed.is_some() || Self::move_expired(&request) {
                        // Plugin callbacks are serialized. This screen query also
                        // fences queued working-pane mutations and focus changes.
                        // An uncertain PTY spawn can still leave a late inert split;
                        // it cannot enqueue another working-pane replacement.
                        if get_focused_pane_info().is_err() { return false; }
                        let result = completed.unwrap_or_else(||
                            "Pane transfer outcome unknown; inspect both tabs before retrying".to_owned());
                        if result != "moved" {
                            if let Some(picker) = request["picker"].as_u64() {
                                focus_terminal_pane(picker as u32, false, false);
                                if get_focused_pane_info().ok() != request["source_tab"].as_u64()
                                    .map(|tab| (tab as usize, PaneId::Terminal(picker as u32))) {
                                    return false;
                                }
                            }
                        }
                        cli_pipe_output(pipe, &(json!({"stopped": true, "result": result}).to_string() + "\n"));
                    }
                    return false;
                }
                let operation = request["operation"].as_str().unwrap_or("").to_owned();
                // Keep replies until acknowledged. Abandoned helpers cannot grow
                // this cache forever: after expiry + one minute, reconciliation
                // can still fence effects and report an honest unknown outcome.
                self.completed_moves.retain(|_, (expiry, _)| Self::now_ms() < *expiry as u128 + 60000);
                let previous = self.completed_moves.get(&operation).map(|(_, result)| result.clone());
                let result = previous.unwrap_or_else(|| self.move_pane(&request)
                    .unwrap_or_else(|error| error.to_owned()));
                if !operation.is_empty() {
                    self.completed_moves.insert(operation, (request["expires"].as_u64().unwrap_or(0), result.clone()));
                }
                cli_pipe_output(pipe, &(result + "\n"));
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
                if !self.supported_runtime {
                    cli_pipe_output(pipe, &(UNSUPPORTED_RUNTIME.to_owned() + "\n"));
                } else if !self.valid(&token) {
                    cli_pipe_output(pipe, "The selected attachment changed; reopen the client chooser.\n");
                } else if self.pending.is_some() {
                    cli_pipe_output(pipe, "A detach request is already pending for this client.\n");
                } else {
                    // Keep the CLI alive through an asynchronous native
                    // round trip before the final identity and focus check.
                    block_cli_pipe_input(pipe);
                    self.pending = Some((pipe.clone(), token));
                    list_clients();
                }
            }
            _ => return false,
        }
        false
    }

    fn now_ms() -> u128 {
        SystemTime::now().duration_since(UNIX_EPOCH)
            .map(|time| time.as_millis()).unwrap_or(u128::MAX)
    }

    fn move_expired(request: &Value) -> bool {
        if request.get("sources").is_none() { return false; }
        let now = Self::now_ms();
        request["operation"].as_str().map(str::is_empty).unwrap_or(true)
            || request["expires"].as_u64().map(|expiry| now >= expiry as u128).unwrap_or(true)
    }

    fn move_pane(&self, request: &Value) -> Result<String, &'static str> {
        if !self.valid(&request["token"]) {
            return Err("The selected attachment changed; reopen the move picker");
        }
        if Self::move_expired(request) {
            return Err("Pane transfer expired; inspect both tabs before retrying");
        }
        let source = request["source"].as_u64().and_then(|id| u32::try_from(id).ok())
            .ok_or("Invalid source pane")?;
        let picker = request["picker"].as_u64().and_then(|id| u32::try_from(id).ok())
            .ok_or("Invalid picker pane")?;
        let source_tab = request["source_tab"].as_u64().ok_or("Invalid source tab")? as usize;
        let source_id = PaneId::Terminal(source);
        let pane = get_pane_info(source_id).ok_or("The original pane closed")?;
        if source == picker || pane.exited || pane.is_suppressed {
            return Err("The original pane changed; reopen the move picker");
        }
        let destination = if request["destination"].is_null() { None } else {
            let id = request["destination"].as_u64().ok_or("Invalid destination tab")? as usize;
            get_tab_info(id).ok_or("The destination tab closed; reopen the move picker")?;
            Some(id)
        };
        let sources = if let Some(values) = request.get("sources") {
            if destination.is_none() {
                return Err("Move all panes requires an existing destination tab");
            }
            let requested = values.as_array().ok_or("Invalid source panes")?.iter()
                .map(|id| id.as_u64().and_then(|id| u32::try_from(id).ok())
                     .ok_or("Invalid source pane"))
                .collect::<Result<Vec<_>, _>>()?;
            // Preserve the helper's floating-first transfer order.
            let unique: BTreeSet<_> = requested.iter().copied().collect();
            if requested.is_empty() || !requested.contains(&source) || requested.contains(&picker)
                || unique.len() != requested.len() {
                return Err("Invalid source panes; reopen the move picker");
            }
            for id in &requested {
                let pane = get_pane_info(PaneId::Terminal(*id)).ok_or("A source pane closed")?;
                if pane.exited || pane.is_suppressed {
                    return Err("A source pane changed; reopen the move picker");
                }
            }
            requested
        } else { vec![source] };
        // Native queries can yield. Confirm the requesting client still owns
        // this picker; never use the globally focused pane for the transfer.
        if get_focused_pane_info().ok() != Some((source_tab, PaneId::Terminal(picker))) {
            return Err("Picker focus changed; reopen the move picker");
        }
        let result = (|| {
            if request.get("sources").is_some() && destination != Some(source_tab) {
                // Zellij closes tabs without selectable tiled panes, even while
                // floating terminals remain. Keep this helper in its source tab
                // until it receives the reply and exits; never transfer it.
                if Self::move_expired(request) {
                    return Err("Pane transfer expired; no working panes were moved");
                }
                embed_multiple_panes(vec![PaneId::Terminal(picker)]);
                if get_pane_info(PaneId::Terminal(picker)).map(|p| p.is_floating) != Some(false)
                    || get_focused_pane_info().ok() != Some((source_tab, PaneId::Terminal(picker))) {
                    return Err("Could not keep the source tab open; no working panes were moved");
                }
            }
            let moved = match destination {
                Some(id) if id == source_tab => Some(id),
                Some(id) => {
                    for pane in &sources {
                        if Self::move_expired(request) {
                            return Err("Pane transfer expired; inspect both tabs before retrying");
                        }
                        // Recheck membership through the requesting client's
                        // native focus, not a cached manifest or tab position.
                        if request.get("sources").is_some() {
                            focus_terminal_pane(*pane, false, false);
                            if get_focused_pane_info().ok() != Some((source_tab, PaneId::Terminal(*pane))) {
                                return Err("A source pane changed; inspect both tabs before retrying");
                            }
                        }
                        Self::move_to_existing_tab(*pane, id, request).map_err(|error| {
                            if request.get("sources").is_some() {
                                "Pane transfer incomplete; inspect both tabs before retrying"
                            } else { error }
                        })?;
                    }
                    Some(id)
                },
                None => break_panes_to_new_tab(&[source_id], None, true),
            };
            let expected_tab = destination.or(moved).ok_or("Zellij could not transfer the pane")?;
            if request.get("sources").is_some() {
                for pane in &sources {
                    focus_terminal_pane(*pane, false, false);
                    if get_focused_pane_info().ok() != Some((expected_tab, PaneId::Terminal(*pane))) {
                        return Err("Pane transfer changed before final confirmation; inspect both tabs before retrying");
                    }
                }
            }
            focus_terminal_pane(source, false, false);
            if get_focused_pane_info().ok() != Some((expected_tab, source_id)) {
                return Err("The destination changed during transfer; inspect the pane before retrying");
            }
            Ok("moved".to_owned())
        })();
        if result.is_err() && get_pane_info(PaneId::Terminal(picker)).is_some() {
            // Errors are printed in the chooser, which remains in its source tab.
            focus_terminal_pane(picker, false, false);
        }
        result
    }

    fn move_to_existing_tab(source: u32, id: usize, request: &Value) -> Result<(), &'static str> {
        let source_id = PaneId::Terminal(source);
        // The pinned BreakPanes APIs mix IDs and positions. Reserve a
        // new split, then replace only that owned pane by native ID.
        let tab = get_tab_info(id).ok_or("The destination tab closed")?;
        go_to_tab(tab.position as u32);
        if get_focused_pane_info().ok().map(|focus| focus.0) != Some(id) {
            return Err("The destination changed; original pane was not moved");
        }
        if Self::move_expired(request) { return Err("Pane transfer expired"); }
        // A held inert command uses the existing RunCommands grant;
        // no login/interactive shell hooks can rename the destination.
        let placeholder = open_command_pane(
            CommandToRun::new_with_args("/bin/sh", vec!["-c", ":"]),
            Default::default(),
        ).ok_or("Could not create a destination split")?;
        focus_pane_with_id(placeholder, false, false);
        if get_focused_pane_info().ok() != Some((id, placeholder)) {
            close_pane_with_id(placeholder);
            return Err("The destination changed; original pane was not moved");
        }
        if Self::move_expired(request) {
            close_pane_with_id(placeholder);
            return Err("Pane transfer expired");
        }
        replace_pane_with_existing_pane(placeholder, source_id, false);
        if get_pane_info(placeholder).is_some() {
            close_pane_with_id(placeholder);
            return Err("Could not place the original pane in the destination split");
        }
        focus_terminal_pane(source, false, false);
        if get_focused_pane_info().ok() != Some((id, source_id)) {
            return Err("The destination changed during transfer");
        }
        Ok(())
    }

    pub fn finish(&mut self) {
        let Some((pipe, token)) = self.pending.take() else { return };
        // The focused-pane query reaches the screen directly and also covers
        // scrollback-editor clients omitted by native ListClients metadata.
        // SessionUpdate can replay stale cached membership. Native attachment
        // IDs and this instance's nonce remain stable across those snapshots.
        if self.valid(&token) && get_focused_pane_info().is_ok() {
            detach();
            cli_pipe_output(&pipe, "detached\n");
        } else {
            cli_pipe_output(&pipe, "The selected attachment changed; reopen the client chooser.\n");
        }
        unblock_cli_pipe_input(&pipe);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn captured_nonleader_survives_election_but_rejects_stale_identity() {
        let receiver = json!({"client_id": 1, "plugin_id": 7,
                              "server_pid": 42, "nonce": "original-instance"});
        // Discovery now chooses bar 6, but the caller captured bar 7 before
        // that change. Only the addressed instance should answer the read.
        assert_eq!(snapshot_route(None, &receiver, 6, true), Ok(false));
        let captured = receiver.clone();
        assert_eq!(snapshot_route(Some(&captured), &receiver, 6, true), Ok(true));
        let mut other_bar = receiver.clone();
        other_bar["plugin_id"] = json!(6);
        assert_eq!(snapshot_route(Some(&captured), &other_bar, 6, true), Ok(false));
        let mut reloaded = receiver.clone();
        reloaded["nonce"] = json!("replacement-instance");
        assert_eq!(snapshot_route(Some(&captured), &reloaded, 6, true),
                   Err("The captured attachment or status plugin changed"));
    }
}
