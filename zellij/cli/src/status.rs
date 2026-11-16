use crate::{config, reload, view};
const HELP: &str = "Usage: zellij-helper status <view [SESSION] | config | reload [--session SESSION]>\n\nThe zellij-status compatibility command accepts view/config/reload directly.\nConfiguration defaults to $XDG_CONFIG_HOME/zellij/lane-status.toml.\nReload updates existing receiver clones only; it never starts a session or plugin.";

pub fn run(args: &[String]) -> Result<(), String> {
    match args {
        [help] if matches!(help.as_str(), "--help" | "-h") => println!("{HELP}"),
        [status, rest @ ..] if status == "status" => match rest {
            [help] if matches!(help.as_str(), "--help" | "-h") => println!("{HELP}"),
            [command, help]
                if matches!(command.as_str(), "view" | "config" | "reload")
                    && matches!(help.as_str(), "--help" | "-h") =>
            {
                println!("{HELP}")
            }
            [command, separator, session] if command == "view" && separator == "--" => println!(
                "{}",
                serde_json::to_string(&view::view(Some(session))).map_err(|e| e.to_string())?
            ),
            [command, session] if command == "refresh-view" => {
                crate::auto_title::refresh(session, None).map_err(|e| e.to_string())?;
                println!(
                    "{}",
                    serde_json::to_string(&view::view(Some(session))).map_err(|e| e.to_string())?
                );
            }
            [command] if command == "config" => println!(
                "{}",
                serde_json::to_string(&config::load()?).map_err(|e| e.to_string())?
            ),
            [command] if command == "view" => println!(
                "{}",
                serde_json::to_string(&view::view(None)).map_err(|e| e.to_string())?
            ),
            [command, session] if command == "view" => println!(
                "{}",
                serde_json::to_string(&view::view(Some(session))).map_err(|e| e.to_string())?
            ),
            [command, options @ ..] if command == "reload" => {
                let selected = match options {
                    [] => std::env::var("ZELLIJ_SESSION_NAME").ok(),
                    [flag, name] if flag == "--session" => Some(name.clone()),
                    [option] if option.starts_with("--session=") => Some(option[10..].to_owned()),
                    _ => return Err(HELP.into()),
                };
                println!("{}", reload::reload(selected.as_deref(), config::load()?)?);
            }
            _ => return Err(HELP.into()),
        },
        _ => return Err(HELP.into()),
    }
    Ok(())
}
