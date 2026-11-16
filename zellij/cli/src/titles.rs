//! Read automatic-title records without granting ownership across server lifetimes.
use rusqlite::{Connection, OpenFlags, OptionalExtension};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::env;
use std::fs;
use std::os::unix::fs::{FileTypeExt, MetadataExt};
use std::path::{Path, PathBuf};
use std::time::Duration;

pub(crate) type Location = (PathBuf, PathBuf);

fn session_location() -> Result<Location, String> {
    crate::context::location().map_err(|error| error.to_string())
}

pub(crate) fn session_identity(session: &str, location: &Location) -> Result<Value, String> {
    let connection = Connection::open_with_flags(&location.1, OpenFlags::SQLITE_OPEN_READ_ONLY)
        .map_err(|error| error.to_string())?;
    connection
        .busy_timeout(Duration::from_millis(100))
        .map_err(|error| error.to_string())?;
    let id: Option<String> = connection
        .query_row(
            "SELECT COALESCE(id, name) FROM sessions WHERE name = ?",
            [session],
            |row| row.get(0),
        )
        .optional()
        .map_err(|error| error.to_string())?;
    let id = id.ok_or("Cannot identify the target session")?;
    if id.is_empty() || id == "." || id == ".." || id.contains('/') {
        return Err("Invalid session socket name".into());
    }
    let socket = location.0.join(id);
    let info = fs::symlink_metadata(&socket).map_err(|error| error.to_string())?;
    // SAFETY: getuid has no preconditions.
    if !info.file_type().is_socket() || info.uid() != unsafe { libc::getuid() } {
        return Err("The session socket is not owned by this user".into());
    }
    let ctime_ns = info
        .ctime()
        .checked_mul(1_000_000_000)
        .and_then(|seconds| seconds.checked_add(info.ctime_nsec()))
        .ok_or("Socket timestamp overflow")?;
    Ok(json!([socket, info.dev(), info.ino(), ctime_ns]))
}

pub(crate) fn session_key(session: &str) -> String {
    format!("{:x}", Sha256::digest(session.as_bytes()))
}

pub(crate) fn record_title(path: &Path, identity: &Value) -> Option<String> {
    let record: Value = serde_json::from_str(&fs::read_to_string(path).ok()?).ok()?;
    if record.get("identity")? != identity {
        return None;
    }
    record.get("title")?.as_str().map(str::to_owned)
}

fn record_paths(directory: &Path, session: &str) -> Vec<(String, PathBuf)> {
    let prefix = format!("{}-", session_key(session));
    let Ok(entries) = fs::read_dir(directory) else {
        return Vec::new();
    };
    entries
        .filter_map(Result::ok)
        .filter_map(|entry| {
            let filename = entry.file_name();
            let tab = filename
                .to_str()?
                .strip_prefix(&prefix)?
                .strip_suffix(".json")?;
            // Zellij tab identifiers are ASCII decimal numbers.
            if tab.is_empty() || !tab.bytes().all(|byte| byte.is_ascii_digit()) {
                return None;
            }
            Some((tab.to_owned(), entry.path()))
        })
        .collect()
}

fn read_titles(
    paths: &[(String, PathBuf)],
    mut identity: impl FnMut() -> Result<Value, String>,
) -> Result<BTreeMap<String, String>, String> {
    let before = identity()?;
    let titles = paths
        .iter()
        .filter_map(|(tab, path)| record_title(path, &before).map(|title| (tab.clone(), title)))
        .collect();
    // Recheck both the index mapping and socket incarnation after record reads.
    Ok(if identity()? == before {
        titles
    } else {
        BTreeMap::new()
    })
}

