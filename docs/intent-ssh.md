# Mac approval over SSH

[Intent](https://github.com/lanej/intent) supplies the approval library and transport tooling. [Keylease](https://github.com/lanej/keylease) remains the credential broker and uses the Intent SDK. Dotfiles installs and updates both tools independently; moving approval transport into Intent does not remove Keylease.

## Install both tools

The `workstation` set selects both tools for `make install`. They can also be selected individually in the machine TOML:

```toml
[tools]
intent = true
keylease = true
```

The selected Keylease plan includes Go and native build tools for its 1Password desktop backend. Explicit installation targets require those prerequisites to be available; Keylease installation rejects a CGO-disabled environment. For explicit installation without the full selected tool plan:

```sh
cd ~/.files
make intent-install keylease-install
```

These targets clone missing sources into `~/src/intent` and `~/src/1password-agent`, then call each project's native `make install` through the project updater. Existing checkouts stay at their selected revision; dirty checkouts are rejected. Keylease's repository requires access to the private repository. Installation preserves running brokers, leases and credentials. Ordinary `make`, `make shell` and bootstrap do not install either tool or activate SSH approval.

Use `project-update pull intent` and `project-update pull keylease` to advance clean default-branch checkouts, then `project-update build intent` and `project-update build keylease` to install them. See [project updates](project-updates.md).

## Existing profiles and SSH setup

Project updates discover existing Intent profiles and paired remote brokers through owner-native lifecycle controls. They stage verified platform binaries, bind native broker ownership and pairing IDs, and preserve stable sockets, routing IDs, and existing SSH connections. Unknown legacy brokers, mismatched pairings, or unreachable targets remain explicitly incomplete. See [project updates](project-updates.md) for activation and recovery.

Installation does not configure automatic approval for ordinary SSH sessions. The [stable remote socket design and executable proof](https://github.com/lanej/intent/tree/main/experiments/stable-socket) uses dedicated SSH connections and a broker-owned stable socket without requiring connection multiplexing. `make intent-ssh` remains a guarded setup target that fails without changing configuration; existing explicitly configured profiles are separate from automatic workstation setup.

The proof demonstrates route handover, caller cancellation and transport loss without replay using a disposable real SSH server and synthetic native decisions. Human Touch ID, Apple Watch and password interaction remains unverified. Its README contains the explicit experimental commands and limits; do not treat it as automatic workstation setup.

## Retire the old managed hook

Remove the obsolete dotfiles-owned approval snippets and their exact managed Include blocks explicitly:

```sh
make intent-ssh-remove
```

This also removes the old Keylease approval hook. The compatibility target `make keylease-ssh-remove` performs the same cleanup. Removal preserves both installed tools, existing sessions, backups, authentication-agent settings and other user configuration. It refuses unmanaged snippets or malformed managed blocks. User-authored SSH options and broad Includes remain yours to edit; the cleanup does not rewrite them or terminate connections.

## Application interfaces

Remote cooperative callers use `intent request --reason 'Publish build abc123'`, the Go package `github.com/lanej/intent`, and an explicitly configured `INTENT_APPROVAL_SOCKET`. These interfaces replace the former Keylease approval commands and imports. Install Intent on remote hosts that invoke its CLI; Go applications may embed its SDK. The SDK embedded in Keylease does not require an installed Intent CLI for local credential approval.

Approval is a cooperative checkpoint. You review the caller-supplied reason and authenticate locally; approval does not verify or execute the claimed action. Credentials and authentication data do not travel to the remote caller.
