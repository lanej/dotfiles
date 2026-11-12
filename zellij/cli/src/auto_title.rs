use crate::{ipc, titles, util::*};
use anyhow::{Context, Result};
use ipc::contract::{action::ActionType, ListPanesAction, ListTabsAction, RenameTabByIdAction};
use lane_zellij_protocol::titles::{glyphs::BRANCH, pane_label};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::collections::{BTreeMap, BTreeSet};
use std::env;
use std::path::PathBuf;
use std::time::{Duration, Instant};

#[derive(Debug, Default, PartialEq, Eq)]
struct Tab {
    name: String,
    // Zellij allocates terminal IDs monotonically. Include hidden live providers,
    // but only an eligible tiled pane can offer a new name.
    panes: BTreeMap<u64, Option<String>>,
}

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
struct Record {
    identity: Value,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    persistent_identity: Option<Value>,
    title: String,
    #[serde(default)]
    providers: BTreeSet<u64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pending_from: Option<String>,
}

fn previous_record(
    record: Record,
    identity: &Value,
    persistent_identity: &Value,
    name: &str,
) -> Record {
    if record.identity == *identity {
        return record;
    }
    if record.persistent_identity.as_ref() == Some(persistent_identity) && record.title == name {
        // rationale: Restored pane IDs cannot retain a previous server's title providers.
        return Record {
            identity: identity.clone(),
            persistent_identity: Some(persistent_identity.clone()),
            title: name.to_owned(),
            ..Record::default()
        };
    }
    Record::default()
}

enum Update {
    Automatic,
    ClearPane(u64),
    ClearAll,
}

fn choose(tab: &Tab, previous: &Record, fallback: &str) -> (String, BTreeSet<u64>) {
    // Records from the bracket-style shell hook contain a title but no provider IDs.
    // Only a proven automatic record may migrate a literal bracket suffix.
    if previous.providers.is_empty() {
        if let Some((project, branch)) = previous
            .title
            .strip_suffix(']')
            .and_then(|s| s.rsplit_once(" ["))
        {
            let title = format!("{project} {BRANCH} {branch}");
            let providers: BTreeSet<_> = tab
                .panes
                .iter()
                .filter_map(|(id, name)| {
                    let name = name.as_deref()?;
                    (name == previous.title || name == title).then_some(*id)
                })
                .collect();
            if !providers.is_empty() {
                return (title, providers);
            }
        }
    }
    let still_owned = !previous.title.is_empty()
        && tab.panes.iter().any(|(id, name)| {
            previous.providers.contains(id) || name.as_deref() == Some(previous.title.as_str())
        });
    let title = if still_owned {
        previous.title.as_str()
    } else {
        tab.panes
            .values()
            .find_map(Option::as_deref)
            .unwrap_or(fallback)
    };
    let providers = tab
        .panes
        .iter()
        .filter_map(|(id, name)| {
            (name.as_deref() == Some(title) || (still_owned && previous.providers.contains(id)))
                .then_some(*id)
        })
        .collect();
    (title.to_owned(), providers)
}

/// Resolve once when the shell installs its hooks; subsequent prompts reuse this context.
pub fn context() -> Result<String> {
    Ok(serde_json::to_string(&crate::context::Session::resolve(
        &session()?,
    )?)?)
}

fn snapshot(client: &ipc::Client<'_>, offer: Option<(u64, &str)>) -> Result<BTreeMap<u64, Tab>> {
    let native_tabs: Vec<Value> = serde_json::from_str(&ipc::output(client.request(
        ActionType::ListTabs(ListTabsAction {
            output_json: true,
            ..Default::default()
        }),
        true,
    )?)?)?;
    let panes: Vec<Value> = serde_json::from_str(&ipc::output(client.request(
        ActionType::ListPanes(ListPanesAction {
            output_json: true,
            ..Default::default()
        }),
        true,
    )?)?)?;
    let mut tabs = BTreeMap::new();
    for p in panes {
        let tab = tabs.entry(number(&p, "tab_id")?).or_insert_with(|| Tab {
            name: p["tab_name"].as_str().unwrap_or_default().to_owned(),
            ..Tab::default()
        });
        if flag(&p, "is_plugin") || flag(&p, "exited") {
            continue;
        }
        let id = number(&p, "id")?;
        let name = if flag(&p, "is_floating") || flag(&p, "is_suppressed") {
            None
        } else {
            pane_label(p["title"].as_str().unwrap_or_default()).or_else(|| {
                offer
                    .filter(|(owner, _)| *owner == id && flag(&p, "is_focused"))
                    .map(|(_, title)| title.to_owned())
            })
        };
        tab.panes.insert(id, name);
    }
    anyhow::ensure!(
        native_tabs.len() == tabs.len()
            && native_tabs.iter().all(|tab| {
                tab["tab_id"]
                    .as_u64()
                    .and_then(|id| tabs.get(&id))
                    .is_some_and(|panes| tab["name"].as_str() == Some(panes.name.as_str()))
            }),
        "Tabs are still loading or changed while reading their panes"
    );
    Ok(tabs)
}

