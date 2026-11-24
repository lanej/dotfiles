use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::fs;
use std::os::unix::fs::{symlink, PermissionsExt};
use std::path::PathBuf;
use std::process::Command;

struct Fixture {
    home: tempfile::TempDir,
    runtime: PathBuf,
}

impl Fixture {
    fn new(capability: Value, immutable: bool, mutate_during_query: bool) -> Self {
        let home = tempfile::tempdir().unwrap();
        let mutation = if mutate_during_query {
            "/bin/chmod 755 \"$0\"\nprintf '\\n# changed\\n' >> \"$0\""
        } else {
            ""
        };
        let script = format!(
            "#!/bin/sh\nif [ \"$1\" = --activation-capabilities ]; then\n{mutation}\nprintf '%s\\n' '{}'\nexit 0\nfi\nprintf '%s\\000' \"$@\"\n",
            capability
        );
        let image = format!("{:x}", Sha256::digest(script.as_bytes()));
        let directory = if immutable {
            home.path().join(".local/lib/zellij/runtimes").join(image)
        } else {
            home.path().join("legacy")
        };
        fs::create_dir_all(&directory).unwrap();
        let runtime = directory.join("zellij");
        fs::write(&runtime, script).unwrap();
        fs::set_permissions(&runtime, fs::Permissions::from_mode(0o555)).unwrap();
        let bin = home.path().join("bin");
        fs::create_dir(&bin).unwrap();
        symlink(&runtime, bin.join("zellij")).unwrap();
        let layouts = home.path().join(".config/zellij/layouts");
        fs::create_dir_all(&layouts).unwrap();
        fs::write(layouts.join("tmux.kdl"), "layout { pane }\n").unwrap();
        Self { home, runtime }
    }

    fn invoke(&self, arguments: &[&str]) -> Vec<String> {
        let mut command = Command::new(env!("CARGO_BIN_EXE_lane-zellij"));
        command
            .args(arguments)
            .env_clear()
            .env("HOME", self.home.path())
            .env("PATH", self.home.path().join("bin"));
        if arguments[0] == "popup" {
            command
                .env("ZELLIJ", "1")
                .env("ZELLIJ_SESSION_NAME", "existing");
        }
        let result = command.output().unwrap();
        assert!(
            result.status.success(),
            "{}",
            String::from_utf8_lossy(&result.stderr)
        );
        result
            .stdout
            .split(|byte| *byte == 0)
            .filter(|value| !value.is_empty())
            .map(|value| String::from_utf8(value.to_vec()).unwrap())
            .collect()
    }
}

fn supported() -> Value {
    json!({
        "schema_version": 1,
        "activation_build": "native-test-build",
        "capabilities": {
            "managed_clients": true,
            "raw_input_checkpoint": true,
            "mutation_fence": true,
            "drain": true,
            "operation_bound_stop": true,
            "no_forced_children": true
        }
    })
}

#[test]
fn capable_immutable_runtime_manages_attach_and_popup() {
    let fixture = Fixture::new(supported(), true, false);
    assert_eq!(
        fixture.invoke(&["attach", "space session"]),
        ["--activation-client", "attach", "--create", "space session"]
    );
    let popup = fixture.invoke(&["popup"]);
    assert_eq!(&popup[..2], ["--activation-client", "--layout-string"]);
    assert!(popup[2].starts_with("layout { pane }"));
    assert_eq!(&popup[3..], ["attach", "--create", "pop-up"]);
}

#[test]
fn legacy_or_incomplete_capability_keeps_ordinary_attach() {
    let legacy = Fixture::new(supported(), false, false);
    assert_eq!(
        legacy.invoke(&["attach", "existing"]),
        ["attach", "--create", "existing"]
    );
    for capability in [
        {
            let mut value = supported();
            value["capabilities"]["raw_input_checkpoint"] = json!(false);
            value
        },
        {
            let mut value = supported();
            value["activation_build"] = json!(null);
            value
        },
        {
            let mut value = supported();
            value["schema_version"] = json!(2);
            value
        },
    ] {
        let fixture = Fixture::new(capability, true, false);
        assert_eq!(
            fixture.invoke(&["attach", "existing"]),
            ["attach", "--create", "existing"]
        );
    }
}

#[test]
fn writable_or_changed_image_never_claims_managed_input() {
    let writable = Fixture::new(supported(), true, false);
    fs::set_permissions(&writable.runtime, fs::Permissions::from_mode(0o755)).unwrap();
    assert_eq!(
        writable.invoke(&["attach", "existing"]),
        ["attach", "--create", "existing"]
    );
    let changed = Fixture::new(supported(), true, true);
    assert_eq!(
        changed.invoke(&["attach", "existing"]),
        ["attach", "--create", "existing"]
    );
}
