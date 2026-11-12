use crate::{context::Session, util::*};
use anyhow::{bail, Context, Result};
use serde_json::{json, Value};
use std::env;
use std::os::unix::fs::PermissionsExt;
use std::os::unix::process::CommandExt;
use std::path::PathBuf;
use std::process::Command;

const HELP: &str = "\
Usage: zellij-context inspect [--session NAME] [--json]
       zellij-pane open [--session NAME] [--tab ID] [--name TITLE] [--cwd DIR] -- COMMAND [ARG...]
       zellij-pane image [--session NAME] [--tab ID] [--name TITLE] [--cwd DIR] IMAGE
       zellij-pane capture [--session NAME] --pane ID [--ansi] [--full]

Session defaults to verified ZELLIJ_SESSION_NAME. Tab defaults to the verified
calling pane's tab; outside that context, pass --tab. Open/image preserve focus
and leave an interactive shell after the command. They print the new pane ID.
Image uses installed kitten icat or kitty +kitten icat; it installs nothing.
Capture prints pane text, optionally styled or including scrollback, not pixels.";

#[derive(Default)]
struct Options {
    session: Option<String>,
    tab: Option<u64>,
    pane: Option<u64>,
    name: Option<String>,
    cwd: Option<PathBuf>,
    json: bool,
    ansi: bool,
    full: bool,
    command: Vec<String>,
}

fn terminal_id(value: &str) -> Result<u64> {
    value
        .strip_prefix("terminal_")
        .unwrap_or(value)
        .parse()
        .context("Pane ID must be terminal_N or a terminal number")
}

fn options(operation: &str, args: &[String]) -> Result<Options> {
    let mut options = Options::default();
    let mut rest = args.iter();
    while let Some(arg) = rest.next() {
        if arg == "--" {
            options.command.extend(rest.cloned());
            break;
        }
        let creates = matches!(operation, "open" | "image");
        match arg.as_str() {
            "--session" => {
                options.session = Some(rest.next().context("--session needs a name")?.clone())
            }
            "--tab" if creates => {
                options.tab = Some(rest.next().context("--tab needs an ID")?.parse()?)
            }
            "--name" if creates => {
                options.name = Some(rest.next().context("--name needs a title")?.clone())
            }
            "--cwd" if creates => {
                options.cwd = Some(rest.next().context("--cwd needs a directory")?.into())
            }
            "--pane" if operation == "capture" => {
                options.pane = Some(terminal_id(rest.next().context("--pane needs an ID")?)?)
            }
            "--json" if operation == "inspect" => options.json = true,
            "--ansi" if operation == "capture" => options.ansi = true,
            "--full" if operation == "capture" => options.full = true,
            _ if operation == "image" && !arg.starts_with('-') => options.command.push(arg.clone()),
            _ => bail!("Unexpected argument {arg:?}\n{HELP}"),
        }
    }
    if matches!(operation, "inspect" | "capture") && !options.command.is_empty() {
        bail!("Unexpected command arguments\n{HELP}");
    }
    if options.session.as_deref() == Some("") {
        bail!("Session name must not be empty");
    }
    Ok(options)
}

fn selected(options: &Options) -> Option<String> {
    options.session.clone().or_else(|| session().ok())
}

fn query(session: &Session, kind: &str) -> Result<Vec<Value>> {
    session.validate(&session.session)?;
    let result: Vec<Value> = serde_json::from_str(&native(
        &session.session,
        &["action", &format!("list-{kind}"), "--all", "--json"],
    )?)?;
    session.validate(&session.session)?;
    Ok(result)
}

fn terminal(panes: &[Value], id: u64) -> Result<&Value> {
    panes
        .iter()
        .find(|pane| pane["id"] == id && pane["is_plugin"] == false)
        .context("The terminal pane no longer exists in the selected session")
}

fn caller(session: &str, panes: &[Value]) -> Option<(u64, u64)> {
    if env::var("ZELLIJ_SESSION_NAME").as_deref() != Ok(session) {
        return None;
    }
    let id = terminal_id(&env::var("ZELLIJ_PANE_ID").ok()?).ok()?;
    let pane = terminal(panes, id).ok()?;
    (!flag(pane, "exited") && !flag(pane, "is_suppressed"))
        .then_some((id, pane["tab_id"].as_u64()?))
}