pub fn refresh(session: &str, offer: Option<(u64, &str)>) -> Result<()> {
    update(session, offer, Update::Automatic)
}

fn update(session: &str, offer: Option<(u64, &str)>, update: Update) -> Result<()> {
    let deadline = Instant::now() + Duration::from_secs(2);
    let context = match (&update, env::var("ZELLIJ_TITLE_CONTEXT")) {
        (Update::Automatic, Ok(value)) => serde_json::from_str::<crate::context::Session>(&value)?,
        _ => crate::context::Session::resolve(session)?,
    };
    context.validate(session)?;
    let identity = context.identity.clone();
    let persistent_identity = context.persistent_identity()?;
    let client = ipc::Client {
        socket: context.socket()?,
        terminal_id: match update {
            Update::ClearPane(pane) => Some(pane.try_into()?),
            _ => offer.map(|(pane, _)| pane.try_into()).transpose()?,
        },
        deadline,
    };
    let dir = state("zellij-auto-titles")?;
    private_dir(&dir)?;
    let key = titles::session_key(session);
    let _lock = Lock::acquire(&dir.join(format!("{key}.lock")), deadline)?;
    let tabs = snapshot(&client, offer)?;
    let clear_tab = if let Update::ClearPane(pane) = update {
        Some(
            *tabs
                .iter()
                .find(|(_, tab)| tab.panes.contains_key(&pane))
                .context("Cannot find the caller's pane in this session")?
                .0,
        )
    } else {
        None
    };
    let mut restored = BTreeMap::<String, Record>::new();
    let mut obsolete = Vec::new();
    for entry in std::fs::read_dir(&dir)? {
        let entry = entry?;
        let filename = entry.file_name();
        let Some(tab_id) = filename
            .to_str()
            .and_then(|name| name.strip_prefix(&format!("{key}-")))
            .and_then(|name| name.strip_suffix(".json"))
        else {
            continue;
        };
        if tab_id.is_empty() || !tab_id.bytes().all(|byte| byte.is_ascii_digit()) {
            continue;
        }
        if let Ok(record) = serde_json::from_slice::<Record>(&std::fs::read(entry.path())?) {
            if record.identity != identity
                && record.persistent_identity.as_ref() == Some(&persistent_identity)
            {
                obsolete.push(entry.path());
                restored.insert(record.title.clone(), record);
            }
        }
    }
    let mut names = BTreeMap::<String, usize>::new();
    for tab in tabs.values() {
        *names.entry(tab.name.clone()).or_default() += 1;
    }
    for (id, tab) in tabs {
        // New tabs start as "Tab #N". An empty native name is the editable
        // field cleared by Ctrl-f r, which another client may be typing into.
        if tab.name.is_empty() {
            continue;
        }
        let path = dir.join(format!("{key}-{id}.json"));
        let previous = match std::fs::read(&path) {
            Ok(bytes) => serde_json::from_slice::<Record>(&bytes)
                .ok()
                .filter(|record| record.identity == identity),
            Err(err) if err.kind() == std::io::ErrorKind::NotFound => None,
            Err(err) => return Err(err.into()),
        }
        .or_else(|| {
            (names.get(&tab.name) == Some(&1))
                .then(|| restored.get(&tab.name).cloned())
                .flatten()
                .map(|record| previous_record(record, &identity, &persistent_identity, &tab.name))
        })
        .unwrap_or_default();
        let fallback = format!("Tab #{}", id + 1);
        let managed =
            tab.name == previous.title || previous.pending_from.as_ref() == Some(&tab.name);
        let clear = matches!(update, Update::ClearAll) || clear_tab == Some(id);
        if !managed && !clear && tab.name != fallback {
            continue;
        }
        let empty = Record::default();
        let (title, providers) = choose(&tab, if managed { &previous } else { &empty }, &fallback);
        let mut record = Record {
            identity: identity.clone(),
            persistent_identity: Some(persistent_identity.clone()),
            title,
            providers,
            pending_from: None,
        };
        if (record == previous && tab.name == record.title)
            || (record.providers.is_empty() && tab.name == fallback && !path.exists())
        {
            continue;
        }
        // A manual rename, pane move or server replacement wins over a stale observation.
        if snapshot(&client, offer)?.get(&id) != Some(&tab) || context.validate(session).is_err() {
            anyhow::bail!("Tab changed while updating its automatic title");
        }
        if tab.name != record.title {
            record.pending_from = Some(tab.name);
            save_json(&path, &json!(record))?;
            ipc::output(client.request(
                ActionType::RenameTabById(RenameTabByIdAction {
                    id,
                    name: record.title.clone(),
                }),
                false,
            )?)?;
            record.pending_from = None;
        }
        save_json(&path, &json!(record)).context("Cannot retain automatic title ownership")?;
    }
    context.validate(session)?;
    for path in obsolete {
        let record: Record = serde_json::from_slice(&std::fs::read(&path)?)?;
        if record.identity != identity {
            std::fs::remove_file(path)?;
        }
    }
    Ok(())
}

