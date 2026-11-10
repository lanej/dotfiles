//! A live, read-only keybinding guide for the user's Zellij configuration.
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
}

register_plugin!(WhichKey);

impl ZellijPlugin for WhichKey {
    fn load(&mut self, _: BTreeMap<String, String>) {
        subscribe(&[
            EventType::PermissionRequestResult,
            EventType::InitialKeybinds,
            EventType::Key,
        ]);
        request_permission(&[PermissionType::ReadApplicationState]);
    }

    fn update(&mut self, event: Event) -> bool {
        match event {
            Event::PermissionRequestResult(PermissionStatus::Granted) => {
                self.allowed = true;
                true
            }
            Event::PermissionRequestResult(PermissionStatus::Denied) => {
                close_self();
                false
            }
            Event::InitialKeybinds(all) => {
                self.bindings = all.into_iter()
                    .filter(|(mode, _)| *mode == InputMode::Tmux)
                    .flat_map(|(_, entries)| entries)
                    .map(|(key, actions)| {
                        let raw = format!("{key:?}");
                        let key = normalize_key(&raw);
                        let description = describe(&key, &actions);
                        (key, description)
                    })
                    .collect();
                self.bindings.sort_by(|left, right| left.0.cmp(&right.0));
                self.bindings.dedup_by(|left, right| left.0 == right.0);
                true
            }
            Event::Key(key) => {
                if key.bare_key == BareKey::Esc || key.bare_key == BareKey::Enter {
                    close_self();
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

// Display is deliberately descriptive, not executable. The server's Action
// Debug representation is a fallback for uncommon/custom actions.
fn describe(key: &str, actions: &[zellij_tile::prelude::actions::Action]) -> String {
    let alias = match key {
        "s" => Some("Split below"), "v" => Some("Split right"),
        "h" => Some("Focus left"), "j" => Some("Focus down"),
        "k" => Some("Focus up"), "l" => Some("Focus right"),
        "c" => Some("New tab"), "z" => Some("Zoom pane"),
        "m" => Some("Move pane"), "M" => Some("Gather panes"),
        "b" => Some("Inbox"), "B" => Some("Notification history"),
        "a" => Some("Watch pane"), "U" => Some("Mute pane"),
        "g" => Some("Golden ratio"), "G" => Some("Force golden ratio"),
        "d" => Some("Detach"), "x" => Some("Close pane"),
        "r" => Some("Rename tab"), ":" => Some("Command palette"),
        "?" => Some("Show keybindings"), "[" => Some("Scroll mode"),
        "/" => Some("Search scrollback"), "e" => Some("Edit scrollback"),
        "P" => Some("Shared popup"), "p" => Some("Paste session yank"),
        "Ctrl a" => Some("Next attention"), "Ctrl r" => Some("Resize mode"),
        "Ctrl f" => Some("Tab picker"), "Ctrl w" => Some("Session picker"),
        "Ctrl q" => Some("Shutdown session"), _ => None,
    };
    alias.map(str::to_owned).unwrap_or_else(|| {
        actions.first().map(|action| format!("{action:?}"))
            .unwrap_or_else(|| "Unassigned".into())
    })
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
        assert_eq!(describe("?", &[]), "Show keybindings");
        assert_eq!(describe("Ctrl a", &[]), "Next attention");
    }
    #[test]
    fn unknown_keys_are_not_discarded() {
        assert_eq!(normalize_key("unfamiliar-key"), "unfamiliar-key");
    }
}