pub fn owned_titles(session: &str) -> BTreeMap<String, String> {
    let state = env::var_os("XDG_STATE_HOME")
        .map(PathBuf::from)
        .or_else(|| {
            crate::config::home()
                .ok()
                .map(|home| home.join(".local/state"))
        });
    let Some(state) = state else {
        return BTreeMap::new();
    };
    let paths = record_paths(&state.join("zellij-auto-titles"), session);
    if paths.is_empty() {
        return BTreeMap::new();
    }
    session_location()
        .and_then(|location| read_titles(&paths, || session_identity(session, &location)))
        .unwrap_or_default()
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::os::unix::net::UnixListener;
    use std::sync::atomic::{AtomicU64, Ordering};
    static NEXT: AtomicU64 = AtomicU64::new(0);
    struct Fixture(PathBuf);
    impl Fixture {
        fn new() -> Self {
            let path = env::temp_dir().join(format!(
                "lane-titles-{}-{}",
                std::process::id(),
                NEXT.fetch_add(1, Ordering::Relaxed)
            ));
            fs::create_dir(&path).unwrap();
            Self(path)
        }
    }
    impl Drop for Fixture {
        fn drop(&mut self) {
            let _ = fs::remove_dir_all(&self.0);
        }
    }

    #[test]
    fn ownership_requires_live_socket_and_matching_record() {
        let fixture = Fixture::new();
        let location = (fixture.0.clone(), fixture.0.join("index.sqlite"));
        let connection = Connection::open(&location.1).unwrap();
        connection.execute_batch("CREATE TABLE sessions (name TEXT, id TEXT); INSERT INTO sessions VALUES ('work', 'native-id');").unwrap();
        let _socket = UnixListener::bind(fixture.0.join("native-id")).unwrap();
        let identity = session_identity("work", &location).unwrap();
        let prefix = session_key("work");
        fs::write(
            fixture.0.join(format!("{prefix}-1.json")),
            json!({"identity": identity, "title": "project"}).to_string(),
        )
        .unwrap();
        fs::write(fixture.0.join(format!("{prefix}-2.json")), "\"legacy\"").unwrap();
        fs::write(
            fixture.0.join(format!("{prefix}-3.json")),
            json!({"identity": ["old"], "title": "stale"}).to_string(),
        )
        .unwrap();
        let paths = record_paths(&fixture.0, "work");
        assert_eq!(
            read_titles(&paths, || session_identity("work", &location)).unwrap(),
            BTreeMap::from([("1".into(), "project".into())])
        );
        let mut reads = 0;
        assert!(read_titles(&paths, || {
            reads += 1;
            if reads == 2 {
                connection
                    .execute("UPDATE sessions SET id = '../outside'", [])
                    .unwrap();
            }
            session_identity("work", &location)
        })
        .is_err());
    }

    #[test]
    fn socket_recreation_and_symlinks_cannot_inherit_ownership() {
        let fixture = Fixture::new();
        let location = (fixture.0.clone(), fixture.0.join("index.sqlite"));
        Connection::open(&location.1).unwrap().execute_batch("CREATE TABLE sessions (name TEXT, id TEXT); INSERT INTO sessions VALUES ('work', 'socket');").unwrap();
        let path = fixture.0.join("socket");
        let _first = UnixListener::bind(&path).unwrap();
        let before = session_identity("work", &location).unwrap();
        fs::remove_file(&path).unwrap();
        let _second = UnixListener::bind(&path).unwrap();
        let after = session_identity("work", &location).unwrap();
        assert_ne!(before, after);
        let record = fixture.0.join("record.json");
        fs::write(
            &record,
            json!({"identity": before, "title": "old title"}).to_string(),
        )
        .unwrap();
        let paths = vec![("1".into(), record)];
        let mut first = true;
        assert!(read_titles(&paths, || {
            let value = if first { before.clone() } else { after.clone() };
            first = false;
            Ok(value)
        })
        .unwrap()
        .is_empty());
        fs::remove_file(&path).unwrap();
        std::os::unix::fs::symlink("index.sqlite", &path).unwrap();
        assert!(session_identity("work", &location).is_err());
    }

    #[test]
    fn records_require_identity_and_revalidation() {
        let fixture = Fixture::new();
        let identity = json!(["/socket", 1, 2, 1_700_000_000_123_456_789i64]);
        let prefix = session_key("work");
        for (tab, record) in [
            ("1", json!({"identity": identity, "title": "project"})),
            ("2", json!("legacy")),
            ("3", json!({"identity": ["old"], "title": "stale"})),
        ] {
            fs::write(
                fixture.0.join(format!("{prefix}-{tab}.json")),
                record.to_string(),
            )
            .unwrap();
        }
        let paths = record_paths(&fixture.0, "work");
        assert_eq!(
            read_titles(&paths, || Ok(identity.clone())).unwrap(),
            BTreeMap::from([("1".into(), "project".into())])
        );
        let mut reads = 0;
        assert!(read_titles(&paths, || {
            reads += 1;
            let mut current = identity.clone();
            if reads == 2 {
                current[3] = json!(1_700_000_000_123_456_790i64);
            }
            Ok(current)
        })
        .unwrap()
        .is_empty());
    }

    #[test]
    fn missing_index_is_never_created() {
        let fixture = Fixture::new();
        let location = (fixture.0.clone(), fixture.0.join("missing.sqlite"));
        assert!(session_identity("work", &location).is_err());
        assert!(!location.1.exists());
    }

    #[test]
    fn session_hash_retains_record_names() {
        assert_eq!(
            session_key("work"),
            "00e13ed7af55b27622f1d6eab5bec0147e68efe28dc2b12461117afa1a5ed40e"
        );
    }
}