fn directory_title() -> Result<String> {
    let cwd = env::var_os("PWD")
        .map(PathBuf::from)
        .unwrap_or(env::current_dir()?);
    let name = cwd
        .file_name()
        .map(|s| s.to_string_lossy())
        .unwrap_or("/".into());
    let mut title = label(&name);
    if let Ok(branch) = run(
        "git",
        &["rev-parse", "--abbrev-ref", "HEAD"],
        Instant::now() + Duration::from_millis(500),
    ) {
        if !branch.trim().is_empty() {
            title.push_str(&format!(" {BRANCH} {}", label(branch.trim())));
        }
    }
    Ok(title)
}

pub fn main(args: &[String]) -> Result<()> {
    const HELP: &str = "Usage: zellij-auto-title [--shell | --clear [--all]]\n\n--clear returns the current pane's tab to automatic naming.\n--clear --all returns every fixed tab name in the current session to automatic naming.";
    match args {
        [flag] if matches!(flag.as_str(), "--help" | "-h") => {
            println!("{HELP}");
            return Ok(());
        }
        [flag] if flag == "--clear" => {
            return update(&session()?, None, Update::ClearPane(pane_id()?));
        }
        [first, second]
            if (first == "--clear" && second == "--all")
                || (first == "--all" && second == "--clear") =>
        {
            return update(&session()?, None, Update::ClearAll);
        }
        [] => {}
        [flag] if flag == "--shell" => {}
        _ => anyhow::bail!("{HELP}"),
    }
    let title = directory_title()?;
    if args == ["--shell"] {
        emit_shell_title(&title)?;
    }
    refresh(&session()?, Some((pane_id()?, &title)))
}

fn emit_shell_title(title: &str) -> Result<()> {
    use std::io::{IsTerminal, Write};
    if std::io::stdout().is_terminal() {
        write!(std::io::stdout(), "\x1b]2;{title}\x07")?;
        std::io::stdout().flush()?;
    }
    Ok(())
}

pub fn shell_title() -> Result<()> {
    emit_shell_title(&directory_title()?)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn restored_titles_require_persistent_session_and_matching_name() {
        let current = json!(["new socket"]);
        let persistent = json!(["index", "session id", 123]);
        for (record_identity, record_persistent, name, expected) in [
            (
                json!(["old socket"]),
                Some(persistent.clone()),
                "api",
                "api",
            ),
            (
                json!(["old socket"]),
                Some(persistent.clone()),
                "manual",
                "",
            ),
            (
                json!(["old socket"]),
                Some(json!(["index", "other", 123])),
                "api",
                "",
            ),
            (
                json!(["old socket"]),
                Some(json!(["index", "session id", 456])),
                "api",
                "",
            ),
            (json!(["old socket"]), None, "api", ""),
        ] {
            let record = previous_record(
                Record {
                    identity: record_identity,
                    persistent_identity: record_persistent,
                    title: "api".into(),
                    providers: BTreeSet::from([7]),
                    pending_from: Some("manual".into()),
                },
                &current,
                &persistent,
                name,
            );
            assert_eq!(record.title, expected);
            assert!(record.providers.is_empty());
            assert!(record.pending_from.is_none());
        }
    }

    #[test]
    fn name_follows_its_last_provider_then_the_oldest_survivor() {
        let mut tab = Tab::default();
        let mut prev = Record::default();
        for (panes, expect) in [
            (vec![(7, "api")], "api"),
            (vec![(2, "logs"), (7, "api"), (9, "api")], "api"),
            (vec![(2, "logs"), (7, "editor"), (9, "api")], "api"),
            (vec![(2, "logs"), (9, "editor")], "api"),
            (vec![(11, "recent"), (2, "logs")], "logs"),
            (vec![], "Tab #1"),
        ] {
            tab.panes = panes
                .into_iter()
                .map(|(id, n)| (id, Some(n.into())))
                .collect();
            (prev.title, prev.providers) = choose(&tab, &prev, "Tab #1");
            assert_eq!(prev.title, expect);
        }
    }
}
