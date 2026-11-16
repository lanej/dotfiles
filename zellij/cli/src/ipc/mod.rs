//! Synchronous Action requests using the pinned runtime's generated protobuf types.
use anyhow::{bail, Context, Result};
use prost::Message;
use std::io::{Read, Write};
use std::os::fd::AsRawFd;
use std::os::unix::net::UnixStream;
use std::path::Path;
use std::time::{Duration, Instant};

#[rustfmt::skip]
// rationale: Keep the runtime's generated contract unchanged, including its enum layout.
#[allow(dead_code)]
#[allow(clippy::large_enum_variant)]
pub mod contract;
use contract::{
    client_to_server_msg, server_to_client_msg, Action, ActionMsg, ClientToServerMsg,
    ServerToClientMsg,
};

const MAX_FRAME: usize = 4 * 1024 * 1024;

#[cfg(test)]
mod tests;

fn remaining(deadline: Instant) -> Result<Duration> {
    deadline
        .checked_duration_since(Instant::now())
        .filter(|duration| !duration.is_zero())
        .context("Zellij request timed out; outcome may be unknown")
}

/// Each request has its own connection, deadline and acknowledgement. Never replays actions.
pub struct Client<'a> {
    pub socket: &'a Path,
    pub terminal_id: Option<u32>,
    pub deadline: Instant,
}

impl Client<'_> {
    /// Returns the original completion message. Queries wait for Log rather than a generic ack.
    pub fn request(
        &self,
        action: contract::action::ActionType,
        query: bool,
    ) -> Result<ServerToClientMsg> {
        self.exchange(action, |response| {
            let complete = matches!(
                &response.message,
                Some(
                    server_to_client_msg::Message::Log(_)
                        | server_to_client_msg::Message::LogError(_)
                        | server_to_client_msg::Message::Exit(_)
                )
            ) || (!query
                && matches!(
                    &response.message,
                    Some(server_to_client_msg::Message::UnblockInputThread(_))
                ));
            Ok(complete.then_some(response))
        })
    }

    /// Send one explicit pipe payload, collecting matching output until its release acknowledgement.
    /// An empty pipe_id gets a per-invocation routing ID; no stdin stream or replay is attempted.
    pub fn pipe(&self, mut action: contract::CliPipeAction) -> Result<PipeResponse> {
        if action.pipe_id.is_empty() {
            static NEXT: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
            action.pipe_id = format!(
                "{}-{}-{}",
                std::process::id(),
                std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .unwrap_or_default()
                    .as_nanos(),
                NEXT.fetch_add(1, std::sync::atomic::Ordering::Relaxed)
            );
        }
        let pipe_id = action.pipe_id.clone();
        let mut output = String::new();
        self.exchange(contract::action::ActionType::CliPipe(action), |response| {
            let complete = match &response.message {
                Some(server_to_client_msg::Message::CliPipeOutput(chunk))
                    if chunk.pipe_name == pipe_id =>
                {
                    if output.len().saturating_add(chunk.output.len()) > MAX_FRAME {
                        bail!("Zellij pipe output exceeds limit; outcome may be unknown");
                    }
                    output.push_str(&chunk.output);
                    false
                }
                Some(server_to_client_msg::Message::UnblockCliPipeInput(release)) => {
                    release.pipe_name == pipe_id
                }
                Some(server_to_client_msg::Message::Log(log)) => {
                    let text = log.lines.join("\n");
                    if output.len().saturating_add(text.len()) > MAX_FRAME {
                        bail!("Zellij pipe output exceeds limit; outcome may be unknown");
                    }
                    output.push_str(&text);
                    true
                }
                Some(
                    server_to_client_msg::Message::LogError(_)
                    | server_to_client_msg::Message::Exit(_),
                ) => true,
                _ => false,
            };
            Ok(complete.then(|| PipeResponse {
                output: std::mem::take(&mut output),
                completion: response,
            }))
        })
    }

    fn exchange<T>(
        &self,
        action: contract::action::ActionType,
        mut receive: impl FnMut(ServerToClientMsg) -> Result<Option<T>>,
    ) -> Result<T> {
        let message = ClientToServerMsg {
            message: Some(client_to_server_msg::Message::Action(ActionMsg {
                action: Some(Action {
                    action_type: Some(action),
                }),
                terminal_id: self.terminal_id,
                client_id: None,
                is_cli_client: true,
            })),
        };
        let bytes = message.encode_to_vec();
        if bytes.len() > MAX_FRAME {
            bail!("Zellij request exceeds the frame limit");
        }
        let socket = socket2::Socket::new(socket2::Domain::UNIX, socket2::Type::STREAM, None)?;
        socket
            .connect_timeout(
                &socket2::SockAddr::unix(self.socket)?,
                remaining(self.deadline)?,
            )
            .context("Cannot connect to Zellij")?;
        let descriptor: std::os::fd::OwnedFd = socket.into();
        let mut stream = UnixStream::from(descriptor);
        stream.set_nonblocking(true)?;
        let mut frame = (bytes.len() as u32).to_le_bytes().to_vec();
        frame.extend(bytes);
        let mut pending = frame.as_slice();
        while !pending.is_empty() {
            remaining(self.deadline)?;
            let written = match stream.write(pending) {
                Ok(written) => written,
                Err(error) if error.kind() == std::io::ErrorKind::Interrupted => continue,
                Err(error) if error.kind() == std::io::ErrorKind::WouldBlock => {
                    self.wait(&stream, libc::POLLOUT)?;
                    continue;
                }
                Err(error) => {
                    return Err(error).context("Zellij write failed; outcome may be unknown")
                }
            };
            if written == 0 {
                bail!("Zellij disconnected; outcome may be unknown");
            }
            pending = &pending[written..];
        }
        loop {
            let mut header = [0; 4];
            self.read(&mut stream, &mut header)?;
            let length = u32::from_le_bytes(header) as usize;
            if length > MAX_FRAME {
                bail!("Zellij response exceeds the frame limit");
            }
            let mut bytes = vec![0; length];
            self.read(&mut stream, &mut bytes)?;
            let response =
                ServerToClientMsg::decode(bytes.as_slice()).context("Invalid Zellij response")?;
            if let Some(result) = receive(response)? {
                return Ok(result);
            }
            remaining(self.deadline)?;
        }
    }

    fn read(&self, stream: &mut UnixStream, mut bytes: &mut [u8]) -> Result<()> {
        while !bytes.is_empty() {
            remaining(self.deadline)?;
            let length = match stream.read(bytes) {
                Ok(length) => length,
                Err(error) if error.kind() == std::io::ErrorKind::Interrupted => continue,
                Err(error) if error.kind() == std::io::ErrorKind::WouldBlock => {
                    self.wait(stream, libc::POLLIN)?;
                    continue;
                }
                Err(error) => {
                    return Err(error).context("Zellij read failed; outcome may be unknown")
                }
            };
            if length == 0 {
                bail!("Zellij disconnected; outcome may be unknown");
            }
            bytes = &mut bytes[length..];
        }
        Ok(())
    }

    fn wait(&self, stream: &UnixStream, events: libc::c_short) -> Result<()> {
        let mut descriptor = libc::pollfd {
            fd: stream.as_raw_fd(),
            events,
            revents: 0,
        };
        loop {
            let timeout = remaining(self.deadline)?
                .as_millis()
                .saturating_add(1)
                .min(i32::MAX as u128) as i32;
            // SAFETY: descriptor is valid for one pollfd; poll neither retains nor closes it.
            let ready = unsafe { libc::poll(&mut descriptor, 1, timeout) };
            if ready > 0 {
                return Ok(());
            }
            if ready < 0 {
                let error = std::io::Error::last_os_error();
                if error.kind() != std::io::ErrorKind::Interrupted {
                    return Err(error).context("Zellij poll failed; outcome may be unknown");
                }
            }
        }
    }
}

