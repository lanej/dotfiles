use crate::{context::Session, ipc, titles, util::*};
use anyhow::{bail, Context, Result};
use base64::{engine::general_purpose::URL_SAFE, Engine};
use ipc::contract::{
    action::ActionType, Direction, GoToTabByIdAction, ListPanesAction, ListTabsAction,
    MoveTabByTabIdAction, SwitchSessionAction,
};
use serde_json::{json, Value};
use std::collections::{BTreeMap, BTreeSet};
use std::time::{Duration, Instant};
use std::{env, fs, path::PathBuf};

pub(crate) struct PickerSession(Session);

impl PickerSession {
    pub(crate) fn resolve(session: &str) -> Result<Self> {
        Ok(Self(Session::resolve(session)?))
    }

    fn client(&self, deadline: Instant) -> Result<ipc::Client<'_>> {
        self.0.validate(&self.0.session)?;
        let terminal_id = if env::var("ZELLIJ_SESSION_NAME").as_deref() == Ok(&self.0.session) {
            pane_id().ok().map(u32::try_from).transpose()?
        } else {
            None
        };
        Ok(ipc::Client {
            socket: self.0.socket()?,
            terminal_id,
            deadline,
        })
    }

    pub(crate) fn action(&self, action: ActionType, query: bool) -> Result<String> {
        self.action_until(action, query, Instant::now() + Duration::from_secs(5))
    }

    fn action_until(&self, action: ActionType, query: bool, deadline: Instant) -> Result<String> {
        ipc::output(self.client(deadline)?.request(action, query)?)
    }

    pub(crate) fn tabs(&self) -> Result<Vec<Value>> {
        self.tabs_until(Instant::now() + Duration::from_secs(5))
    }

    fn tabs_until(&self, deadline: Instant) -> Result<Vec<Value>> {
        Ok(serde_json::from_str(&self.action_until(
            ActionType::ListTabs(ListTabsAction {
                output_json: true,
                ..Default::default()
            }),
            true,
            deadline,
        )?)?)
    }

    pub(crate) fn panes(&self, all: bool) -> Result<Vec<Value>> {
        Ok(serde_json::from_str(&self.action(
            ActionType::ListPanes(ListPanesAction {
                output_json: true,
                show_all: all,
                ..Default::default()
            }),
            true,
        )?)?)
    }
}

fn pipe(session: &str, name: &str, payload: &Value, deadline: Instant) -> Result<String> {
    PickerSession::resolve(session)?
        .client(deadline)?
        .pipe(ipc::contract::CliPipeAction {
            name: Some(name.to_owned()),
            payload: Some(payload.to_string()),
            plugin: Some(PLUGIN.to_owned()),
            ..Default::default()
        })?
        .into_output()
}

fn status_pipe(session: &str, name: &str, payload: &Value) -> Result<String> {
    pipe(
        session,
        name,
        payload,
        Instant::now() + Duration::from_secs(5),
    )
}

