//! Read-only activation probes sent to existing native plugin IDs.
use crate::{context::Session, ipc};
use anyhow::{bail, Context, Result};
use kdl::{KdlDocument, KdlEntry, KdlNode};
use lane_zellij_protocol::{ActivationImageReply, ActivationImageRequest, ACTIVATION_IMAGE};
use serde::Deserialize;
use std::collections::BTreeMap;
use std::io::Read;
use std::time::{Duration, Instant};

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct RestorePane {
    pane_id: u32,
    is_plugin: bool,
    title: String,
    command: Option<String>,
    cwd: Option<String>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct RestoreLayout {
    layout: String,
    panes: Vec<RestorePane>,
}

fn marker(node: &KdlNode) -> Option<(bool, u32)> {
    let name = node.get("name")?.value().as_string()?;
    let (plugin, id) = if let Some(id) = name.strip_prefix("__zellij_activation_terminal_") {
        (false, id)
    } else {
        (true, name.strip_prefix("__zellij_activation_plugin_")?)
    };
    Some((plugin, id.strip_suffix("__")?.parse().ok()?))
}

fn rewrite(
    document: &mut KdlDocument,
    panes: &mut BTreeMap<(bool, u32), RestorePane>,
) -> Result<()> {
    for node in document.nodes_mut() {
        if let Some(key) = marker(node) {
            let pane = panes
                .remove(&key)
                .context("Native pane has no frozen restoration binding")?;
            node.entries_mut()
                .retain(|entry| entry.name().is_none_or(|name| name.value() != "name"));
            node.entries_mut()
                .push(KdlEntry::new_prop("name", pane.title));
            if !key.0 {
                node.entries_mut().retain(|entry| {
                    entry
                        .name()
                        .is_none_or(|name| name.value() != "activation_pane_id")
                });
                node.entries_mut()
                    .push(KdlEntry::new_prop("activation_pane_id", i64::from(key.1)));
            }
            if let Some(command) = pane.command {
                anyhow::ensure!(
                    !key.0 && command.starts_with('/'),
                    "Expected a private absolute terminal launcher"
                );
                node.entries_mut().retain(|entry| {
                    entry
                        .name()
                        .is_none_or(|name| !matches!(name.value(), "command" | "cwd"))
                });
                node.entries_mut()
                    .push(KdlEntry::new_prop("command", command));
                if let Some(cwd) = pane.cwd {
                    anyhow::ensure!(cwd.starts_with('/'), "Expected an absolute pane cwd");
                    node.entries_mut().push(KdlEntry::new_prop("cwd", cwd));
                }
                let children = node.children_mut().get_or_insert_with(KdlDocument::new);
                children
                    .nodes_mut()
                    .retain(|child| !matches!(child.name().value(), "args" | "start_suspended"));
                let mut suspended = KdlNode::new("start_suspended");
                suspended.push(false);
                children.nodes_mut().push(suspended);
            }
        }
        if let Some(children) = node.children_mut() {
            rewrite(children, panes)?;
        }
    }
    Ok(())
}

/// Parse the native KDL grammar, retaining geometry, tabs, floats, stacks and plugin configuration.
pub fn layout() -> Result<()> {
    let mut input = String::new();
    std::io::stdin()
        .take(4 * 1024 * 1024 + 1)
        .read_to_string(&mut input)?;
    anyhow::ensure!(
        input.len() <= 4 * 1024 * 1024,
        "Activation layout input exceeds limit"
    );
    let request: RestoreLayout = serde_json::from_str(&input)?;
    let mut document: KdlDocument = request
        .layout
        .parse()
        .context("Invalid native activation layout")?;
    let mut panes = BTreeMap::new();
    for pane in request.panes {
        anyhow::ensure!(
            panes.insert((pane.is_plugin, pane.pane_id), pane).is_none(),
            "Duplicate native pane restoration owner"
        );
    }
    rewrite(&mut document, &mut panes)?;
    anyhow::ensure!(
        panes.is_empty(),
        "A frozen native pane disappeared from the layout"
    );
    print!("{document}");
    Ok(())
}

fn structure(document: &KdlDocument) -> serde_json::Value {
    serde_json::Value::Array(
        document
            .nodes()
            .iter()
            .filter(|node| !matches!(node.name().value(), "args" | "start_suspended" | "cwd"))
            .map(|node| {
                let entries: Vec<_> = node
                    .entries()
                    .iter()
                    .filter(|entry| {
                        let key = entry.name().map(|name| name.value());
                        !matches!(
                            key,
                            Some("command" | "cwd" | "contents_file" | "activation_pane_id")
                        ) && !(node.name().value() == "pane" && key == Some("name"))
                    })
                    .map(|entry| {
                        serde_json::json!([
                            entry.name().map(|name| name.value()),
                            entry.value().to_string()
                        ])
                    })
                    .collect();
                serde_json::json!({"kind":node.name().value(),"entries":entries,
            "children":node.children().map(structure)})
            })
            .collect(),
    )
}

pub fn shape() -> Result<()> {
    use sha2::{Digest, Sha256};
    let mut input = String::new();
    std::io::stdin()
        .take(4 * 1024 * 1024 + 1)
        .read_to_string(&mut input)?;
    anyhow::ensure!(
        input.len() <= 4 * 1024 * 1024,
        "Activation layout exceeds limit"
    );
    let document: KdlDocument = input.parse().context("Invalid native layout")?;
    let hash = Sha256::digest(serde_json::to_vec(&structure(&document))?);
    println!("{hash:x}");
    Ok(())
}

pub fn probe(args: &[String]) -> Result<()> {
    let [session_flag, name, plugin_flag, plugin] = args else {
        bail!("Usage: zellij-context activation-image --session NAME --plugin ID");
    };
    if session_flag != "--session" || plugin_flag != "--plugin" {
        bail!("Usage: zellij-context activation-image --session NAME --plugin ID");
    }
    let plugin_id = plugin.parse::<u32>()?;
    let session = Session::resolve(name)?;
    let mut nonce = [0u8; 16];
    std::fs::File::open("/dev/urandom")?.read_exact(&mut nonce)?;
    let request = ActivationImageRequest {
        schema_version: 1,
        request: nonce.iter().map(|byte| format!("{byte:02x}")).collect(),
        plugin_id,
    };
    let response = ipc::Client {
        socket: session.socket()?,
        terminal_id: None,
        deadline: Instant::now() + Duration::from_secs(3),
    }
    .pipe(ipc::contract::CliPipeAction {
        name: Some(ACTIVATION_IMAGE.into()),
        payload: Some(serde_json::to_string(&request)?),
        // Broadcast only to existing instances. A plugin URL would launch a
        // missing image; the native ID inside the request limits who replies.
        ..Default::default()
    })?;
    session.validate(name)?;
    let replies: Vec<ActivationImageReply> = response
        .output
        .lines()
        .filter(|line| !line.trim().is_empty())
        .map(serde_json::from_str)
        .collect::<std::result::Result<_, _>>()?;
    anyhow::ensure!(!replies.is_empty(), "Loaded plugin image probe unavailable");
    for reply in &replies {
        anyhow::ensure!(
            reply.schema_version == 1
                && reply.request == request.request
                && reply.plugin_id == plugin_id,
            "Loaded plugin reply identity changed"
        );
        anyhow::ensure!(
            reply.image_id.len() == 64
                && reply.image_id.bytes().all(|byte| byte.is_ascii_hexdigit()),
            "Plugin was not built with a verifiable image identity"
        );
    }
    serde_json::to_writer(std::io::stdout(), &replies)
        .context("Cannot report loaded plugin identities")?;
    println!();
    Ok(())
}
