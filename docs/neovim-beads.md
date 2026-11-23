# Beads tasks in Neovim

`:Beads` opens a persistent task explorer beside ordinary editable Markdown documents. Browsing, creating, editing and saving tasks work without chat or a Pi worker. The [Beads service](beads.md) owns durable task state; saving never dispatches work or records a planning/review approval.

## Configuration

Set `vim.g.beads` before loading the dotfiles configuration, or call `require("beads").setup(...)` explicitly after startup. No service is contacted at startup. Projects are explicit and independent of the source checkout or current working directory:

```lua
require("beads").setup({
  default_project = "personal",
  projects = {
    personal = {
      url = "http://127.0.0.1:8790",
      project_id = "your-project-uuid",
      -- prefix = "octo", -- Required if issue_prefix is unavailable from the API.
      -- token_file = "/absolute/path/to/token",
      -- actor = "nvim",
    },
  },
})
```

Use the project ID reported by `GET /v0/beads/context`. The client requires the configured project, Dolt server backend and necessary capabilities to match; it does not adopt a different workspace automatically. Remote HTTP requires a loopback tunnel; non-loopback services require HTTPS. Token files are read for requests and excluded from command arguments and error messages. The editor uses Neovim, curl and the pinned Nui library already installed by this configuration. Changing an already configured project's authority requires restarting Neovim.

## Navigation

| Command | Action |
|---|---|
| `:Beads [project]` | Open or focus that project's persistent explorer. |
| `:BeadsOpen [id]` | Open a task in a normal editing window; reuse its buffer across windows/tabs. |
| `:BeadsNew [parent-id]` | Open an unsaved root or child draft. |
| `:BeadsRefresh` | Refresh the graph while preserving expansion, selection, focus and dirty documents. |
| `:BeadsRelationships` | Inspect incoming/outgoing relationships and open a linked task. |
| `:BeadsStatus status` | Explicitly change status under revision and server policy checks. |
| `:BeadsRecover` | Open a durable pending-creation draft for reconciliation. |
| `:BeadsReload[!]` | Reload an existing task's latest document/revision; `!` explicitly replaces unsaved text. |

In the explorer use `j`/`k` to move, `l` to expand, `h` to collapse or move to the parent, Tab to toggle, Enter/`o` to open, `a` to create a child, `A` to create a root, `s` to enter a status, `gr` for relationships, `r` to refresh and `q` to close the explorer. Blocker links are independent of nesting. Containment does not indicate readiness or authorize child dispatch. Orphans and cyclic containment remain inspectable with warnings.

Filled status icons identify tasks: `` open, `󰐊` in progress, `` blocked, `󰥔` deferred and `` closed. Custom states retain their names. Task state comes from Beads. There is no stock attention field shared by every controller: an optional project `attention = function(task) ... end` can return a compact label from the controller-owned metadata available in that project. Returning nil displays no signal; status and attention never substitute for runtime admission checks.

![Neovim screen cells at 120 columns](screenshots/neovim-beads/120-columns.png)

[The 64-column capture](screenshots/neovim-beads/64-columns.png) exercises the same split and editable document at a narrower width. These images preserve RGB highlight attributes and bold Nerd Font glyphs from an isolated Neovim UI.

## Appearance

