//! Display names shared by the bar, picker, and host title hook.
pub mod glyphs {
    include!("../../../design-system/generated/zellij-symbols.rs");
}

pub fn pane_label(raw: &str) -> Option<String> {
    let name: String = raw.chars().filter(|c| !c.is_control()).collect();
    if name.trim().is_empty()
        || name
            .strip_prefix("Pane #")
            .is_some_and(|suffix| !suffix.is_empty() && suffix.bytes().all(|c| c.is_ascii_digit()))
    {
        return None;
    }
    Some(compact(&name).unwrap_or(name))
}

fn compact(title: &str) -> Option<String> {
    let title = title
        .strip_prefix("[ ! ] Action Required | ")
        .unwrap_or(title);
    let (identity, rest) = title.split_once(" | ")?;
    let (agent, project) = if identity == "codex" {
        let (id, fields) = rest.split_once(" | ")?;
        let prefix = id.trim_end_matches("...").trim_end_matches('…');
        if !(16..=36).contains(&prefix.len())
            || !prefix.bytes().enumerate().all(|(i, b)| match i {
                8 | 13 | 18 | 23 => b == b'-',
                _ => b.is_ascii_hexdigit(),
            })
        {
            return None;
        }
        let (status, project) = fields.split_once(" | ").unwrap_or(("", fields));
        let project = match status {
            "Working" | "Thinking" => match project.rsplit_once(' ') {
                Some((name, "⠋" | "⠙" | "⠹" | "⠸" | "⠼" | "⠴" | "⠦" | "⠧" | "⠇" | "⠏")) => {
                    name
                }
                _ => project,
            },
            "" | "Ready" | "Idle" | "Interrupted" | "Blocked" | "Waiting" | "Error" | "Failed" => {
                project
            }
            _ => fields,
        };
        ("󰚩", project)
    } else {
        let mut words = identity.split_whitespace();
        let agent = words.next()?;
        let id = words.next()?;
        if !matches!(agent, "󰚩" | "✳")
            || id.len() != 8
            || !id.bytes().all(|b| b.is_ascii_hexdigit())
            || !matches!(words.next()?, "" | "" | "" | "" | "")
            || words.next().is_some()
        {
            return None;
        }
        (agent, rest)
    };
    (!project.trim().is_empty()).then(|| format!("{agent} {project}"))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn shows_the_project_across_native_and_previous_hook_titles() {
        for title in [
            "codex | 01a1c7cd-f9da-7a91-99da-0cd88... | Working | api ⠋",
            "[ ! ] Action Required | codex | 01a1c7cd-f9da-7a91… | api",
            "󰚩 01a1c7cd  | api",
        ] {
            assert_eq!(compact(title).as_deref(), Some("󰚩 api"));
        }
        assert_eq!(
            compact("✳ abcdef12  | repo | worktree").as_deref(),
            Some("✳ repo | worktree")
        );
        assert_eq!(compact("codex | team notes | Ready | api"), None);
    }
}
