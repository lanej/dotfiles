use std::fs;
use std::io::Write;
use std::path::PathBuf;
use std::process::{Command, Output, Stdio};
use std::sync::atomic::{AtomicUsize, Ordering};

static NEXT: AtomicUsize = AtomicUsize::new(0);

struct Fixture(PathBuf);

impl Fixture {
    fn new() -> Self {
        let path = std::env::temp_dir().join(format!(
            "shortpath-test-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir(&path).unwrap();
        Self(path)
    }

    fn file(&self, name: &str) {
        let path = self.0.join(name);
        fs::create_dir_all(path.parent().unwrap()).unwrap();
        fs::write(path, b"").unwrap();
    }

    fn run(&self, args: &[&str], input: &[u8]) -> Output {
        let mut child = Command::new(env!("CARGO_BIN_EXE_shortpath"))
            .args(args)
            .current_dir(&self.0)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .unwrap();
        child.stdin.take().unwrap().write_all(input).unwrap();
        child.wait_with_output().unwrap()
    }
}

impl Drop for Fixture {
    fn drop(&mut self) {
        fs::remove_dir_all(&self.0).unwrap();
    }
}

#[test]
fn sibling_collisions_defaults_and_options() {
    let f = Fixture::new();
    f.file("projects/payments/src/main.rs");
    f.file("products/unused");
    f.file("projects/payroll/unused");
    let result = f.run(&["projects/payments/src/main.rs"], b"");
    assert!(result.status.success(), "{:?}", result);
    assert_eq!(result.stdout, b"proj/paym/s/main.rs\n");
    let result = f.run(
        &["-m", "2", "--keep", "2", "projects/payments/src/main.rs"],
        b"",
    );
    assert!(result.status.success());
    assert_eq!(result.stdout, b"proj/paym/src/main.rs\n");
    let result = f.run(&["-k", "0", "projects/payments/src/main.rs"], b"");
    assert!(result.status.success());
    assert_eq!(result.stdout, b"proj/paym/s/m\n");
}

#[test]
fn prefix_names_hidden_names_unicode_and_order() {
    let f = Fixture::new();
    for name in ["foo", "foobar", ".config", ".cache", "éclair", "école"] {
        f.file(name);
    }
    let result = f.run(
        &["-k", "0"],
        "foo\nfoobar\n.config\n.cache\néclair\nécole".as_bytes(),
    );
    assert!(result.status.success());
    assert_eq!(
        String::from_utf8(result.stdout).unwrap(),
        "foo\nfoob\n.co\n.ca\nécl\néco\n"
    );
}

#[test]
fn null_records_preserve_newlines_and_spaces() {
    let f = Fixture::new();
    f.file("long directory/line\nbreak.txt");
    let result = f.run(&["--null"], b"long directory/line\nbreak.txt\0");
    assert!(result.status.success());
    assert_eq!(result.stdout, b"l/line\nbreak.txt\0");
    let result = f.run(&["long directory/line\nbreak.txt"], b"");
    assert!(!result.status.success());
    assert!(result.stdout.is_empty());
}

#[test]
fn missing_and_invalid_records_fail_but_continue() {
    let f = Fixture::new();
    f.file("present");
    let result = f.run(&[], b"missing\n\xff\npresent\n\n");
    assert!(!result.status.success());
    assert_eq!(result.stdout, b"present\n");
    assert!(
        String::from_utf8(result.stderr)
            .unwrap()
            .contains("missing")
    );
    for args in [
        vec!["--min-length", "0"],
        vec!["--keep", "-1"],
        vec!["--wat"],
        vec!["-m"],
    ] {
        assert!(!f.run(&args, b"").status.success());
    }
}

#[test]
fn dot_parent_trailing_slash_and_option_like_paths() {
    let f = Fixture::new();
    f.file("directory/file");
    f.file("-name");
    let result = f.run(
        &[
            "./directory/",
            "directory/../directory/file",
            ".",
            "--",
            "-name",
        ],
        b"",
    );
    assert!(result.status.success(), "{:?}", result);
    assert_eq!(result.stdout, b"./directory/\nd/../d/file\n.\n-name\n");
    let absolute = f.0.join("directory/file");
    let result = f.run(&["-k", "999", absolute.to_str().unwrap()], b"");
    assert!(result.status.success());
    assert_eq!(
        String::from_utf8(result.stdout).unwrap(),
        format!("{}\n", absolute.display())
    );
}

#[cfg(unix)]
#[test]
fn symlinks_use_original_parent() {
    use std::os::unix::fs::symlink;
    let f = Fixture::new();
    f.file("destination/alpha/file");
    f.file("destination/alpine/other");
    symlink("destination", f.0.join("link")).unwrap();
    symlink("missing", f.0.join("dangling")).unwrap();
    let result = f.run(&["link/alpha/file", "dangling"], b"");
    assert!(result.status.success());
    assert_eq!(result.stdout, b"l/alph/file\ndangling\n");
}
