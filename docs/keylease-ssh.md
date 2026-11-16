# Keylease and SSH approval

Keylease remains installed by dotfiles as the credential broker. Its approval library and SSH transport moved to [Intent](intent-ssh.md); this separation does not uninstall Keylease or stop existing brokers and leases.

The `workstation` set selects both tools for `make install`. Explicit installation is `make intent-install keylease-install`. Follow [the current SSH approval guidance](intent-ssh.md) for installation, transport status and removal of the obsolete managed hook. Automatic SSH activation awaits production integration of the stable remote socket design.
