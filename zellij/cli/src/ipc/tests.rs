use super::*;
use contract::{action::ActionType, QueryTabNamesAction};
use std::os::unix::net::UnixListener;
use std::thread;

fn query() -> ActionType {
    ActionType::QueryTabNames(QueryTabNamesAction {})
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
