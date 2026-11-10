//! A passive, mode-aware keybinding guide for the user's Zellij configuration.
//!
//! Unlike a static reference sheet, the source is InitialKeybinds from the
//! running server. In particular we do not intercept/forward application input.
use std::collections::BTreeMap;
use zellij_tile::prelude::*;

#[derive(Default)]
struct WhichKey {
    allowed: bool,
    bindings: Vec<(String, String)>,
    scroll: usize,
    prefix_mode: bool,
    pinned: bool,
    epoch: u64,
    pending_epoch: Option<u64>,
    visible: bool,
}

register_plugin!(WhichKey);

impl ZellijPlugin for WhichKey {
    fn load(&mut self, _: BTreeMap<String, String>) {
        subscribe(&[
            EventType::PermissionRequestResult,
            EventType::InitialKeybinds,
            EventType::Key,
            EventType::ModeUpdate,
            EventType::Timer,
        ]);
        request_permission(&[
            PermissionType::ReadApplicationState,
            PermissionType::ChangeApplicationState,
        ]);
    }

    fn update(&mut self, event: Event) -> bool {
        match event {
            Event::PermissionRequestResult(PermissionStatus::Granted) => {
                self.allowed = true;
                hide_self();
                true
            }
            Event::PermissionRequestResult(PermissionStatus::Denied) => {
                close_self();
                false
            }
            Event::ModeUpdate(mode) if self.allowed => {
                let prefix = mode.mode == InputMode::Tmux;
                if prefix && !self.prefix_mode && !self.pinned {
                    // Zellij continues to own subsequent keys.
                    self.epoch = self.epoch.wrapping_add(1);
                    self.pending_epoch = Some(self.epoch);
                    set_timeout(0.35);
                } else if !prefix && self.prefix_mode && !self.pinned {
                    self.pending_epoch = None;
                    if self.visible {
                        hide_self();
                        self.visible = false;
                    }
                }
                self.prefix_mode = prefix;
                false
            }
            Event::Timer(_) if self.allowed => {
                if self.prefix_mode && !self.pinned
                    && self.pending_epoch.take() == Some(self.epoch)
                {
                    // Never focus the overlay: native Tmux bindings keep input.
                    show_pane_with_id(PaneId::Plugin(get_plugin_ids().plugin_id), true, false);
                    self.visible = true;
                    true
                } else {
                    false
                }
            }
            Event::InitialKeybinds(all) => {
                let descriptions = binding_descriptions(include_str!("../../config.kdl"));
                self.bindings = all.into_iter()
                    .filter(|(mode, _)| *mode == InputMode::Tmux)
                    .flat_map(|(_, entries)| entries)
                    .map(|(key, actions)| {
                        let raw = format!("{key:?}");
                        let key = normalize_key(&raw);
                        let description = descriptions.get(&key).cloned().unwrap_or_else(|| {
                            actions.first().map(|action| format!("{action:?}"))
                                .unwrap_or_else(|| "Unassigned".into())
                        });
                        (key, description)
                    })
                    .collect();
                self.bindings.sort_by(|left, right| left.0.cmp(&right.0));
                self.bindings.dedup_by(|left, right| left.0 == right.0);
                true
            }
            Event::Key(key) => {
                if key.bare_key == BareKey::Esc || key.bare_key == BareKey::Enter {
                    self.pinned = false;
                    hide_self();
                    self.visible = false;
                } else if key.bare_key == BareKey::Down
                    || (key.bare_key == BareKey::Char('j') && key.has_no_modifiers())
                {
                    self.scroll = self.scroll.saturating_add(1);
                } else if key.bare_key == BareKey::Up
                    || (key.bare_key == BareKey::Char('k') && key.has_no_modifiers())
                {
                    self.scroll = self.scroll.saturating_sub(1);
                }
                true
            }
            _ => false,
        }
    }

    fn pipe(&mut self, message: PipeMessage) -> bool {
        if !self.allowed || message.source != PipeSource::Keybind
            || message.name != "which-key-toggle"
        {
            return false;
        }
        self.pinned = !self.pinned;
        self.pending_epoch = None;
        if self.pinned {
            show_self(true);
            self.visible = true;
        } else {
            hide_self();
            self.visible = false;
        }
        true
    }

    fn render(&mut self, rows: usize, columns: usize) {
        if !self.allowed || rows < 4 || columns < 24 {
            return;
        }
        // This surface never runs the bindings: existing native shortcuts
        // remain authoritative and continue to use the original Tmux mode.
        let visible = rows.saturating_sub(3);
        self.scroll = self.scroll.min(self.bindings.len().saturating_sub(visible));
        print!("\x1b[2J\x1b[H");
        print_text_with_coordinates(
            Text::from(" Ctrl-f  ·  keybindings").color_range(1, ..),
            0, 0, Some(columns), Some(1),
        );
        for (i, (key, description)) in self.bindings.iter()
            .skip(self.scroll).take(visible).enumerate()
        {
            let available = columns.saturating_sub(20);
            let short: String = description.chars().take(available).collect();
            let line = format!(" {:<17} {}", key, short);
            print_text_with_coordinates(Text::from(line), 0, i + 1, Some(columns), Some(1));
        }
        let footer = format!(" {}/{}  ↑↓/jk scroll · Esc close", self.scroll + usize::from(!self.bindings.is_empty()), self.bindings.len());
        print_text_with_coordinates(Text::from(footer), 0, rows - 1, Some(columns), Some(1));
    }
}

// The human-readable label lives immediately above the binding in config.kdl.
// The runtime event remains authoritative for which bindings actually exist.
fn binding_descriptions(config: &str) -> BTreeMap<String, String> {
    let mut labels = BTreeMap::new();
    let Some(tmux) = config.split_once("    tmux {").map(|(_, rest)| rest) else {
        return labels;
    };
    let block = tmux.split_once("    resize {").map_or(tmux, |(block, _)| block);
    let mut pending: Option<&str> = None;
    for line in block.lines() {
        let line = line.trim();
        if let Some(description) = line.strip_prefix("// which-key: ") {
            pending = Some(description);
        } else if let Some(bindings) = line.strip_prefix("bind ") {
            if let Some(description) = pending.take() {
                let keys = bindings.split('{').next().unwrap_or("");
                for part in keys.split('"').skip(1).step_by(2) {
                    labels.insert(part.to_owned(), description.to_owned());
                }
            }
        } else if !line.is_empty() && !line.starts_with("//") {
            pending = None;
        }
    }
    labels
}

// Zellij's key Debug spelling is an implementation detail. Avoid losing
// an unfamiliar shortcut: show the raw representation in that case.
fn normalize_key(raw: &str) -> String {
    let basic = raw.strip_prefix("KeyWithModifier { bare_key: ");
    if let Some(value) = basic {
        if let Some(character) = value.strip_prefix("Char('") {
            if let Some(end) = character.find("')") {
                let name = &character[..end];
                if raw.contains("Ctrl") { return format!("Ctrl {name}"); }
                if raw.contains("Alt") { return format!("Alt {name}"); }
                return name.into();
            }
        }
    }
    raw.into()
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn aliases_cover_the_public_entrypoint() {
        let descriptions = binding_descriptions(include_str!("../../config.kdl"));
        assert_eq!(descriptions.get("?").map(String::as_str), Some("Keybinding guide"));
        assert_eq!(descriptions.get("Ctrl a").map(String::as_str), Some("Next attention"));
    }
    #[test]
    fn unknown_keys_are_not_discarded() {
        assert_eq!(normalize_key("unfamiliar-key"), "unfamiliar-key");
    }
}
