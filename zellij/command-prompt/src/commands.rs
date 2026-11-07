use clap::{CommandFactory, Parser};
use std::{path::PathBuf, sync::OnceLock};
use zellij_tile::prelude::actions::Action;
use zellij_utils::cli::CliAction;
use zellij_utils::plugin_api::action::ProtobufAction;

// Queries are rendered from native state by the palette. These mutations use
// Zellij's parser and plugin protocol; loading layout files stays in the shell.
const COMMANDS: &[&str] = &[
    "clear",
    "close-pane",
    "close-tab",
    "edit",
    "focus-last-pane",
    "focus-next-pane",
    "focus-previous-pane",
    "go-to-next-attention",
    "go-to-next-tab",
    "go-to-previous-tab",
    "go-to-tab",
    "go-to-tab-name",
    "hide-floating-panes",
    "move-focus",
    "move-focus-or-tab",
    "move-pane",
    "move-pane-backwards",
    "move-tab",
    "new-pane",
    "new-tab",
    "next-swap-layout",
    "previous-swap-layout",
    "rename-pane",
    "rename-session",
    "rename-tab",
    "resize",
    "show-floating-panes",
    "toggle-active-sync-tab",
    "toggle-floating-panes",
    "toggle-fullscreen",
    "toggle-pane-embed-or-floating",
    "toggle-pane-frames",
    "undo-rename-pane",
    "undo-rename-tab",
];

pub fn metadata() -> &'static [clap::Command] {
    static METADATA: OnceLock<Vec<clap::Command>> = OnceLock::new();
    METADATA.get_or_init(|| {
        let mut command = CommandLine::command();
        command.build();
        command
            .get_subcommands()
            .filter(|command| COMMANDS.contains(&command.get_name()))
            .cloned()
            .collect()
    })
}

pub fn argument_supported(name: &str) -> bool {
    !matches!(
        name.replace('_', "-").as_str(),
        "near-current-pane"
            | "no-focus"
            | "stacked"
            | "in-place"
            | "layout"
            | "layout-string"
            | "initial-plugin"
            | "plugin"
            | "pane-id"
            | "tab-id"
    )
}

#[derive(Parser)]
#[command(name = ":", disable_help_subcommand = true, color = clap::ColorChoice::Never)]
struct CommandLine {
    #[command(subcommand)]
    action: CliAction,
}

pub enum Parsed {
    Actions(Vec<Action>),
    Help(String),
}

pub fn parse(line: &str, cwd: PathBuf) -> Result<Parsed, String> {
    let words = shlex::split(line.trim().trim_start_matches(':'))
        .ok_or("Unclosed quote or trailing escape. Use quotes around names with spaces.")?;
    let Some(name) = words.first() else {
        return Ok(Parsed::Actions(vec![]));
    };
    if !COMMANDS.contains(&name.as_str()) {
        return Err(format!("Unknown or unsupported command: {name}. Enter help to choose a Zellij action. Shell commands and stdout queries belong in your terminal."));
    }
    let parsed = match CommandLine::try_parse_from(std::iter::once(":".to_owned()).chain(words)) {
        Ok(parsed) => parsed,
        Err(error) if error.kind() == clap::error::ErrorKind::DisplayHelp => {
            return Ok(Parsed::Help(error.to_string()));
        }
        Err(error) => return Err(error.to_string()),
    };
    match &parsed.action {
        CliAction::NewPane {
            near_current_pane: true,
            ..
        }
        | CliAction::NewPane { no_focus: true, .. }
        | CliAction::NewPane { stacked: true, .. }
        | CliAction::NewPane { in_place: true, .. }
        | CliAction::Edit {
            near_current_pane: true,
            ..
        }
        | CliAction::Edit { no_focus: true, .. }
        | CliAction::Edit { in_place: true, .. } => {
            // RunAction's source is this suppressed plugin, not the invoking
            // terminal. These modes use the source pane rather than the client.
            return Err("Use your terminal for --near-current-pane, --no-focus, --stacked and --in-place. These flags need a terminal-pane origin.".into());
        }
        CliAction::NewTab {
            layout: Some(_), ..
        }
        | CliAction::NewTab {
            layout_string: Some(_),
            ..
        }
        | CliAction::NewTab {
            initial_plugin: Some(_),
            ..
        }
        | CliAction::NewPane {
            plugin: Some(_), ..
        } => {
            return Err("Open layouts and other plugins from your terminal. This prompt does not load external plugins or layout files.".into());
        }
        _ => {}
    }
    let actions = Action::actions_from_cli(parsed.action, Box::new(move || cwd.clone()), None)?;
    let actions: Vec<Action> = actions
        .into_iter()
        .flat_map(|action| match action {
            // The CLI uses its ID-aware variant even without an explicit ID. That
            // variant is not on the plugin wire protocol; these native input actions
            // perform the same rename for the invoking client's focused pane.
            Action::RenamePaneByPaneId {
                pane_id: None,
                name,
            } => vec![
                Action::PaneNameInput { input: vec![0] },
                Action::PaneNameInput { input: name },
            ],
            action => vec![action],
        })
        .collect();
    for action in &actions {
        ProtobufAction::try_from(action.clone()).map_err(|error| format!(
            "This command variant is unavailable through the plugin API: {error}. Use your terminal."
        ))?;
    }
    Ok(Parsed::Actions(actions))
}
