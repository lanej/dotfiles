use crate::util::*;
use anyhow::{bail, Context, Result};
use serde_json::Value;
use std::collections::BTreeSet;
use std::time::{Duration, Instant};
struct Navigation {
    session: String,
    pane: u64,
    deadline: Instant,
}
impl Navigation {
    fn action(&self, args: &[&str]) -> Result<String> {
        let mut command = vec!["action"];
        command.extend_from_slice(args);
        zellij(&self.session, &command, self.deadline)
    }
    fn query(&self, args: &[&str]) -> Result<String> {
        while Instant::now() < self.deadline {
            let output = self.action(args)?;
            if !output.trim().is_empty() {
                return Ok(output);
            }
            std::thread::sleep(Duration::from_millis(20));
        }
        bail!("Zellij returned no response before the navigation deadline")
    }
    fn json(&self, command: &str) -> Result<Value> {
        Ok(serde_json::from_str(&self.query(&[command, "--json"])?)?)
    }
    fn client(&self) -> Result<Option<(u64, String)>> {
        let output = self.query(&["list-clients"])?;
        let mut lines = output.lines();
        if lines
            .next()
            .map(|s| s.split_whitespace().collect::<Vec<_>>())
            != Some(vec!["CLIENT_ID", "ZELLIJ_PANE_ID", "RUNNING_COMMAND"])
        {
            bail!("Cannot establish the active Zellij client");
        }
        let clients: Vec<_> = lines
            .filter(|l| !l.trim().is_empty())
            .map(|l| {
                let mut fields = l.split_whitespace();
                Ok((
                    fields.next().context("Missing client")?.parse::<u64>()?,
                    fields.next().context("Missing client pane")?.to_owned(),
                ))
            })
            .collect::<Result<_>>()?;
        if clients.len() > 1 {
            bail!("Pane navigation needs one attached client; use Ctrl-f h/j/k/l");
        }
        let tabs = self.json("list-tabs")?;
        let mut attached = BTreeSet::new();
        for tab in tabs.as_array().context("Invalid tabs")? {
            for id in tab["other_focused_clients"]
                .as_array()
                .context("Missing client metadata")?
            {
                attached.insert(id.as_u64().context("Invalid client ID")?);
            }
        }
        if attached.len() != 1 {
            bail!("Pane navigation needs one attached client; use Ctrl-f h/j/k/l");
        }
        let client_id = *attached.first().context("Missing attached client")?;
        if let Some(client) = clients.first() {
            if client.0 != client_id {
                bail!("Cannot establish the active Zellij client");
            }
            return Ok((client.1 == format!("terminal_{}", self.pane)).then(|| client.clone()));
        }
        // In-place scrollback editors are omitted from list-clients. Require
        // exactly one attached client and a visible, focused pane in its active
        // tab before treating the editor as the owner of a client-relative action.
        let active_tabs: BTreeSet<_> = tabs
            .as_array()
            .context("Invalid tabs")?
            .iter()
            .filter(|tab| {
                tab["other_focused_clients"]
                    .as_array()
                    .is_some_and(|ids| ids.iter().any(|id| id.as_u64() == Some(client_id)))
            })
            .map(|tab| tab["tab_id"].as_u64().context("Invalid tab ID"))
            .collect::<Result<_>>()?;
        let panes = self.json("list-panes")?;
        let source = panes
            .as_array()
            .context("Invalid panes")?
            .iter()
            .find(|pane| !flag(pane, "is_plugin") && pane["id"] == self.pane);
        let Some(source) = source else {
            return Ok(None);
        };
        if !flag(source, "is_focused")
            || flag(source, "is_suppressed")
            || !active_tabs.contains(&source["tab_id"].as_u64().context("Invalid pane tab")?)
        {
            return Ok(None);
        }
        Ok(Some((client_id, format!("terminal_{}", self.pane))))
    }
}
pub fn main(args: &[String]) -> Result<()> {
    let [direction] = args else {
        bail!("Usage: zellij-navigate left|down|up|right|previous");
    };
    if !matches!(
        direction.as_str(),
        "left" | "down" | "up" | "right" | "previous"
    ) {
        bail!("Invalid direction");
    }
    if crate::context::provider()? != "zellij" {
        bail!("The calling pane belongs to another multiplexer");
    }
    let nav = Navigation {
        session: session()?,
        pane: pane_id()?,
        deadline: Instant::now() + Duration::from_secs(2),
    };
    let owner = nav.client()?;
    if owner.is_none() {
        return Ok(());
    }
    let panes = nav.json("list-panes")?;
    let pane = panes
        .as_array()
        .context("Invalid panes")?
        .iter()
        .find(|p| !flag(p, "is_plugin") && p["id"] == nav.pane)
        .context("The calling Zellij pane no longer exists")?;
    let tab = nav.json("current-tab-info")?;
    if !flag(pane, "is_focused")
        || flag(pane, "is_fullscreen")
        || tab["tab_id"] != pane["tab_id"]
        || flag(&tab, "is_fullscreen_active")
    {
        return Ok(());
    }
    if nav.client()? != owner {
        return Ok(());
    }
    if direction == "previous" {
        nav.action(&["focus-last-pane"])?;
    } else {
        nav.action(&["move-focus", direction])?;
    }
    Ok(())
}
