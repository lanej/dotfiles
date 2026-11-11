use crate::{ipc, titles, util::*};
use anyhow::{Context, Result};
use ipc::contract::{action::ActionType, ListPanesAction, RenameTabByIdAction};
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

#[derive(Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
struct Record {
    identity: Value,
    title: String,
    #[serde(default)]
    providers: BTreeSet<u64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pending_from: Option<String>,
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

#[derive(Serialize, Deserialize)]
struct TitleContext {
    session: String,
    location: titles::Location,
    identity: Value,
}

impl TitleContext {
    fn resolve(session: &str, deadline: Instant) -> Result<Self> {
        let location = crate::context::location(deadline)?;
        let identity = titles::session_identity(session, &location).map_err(anyhow::Error::msg)?;
        Ok(Self {
            session: session.to_owned(),
            location,
            identity,
        })
    }

    fn validate(&self, session: &str) -> Result<()> {
        anyhow::ensure!(
            self.session == session,
            "Title context belongs to another session"
        );
        anyhow::ensure!(
            titles::session_identity(session, &self.location).map_err(anyhow::Error::msg)?
                == self.identity,
            "Title context belongs to a previous server"
        );
        Ok(())
    }
}

/// Resolve once when the shell installs its hooks; subsequent prompts reuse this context.
pub fn context() -> Result<String> {
    Ok(serde_json::to_string(&TitleContext::resolve(
        &session()?,
        Instant::now() + Duration::from_secs(1),
    )?)?)
}

fn snapshot(client: &ipc::Client<'_>, offer: Option<(u64, &str)>) -> Result<BTreeMap<u64, Tab>> {
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
    Ok(tabs)
}

pub fn refresh(session: &str, offer: Option<(u64, &str)>) -> Result<()> {
    let deadline = Instant::now() + Duration::from_secs(2);
    let context = match env::var("ZELLIJ_TITLE_CONTEXT") {
        Ok(value) => serde_json::from_str::<TitleContext>(&value)?,
        Err(_) => TitleContext::resolve(session, deadline)?,
    };
    context.validate(session)?;
    let identity = context.identity.clone();
    let client = ipc::Client {
        socket: std::path::Path::new(identity[0].as_str().context("Missing session socket")?),
        terminal_id: offer.map(|(pane, _)| pane.try_into()).transpose()?,
        deadline,
    };
    let dir = state("zellij-auto-titles")?;
    private_dir(&dir)?;
    let key = titles::session_key(session);
    let _lock = Lock::acquire(&dir.join(format!("{key}.lock")), deadline)?;
    for (id, tab) in snapshot(&client, offer)? {
        // New tabs start as "Tab #N". An empty native name is the editable
        // field cleared by Ctrl-f r, which another client may be typing into.
        if tab.name.is_empty() {
            continue;
        }
        let path = dir.join(format!("{key}-{id}.json"));
        let previous = match std::fs::read(&path) {
            Ok(bytes) => serde_json::from_slice::<Record>(&bytes)
                .ok()
                .filter(|r| r.identity == identity),
            Err(err) if err.kind() == std::io::ErrorKind::NotFound => None,
            Err(err) => return Err(err.into()),
        }
        .unwrap_or_default();
        let fallback = format!("Tab #{}", id + 1);
        let managed =
            tab.name == previous.title || previous.pending_from.as_ref() == Some(&tab.name);
        if !managed && tab.name != fallback {
            continue;
        }
        let empty = Record::default();
        let (title, providers) = choose(&tab, if managed { &previous } else { &empty }, &fallback);
        let mut record = Record {
            identity: identity.clone(),
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
    anyhow::ensure!(
        args.is_empty() || args == ["--shell"],
        "Usage: zellij-auto-title [--shell]"
    );
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