/// Pipe output plus the original release/error message, including an optional exit code.
pub struct PipeResponse {
    pub output: String,
    pub completion: ServerToClientMsg,
}

impl PipeResponse {
    pub fn into_output(self) -> Result<String> {
        match self.completion.message {
            Some(server_to_client_msg::Message::UnblockCliPipeInput(release)) => {
                if release.exit_code.is_some_and(|code| code != 0) {
                    bail!(
                        "Zellij pipe exit {}: {}",
                        release.exit_code.unwrap(),
                        self.output
                    );
                }
                Ok(self.output)
            }
            Some(server_to_client_msg::Message::Log(_)) => Ok(self.output),
            Some(server_to_client_msg::Message::LogError(error)) => {
                bail!("{}\n{}", error.lines.join("\n"), self.output)
            }
            Some(server_to_client_msg::Message::Exit(exit)) => bail!(
                "Zellij pipe exit {}: {}\n{}",
                exit.exit_reason,
                exit.payload.unwrap_or_default(),
                self.output
            ),
            _ => bail!("Missing Zellij pipe completion"),
        }
    }
}

/// Read a completed Action's textual result without discarding server errors.
pub fn output(response: ServerToClientMsg) -> Result<String> {
    match response.message {
        Some(server_to_client_msg::Message::Log(log)) => Ok(log.lines.join("\n")),
        Some(server_to_client_msg::Message::UnblockInputThread(_)) => Ok(String::new()),
        Some(server_to_client_msg::Message::LogError(error)) => bail!("{}", error.lines.join("\n")),
        Some(server_to_client_msg::Message::Exit(exit)) => bail!(
            "Zellij exit {}: {}",
            exit.exit_reason,
            exit.payload.unwrap_or_default()
        ),
        _ => bail!("Missing Zellij completion"),
    }
}
