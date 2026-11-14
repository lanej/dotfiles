# Mac approval over ordinary SSH

Keylease lets a remote command or Go application request one-time approval on your Mac. Dotfiles configures ordinary OpenSSH sessions to carry those requests automatically. You review the remote caller's reason, then authenticate with an available Mac method: Touch ID, Apple Watch, or password. This is a cooperative checkpoint; approval does not verify or execute the claimed action.

## Configure the Mac

Build and install the updated [Keylease](https://github.com/lanej/keylease) with its native approval app, then enable the SSH configuration explicitly:

```sh
cd ~/src/1password-agent
make install
cd ~/.files
make keylease-ssh
```

`make keylease-ssh` configures an installed binary at `~/.local/bin/keylease`; pass `KEYLEASE_BINARY=/absolute/path/keylease` for another installation. It requires macOS and OpenSSH 10.3 or newer, validates the resulting configuration with `ssh -G`, and preserves existing SSH settings, including your 1Password `IdentityAgent`. It saves the original config as `~/.ssh/config.before-keylease` once. The config includes a generated `~/.ssh/config.d/keylease.conf`; its source template is `ssh/keylease.conf.template`.

This is an opt-in configuration target. Ordinary `make`, `make shell`, and bootstrap do not install Keylease or start an approval service. Remote Linux or macOS hosts need the updated Keylease on their noninteractive SSH command PATH. No SSH daemon configuration change is required.

## Use it

Connect normally, including with SSH options or a configured host alias:

```sh
ssh myhost
keylease approval request --reason 'Deploy revision abc123 to production' &&
  ./deploy abc123
```

Direct commands work too:

```sh
ssh myhost "keylease approval request --reason 'Publish build abc123'"
```

The remote Go package is `github.com/lanej/keylease/approval`. `approval.ClientFromEnv()` uses an explicit `KEYLEASE_APPROVAL_SOCKET` first; otherwise it discovers a private receipt keyed by the `SSH_CONNECTION` set by sshd. Approval waits within the caller's context for setup to finish. A missing or failed setup cannot return approval, and submitted requests are not automatically retried.

## Connection lifetime and recovery

The generated configuration uses `ControlMaster auto`, a private `ControlPath`, and a 30-second `ControlPersist` timeout. A short `LocalCommand` starts an approval broker scoped to that underlying connection. Shells sharing the connection share the endpoint and its busy slot; every approval requires fresh authentication. The broker leaves your authentication agent and remote shell commands alone. Clients that do not use OpenSSH config need separate integration.

The broker observes its SSH master's process and socket without keeping the connection alive. It stops after the master exits or its socket is replaced. The approval window shows the TCP endpoints reported by the local master; if a proxy transport hides the destination, it explicitly reports that missing destination. The request reason always comes from the remote caller.

Once a transport closes, its remote metadata may remain until the next connection. Subsequent setup removes only owned receipts and matching private session directories whose socket has no listener, with a bounded cleanup pass. It preserves active sessions, unexpected files, and uncertain failures. These receipts contain only endpoint metadata, never credentials or approval decisions. Hook failures are logged under `~/.keylease-ssh/*.log`; ordinary SSH remains usable when the remote host has no Keylease.

To disable automatic approval for a host, put `PermitLocalCommand no` in that host's earlier SSH configuration. To remove the managed integration for future connections:

```sh
make keylease-ssh-remove
```

Removal preserves your other SSH settings and does not interrupt existing connections. The focused setup check is `make test-keylease-ssh`; native authentication requires a person at the Mac and is verified separately in Keylease.
