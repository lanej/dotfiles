//! Discover editors by their own RPC identity, never by pane titles or injected keystrokes.
use crate::file_routes::{new_pane, Target};
use crate::util::*;
use anyhow::{ensure, Context, Result};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::fs;
use std::os::unix::fs::{DirBuilderExt, MetadataExt, PermissionsExt};
use std::path::PathBuf;
use std::time::{Duration, Instant};

#[derive(Clone, Deserialize, PartialEq, Serialize)]
struct Identity {
    socket: String,
    pid: u32,
    session: String,
    pane: u64,
}

#[derive(Deserialize, Serialize)]
struct Registration {
    editor: Identity,
    server: Value,
}

fn directory() -> Result<PathBuf> {
    let base = std::env::var_os("XDG_RUNTIME_DIR")
        .map(PathBuf::from)
        .filter(|p| p.is_absolute())
        .unwrap_or_else(std::env::temp_dir);
    let path = base.join(format!("lane-zellij-editors-{}", unsafe { libc::getuid() }));
    match fs::DirBuilder::new().mode(0o700).create(&path) {
        Ok(()) => (),
        Err(error) if error.kind() == std::io::ErrorKind::AlreadyExists => (),
        Err(error) => return Err(error.into()),
    }
    let metadata = fs::symlink_metadata(&path)?;
    ensure!(
        metadata.is_dir()
            && metadata.uid() == unsafe { libc::getuid() }
            && metadata.permissions().mode() & 0o077 == 0,
        "Editor registry is not a private directory: {}",
        path.display()
    );
    Ok(path)
}

fn filename(identity: &Identity) -> String {
    format!(
        "{}.json",
        hash(
            &json!([
                identity.session,
                identity.pane,
                identity.pid,
                identity.socket
            ])
            .to_string()
        )
    )
}

pub fn register(socket: &str, pid: &str, remove: bool) -> Result<()> {
    let editor = Identity {
        socket: socket.into(),
        pid: pid.parse()?,
        session: session()?,
        pane: pane_id()?,
    };
    ensure!(
        std::path::Path::new(socket).is_absolute(),
        "Expected a Neovim Unix socket"
    );
    let directory = directory()?;
    let path = directory.join(filename(&editor));
    if remove {
        match fs::remove_file(path) {
            Ok(()) => (),
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => (),
            Err(error) => return Err(error.into()),
        }
    } else {
        let registration = Registration {
            editor,
            server: crate::context::Session::resolve(&session()?)?.identity,
        };
        let temporary = tempfile::NamedTempFile::new_in(directory)?;
        serde_json::to_writer(temporary.as_file(), &registration)?;
        temporary.persist(path)?;
    }
    Ok(())
}

fn remote(editor: &Identity, expression: &str) -> Result<Value> {
    let response = run(
        "nvim",
        &["--server", &editor.socket, "--remote-expr", expression],
        Instant::now() + Duration::from_secs(2),
    )?;
    Ok(serde_json::from_str(response.trim())?)
}

fn identity(editor: &Identity) -> Result<Identity> {
    Ok(serde_json::from_value(remote(
        editor,
        "json_encode(luaeval(\"require('file-opener').identity()\"))",
    )?)?)
}

fn terminal(panes: &[Value], id: u64) -> Option<&Value> {
    panes
        .iter()
        .find(|p| p["id"].as_u64() == Some(id) && !flag(p, "is_plugin") && !flag(p, "exited"))
}

fn editors(session: &str, source: &Value) -> Result<Vec<Identity>> {
    let server = crate::context::Session::resolve(session)?;
    let panes = snapshot(session, "panes")?;
    let mut editors = vec![];
    for entry in fs::read_dir(directory()?)? {
        let entry = entry?;
        if entry.path().extension().is_none_or(|ext| ext != "json") {
            continue;
        }
        let Ok(raw) = fs::read(entry.path()) else {
            continue;
        };
        let Ok(registration) = serde_json::from_slice::<Registration>(&raw) else {
            continue;
        };
        let editor = registration.editor;
        if editor.session != session || registration.server != server.identity {
            continue;
        }
        if !terminal(&panes, editor.pane).is_some_and(|p| p["tab_id"] == source["tab_id"]) {
            continue;
        }
        if identity(&editor).is_ok_and(|current| current == editor) && !editors.contains(&editor) {
            editors.push(editor);
        }
    }
    editors.sort_by_key(|editor| (editor.pane, editor.pid));
    Ok(editors)
}

fn vim_string(value: &str) -> String {
    format!("'{}'", value.replace('\'', "''"))
}