pub fn inspect(args: &[String]) -> Result<()> {
    if matches!(args, [arg] if matches!(arg.as_str(), "--help" | "-h")) {
        println!("{HELP}");
        return Ok(());
    }
    let options = options("inspect", args)?;
    let selected = selected(&options);
    let observation = (|| -> Result<Value> {
        let Some(name) = &selected else {
            let sessions = run(
                "zellij",
                &["list-sessions", "--no-formatting"],
                std::time::Instant::now() + std::time::Duration::from_secs(5),
            )?;
            return Ok(json!({
                "status": "selection_required",
                "sessions_text": sessions,
                "detail": "Choose a session from task context and pass --session; socket access may restrict discovery."
            }));
        };
        let session = Session::resolve(name)?;
        let panes = query(&session, "panes")?;
        let tabs = query(&session, "tabs")?;
        let clients = native(name, &["action", "list-clients"])?;
        session.validate(name)?;
        let caller = caller(name, &panes);
        Ok(json!({
            "status": "available",
            "session": name,
            "caller_pane": caller.map(|(id, _)| format!("terminal_{id}")),
            "caller_tab": caller.map(|(_, tab)| tab),
            "panes": panes,
            "tabs": tabs,
            "clients_text": clients
        }))
    })();
    let value = match observation {
        Ok(value) => value,
        Err(error) => {
            if options.json {
                println!(
                    "{}",
                    json!({"status": "unavailable", "session": selected, "error": error.to_string()})
                );
            }
            return Err(error.context(
                "Context unavailable; restricted socket access does not prove the session exited",
            ));
        }
    };
    if options.json {
        println!("{}", serde_json::to_string_pretty(&value)?);
    } else if value["status"] == "selection_required" {
        print!("{}", value["sessions_text"].as_str().unwrap_or(""));
        println!("{}", value["detail"].as_str().unwrap_or(""));
    } else {
        println!(
            "Session: {}",
            clean(value["session"].as_str().unwrap_or(""), 100)
        );
        if let Some(id) = value["caller_pane"].as_str() {
            println!("Caller: {id}, tab {}", value["caller_tab"]);
        } else {
            println!("Caller: unavailable; pass --tab when opening a view");
        }
        for pane in value["panes"].as_array().context("Invalid pane list")? {
            if pane["is_plugin"] == false && !flag(pane, "is_suppressed") {
                println!(
                    "terminal_{}  tab {}  {}{}",
                    number(pane, "id")?,
                    number(pane, "tab_id")?,
                    clean(pane["title"].as_str().unwrap_or(""), 80),
                    if flag(pane, "exited") {
                        " [exited]"
                    } else {
                        ""
                    }
                );
            }
        }
        print!("{}", value["clients_text"].as_str().unwrap_or(""));
    }
    Ok(())
}

fn target(options: &Options) -> Result<(Session, u64)> {
    let name = selected(options).context("Pass --session outside a verified Zellij context")?;
    let session = Session::resolve(&name)?;
    let panes = query(&session, "panes")?;
    let tab = options
        .tab
        .or_else(|| caller(&name, &panes).map(|(_, tab)| tab))
        .context("Pass --tab: the calling pane's tab could not be verified")?;
    if !query(&session, "tabs")?
        .iter()
        .any(|candidate| candidate["tab_id"] == tab)
    {
        bail!("The selected tab no longer exists");
    }
    Ok((session, tab))
}

fn capture(options: &Options) -> Result<()> {
    let name = selected(options).context("Pass --session outside a verified Zellij context")?;
    let id = options.pane.context("Capture requires --pane")?;
    let session = Session::resolve(&name)?;
    let before = query(&session, "panes")?;
    let before = terminal(&before, id)?;
    let identity = json!([
        before["tab_id"],
        before["terminal_command"],
        before["pane_cwd"]
    ]);
    let pane_id = format!("terminal_{id}");
    let mut command = vec!["action", "dump-screen", "--pane-id", &pane_id];
    if options.ansi {
        command.push("--ansi");
    }
    if options.full {
        command.push("--full");
    }
    let output = native(&name, &command)?;
    let after = query(&session, "panes")?;
    let after = terminal(&after, id)?;
    if identity
        != json!([
            after["tab_id"],
            after["terminal_command"],
            after["pane_cwd"]
        ])
    {
        bail!("Pane context changed during capture; refresh before using its contents");
    }
    print!("{output}");
    Ok(())
}

