# Mac approval over ordinary SSH

Intent lets a remote command or Go application request one-time approval on your Mac. Dotfiles configures ordinary OpenSSH sessions to carry those requests automatically. You review the remote caller's reason, then authenticate with an available Mac method: Touch ID, Apple Watch, or password. This is a cooperative checkpoint; approval does not verify or execute the claimed action.

## Configure the Mac

Build and install the updated [Intent](https://github.com/lanej/intent) with its embedded approval SDK, then enable the SSH configuration explicitly:

```sh
cd ~/src/intent
make install
cd ~/.files
make intent-ssh
```

`make intent-ssh` configures an installed binary at `~/.local/bin/intent`; pass `INTENT_BINARY=/absolute/path/intent` for another installation. It requires macOS and OpenSSH 10.3 or newer, validates the resulting configuration with `ssh -G`, and preserves existing SSH settings, including your 1Password `IdentityAgent`. It saves the original config as `~/.ssh/config.before-intent` once. The config includes a generated `~/.ssh/config.d/intent.conf`; its source template is `ssh/intent.conf.template`.

This is an opt-in configuration target. Ordinary `make`, `make shell`, and bootstrap do not install Intent or start an approval service. Remote Linux or macOS hosts need the updated Intent on their noninteractive SSH command PATH. No SSH daemon configuration change is required.

## Use it

Connect normally, including with SSH options or a configured host alias:

```sh
ssh myhost
intent request --reason 'Deploy revision abc123 to production' &&
  ./deploy abc123
```

Direct commands work too:

```sh
ssh myhost "intent request --reason 'Publish build abc123'"
```

The remote Go package is `github.com/lanej/intent`. `intent.ClientFromEnv()` uses an explicit `INTENT_APPROVAL_SOCKET` first; otherwise it discovers a private receipt keyed by the `SSH_CONNECTION` set by sshd. Approval waits within the caller's context for setup to finish. A missing or failed setup cannot return approval, and submitted requests are not automatically retried.

## Connection lifetime and recovery

The generated configuration uses `ControlMaster auto`, a private `ControlPath`, and a 30-second `ControlPersist` timeout. A short `LocalCommand` starts an approval broker scoped to that underlying connection. Shells sharing the connection share the endpoint and its busy slot; every approval requires fresh authentication. The broker leaves your authentication agent and remote shell commands alone. Clients that do not use OpenSSH config need separate integration.

The broker observes its SSH master's process and socket without keeping the connection alive. It stops after the master exits or its socket is replaced. The approval window shows the TCP endpoints reported by the local master; if a proxy transport hides the destination, it explicitly reports that missing destination. The request reason always comes from the remote caller.

Once a transport closes, its remote metadata may remain until the next connection. Subsequent setup removes only owned receipts and matching private session directories whose socket has no listener, with a bounded cleanup pass. It preserves active sessions, unexpected files, and uncertain failures. These receipts contain only endpoint metadata, never credentials or approval decisions. Hook failures are logged under `~/.intent-ssh/*.log`; ordinary SSH remains usable when the remote host has no Intent.

To disable automatic approval for a host, put `PermitLocalCommand no` in that host's earlier SSH configuration. To remove the managed integration for future connections:

```sh
make intent-ssh-remove
```

Removal preserves your other SSH settings and does not interrupt existing connections. The focused setup check is `make test-intent-ssh`; native authentication requires a person at the Mac and is exercised separately in Intent.

## Migrate from Keylease SSH approval

Install [Intent v0.1.0](https://github.com/lanej/intent/releases/tag/v0.1.0) on both ends before enabling `make intent-ssh`. Setup removes the previous dotfiles-owned Keylease include and snippet while preserving unrelated configuration and the original Keylease backup. Intent uses a new control directory, so existing sessions finish naturally; reconnect to use Intent. Remote commands and Go imports must migrate together: `intent request`, `github.com/lanej/intent`, and `INTENT_APPROVAL_SOCKET` replace the former Keylease interfaces without aliases.

Keylease credential approval uses the Intent Go SDK directly and needs no installed Intent CLI. Intent's Mac helper is embedded, ad-hoc signed, and not notarized; no adjacent application bundle is required.
