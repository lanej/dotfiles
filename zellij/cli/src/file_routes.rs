//! File dispatch stays on the source pane's host; filenames never become shell code.
use crate::util::*;
use anyhow::{bail, ensure, Context, Result};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashSet;
use std::fs;
use std::io::{Read, Seek, SeekFrom};
use std::os::unix::process::CommandExt;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::time::{Duration, Instant};

#[derive(Clone, Debug, Default, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Target {
    pub path: String,
    #[serde(default)]
    pub host: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub line: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub column: Option<u64>,
}

#[derive(Clone, Copy, Debug, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
enum Handler {
    Neovim,
    Image,
    System,
    Command,
}

#[derive(Clone, Copy, Debug, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
enum Launch {
    Pane,
    Background,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct Route {
    extensions: Vec<String>,
    handler: Handler,
    command: Option<Vec<String>>,
    launch: Option<Launch>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct Table {
    routes: Vec<Route>,
}

impl Table {
    fn parse(raw: &str) -> Result<Self> {
        let table: Self = toml::from_str(raw)?;
        let mut extensions = HashSet::new();
        for route in &table.routes {
            ensure!(!route.extensions.is_empty(), "A route needs extensions");
            for extension in &route.extensions {
                ensure!(
                    !extension.is_empty()
                        && !extension.starts_with('.')
                        && !extension.ends_with('.')
                        && extension
                            .chars()
                            .all(|c| c.is_ascii_alphanumeric() || matches!(c, '.' | '-' | '_')),
                    "Invalid extension: {extension}"
                );
                ensure!(
                    extensions.insert(extension.to_ascii_lowercase()),
                    "Duplicate extension: {extension}"
                );
            }
            if route.handler == Handler::Command {
                let command = route
                    .command
                    .as_ref()
                    .context("A command route needs a command array")?;
                ensure!(
                    !command.is_empty() && !command[0].is_empty(),
                    "A command route needs a program"
                );
                ensure!(
                    route.launch.is_some(),
                    "A command route needs launch = pane or background"
                );
                for argument in command {
                    let plain = argument
                        .replace("{path}", "")
                        .replace("{line}", "")
                        .replace("{column}", "");
                    ensure!(
                        !plain.contains(['{', '}']),
                        "Unknown placeholder in {argument}"
                    );
                    ensure!(!argument.contains('\0'), "Invalid command argument");
                }
                ensure!(
                    !command[0].contains(['{', '}']),
                    "The command program cannot be a placeholder"
                );
            } else {
                ensure!(
                    route.command.is_none() && route.launch.is_none(),
                    "Only command routes accept command and launch"
                );
            }
        }
        Ok(table)
    }

    fn load() -> Result<Self> {
        let path = std::env::var_os("XDG_CONFIG_HOME")
            .map(PathBuf::from)
            .filter(|p| p.is_absolute())
            .unwrap_or(home()?.join(".config"))
            .join("zellij/file-routes.toml");
        let raw = match fs::read_to_string(&path) {
            Ok(raw) => raw,
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
                include_str!("../../file-routes.toml").into()
            }
            Err(error) => return Err(error).with_context(|| path.display().to_string()),
        };
        Self::parse(&raw).with_context(|| format!("Invalid routing table {}", path.display()))
    }

    fn route(&self, path: &Path) -> Option<&Route> {
        let name = path.file_name()?.to_str()?.to_ascii_lowercase();
        self.routes
            .iter()
            .flat_map(|route| {
                let name = &name;
                route.extensions.iter().filter_map(move |ext| {
                    name.ends_with(&format!(".{}", ext.to_ascii_lowercase()))
                        .then_some((ext.len(), route))
                })
            })
            .max_by_key(|(length, _)| *length)
            .map(|(_, route)| route)
    }
}

pub fn resolve(target: &Target, cwd: &Path) -> Result<PathBuf> {
    ensure!(
        !target.path.chars().any(char::is_control),
        "Invalid filename"
    );
    ensure!(
        target.line != Some(0) && target.column != Some(0),
        "File positions start at 1"
    );
    if !target.host.is_empty() && !target.host.eq_ignore_ascii_case("localhost") {
        let hostname = run("hostname", &[], Instant::now() + Duration::from_secs(2))?;
        let hostname = hostname.trim();
        ensure!(
            hostname.eq_ignore_ascii_case(&target.host)
                || hostname
                    .split('.')
                    .next()
                    .is_some_and(|short| short.eq_ignore_ascii_case(&target.host)),
            "The file link belongs to a different host: {}",
            target.host
        );
    }
    let path = match target.path.strip_prefix("~/") {
        Some(rest) => home()?.join(rest),
        None => cwd.join(&target.path),
    };
    ensure!(
        path.is_file(),
        "File does not exist in this worktree: {}",
        path.display()
    );
    Ok(path.canonicalize()?)
}

fn mime_handler(mime: &str) -> Handler {
    match mime.trim() {
        mime if mime.starts_with("text/")
            || matches!(
                mime,
                "application/json" | "application/xml" | "application/javascript" | "inode/x-empty"
            ) =>
        {
            Handler::Neovim
        }
        "image/png" | "image/jpeg" | "image/webp" | "image/gif" | "image/bmp" | "image/tiff"
        | "image/avif" | "image/svg+xml" | "image/x-icon" | "image/heic" | "image/jxl" => {
            Handler::Image
        }
        _ => Handler::System,
    }
}

fn arguments(template: &[String], target: &Target) -> Vec<String> {
    template
        .iter()
        .map(|arg| {
            // Expand template tokens once; a filename containing another token is literal.
            let mut expanded = String::new();
            let mut rest = arg.as_str();
            while let Some(start) = rest.find('{') {
                expanded.push_str(&rest[..start]);
                let end = rest[start..].find('}').unwrap() + start;
                match &rest[start..=end] {
                    "{path}" => expanded.push_str(&target.path),
                    "{line}" => expanded.push_str(&target.line.unwrap_or(1).to_string()),
                    "{column}" => expanded.push_str(&target.column.unwrap_or(1).to_string()),
                    _ => unreachable!("validated routing table"),
                }
                rest = &rest[end + 1..];
            }
            expanded.push_str(rest);
            expanded
        })
        .collect()
}

/// Background launch success means the program started, not that a GUI displayed the file.
fn background(args: &[String], cwd: &Path) -> Result<()> {
    let mut error = tempfile::tempfile()?;
    let mut child = Command::new(&args[0])
        .args(&args[1..])
        .current_dir(cwd)
        .process_group(0)
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(error.try_clone()?)
        .spawn()
        .with_context(|| format!("Could not start {}", args[0]))?;
    let deadline = Instant::now() + Duration::from_millis(250);
    loop {
        if let Some(status) = child.try_wait()? {
            if !status.success() {
                error.seek(SeekFrom::Start(0))?;
                let mut message = String::new();
                error.take(16 * 1024).read_to_string(&mut message)?;
                bail!("{} exited with {status}: {}", args[0], message.trim());
            }
            return Ok(());
        }
        if Instant::now() >= deadline {
            // Do not kill an associated application just because it stays open.
            return Ok(());
        }
        std::thread::sleep(Duration::from_millis(10));
    }
}

pub fn new_pane(
    session: &str,
    origin: u64,
    pane: &Value,
    cwd: &Path,
    args: &[String],
    name: &str,
) -> Result<()> {
    let current = source_pane(session, origin, pane)?;
    let mut command = Command::new("zellij");
    command
        .env("ZELLIJ_PANE_ID", origin.to_string())
        .arg(format!("--session={session}"))
        .args(["action", "new-pane", "--near-current-pane"]);
    if flag(&current, "is_floating") {
        command.arg("--floating");
    } else {
        native(
            session,
            &[
                "action",
                "hide-floating-panes",
                "--tab-id",
                &number(pane, "tab_id")?.to_string(),
            ],
        )?;
        command.args(["--direction", "right"]);
    }
    let result = command
        .args(["--close-on-exit", "--cwd"])
        .arg(cwd)
        .args(["--name", &clean(name, 120)])
        .args(["--", "zellij-helper", "file-run"])
        .args(args)
        .output()?;
    ensure!(
        result.status.success(),
        "Could not open file pane: {}",
        String::from_utf8_lossy(&result.stderr).trim()
    );
    let id = std::str::from_utf8(&result.stdout)?.trim();
    focus_pane(session, id)?;
    Ok(())
}

pub fn focus_pane(session: &str, id: &str) -> Result<()> {
    let result = native(session, &["action", "focus-pane-id", id]);
    if result.is_err() {
        // Closing/hiding the receiver can already have restored this pane's focus.
        let number: u64 = id.strip_prefix("terminal_").unwrap_or(id).parse()?;
        if snapshot(session, "panes")?.iter().any(|pane| {
            pane["id"].as_u64() == Some(number)
                && !flag(pane, "is_plugin")
                && flag(pane, "is_focused")
        }) {
            return Ok(());
        }
    }
    result.map(|_| ())
}

fn source_pane(session: &str, origin: u64, expected: &Value) -> Result<Value> {
    let panes = snapshot(session, "panes")?;
    let current = panes
        .iter()
        .find(|p| p["id"].as_u64() == Some(origin) && !flag(p, "is_plugin") && !flag(p, "exited"))
        .context("The source pane closed")?;
    ensure!(
        current["tab_id"] == expected["tab_id"]
            && current["pane_cwd"] == expected["pane_cwd"]
            && current["terminal_command"] == expected["terminal_command"],
        "The source pane moved or changed; select the file again"
    );
    Ok(current.clone())
}

pub fn run_program(args: &[String]) -> Result<()> {
    ensure!(!args.is_empty(), "Missing program");
    let status = Command::new(&args[0]).args(&args[1..]).status()?;
    ensure!(status.success(), "{} exited with {status}", args[0]);
    Ok(())
}

pub fn open(session: &str, origin: u64, pane: &Value, cwd: &Path, target: Target) -> Result<()> {
    let server = crate::context::Session::resolve(session)?;
    let path = resolve(&target, cwd)?;
    let table = Table::load()?;
    let route = table.route(&path);
    let handler = match route {
        Some(route) => route.handler,
        None => mime_handler(&run(
            "file",
            &[
                "--brief",
                "--mime-type",
                "--",
                path.to_str().context("Filename is not UTF-8")?,
            ],
            Instant::now() + Duration::from_secs(3),
        )?),
    };
    let target = Target {
        path: path.to_str().context("Filename is not UTF-8")?.into(),
        ..target
    };
    let name = path
        .file_name()
        .and_then(|name| name.to_str())
        .context("Missing filename")?;
    server.validate(session)?;
    source_pane(session, origin, pane)?;
    match handler {
        Handler::Neovim => crate::editor::open(session, origin, pane, cwd, &target),
        Handler::Image => {
            ensure!(
                exists("kitten"),
                "Install kitten on the host running this Zellij session"
            );
            new_pane(
                session,
                origin,
                pane,
                cwd,
                &["zellij-helper".into(), "image-view".into(), target.path],
                name,
            )
        }
        Handler::System => {
            let program = if cfg!(target_os = "macos") {
                "open"
            } else {
                "xdg-open"
            };
            background(&[program.into(), target.path.clone()], cwd).with_context(|| {
                format!(
                    "Could not open {} on this host; the file has not been transferred",
                    target.path
                )
            })
        }
        Handler::Command => {
            let route = route.unwrap();
            let args = arguments(route.command.as_ref().unwrap(), &target);
            match route.launch.unwrap() {
                Launch::Pane => new_pane(session, origin, pane, cwd, &args, name),
                Launch::Background => background(&args, cwd),
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn routes_and_literal_argument_expansion() {
        let table = Table::parse(
            r#"
[[routes]]
extensions = ["gz"]
handler = "system"
[[routes]]
extensions = ["tar.gz"]
handler = "command"
command = ["viewer", "{path}", "{line}:{column}"]
launch = "pane"
"#,
        )
        .unwrap();
        let route = table.route(Path::new("archive.TAR.GZ")).unwrap();
        assert_eq!(route.handler, Handler::Command);
        let target = Target {
            path: "/tmp/a {line};$(x).tar.gz".into(),
            line: Some(42),
            ..Default::default()
        };
        assert_eq!(
            arguments(route.command.as_ref().unwrap(), &target),
            ["viewer", "/tmp/a {line};$(x).tar.gz", "42:1"]
        );
        assert!(Table::parse("[[routes]]\nextensions=['rs','RS']\nhandler='neovim'").is_err());
        assert!(Table::parse("[[routes]]\nextensions=['x']\nhandler='command'\ncommand=['app','{unknown}']\nlaunch='pane'").is_err());
        assert_eq!(mime_handler("text/plain\n"), Handler::Neovim);
        assert_eq!(mime_handler("application/pdf"), Handler::System);
    }

    #[test]
    fn shipped_table_and_resolution() {
        let table = Table::parse(include_str!("../../file-routes.toml")).unwrap();
        assert_eq!(
            table.route(Path::new("file.SVG")).unwrap().handler,
            Handler::Image
        );
        let work = tempfile::tempdir().unwrap();
        fs::write(work.path().join("hello world"), "text").unwrap();
        let target = Target {
            path: "hello world".into(),
            ..Default::default()
        };
        assert_eq!(
            resolve(&target, work.path()).unwrap(),
            work.path().canonicalize().unwrap().join("hello world")
        );
        assert!(resolve(
            &Target {
                path: "missing".into(),
                ..target
            },
            work.path()
        )
        .is_err());
    }
}
