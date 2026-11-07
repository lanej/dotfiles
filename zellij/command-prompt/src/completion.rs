use crate::commands;
use std::ops::Range;
use zellij_tile::prelude::{PaneInfo, SessionInfo, TabInfo};
use zellij_tile::ui_components::fuzzy_match_indices;

pub const LOCAL_COMMANDS: &[(&str, &str)] = &[
    ("help", "Search supported commands and their descriptions"),
    ("history", "Search this client's recent commands"),
    (
        "list-panes",
        "Search panes; Enter jumps to the selected pane",
    ),
    ("list-tabs", "Search tabs; Enter jumps to the selected tab"),
    (
        "list-sessions",
        "Search running sessions; Enter switches session",
    ),
    ("focus-pane-id", "Focus a live pane by its stable ID"),
    ("go-to-tab-by-id", "Focus a live tab by its stable ID"),
    ("switch-session", "Switch to an existing session by name"),
];

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Suggestion {
    pub value: String,
    pub label: String,
    pub detail: String,
}

impl Suggestion {
    pub fn new(
        value: impl Into<String>,
        label: impl Into<String>,
        detail: impl Into<String>,
    ) -> Self {
        Self {
            value: value.into(),
            label: label.into(),
            detail: detail.into(),
        }
    }
}

#[derive(Default, Clone)]
pub struct Context {
    pub tabs: Vec<TabInfo>,
    pub panes: Vec<(usize, PaneInfo)>,
    pub sessions: Vec<SessionInfo>,
    pub pane_name: String,
    pub tab_name: String,
    pub session_name: String,
}

#[derive(Debug)]
pub struct Completions {
    pub replace: Range<usize>,
    pub items: Vec<Suggestion>,
    pub help: String,
    pub command: bool,
}

pub fn quote(value: &str) -> String {
    shlex::try_quote(value)
        .map(|v| v.into_owned())
        .unwrap_or_default()
}

// Completion must work before a quote is closed and in the middle of a line.
// These spans only locate tokens. Execution still uses shlex and Zellij's parser.
fn tokens(line: &str) -> Vec<Range<usize>> {
    let mut spans = vec![];
    let (mut start, mut quote, mut escaped) = (None, None, false);
    for (i, c) in line.char_indices() {
        if start.is_none() && !c.is_whitespace() {
            start = Some(i);
        }
        if escaped {
            escaped = false;
            continue;
        }
        if c == '\\' && quote != Some('\'') {
            escaped = true;
            continue;
        }
        if Some(c) == quote {
            quote = None;
        } else if quote.is_none() && matches!(c, '\'' | '"') {
            quote = Some(c);
        } else if quote.is_none() && c.is_whitespace() {
            if let Some(begin) = start.take() {
                spans.push(begin..i);
            }
        }
    }
    if let Some(begin) = start {
        spans.push(begin..line.len());
    }
    spans
}

fn unquote_prefix(raw: &str) -> String {
    let (mut result, mut quote, mut escaped) = (String::new(), None, false);
    for c in raw.chars() {
        if escaped {
            result.push(c);
            escaped = false;
        } else if c == '\\' && quote != Some('\'') {
            escaped = true;
        } else if Some(c) == quote {
            quote = None;
        } else if quote.is_none() && matches!(c, '\'' | '"') {
            quote = Some(c);
        } else {
            result.push(c);
        }
    }
    result
}

pub fn matches(query: &str, candidate: &str) -> bool {
    query.is_empty() || fuzzy_match_indices(query, candidate).is_some()
}