The sidebar uses the pinned [Nui tree component](https://github.com/MunifTanjim/nui.nvim/tree/main/lua/nui/tree) for task nodes, with file-browser conventions familiar from nvim-tree: disclosure arrows, branch guides, emphasized parents and a distinct selection. The fixed-width panel has a project summary, keyboard hints and visible loading/stale states. Long titles are clipped at character boundaries to fit the panel; open the document to read the full title and task identity.

Highlights resolve through the shared dotfiles theme’s semantic roles and survive colorscheme reloads. Status and attention have separate colors. Icons use the terminal’s Nerd Font; the editor configuration uses Hack Nerd Font Mono. The document shows saved, unsaved, failed or pending-creation state beside its managed context. Word-boundary wrapping and conceal settings are restored when the window returns to a different buffer.

## Editing and explicit saves

The first line is `# Title`. All text below it and above the generated `<!-- beads:acceptance:… -->` boundary maps to the description; text below the boundary maps to `acceptance_criteria`. New drafts include problem, outcome, scope, constraints and source-link headings. Existing headings, fenced examples and trailing newlines round-trip without being reinterpreted as fields. The managed boundary displays as an acceptance heading with conceal enabled; `:setlocal conceallevel=0` reveals its exact marker if it needs repair. Preserve the unique boundary when editing; missing or duplicated boundaries fail validation before any write.

Use `:write` to save. Identity, revision, parent and runtime ownership are managed separately from Markdown. A child draft has no bound Bead ID until the first successful save atomically creates the task and its parent link. Later saves update the same identity with revision checks and preserve assignee, attempt and unrelated metadata. Editing a claimed brief changes the revision, so the existing runtime's accepted-brief checks refuse stale work. Status changes are separate actions and honor close/blocker policy without force overrides.

Switching nodes, hiding/closing the explorer or closing a separate chat neither saves nor discards document text. Normal hidden buffers retain edits; explicit forced buffer deletion or quitting Neovim can discard ordinary unsaved text. A refresh updates the graph only. If text changes while a save runs, the newer text stays modified and requires another explicit save.

## Conflicts and uncertain creation

A failed or conflicting save retains edits and the original revision. Compare the task's current state before resolving the conflict; copy the local text to a separate ordinary buffer/file if needed, then use `:BeadsReload!` to deliberately replace the document with its latest remote revision. Apply the intended changes to that refreshed document and save again. Refresh never silently rebases a dirty document.

Before creation, the editor writes a private receipt under `stdpath("state")/beads`. After a lost response, `:write` on that draft or `:BeadsRecover` after restart only reconciles the recorded operation; it never sends another create request. Successful reconciliation requires the same project, operation marker, parent and submitted authored fields. Local edits made after submission remain modified.

Missing tasks, unavailable reads, mismatched markers/parents or intervening remote edits leave the draft and receipt pending for manual inspection. A missing task does not prove creation never committed. Inspect the target through the configured service and preserve the receipt/draft while resolving the outcome; do not delete the receipt merely to retry. The receipt stores the submitted text, not a crash-proof journal of subsequent unsaved keystrokes. A confirmed no-write server refusal permits a corrected explicit save.

## Development checks

`make test-nvim-beads` exercises public editor commands against a controlled HTTP boundary, including lost responses and recovery in a new Neovim process. It uses the installed Nui checkout at the lockfile revision; set `NVIM_TEST_NUI=/path/to/nui.nvim` to select another checkout of that same revision. `make check-beads-lua` checks generated binding freshness after `npm ci --prefix tools/task-runtime`. Regenerate using `npm --prefix tools/task-runtime run generate:beads-lua`; keep the schema and both generated clients synchronized when updating Beads.

For native compatibility, use a [Studio source checkout](https://github.com/lanej/studio) with its pinned Bun version and locked dependencies installed, then run `make test-nvim-beads-native STUDIO_TEST_SOURCE=/absolute/path/to/studio BEADS_TEST_BD=/path/to/pinned/bd BEADS_TEST_DOLT=/path/to/pinned/dolt`. The harness imports Studio’s isolated fixtures and runtime guard directly; CI pins that public source checkout to a specific commit. The native check creates disposable task storage, verifies atomic relationships and guarded saves, and checks that editing claimed work preserves ownership while the existing runtime rejects the old accepted brief. It never targets the installed task service.

`uv run --script scripts/capture-nvim-beads.py` reproduces the normal and narrow RGB captures using the same disposable HTTP fixture. Override `--nui`, `--fonts` or `--output-dir` as needed; `--fonts` expects the regular and bold Hack Nerd Font Mono files. This capture tooling is independent of editor runtime dependencies.