fn open_expression(target: &Target, editor: &Identity) -> Result<String> {
    Ok(format!(
        "json_encode(luaeval(\"require('file-opener').open(_A.target, _A.editor)\", json_decode({})))",
        vim_string(&serde_json::to_string(&json!({"target": target, "editor": editor}))?)
    ))
}

pub fn open(
    session: &str,
    origin: u64,
    source: &Value,
    cwd: &std::path::Path,
    target: &Target,
) -> Result<()> {
    let server = crate::context::Session::resolve(session)?;
    let choices = editors(session, source)?;
    let selected = match choices.as_slice() {
        [] => {
            let payload = serde_json::to_string(&serde_json::to_string(target)?)?;
            return new_pane(
                session,
                origin,
                source,
                cwd,
                &[
                    "nvim".into(),
                    "-c".into(),
                    format!("lua require('file-opener').open(vim.json.decode({payload}))"),
                    "--".into(),
                    target.path.clone(),
                ],
                std::path::Path::new(&target.path)
                    .file_name()
                    .and_then(|name| name.to_str())
                    .context("Missing filename")?,
            );
        }
        [editor] => editor.clone(),
        _ => {
            let panes = snapshot(session, "panes")?;
            let rows = choices
                .iter()
                .enumerate()
                .map(|(index, editor)| {
                    let pane = terminal(&panes, editor.pane);
                    format!(
                        "{index}\tPane {} (PID {}): {} — {}",
                        editor.pane,
                        editor.pid,
                        clean(
                            pane.and_then(|p| p["title"].as_str()).unwrap_or("Neovim"),
                            80
                        ),
                        clean(pane.and_then(|p| p["pane_cwd"].as_str()).unwrap_or(""), 200)
                    )
                })
                .collect::<Vec<_>>()
                .join("\n");
            let Some(index) = fzf(
                &[
                    "--height=100%".into(),
                    "--reverse".into(),
                    "--no-multi".into(),
                    "--delimiter=\t".into(),
                    "--with-nth=2..".into(),
                    "--header=Open in Neovim: Enter confirms; Esc cancels".into(),
                ],
                rows + "\n",
            )?
            else {
                return Ok(());
            };
            choices
                .get(index.parse::<usize>()?)
                .context("Invalid editor selection")?
                .clone()
        }
    };
    server.validate(session)?;
    let panes = snapshot(session, "panes")?;
    let current_source = terminal(&panes, origin).context("The source pane closed")?;
    ensure!(
        current_source["tab_id"] == source["tab_id"]
            && current_source["pane_cwd"] == source["pane_cwd"],
        "The source pane moved or changed directories"
    );
    let destination = terminal(&panes, selected.pane).context("The editor pane closed")?;
    ensure!(
        destination["tab_id"] == source["tab_id"] && identity(&selected)? == selected,
        "The editor moved or changed; select the file again"
    );
    let opened: Identity =
        serde_json::from_value(remote(&selected, &open_expression(target, &selected)?)?)?;
    ensure!(
        opened == selected,
        "The editor changed while opening the file"
    );
    server.validate(session)?;
    let panes = snapshot(session, "panes")?;
    let destination =
        terminal(&panes, selected.pane).context("The editor pane closed after opening the file")?;
    let source_now = terminal(&panes, origin).context("The source pane closed")?;
    ensure!(
        destination["tab_id"] == source["tab_id"] && source_now["tab_id"] == source["tab_id"],
        "A pane moved while opening the file; focus was not changed"
    );
    if flag(destination, "is_floating") {
        native(
            session,
            &[
                "action",
                "show-floating-panes",
                "--tab-id",
                &number(source, "tab_id")?.to_string(),
            ],
        )?;
    } else {
        native(
            session,
            &[
                "action",
                "hide-floating-panes",
                "--tab-id",
                &number(source, "tab_id")?.to_string(),
            ],
        )?;
    }
    crate::file_routes::focus_pane(session, &selected.pane.to_string())?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn expression_keeps_unusual_filenames_as_data() {
        let target = Target {
            path: "/tmp/a'b\\c {line};$(touch nope).rs".into(),
            line: Some(42),
            ..Default::default()
        };
        let editor = Identity {
            socket: "/tmp/nvim.sock".into(),
            pid: 1,
            session: "test".into(),
            pane: 1,
        };
        let expression = open_expression(&target, &editor).unwrap();
        assert!(expression.contains("a''b"));
        assert!(expression.contains("\\\\c"));
    }
}