fn image_command(options: &Options) -> Result<Vec<String>> {
    let [image] = options.command.as_slice() else {
        bail!("Image requires one local image path\n{HELP}");
    };
    let cwd = options.cwd.clone().unwrap_or(env::current_dir()?);
    let image = cwd
        .join(image)
        .canonicalize()
        .context("Cannot read image path")?;
    if !image.is_file() {
        bail!("Image path must be a file");
    }
    let viewer = ["kitten", "kitty"].into_iter().find_map(|program| {
        env::split_paths(&env::var_os("PATH").unwrap_or_default()).find_map(|directory| {
            let path = directory.join(program);
            std::fs::metadata(&path)
                .is_ok_and(|metadata| {
                    metadata.is_file() && metadata.permissions().mode() & 0o111 != 0
                })
                .then_some((program, path))
        })
    });
    let (program, viewer) = viewer.context(
        "Image viewer unavailable: install kitten or kitty through the normal tool setup",
    )?;
    // rationale: A new pane inherits the server's PATH, which can differ from the caller's.
    let viewer = viewer
        .canonicalize()
        .context("Cannot resolve image viewer")?;
    let mut command = vec![viewer
        .to_str()
        .context("Viewer path must be UTF-8")?
        .to_owned()];
    if program == "kitty" {
        command.push("+kitten".into());
    }
    command.push("icat".into());
    command.extend([
        "--stdin=no".into(),
        "--transfer-mode=stream".into(),
        "--detection-timeout=3".into(),
        "--fit=both".into(),
        image
            .to_str()
            .context("Image path must be UTF-8")?
            .to_owned(),
    ]);
    Ok(command)
}

fn open(options: &Options, command: &[String]) -> Result<()> {
    if command.is_empty() || command[0].is_empty() {
        bail!("Open requires a command after --\n{HELP}");
    }
    let cwd = options.cwd.clone().unwrap_or(env::current_dir()?);
    let cwd = cwd
        .canonicalize()
        .context("Cannot resolve working directory")?;
    if !cwd.is_dir() {
        bail!("Working directory must be a directory");
    }
    let (session, tab) = target(options)?;
    let tab = tab.to_string();
    let executable = executable()?;
    let name = options.name.as_deref().unwrap_or("Shared view");
    let cwd = cwd.to_str().context("Working directory must be UTF-8")?;
    let executable = executable.to_str().context("Helper path must be UTF-8")?;
    let mut args = vec![
        "action",
        "new-pane",
        "--tab-id",
        &tab,
        "--no-focus",
        "--name",
        name,
        "--cwd",
        cwd,
        "--",
        executable,
        "pane",
        "_run",
        "--",
    ];
    args.extend(command.iter().map(String::as_str));
    session.validate(&session.session)?;
    let result = native(&session.session, &args)
        .context("Pane creation was not confirmed; inspect context before retrying")?;
    let id = terminal_id(result.trim())
        .context("Pane creation returned no valid ID; inspect context before retrying")?;
    let panes = query(&session, "panes")
        .context("Created pane could not be verified; inspect context before retrying")?;
    let created = terminal(&panes, id)?;
    if created["tab_id"].as_u64() != Some(tab.parse()?) {
        bail!("Created pane moved before confirmation; inspect context before retrying");
    }
    println!("terminal_{id}");
    Ok(())
}

pub fn main(args: &[String]) -> Result<()> {
    let Some((operation, args)) = args.split_first() else {
        bail!("{HELP}");
    };
    if matches!(operation.as_str(), "--help" | "-h") {
        println!("{HELP}");
        return Ok(());
    }
    if operation == "_run" {
        let Some(command) = args.strip_prefix(&["--".to_owned()]) else {
            bail!("Internal view runner requires -- COMMAND");
        };
        if command.is_empty() {
            bail!("Internal view runner requires a command");
        }
        // rationale: Catch SIGINT in the parent shell while positional arguments preserve literal argv.
        let error = Command::new("/bin/sh")
            .args([
                "-ic",
                "trap : INT; \"$@\"; result=$?; printf '\\nCommand exit status: %s\\n' \"$result\"; exec /bin/sh -i",
                "zellij-pane",
            ])
            .args(command)
            .exec();
        return Err(error).context("Cannot start persistent view shell");
    }
    if !matches!(operation.as_str(), "open" | "capture" | "image") {
        bail!("{HELP}");
    }
    if matches!(args, [arg] if matches!(arg.as_str(), "--help" | "-h")) {
        println!("{HELP}");
        return Ok(());
    }
    let options = options(operation, args)?;
    match operation.as_str() {
        "capture" => capture(&options),
        "open" => open(&options, &options.command),
        "image" => open(&options, &image_command(&options)?),
        _ => unreachable!(),
    }
}
