use super::*;
use contract::{action::ActionType, QueryTabNamesAction};
use std::os::unix::net::UnixListener;
use std::thread;

fn query() -> ActionType {
    ActionType::QueryTabNames(QueryTabNamesAction {})
}

fn send(stream: &mut UnixStream, message: server_to_client_msg::Message) {
    let bytes = ServerToClientMsg {
        message: Some(message),
    }
    .encode_to_vec();
    stream
        .write_all(&(bytes.len() as u32).to_le_bytes())
        .unwrap();
    stream.write_all(&bytes).unwrap();
}

#[test]
fn pipe_waits_for_its_release_and_preserves_output_and_exit_code() {
    let work = tempfile::tempdir().unwrap();
    let path = work.path().join("socket");
    let listener = UnixListener::bind(&path).unwrap();
    let worker = thread::spawn(move || {
        for code in [0, 42] {
            let (mut stream, _) = listener.accept().unwrap();
            let request = receive(&mut stream);
            let Some(client_to_server_msg::Message::Action(action)) = request.message else {
                panic!("Expected Action");
            };
            let Some(ActionType::CliPipe(pipe)) = action.action.unwrap().action_type else {
                panic!("Expected pipe");
            };
            assert_eq!(pipe.pipe_id, "request-1");
            assert_eq!(pipe.payload.as_deref(), Some("payload"));
            for message in [
                server_to_client_msg::Message::UnblockInputThread(
                    contract::UnblockInputThreadMsg {},
                ),
                server_to_client_msg::Message::CliPipeOutput(contract::CliPipeOutputMsg {
                    pipe_name: "other".into(),
                    output: "ignore".into(),
                }),
                server_to_client_msg::Message::UnblockCliPipeInput(
                    contract::UnblockCliPipeInputMsg {
                        pipe_name: "other".into(),
                        exit_code: None,
                    },
                ),
                server_to_client_msg::Message::CliPipeOutput(contract::CliPipeOutputMsg {
                    pipe_name: "request-1".into(),
                    output: "first".into(),
                }),
                server_to_client_msg::Message::CliPipeOutput(contract::CliPipeOutputMsg {
                    pipe_name: "request-1".into(),
                    output: " second".into(),
                }),
                server_to_client_msg::Message::UnblockCliPipeInput(
                    contract::UnblockCliPipeInputMsg {
                        pipe_name: "request-1".into(),
                        exit_code: Some(code),
                    },
                ),
            ] {
                send(&mut stream, message);
            }
        }
    });
    let client = Client {
        socket: &path,
        terminal_id: Some(7),
        deadline: Instant::now() + Duration::from_secs(2),
    };
    let action = contract::CliPipeAction {
        pipe_id: "request-1".into(),
        payload: Some("payload".into()),
        ..Default::default()
    };
    assert_eq!(
        client.pipe(action.clone()).unwrap().into_output().unwrap(),
        "first second"
    );
    let failed = client.pipe(action).unwrap();
    assert_eq!(failed.output, "first second");
    let Some(server_to_client_msg::Message::UnblockCliPipeInput(release)) =
        &failed.completion.message
    else {
        panic!("Expected release");
    };
    assert_eq!(release.exit_code, Some(42));
    assert!(failed
        .into_output()
        .unwrap_err()
        .to_string()
        .contains("42: first second"));
    worker.join().unwrap();
}

#[test]
fn pipe_lost_release_never_replays_the_payload() {
    let work = tempfile::tempdir().unwrap();
    let path = work.path().join("socket");
    let listener = UnixListener::bind(&path).unwrap();
    let worker = thread::spawn(move || {
        let (mut stream, _) = listener.accept().unwrap();
        receive(&mut stream);
        send(
            &mut stream,
            server_to_client_msg::Message::CliPipeOutput(contract::CliPipeOutputMsg {
                pipe_name: "one".into(),
                output: "partial".into(),
            }),
        );
        drop(stream);
        listener.set_nonblocking(true).unwrap();
        assert_eq!(
            listener.accept().unwrap_err().kind(),
            std::io::ErrorKind::WouldBlock
        );
    });
    let client = Client {
        socket: &path,
        terminal_id: None,
        deadline: Instant::now() + Duration::from_secs(1),
    };
    let error = client
        .pipe(contract::CliPipeAction {
            pipe_id: "one".into(),
            ..Default::default()
        })
        .err()
        .unwrap();
    assert!(error.to_string().contains("outcome may be unknown"));
    worker.join().unwrap();
}

