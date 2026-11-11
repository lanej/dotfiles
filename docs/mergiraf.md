# Mergiraf trial

[Mergiraf](https://mergiraf.org/) adds syntax-aware merging to Git. The `shell` set selects it by default; installation activates the driver globally for the installed version's supported file types. The minimal `base` set does not select it, and machines can opt out with `tools.mergiraf = false`.

## Install and activate

Run `make plan` and `make install` to install and activate the shell default. Machines outside the `shell` set can select it with `mergiraf = true` under the existing `[tools]` table in their machine TOML (`~/.config/dotfiles/config.toml`, or the configured alternative). The catalog requires Mergiraf 0.20.0 or newer and supplies a locked Cargo install of 0.20.0 when the package manager cannot provide a suitable version. Its dependencies are Git and Rust.

Configuration runs `mergiraf languages --gitattributes` and combines those rules with the existing diff attributes in `~/.config/dotfiles/mergiraf/attributes`. Git reads the result through the managed `~/.gitattributes` link. No per-repository setup is needed. The installed 0.20.0 binary advertises Markdown as well as TOML, JSON, Lua, and other languages; Zsh is not included. The generated rules follow the installed binary rather than a separately maintained extension list.

Repository `.gitattributes` and `.git/info/attributes` retain precedence over these global defaults. To use ordinary text merging for one pattern in a repository, add:

```gitattributes
*.toml merge=text
```

Use `git rev-parse --git-path info/attributes` to locate the local attributes file in a worktree, and preserve existing rules. Global activation does not change collaborators' configuration.

Use `diff3` for trial merges and rebases:

```sh
git -c merge.conflictStyle=diff3 merge other-branch
git -c merge.conflictStyle=diff3 rebase origin/master
```

The global `zdiff3` preference stays intact. Mergiraf's manual `mergiraf solve path/to/file` command needs the base revision in conflict markers; `zdiff3` can trim that information and prevent reconstruction. The driver receives all three original files, so it does not depend on reconstructing them from existing conflict markers. See [upstream usage](https://mergiraf.org/usage.html).

Review automatic resolutions with the `mergiraf review <merge-id>` command printed by the driver, inspect the resulting diff, and run the affected checks. Fugitive remains the configured manual merge tool. Syntax-aware merging cannot establish that the combined behavior is correct.

To retry an unsatisfactory merge, abort that operation first, then rerun with Mergiraf disabled:

```sh
git merge --abort
mergiraf=0 git merge other-branch
```

For a rebase, use `git rebase --abort` and `mergiraf=0 git rebase ...`. To disable activation permanently, set `mergiraf = false` under `[tools]` and run `make configure`; Git setup restores the base attributes link. This does not uninstall the binary. Configuration never installs software: selecting Mergiraf before installing its executable produces a missing-dependency error; run `make install` to install and activate it together.

## Concrete examples

These are synthetic examples shaped like this repository's tool configuration and Neovim Lua, exercised with real Git merges and Mergiraf 0.20.0. They demonstrate specific cases, not a measured reduction in this repository's historical conflicts. Run the comparison without changing your checkout or Git configuration:

```sh
python3 scripts/test-mergiraf.py
```

The script creates disposable repositories and a temporary home, runs the real `make mergiraf-config` target, reads the driver and attributes location from `git/gitconfig`, and prints ordinary Git and Mergiraf results. It checks the expected combinations, retained disagreements, rerun stability, repository overrides, and the escape hatch. CI runs the same comparison on macOS and Linux.

| Concurrent change | Ordinary Git | Mergiraf |
| --- | --- | --- |
| Add different tools under `[tools]` | Conflict | Retains both additions |
| Change different fields on one Lua line | Conflict | Retains both edits |
| Set one TOML key to different values | Conflict | Retains the conflict |
| Add the same JSON key at different locations with different values | Clean merge with duplicate keys | Flags a conflict |

### Add different tools

Both branches start with `[tools]` containing `git = true`. One adds `mergiraf = true`; the other adds `zellij = true`. Git sees competing insertions at the same location:

```toml
[tools]
git = true
<<<<<<< HEAD
mergiraf = true
||||||| BASE
=======
zellij = true
>>>>>>> theirs
```

Mergiraf keeps both independent entries:

```toml
[tools]
git = true
mergiraf = true
zellij = true
```

### Edit separate Lua fields

Base:

```lua
return { timeout = 1000, enabled = false }
```

One branch reduces `timeout` to `500`; the other enables the option. Git conflicts on the whole line. Mergiraf produces:

```lua
return { timeout = 500, enabled = true }
```

### Preserve a real disagreement

Starting from `timeout = 1000`, one branch chooses `500` and the other chooses `2000`. Both tools leave a conflict requiring a decision:

```toml
[editor]
<<<<<<< HEAD
timeout = 500
||||||| BASE
timeout = 1000
=======
timeout = 2000
>>>>>>> theirs
```

### Reveal duplicate JSON keys

One branch inserts `"timeout": 500` at the beginning of an existing JSON object; another appends `"timeout": 2000` at the end. Git merges both without a conflict:

```json
{
  "timeout": 500,
  "alpha": 1,
  "beta": 2,
  "gamma": 3,
  "delta": 4,
  "timeout": 2000
}
```

Mergiraf detects the duplicate key and asks for a decision instead of silently retaining both values. In the conflict examples above, `BASE` replaces the temporary commit hash for readability; the script prints actual Git output.
