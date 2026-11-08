//! Bounded subprocess execution. Drain both pipes without blocking on a child
//! (or descendant) that keeps one open; kill and reap on every error path.
use std::io::{ErrorKind, Read};
use std::os::fd::AsRawFd;
use std::os::unix::process::CommandExt;
use std::process::{Child, Command, Stdio};
use std::time::{Duration, Instant};

struct Running(Child, bool);
impl Drop for Running {
    fn drop(&mut self) {
        // Each command has its own process group. Descendants must not outlive
        // a timeout and retain stdout/stderr or continue a reload operation.
        if !self.1 {
            unsafe {
                libc::kill(-(self.0.id() as i32), libc::SIGKILL);
            }
            let _ = self.0.wait();
        }
    }
}

fn nonblocking(pipe: &impl AsRawFd) -> Result<(), String> {
    let fd = pipe.as_raw_fd();
    let flags = unsafe { libc::fcntl(fd, libc::F_GETFL) };
    if flags < 0 || unsafe { libc::fcntl(fd, libc::F_SETFL, flags | libc::O_NONBLOCK) } < 0 {
        return Err(std::io::Error::last_os_error().to_string());
    }
    Ok(())
}

fn drain(pipe: &mut impl Read, bytes: &mut Vec<u8>, limit: usize) -> Result<bool, String> {
    let mut buffer = [0; 16 * 1024];
    match pipe.read(&mut buffer) {
        Ok(0) => Ok(true),
        Ok(count) => {
            if bytes.len() + count > limit {
                return Err("command output exceeds limit".into());
            }
            bytes.extend_from_slice(&buffer[..count]);
            Ok(false)
        }
        Err(error) if matches!(error.kind(), ErrorKind::WouldBlock | ErrorKind::Interrupted) => {
            Ok(false)
        }
        Err(error) => Err(error.to_string()),
    }
}

pub fn output(program: &str, args: &[&str], deadline: Instant) -> Result<String, String> {
    if Instant::now() >= deadline {
        return Err("command deadline exceeded".into());
    }
    let child = Command::new(program)
        .args(args)
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .process_group(0)
        .spawn()
        .map_err(|e| format!("{program}: {e}"))?;
    let mut child = Running(child, false);
    let mut stdout = child.0.stdout.take().unwrap();
    let mut stderr = child.0.stderr.take().unwrap();
    nonblocking(&stdout)?;
    nonblocking(&stderr)?;
    let (mut out, mut error) = (Vec::new(), Vec::new());
    loop {
        if Instant::now() >= deadline {
            return Err("command deadline exceeded".into());
        }
        let out_done = drain(&mut stdout, &mut out, 4 * 1024 * 1024)?;
        let err_done = drain(&mut stderr, &mut error, 64 * 1024)?;
        if let Some(status) = child.0.try_wait().map_err(|e| e.to_string())? {
            if out_done && err_done {
                if !status.success() {
                    let error = String::from_utf8_lossy(&error);
                    return Err(if error.trim().is_empty() {
                        format!("{program} command failed")
                    } else {
                        error.trim().to_owned()
                    });
                }
                child.1 = true;
                return String::from_utf8(out).map_err(|e| e.to_string());
            }
        }
        std::thread::sleep(Duration::from_millis(5));
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn captures_both_streams_without_deadlocking() {
        let out = output(
            "sh",
            &["-c", "printf yes; printf error >&2"],
            Instant::now() + Duration::from_secs(1),
        )
        .unwrap();
        assert_eq!(out, "yes");
        assert_eq!(
            output(
                "sh",
                &["-c", "printf failure >&2; exit 1"],
                Instant::now() + Duration::from_secs(1)
            )
            .unwrap_err(),
            "failure"
        );
    }
    #[test]
    fn inherited_pipes_do_not_extend_the_deadline() {
        let start = Instant::now();
        assert!(output(
            "sh",
            &["-c", "sleep 10 & exit 0"],
            start + Duration::from_millis(100)
        )
        .is_err());
        assert!(start.elapsed() < Duration::from_secs(1));
    }
}
