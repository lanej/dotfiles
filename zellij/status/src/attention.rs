use zellij_tile::prelude::*;

pub const MESSAGE: &str = "attention-next-tab";

// tmux-quickswitch-alert visits windows, not individual panes. Keep its
// numeric, current-session policy in the plugin instead of changing native
// GoToNextAttention's cross-session severity/recency semantics.
pub fn jump(tabs: &[TabInfo], attention: &GlobalAttention, message: &PipeMessage) {
    if !message.is_private || !crate::clipboard::is_own_client(message) { return; }
    let Some(session) = attention.sessions.iter().find(|session| session.is_current
        && session.name == attention.current_session) else { return };
    if session.attention.muted { return; }
    let Ok(origin) = get_focused_pane_info() else { return };
    let Some(current) = get_tab_info(origin.0) else { return };
    // Attention updates arrive independently of layout/session metadata.
    // Each item carries a stable tab ID, so never join live tab positions to
    // a cached PaneManifest or wait for an unrelated SessionUpdate.
    let mut tiers = std::collections::BTreeMap::new();
    for item in &session.attention.items {
        let status = item.attention.effective_status();
        let tier = match status {
            AttentionStatus::NeedsYou => item.attention.source
                .map(|source| source.as_str()) == Some("bell"),
            AttentionStatus::Failed => false,
            AttentionStatus::Working | AttentionStatus::NewOutput => true,
            _ => continue,
        };
        tiers.entry(item.tab_id).and_modify(|old: &mut bool| *old &= tier).or_insert(tier);
    }
    let ids: std::collections::BTreeSet<_> = tabs.iter().map(|tab| tab.tab_id)
        .chain(tiers.keys().copied()).collect();
    let mut candidates: Vec<_> = ids.into_iter()
        .filter(|id| *id != origin.0)
        .filter_map(get_tab_info)
        .filter(|tab| !tab.attention.muted)
        .filter_map(|tab| {
            // Keep tmux's explicit ! title marker and ordinary native bells,
            // including a bell not yet present in the attention publication.
            let tier = if tab.name.starts_with('!') { Some(false) }
                else { tiers.get(&tab.tab_id).copied().or_else(|| tab.has_bell_notification.then_some(true)) }?;
            Some((tier, tab.position, tab.tab_id))
        })
        .collect();
    candidates.sort_unstable();
    let Some(&(tier, _, _)) = candidates.first() else { return };
    let target = candidates.iter().filter(|candidate| candidate.0 == tier)
        .find(|candidate| candidate.1 > current.position)
        .or_else(|| candidates.first());
    let Some(&(_, _, id)) = target else { return };
    // Queries can yield. Do not steal this client's focus if it has already
    // moved. Native stable-ID routing cannot select an unrelated tab after
    // another client closes or reorders the destination.
    if get_focused_pane_info().ok() == Some(origin) {
        switch_tab_to_id(id as u64);
    }
}

// Upstream bf517077 exposes this protocol command and server implementation,
// but not its Rust convenience shim. Use the SDK's own wire conversion until
// zellij-tile exports the equivalent helper; no fork-only API is involved.
fn switch_tab_to_id(tab_id: u64) {
    use zellij_tile::shim::{plugin_api::plugin_command::ProtobufPluginCommand, prost::Message};
    let command: ProtobufPluginCommand = PluginCommand::SwitchTabToId(tab_id).try_into().unwrap();
    object_to_stdout(&command.encode_to_vec());
    #[cfg(target_family = "wasm")]
    unsafe { host_run_plugin_command() };
}

#[cfg(target_family = "wasm")]
#[link(wasm_import_module = "zellij")]
extern "C" { fn host_run_plugin_command(); }