pub fn complete(line: &str, cursor: usize, context: &Context, history: &[String]) -> Completions {
    let cursor = line
        .char_indices()
        .nth(cursor)
        .map(|(i, _)| i)
        .unwrap_or(line.len());
    let spans = tokens(line);
    let current = spans
        .iter()
        .find(|span| span.start <= cursor && cursor <= span.end)
        .cloned()
        .unwrap_or(cursor..cursor);
    let before: Vec<String> = spans
        .iter()
        .filter(|s| s.end < current.start)
        .map(|s| unquote_prefix(&line[s.clone()]))
        .collect();
    let prefix = unquote_prefix(&line[current.start..cursor]);
    let mut result = Completions {
        replace: current,
        items: vec![],
        help: String::new(),
        command: before.is_empty(),
    };
    let metadata = commands::metadata();
    if before.is_empty() {
        result.items = metadata
            .iter()
            .map(|command| {
                Suggestion::new(
                    command.get_name(),
                    command.get_name(),
                    command
                        .get_about()
                        .map(ToString::to_string)
                        .unwrap_or_default(),
                )
            })
            .chain(
                LOCAL_COMMANDS
                    .iter()
                    .map(|(name, help)| Suggestion::new(*name, *name, *help)),
            )
            .collect();
        result.items.retain(|item| {
            matches(
                prefix.trim_start_matches(':'),
                &format!("{} {}", item.label, item.detail),
            )
        });
        result.items.sort_by_key(|item| {
            (
                !item.value.starts_with(prefix.trim_start_matches(':')),
                history
                    .iter()
                    .position(|line| line.split_whitespace().next() == Some(item.value.as_str()))
                    .unwrap_or(usize::MAX),
                item.value.clone(),
            )
        });
        result.help = "Type an action, or search commands by name or description".into();
        return result;
    }
    let name = before[0].trim_start_matches(':');
    if let Some((_, help)) = LOCAL_COMMANDS.iter().find(|(n, _)| *n == name) {
        result.help = (*help).into();
        result.items = match name {
            "focus-pane-id" if before.len() == 1 => pane_targets(context),
            "go-to-tab-by-id" if before.len() == 1 => tab_targets(context, true),
            "switch-session" if before.len() == 1 => session_targets(context),
            _ => vec![],
        };
    } else if let Some(command) = metadata.iter().find(|command| command.get_name() == name) {
        result.help = command
            .get_about()
            .map(ToString::to_string)
            .unwrap_or_default();
        let mut position = 1;
        let mut pending = None;
        for word in before.iter().skip(1) {
            if pending.take().is_some() {
                continue;
            }
            if word == "--" {
                return result;
            } // Program arguments belong to that program.
            if word.starts_with('-') {
                if let Some(arg) = command.get_arguments().find(|arg| flag_matches(arg, word)) {
                    if arg.get_num_args().is_some_and(|n| n.takes_values()) && !word.contains('=') {
                        pending = Some(arg.clone());
                    }
                }
            } else {
                position += 1;
            }
        }
        if prefix.starts_with('-') && pending.is_none() {
            result.items = command
                .get_arguments()
                .filter(|arg| commands::argument_supported(arg.get_id().as_str()))
                .filter_map(|arg| arg.get_long().map(|flag| (arg, format!("--{flag}"))))
                .filter(|(_, flag)| !before.contains(flag))
                .map(|(arg, flag)| {
                    Suggestion::new(
                        &flag,
                        &flag,
                        arg.get_help().map(ToString::to_string).unwrap_or_default(),
                    )
                })
                .collect();
        } else {
            let arg = pending.or_else(|| {
                command
                    .get_positionals()
                    .find(|arg| arg.get_index() == Some(position))
                    .cloned()
            });
            if let Some(arg) = arg {
                result.help = format!(
                    "{}: {}",
                    arg.get_id(),
                    arg.get_help().map(ToString::to_string).unwrap_or_default()
                );
                result.items = match (name, arg.get_id().as_str()) {
                    ("go-to-tab-name", "name") => context
                        .tabs
                        .iter()
                        .map(|t| {
                            Suggestion::new(
                                &t.name,
                                format!("{}  {}", t.position, t.name),
                                "tab name",
                            )
                        })
                        .collect(),
                    ("go-to-tab", "index") => tab_targets(context, false),
                    ("rename-pane", "name") => vec![Suggestion::new(
                        &context.pane_name,
                        &context.pane_name,
                        "current pane name",
                    )],
                    ("rename-tab", "name") => vec![Suggestion::new(
                        &context.tab_name,
                        &context.tab_name,
                        "current tab name",
                    )],
                    ("rename-session", "name") => vec![Suggestion::new(
                        &context.session_name,
                        &context.session_name,
                        "current session name",
                    )],
                    (_, "direction") => ["left", "right", "up", "down"]
                        .into_iter()
                        .map(|v| Suggestion::new(v, v, "direction"))
                        .collect(),
                    (_, "resize") => ["increase", "decrease"]
                        .into_iter()
                        .map(|v| Suggestion::new(v, v, "resize amount"))
                        .collect(),
                    _ => arg
                        .get_value_parser()
                        .possible_values()
                        .into_iter()
                        .flatten()
                        .map(|v| {
                            Suggestion::new(
                                v.get_name(),
                                v.get_name(),
                                v.get_help().map(ToString::to_string).unwrap_or_default(),
                            )
                        })
                        .collect(),
                };
            }
        }
    }
    result
        .items
        .retain(|item| matches(&prefix, &format!("{} {}", item.label, item.detail)));
    if !prefix.is_empty() {
        let query = prefix.to_lowercase();
        result.items.sort_by_key(|item| {
            (
                !item.value.to_lowercase().starts_with(&query),
                !matches(&prefix, &item.label),
            )
        });
    }
    result
}