pub fn display_tab(tab: &Value, panes: &[Value]) -> Result<String> {
    let id = number(tab, "tab_id")?;
    let name = text(tab, "name")?;
    let name = if legacy() || (!name.is_empty() && name != format!("Tab #{}", id + 1)) {
        name.to_owned()
    } else {
        panes
            .iter()
            .filter(|p| {
                p["tab_id"] == id
                    && !flag(p, "is_plugin")
                    && !flag(p, "is_floating")
                    && !flag(p, "is_suppressed")
                    && !flag(p, "exited")
            })
            .filter_map(|p| {
                Some((
                    p["id"].as_u64()?,
                    lane_zellij_protocol::titles::pane_label(p["title"].as_str()?)?,
                ))
            })
            .min_by_key(|(pane, _)| *pane)
            .map(|(_, name)| name)
            .unwrap_or(format!("Tab #{}", number(tab, "position")?))
    };
    Ok(name
        .chars()
        .map(|c| {
            if printable(c) || matches!(c, '' | '󰚩') {
                c
            } else {
                ' '
            }
        })
        .collect())
}
fn session_names() -> Result<Vec<String>> {
    let output = run(
        "zellij",
        &["list-sessions", "--no-formatting"],
        Instant::now() + Duration::from_secs(5),
    )?;
    let pattern =
        regex::Regex::new(r"^.+ ago\] (?:\(current\)|\(EXITED - attach to resurrect\))?$")?;
    let mut names = vec![];
    for line in output.lines() {
        let (name, meta) = line
            .rsplit_once(" [Created ")
            .context("Cannot parse session names; use the native session manager")?;
        if !pattern.is_match(meta) {
            bail!("Cannot parse session names; use the native session manager");
        }
        if !meta.ends_with("(EXITED - attach to resurrect)") {
            names.push(name.to_owned());
        }
    }
    Ok(names)
}
fn choose(rows: Vec<String>, heading: &str, preview: Option<&str>) -> Result<Option<String>> {
    let theme = env::var_os("DOTFILES_THEME_DIR")
        .map(PathBuf::from)
        .unwrap_or(root()?.join("design-system/generated"));
    let colors = fs::read_to_string(theme.join("fzf.txt"))
        .context("Cannot read picker theme; run make theme-generate")?;
    let mut args = vec![
        "--height=100%".into(),
        "--reverse".into(),
        "--no-multi".into(),
        "--delimiter=\t".into(),
        "--with-nth=2..".into(),
        format!("--header={heading}"),
        colors.trim().into(),
    ];
    if let Some(preview) = preview {
        args.push(format!(
            "--preview={} {} {{1}}",
            helper_command("picker")?,
            quote(preview)
        ));
        args.push(format!(
            "--preview-window={}",
            if preview == "--preview-tab" {
                "right:70%:border-left"
            } else {
                "right:60%"
            }
        ));
    }
    fzf(&args, rows.join("\n") + "\n")
}
fn replies(output: &str) -> Result<Vec<Value>> {
    let rows: Vec<Value> = output
        .lines()
        .filter(|l| !l.trim().is_empty())
        .map(serde_json::from_str)
        .collect::<std::result::Result<_, _>>()?;
    for row in &rows {
        if let Some(error) = row.get("error").and_then(Value::as_str) {
            bail!("{error}");
        }
    }
    Ok(rows)
}
pub fn client_choices(session: &str) -> Result<BTreeMap<u64, Value>> {
    let connection = PickerSession::resolve(session)?;
    let deadline = Instant::now() + Duration::from_secs(5);
    while Instant::now() < deadline {
        let attempt = (|| -> Result<Option<BTreeMap<u64, Value>>> {
            let rows = replies(&pipe(
                session,
                "lane-client-snapshot",
                &json!({"auto_titles":titles::owned_titles(session)}),
                deadline,
            )?)?;
            let tabs = connection.tabs_until(deadline)?;
            let mut attached = BTreeSet::new();
            for tab in tabs {
                for id in tab["other_focused_clients"]
                    .as_array()
                    .context("Missing client metadata")?
                {
                    attached.insert(id.as_u64().context("Invalid client ID")?);
                }
            }
            let mut choices = BTreeMap::new();
            for row in rows {
                let id = number(&row["token"], "client_id")?;
                if attached.contains(&id) {
                    choices.insert(id, row);
                }
            }
            Ok((!attached.is_empty()
                && choices.keys().copied().collect::<BTreeSet<_>>() == attached)
                .then_some(choices))
        })();
        match attempt {
            Ok(Some(rows)) => return Ok(rows),
            Err(error)
                if !error.to_string().contains("deadline") && !error.is::<serde_json::Error>() =>
            {
                return Err(error)
            }
            _ => {}
        }
        std::thread::sleep(Duration::from_millis(100));
    }
    bail!("Timed out waiting for all attached clients. Check lane-status permission prompts on each attached client, then reopen the chooser")
}
fn pick_client(session: &str) -> Result<()> {
    println!("Loading attached clients...");
    let choices = client_choices(session)?;
    let rows = choices
        .iter()
        .map(|(id, row)| {
            format!(
                "{id}\tClient {id} | {} | {}",
                label(row["tab"].as_str().unwrap_or("")),
                label(row["pane"].as_str().unwrap_or(""))
            )
        })
        .collect();
    if let Some(selected) = choose(rows, "Detach one client: Enter confirms; Esc cancels", None)? {
        let id: u64 = selected.parse()?;
        let row = choices.get(&id).context("Invalid client selection")?;
        let reply = status_pipe(session, "lane-client-detach", &row["token"])?;
        if reply.trim() != "detached" {
            bail!(
                "{}",
                if reply.trim().is_empty() {
                    "The selected attachment changed; reopen the client chooser"
                } else {
                    reply.trim()
                }
            );
        }
    }
    Ok(())
}
fn pick_tab(session: &str) -> Result<()> {
    let connection = PickerSession::resolve(session)?;
    let mut tabs = connection.tabs()?;
    let panes = connection.panes(false)?;
    let own = pane_id().ok();
    let source = panes
        .iter()
        .find(|p| !flag(p, "is_plugin") && p["id"].as_u64() == own)
        .map(|p| p["tab_id"].clone());
    tabs.sort_by_key(|tab| {
        let priority = match tab["attention"]["status"].as_str() {
            Some("NeedsYou" | "Failed") => 0,
            Some("Done") => 1,
            Some("Working") => 2,
            _ if flag(tab, "has_bell_notification") => 0,
            _ => 3,
        };
        (priority, tab["position"].as_u64().unwrap_or(u64::MAX))
    });
    let rows = tabs
        .iter()
        .map(|tab| {
            Ok(format!(
                "{}\t{}: {}{}{}",
                number(tab, "tab_id")?,
                number(tab, "position")? + u64::from(legacy()),
                display_tab(tab, &panes)?,
                if Some(&tab["tab_id"]) == source.as_ref() {
                    " [current]"
                } else {
                    ""
                },
                if flag(tab, "has_bell_notification") {
                    " [bell]"
                } else {
                    ""
                }
            ))
        })
        .collect::<Result<_>>()?;
    if let Some(token) = choose(rows, "Tabs (attention first)", Some("--preview-tab"))? {
        let id: u64 = token.parse()?;
        if !tabs.iter().any(|t| t["tab_id"] == id)
            || !connection.tabs()?.iter().any(|t| t["tab_id"] == id)
        {
            bail!("The selected tab no longer exists");
        }
        connection.action(ActionType::GoToTabById(GoToTabByIdAction { id }), false)?;
    }
    Ok(())
}
fn swap_order(mut tabs: Vec<Value>) -> Result<Vec<u64>> {
    tabs.sort_by_key(|t| t["position"].as_u64());
    let mut seen = BTreeSet::new();
    let mut order = vec![];
    for (index, tab) in tabs.iter().enumerate() {
        let id = number(tab, "tab_id")?;
        if !seen.insert(id) || number(tab, "position")? != index as u64 {
            bail!("Tab positions are inconsistent; reopen the swap picker");
        }
        order.push(id);
    }
    Ok(order)
}
struct Swap<'a> {
    session: &'a str,
    source: u64,
    tab: u64,
    picker: u64,
    token: Value,
    connection: PickerSession,
}
impl Swap<'_> {
    fn check(&self, order: &[u64]) -> Result<()> {
        let rows = replies(&status_pipe(
            self.session,
            "lane-client-snapshot",
            &json!({"auto_titles":titles::owned_titles(self.session),"token":self.token}),
        )?)?;
        if rows.len() != 1 || rows[0]["token"] != self.token {
            bail!("The captured attachment snapshot was not confirmed");
        }
        if rows[0]["pane_id"] != format!("terminal_{}", self.picker) {
            bail!("Picker lost its requesting client");
        }
        let panes = self.connection.panes(false)?;
        for id in [self.source, self.picker] {
            if !panes.iter().any(|p| {
                !flag(p, "is_plugin")
                    && p["id"] == id
                    && p["tab_id"] == self.tab
                    && !flag(p, "is_suppressed")
            }) {
                bail!("The original pane or picker changed tabs or closed");
            }
        }
        if swap_order(self.connection.tabs()?)? != order {
            bail!("Tab order or membership changed");
        }
        Ok(())
    }
}
fn owner_token(session: &str, picker: u64) -> Result<Value> {
    let owners: Vec<_> = client_choices(session)?
        .into_values()
        .filter(|row| row["pane_id"] == format!("terminal_{picker}"))
        .collect();
    if owners.len() != 1 {
        bail!("Cannot identify the picker's attached client");
    }
    Ok(owners[0]["token"].clone())
}
fn swap_tab(session: &str) -> Result<()> {
    if legacy() {
        bail!("Tab swap needs the status plugin and pinned runtime; run make zellij-status zellij and restart this session");
    }
    let connection = PickerSession::resolve(session)?;
    let source = origin_id()?;
    let picker = pane_id()?;
    let panes = connection.panes(false)?;
    let pane = panes
        .iter()
        .find(|p| !flag(p, "is_plugin") && p["id"] == source)
        .context("The original pane closed; reopen the swap picker")?;
    let swap = Swap {
        session,
        source,
        tab: number(pane, "tab_id")?,
        picker,
        token: owner_token(session, picker)?,
        connection,
    };
    let mut tabs = swap.connection.tabs()?;
    let mut order = swap_order(tabs.clone())?;
    swap.check(&order)?;
    tabs.sort_by_key(|t| t["position"].as_u64());
    let rows = tabs
        .iter()
        .map(|t| {
            Ok(format!(
                "{}\t{}: {}{}",
                number(t, "tab_id")?,
                number(t, "position")?,
                display_tab(t, &panes)?,
                if t["tab_id"] == swap.tab {
                    " [current]"
                } else {
                    ""
                }
            ))
        })
        .collect::<Result<_>>()?;
    let Some(selected) = choose(rows, "Swap tab positions", Some("--preview-tab"))? else {
        return Ok(());
    };
    let destination: u64 = selected.parse()?;
    let a = order
        .iter()
        .position(|id| *id == swap.tab)
        .context("Missing source")?;
    let b = order
        .iter()
        .position(|id| *id == destination)
        .context("Invalid swap destination")?;
    swap.check(&order)?;
    if a == b {
        return Ok(());
    }
    let step = if a < b { 1isize } else { -1 };
    let distance = a.abs_diff(b);
    let mut final_order = order.clone();
    final_order.swap(a, b);
    let mut attempted = false;
    let result = (|| -> Result<()> {
        for (id, delta, count) in [
            (swap.tab, step, distance),
            (destination, -step, distance - 1),
        ] {
            for _ in 0..count {
                swap.check(&order)?;
                let index = order
                    .iter()
                    .position(|v| *v == id)
                    .context("Missing moving tab")?;
                let neighbor = index
                    .checked_add_signed(delta)
                    .filter(|n| *n < order.len())
                    .context("Refusing a wrapping tab move")?;
                let mut expected = order.clone();
                expected.swap(index, neighbor);
                attempted = true;
                let command = swap.connection.action(
                    ActionType::MoveTabByTabId(MoveTabByTabIdAction {
                        id,
                        direction: if delta > 0 {
                            Direction::Right
                        } else {
                            Direction::Left
                        } as i32,
                    }),
                    false,
                );
                let inspection = swap.check(&expected);
                if let Err(error) = command {
                    bail!(
                        "Move command: {error}; inspection: {}",
                        inspection
                            .map(|_| "order observed".to_owned())
                            .unwrap_or_else(|e| e.to_string())
                    );
                }
                inspection?;
                order = expected;
            }
        }
        if order != final_order {
            bail!("Endpoint swap was not confirmed");
        }
        Ok(())
    })();
    if attempted {
        result.context("Tab swap stopped; tabs may be partially reordered. Inspect their positions before retrying. No rollback was attempted.")
    } else {
        result
    }
}
struct IgnoreInterrupt(libc::sighandler_t);
impl IgnoreInterrupt {
    fn new() -> Self {
        Self(unsafe { libc::signal(libc::SIGINT, libc::SIG_IGN) })
    }
}
impl Drop for IgnoreInterrupt {
    fn drop(&mut self) {
        unsafe {
            libc::signal(libc::SIGINT, self.0);
        }
    }
}
fn gather_panes(session: &str, request: &mut Value) -> Result<String> {
    request["operation"] = json!(nonce()?);
    request["expires"] = json!(now_ms() + 15000);
    let _signal = IgnoreInterrupt::new();
    let _ = status_pipe(session, "lane-move-pane", request);
    println!(
        "Confirming pane transfer has stopped. Keep this pane open; cancellation is deferred."
    );
    loop {
        if let Ok(output) = status_pipe(session, "lane-move-status", request) {
            if let Ok(stopped) = serde_json::from_str::<Value>(&output) {
                if stopped["stopped"] == true {
                    return Ok(text(&stopped, "result")?.to_owned());
                }
            }
        }
        std::thread::sleep(Duration::from_millis(250));
    }
}
fn move_pane(session: &str, all: bool) -> Result<()> {
    if legacy() {
        bail!("The move picker needs the status plugin and pinned runtime; run make zellij-status zellij and restart this session");
    }
    let connection = PickerSession::resolve(session)?;
    let source = origin_id()?;
    let picker = pane_id()?;
    let panes = connection.panes(false)?;
    let source_pane = panes
        .iter()
        .find(|p| !flag(p, "is_plugin") && p["id"] == source)
        .context("The original pane changed; reopen the move picker")?;
    let tab = number(source_pane, "tab_id")?;
    if !panes
        .iter()
        .any(|p| !flag(p, "is_plugin") && p["id"] == picker && p["tab_id"] == tab)
    {
        bail!("The original pane changed; reopen the move picker");
    }
    let token = owner_token(session, picker)?;
    let mut tabs = connection.tabs()?;
    tabs.sort_by_key(|t| t["position"].as_u64());
    let mut rows = if all {
        vec![]
    } else {
        vec!["new\tNew Tab".into()]
    };
    for t in &tabs {
        rows.push(format!(
            "{}\t{}: {}{}",
            number(t, "tab_id")?,
            number(t, "position")?,
            display_tab(t, &panes)?,
            if t["tab_id"] == tab { " [current]" } else { "" }
        ));
    }
    let Some(selected) = choose(
        rows,
        if all {
            "Move all panes to tab"
        } else {
            "Move pane to tab"
        },
        Some("--preview-move"),
    )?
    else {
        return Ok(());
    };
    if selected == tab.to_string() {
        return Ok(());
    }
    let destination = if selected == "new" && !all {
        None
    } else {
        Some(selected.parse::<u64>()?)
    };
    if let Some(id) = destination {
        if !tabs.iter().any(|t| t["tab_id"] == id)
            || !connection.tabs()?.iter().any(|t| t["tab_id"] == id)
        {
            bail!("The destination tab closed; reopen the move picker");
        }
    }
    let current = connection.panes(all)?;
    if !current.iter().any(|p| {
        !flag(p, "is_plugin")
            && p["id"] == source
            && p["tab_id"] == tab
            && !flag(p, "is_suppressed")
            && !flag(p, "exited")
    }) {
        bail!("The original pane changed; reopen the move picker");
    }
    let mut request = json!({"token":token,"source":source,"source_tab":tab,"picker":picker,"destination":destination});
    let reply = if all {
        let mut sources: Vec<_> = current.iter().filter(|p| p["tab_id"] == tab).collect();
        if sources
            .iter()
            .any(|p| !flag(p, "is_plugin") && flag(p, "is_suppressed"))
        {
            bail!(
                "Restore suppressed terminals or close scrollback editors before moving all panes"
            );
        }
        if !sources
            .iter()
            .any(|p| !flag(p, "is_plugin") && p["id"] == picker)
        {
            bail!("The picker changed; reopen it");
        }
        sources.sort_by_key(|p| (!flag(p, "is_floating"), p["id"].as_u64()));
        let ids: Vec<u64> = sources
            .iter()
            .filter(|p| {
                !flag(p, "is_plugin")
                    && p["id"] != picker
                    && flag(p, "is_selectable")
                    && !flag(p, "exited")
            })
            .map(|p| number(p, "id"))
            .collect::<Result<_>>()?;
        if !ids.contains(&source) {
            bail!("The original pane changed; reopen the move picker");
        }
        request["sources"] = json!(ids);
        let result = gather_panes(session, &mut request)?;
        let _ = status_pipe(session, "lane-move-ack", &request);
        result
    } else {
        status_pipe(session, "lane-move-pane", &request)?
            .trim()
            .to_owned()
    };
    if reply != "moved" {
        bail!(
            "{}",
            if reply.is_empty() {
                "Pane transfer was not confirmed; inspect both tabs before retrying"
            } else {
                &reply
            }
        );
    }
    Ok(())
}
fn pick_session(session: &str) -> Result<()> {
    let choices: Vec<_> = session_names()?
        .into_iter()
        .map(|name| (URL_SAFE.encode(&name), name))
        .collect();
    let rows = choices
        .iter()
        .map(|(token, name)| {
            format!(
                "{token}\t{}{}",
                label(name),
                if name == session { " [current]" } else { "" }
            )
        })
        .collect();
    if let Some(token) = choose(rows, "Running sessions", Some("--preview-session"))? {
        let target = &choices
            .iter()
            .find(|(key, _)| key == &token)
            .context("Invalid session selection")?
            .1;
        if !session_names()?.contains(target) {
            bail!("The selected session is no longer running");
        }
        if target != session {
            let connection = PickerSession::resolve(session)?;
            let response = connection
                .client(Instant::now() + Duration::from_secs(5))?
                .request(
                    ActionType::SwitchSession(SwitchSessionAction {
                        name: target.to_owned(),
                        ..Default::default()
                    }),
                    false,
                )?;
            // rationale: The pinned runtime disconnects this CLI connection when switching sessions.
            // Keep other exit reasons visible instead of treating an arbitrary disconnect as success.
            if !matches!(&response.message, Some(ipc::contract::server_to_client_msg::Message::Exit(exit))
                if exit.exit_reason == ipc::contract::ExitReason::Disconnect as i32)
            {
                ipc::output(response)?;
            }
        }
    }
    Ok(())
}
pub fn preview_session(session: &str) -> Result<()> {
    let connection = PickerSession::resolve(session)?;
    let mut tabs = connection.tabs()?;
    let panes = connection.panes(false)?;
    tabs.sort_by_key(|t| t["position"].as_u64());
    for tab in tabs {
        println!(
            "{} {}: {}",
            if flag(&tab, "active") { "*" } else { " " },
            number(&tab, "position")? + u64::from(legacy()),
            display_tab(&tab, &panes)?
        );
    }
    Ok(())
}
pub fn main(args: &[String]) -> Result<()> {
    let session = session()?;
    match args {
        [mode]=>match mode.as_str(){"tabs"=>pick_tab(&session),"sessions"=>pick_session(&session),"clients"=>pick_client(&session),"swap-tab"=>swap_tab(&session),"move-pane"=>move_pane(&session,false),"move-all-panes"=>move_pane(&session,true),"client-snapshot"=>{println!("{}",serde_json::to_string(&client_choices(&session)?)?);Ok(())},_=>bail!("Unknown picker mode")},
        [mode,id] if mode=="--preview-move"&&id=="new"=>{println!("Move the original live pane to a new tab.");Ok(())},
        [mode,id] if matches!(mode.as_str(),"--preview-tab"|"--preview-move")=>crate::preview::tab(&session,id.parse()?),
        [mode,token] if mode=="--preview-session"=>preview_session(&String::from_utf8(URL_SAFE.decode(token)?)?),
        _=>bail!("Usage: zellij-picker tabs|swap-tab|move-pane|move-all-panes|sessions|clients (inside Zellij)"),
    }
}