fn receive(stream: &mut UnixStream) -> ClientToServerMsg {
    let mut header = [0; 4];
    stream.read_exact(&mut header).unwrap();
    let mut bytes = vec![0; u32::from_le_bytes(header) as usize];
    stream.read_exact(&mut bytes).unwrap();
    ClientToServerMsg::decode(bytes.as_slice()).unwrap()
}

#[test]
fn query_waits_for_fragmented_output_and_preserves_server_errors() {
    let work = tempfile::tempdir().unwrap();
    let path = work.path().join("socket");
    let listener = UnixListener::bind(&path).unwrap();
    let worker = thread::spawn(move || {
        for error in [false, true] {
            let (mut stream, _) = listener.accept().unwrap();
            stream
                .set_read_timeout(Some(Duration::from_secs(1)))
                .unwrap();
            let request = receive(&mut stream);
            let Some(client_to_server_msg::Message::Action(action)) = request.message else {
                panic!("Expected Action");
            };
            assert_eq!(action.terminal_id, Some(7));
            assert!(action.is_cli_client);
            assert_eq!(action.action.unwrap().action_type, Some(query()));
            for message in [
                server_to_client_msg::Message::UnblockInputThread(
                    contract::UnblockInputThreadMsg {},
                ),
                if error {
                    server_to_client_msg::Message::LogError(contract::LogErrorMsg {
                        lines: vec!["denied".into(), "details".into()],
                    })
                } else {
                    server_to_client_msg::Message::Log(contract::LogMsg {
                        lines: vec!["project".into()],
                    })
                },
            ] {
                let bytes = ServerToClientMsg {
                    message: Some(message),
                }
                .encode_to_vec();
                let mut frame = (bytes.len() as u32).to_le_bytes().to_vec();
                frame.extend(bytes);
                for chunk in frame.chunks(2) {
                    stream.write_all(chunk).unwrap();
                }
            }
        }
    });
    let client = Client {
        socket: &path,
        terminal_id: Some(7),
        deadline: Instant::now() + Duration::from_secs(2),
    };
    assert_eq!(
        output(client.request(query(), true).unwrap()).unwrap(),
        "project"
    );
    let error = client.request(query(), true).unwrap();
    assert!(matches!(
        error.message,
        Some(server_to_client_msg::Message::LogError(_))
    ));
    assert_eq!(output(error).unwrap_err().to_string(), "denied\ndetails");
    worker.join().unwrap();
}

#[test]
fn timeout_does_not_replay_and_oversized_responses_fail() {
    for oversize in [false, true] {
        let work = tempfile::tempdir().unwrap();
        let path = work.path().join("socket");
        let listener = UnixListener::bind(&path).unwrap();
        let worker = thread::spawn(move || {
            let (mut stream, _) = listener.accept().unwrap();
            stream
                .set_read_timeout(Some(Duration::from_secs(1)))
                .unwrap();
            receive(&mut stream);
            if oversize {
                stream
                    .write_all(&((MAX_FRAME + 1) as u32).to_le_bytes())
                    .unwrap();
            } else {
                thread::sleep(Duration::from_millis(150));
            }
            listener.set_nonblocking(true).unwrap();
            assert_eq!(
                listener.accept().unwrap_err().kind(),
                std::io::ErrorKind::WouldBlock
            );
        });
        let client = Client {
            socket: &path,
            terminal_id: None,
            deadline: Instant::now() + Duration::from_millis(100),
        };
        let error = client.request(query(), true).unwrap_err().to_string();
        assert!(
            error.contains(if oversize {
                "frame limit"
            } else {
                "outcome may be unknown"
            }),
            "{error}"
        );
        worker.join().unwrap();
    }
}