fn flag_matches(arg: &clap::Arg, word: &str) -> bool {
    let word = word.split('=').next().unwrap_or(word);
    arg.get_long()
        .is_some_and(|long| word == format!("--{long}"))
        || arg
            .get_short()
            .is_some_and(|short| word == format!("-{short}"))
}

pub fn pane_targets(context: &Context) -> Vec<Suggestion> {
    context
        .panes
        .iter()
        .filter(|(_, p)| p.is_selectable && !p.is_suppressed)
        .map(|(tab, pane)| {
            let id = format!(
                "{}_{}",
                if pane.is_plugin { "plugin" } else { "terminal" },
                pane.id
            );
            Suggestion::new(
                &id,
                format!("{id}  {}", pane.title),
                format!(
                    "tab {tab}  {}",
                    pane.terminal_command.as_deref().unwrap_or("")
                ),
            )
        })
        .collect()
}

pub fn tab_targets(context: &Context, stable: bool) -> Vec<Suggestion> {
    context
        .tabs
        .iter()
        .map(|tab| {
            Suggestion::new(
                if stable {
                    tab.tab_id.to_string()
                } else {
                    (tab.position + 1).to_string()
                },
                format!("{}  {}", tab.position, tab.name),
                if stable {
                    format!("tab ID {}", tab.tab_id)
                } else {
                    format!("native index {}", tab.position + 1)
                },
            )
        })
        .collect()
}

pub fn session_targets(context: &Context) -> Vec<Suggestion> {
    context
        .sessions
        .iter()
        .map(|session| {
            Suggestion::new(
                &session.name,
                &session.name,
                format!(
                    "{} tabs  {} clients{}",
                    session.tabs.len(),
                    session.connected_clients,
                    if session.is_current_session {
                        "  current"
                    } else {
                        ""
                    }
                ),
            )
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn completion_edits_only_the_token_at_the_unicode_cursor() {
        let ctx = Context {
            tab_name: "déploy 'green'".into(),
            ..Default::default()
        };
        let line = "rename-tab \"dé\" --help";
        let result = complete(line, 14, &ctx, &[]);
        assert_eq!(result.items[0].value, ctx.tab_name);
        let edited = format!(
            "{}{}{}",
            &line[..result.replace.start],
            quote(&result.items[0].value),
            &line[result.replace.end..]
        );
        assert_eq!(
            shlex::split(&edited).unwrap(),
            ["rename-tab", "déploy 'green'", "--help"]
        );
    }

    #[test]
    fn live_tabs_complete_names_with_spaces_and_native_positions() {
        let ctx = Context {
            tabs: vec![TabInfo {
                name: "build logs".into(),
                position: 0,
                tab_id: 42,
                ..Default::default()
            }],
            ..Default::default()
        };
        assert_eq!(
            complete("go-to-tab-name \"bu", 18, &ctx, &[]).items[0].value,
            "build logs"
        );
        assert_eq!(complete("go-to-tab ", 10, &ctx, &[]).items[0].value, "1");
        assert_eq!(
            complete("go-to-tab-by-id ", 16, &ctx, &[]).items[0].value,
            "42"
        );
    }

    #[test]
    fn native_flags_and_values_stop_at_program_arguments() {
        let ctx = Context::default();
        assert!(complete("new-pane --dir", 14, &ctx, &[])
            .items
            .iter()
            .any(|i| i.value == "--direction"));
        assert!(complete("new-pane --direction r", 22, &ctx, &[])
            .items
            .iter()
            .any(|i| i.value == "right"));
        assert!(complete("new-pane -- htop --", 18, &ctx, &[])
            .items
            .is_empty());
        assert!(!complete("new-pane --", 11, &ctx, &[])
            .items
            .iter()
            .any(|i| matches!(
                i.value.as_str(),
                "--no-focus" | "--in-place" | "--stacked" | "--plugin"
            )));
    }
}
