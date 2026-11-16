use zellij_tile::prelude::*;

pub const MESSAGE: &str = "attention-next-tab";
pub const HIGHEST: &str = "attention-highest-tab";

// tmux-quickswitch-alert visits windows, not individual panes. Keep its
// numeric, current-session policy in the plugin instead of changing native
// GoToNextAttention's cross-session severity/recency semantics.
pub fn jump(tabs: &[TabInfo], attention: &GlobalAttention, message: &PipeMessage,
            policy: &crate::attention_policy::Policy) {
    if !message.is_private || !crate::clipboard::is_own_client(message) { return; }
    let highest = message.name == HIGHEST;
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
        let Some(tier) = policy.attention_rank(&item.attention) else { continue };
        tiers.entry(item.tab_id).and_modify(|old: &mut usize| *old = (*old).min(tier)).or_insert(tier);
    }
    let ids: std::collections::BTreeSet<_> = tabs.iter().map(|tab| tab.tab_id)
        .chain(tiers.keys().copied()).collect();
    let mut candidates: Vec<_> = ids.into_iter()
        // A direct jump stays put when this is already the highest-ranked tab.
        // Only the cycling shortcut excludes the current tab.
        .filter(|id| highest || *id != origin.0)
        .filter_map(get_tab_info)
        .filter(|tab| !tab.attention.muted)
        .filter_map(|tab| {
            // Keep tmux's explicit ! title marker and ordinary native bells,
            // including a bell not yet present in the attention publication.
            let tier = policy.tab_rank(tiers.get(&tab.tab_id).copied(),
                                       tab.name.starts_with('!'), tab.has_bell_notification)?;
            Some((tier, tab.position, tab.tab_id))
        })
        .collect();
    candidates.sort_unstable();
    let Some(&(tier, _, _)) = candidates.first() else { return };
    let target = if highest { candidates.first() } else {
        candidates.iter().filter(|candidate| candidate.0 == tier)
            .find(|candidate| candidate.1 > current.position)
            .or_else(|| candidates.first())
    };
    let Some(&(_, _, id)) = target else { return };
    if id == origin.0 { return; }
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
