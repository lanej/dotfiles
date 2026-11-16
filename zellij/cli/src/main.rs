mod agent;
mod agent_titles;
mod auto_title;
mod balance;
mod clipboard;
mod command;
mod config;
mod context;
mod image_hints;
mod ipc;
mod navigation;
mod notify;
mod panes;
mod picker;
mod preview;
mod reload;
mod session;
mod status;
mod titles;
mod util;
mod view;
use anyhow::{bail, Result};
use std::io::{IsTerminal, Write};
const HELP:&str="Usage: zellij-helper <status|agent|attach|ssh|auto-title|shell-title|clipboard|context|pane|image-hints|navigate|popup|shutdown|balance|notify|picker|claude-title|codex-title> [arguments]";
fn run(args: &[String]) -> Result<()> {
    match args {
        [] => println!("{HELP}"),
        [help] if matches!(help.as_str(), "--help" | "-h") => println!("{HELP}"),
        [command, rest @ ..] => match command.as_str() {
            "status" => status::run(args).map_err(anyhow::Error::msg)?,
            "agent" => agent::main(rest)?,
            "claude-title" => {
                let _ = agent_titles::claude(rest);
            }
            "codex-title" => {
                let _ = agent_titles::codex(rest);
            }
            "balance" => balance::main(rest)?,
            "notify" => notify::main(rest)?,
            "picker" => picker::main(rest)?,
            "attach" => session::attach(rest)?,
            "ssh" => session::ssh(rest)?,
            "shell-title" if rest.is_empty() => {
                let _ = auto_title::shell_title();
            }
            "auto-title" => {
                if rest.is_empty() || rest == ["--shell"] {
                    let _ = auto_title::main(rest);
                } else {
                    auto_title::main(rest)?;
                }
            }
            "clipboard" => clipboard::main(rest)?,
            "image-hints" if rest.is_empty() => image_hints::run()?,
            "image-view" if rest.len() == 1 => image_hints::view(&rest[0])?,
            "context" if rest == ["provider"] => println!("{}", context::provider()?),
            "context" if rest == ["socket"] => println!("{}", context::socket()?),
            "context" if rest == ["title-context"] => println!("{}", auto_title::context()?),
            "context" if rest.first().is_some_and(|arg| arg == "inspect") => {
                panes::inspect(&rest[1..])?
            }
            "pane" => panes::main(rest)?,
            "navigate" => navigation::main(rest)?,
            "popup" if rest.is_empty() => session::popup()?,
            "shutdown" if rest.is_empty() => session::shutdown()?,
            _ => bail!("{HELP}"),
        },
    }
    Ok(())
}
fn main() {
    let mut arguments = std::env::args();
    let executable = arguments.next().unwrap_or_default();
    let name = std::path::Path::new(&executable)
        .file_name()
        .and_then(|name| name.to_str())
        .unwrap_or("");
    let mut args: Vec<_> = arguments.collect();
    let subcommand = match name {
        "zellij-helper" | "lane-zellij" => None,
        "claude-zellij-title-hook" => Some("claude-title"),
        "codex-zellij-title-hook" => Some("codex-title"),
        _ => name.strip_prefix("zellij-"),
    };
    if let Some(subcommand) = subcommand {
        args.insert(0, subcommand.to_owned());
    }
    if let Err(error) = run(&args) {
        eprintln!(
            "zellij-{}: {error:#}",
            args.first().map(String::as_str).unwrap_or("helper")
        );
        let interactive = match args.first().map(String::as_str) {
            Some("popup" | "shutdown") => true,
            Some("picker") => args.get(1).is_some_and(|arg| !arg.starts_with("--preview")),
            Some("notify") => args.get(1).is_some_and(|arg| arg == "history"),
            _ => false,
        };
        if interactive && std::io::stdin().is_terminal() {
            print!("Press Enter to close.");
            let _ = std::io::stdout().flush();
            let _ = std::io::stdin().read_line(&mut String::new());
        }
        std::process::exit(1);
    }
}
