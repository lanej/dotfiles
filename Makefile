.DEFAULT_GOAL := setup
SETUP_TARGETS += shell git tmux-config tmux-plugins vim-config sql-formatters ruby kitty-config kitty-terminfo
SETUP_TARGETS += zsh-config zsh-plugins wezterm python go claude-config cargo presenterm mail quarto codex-config codex-mcp
SETUP_TARGETS += dev-cache-config
LINUX_SETUP_TARGETS := X polybar bspwm
DARWIN_SETUP_TARGETS := yabai
DOTFILES := $(shell pwd)
GO ?= go
INSTRUCTION_SIZE_BASE ?= HEAD
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Linux)
SETUP_TARGETS += $(LINUX_SETUP_TARGETS)
else ifeq ($(UNAME_S),Darwin)
SETUP_TARGETS += $(DARWIN_SETUP_TARGETS)
endif

# The runner reports every step and returns failure only after trying them all.
all: setup

setup:
ifneq ($(findstring n,$(firstword $(filter-out --%,$(MAKEFLAGS)))),)
	+@$(MAKE) -f "$(firstword $(MAKEFILE_LIST))" --no-print-directory --keep-going $(SETUP_TARGETS)
else
	+@bash "$(DOTFILES)/scripts/setup-checklist.sh" $(MAKE) -f "$(firstword $(MAKEFILE_LIST))" --no-print-directory --keep-going -- $(SETUP_TARGETS)
endif

define require-command
	@command -v "$(1)" >/dev/null 2>&1 || { printf '%s\n' 'Missing dependency: $(1). Install it or add it to PATH, then rerun make.' >&2; exit 1; }
endef

define require-os
	@test "$(UNAME_S)" = "$(1)" || { printf '%s\n' '$@: requires $(1); detected $(UNAME_S).' >&2; exit 1; }
endef

instruction-size:
	$(call require-command,git)
	$(call require-command,jq)
	@bash "$(DOTFILES)/claude/evals/skill-maintenance/check_size.sh" --base "$(INSTRUCTION_SIZE_BASE)" --installed-home "$(HOME)"

lint: audit-skills instruction-size

banner:
	@cat banner.txt
dev:
	@mkdir -p $(HOME)/src
shell:
	@mkdir -p $(HOME)/.local/bin
	@ln -fs $(DOTFILES)/bin/* $(HOME)/.local/bin/
	@ln -fs $(DOTFILES)/sh/alias $(HOME)/.alias
	@ln -fs $(DOTFILES)/sh/profile $(HOME)/.profile
	@mkdir -p $(HOME)/.config/htop
	@ln -fs $(DOTFILES)/sh/htoprc $(HOME)/.config/htop/htoprc
	@mkdir -p $(HOME)/.config/bottom
	@ln -fs $(DOTFILES)/sh/bottom.toml $(HOME)/.config/bottom/bottom.toml
	@mkdir -p $(HOME)/.config/btop
	@ln -fs $(DOTFILES)/btop/btop.conf $(HOME)/.config/btop/btop.conf
	@mkdir -p $(HOME)/.local/share/z
	@touch "$(HOME)/.z"
	@ln -fs $(DOTFILES)/share/z.sh $(HOME)/.local/share/z/z.sh
	@ln -fs $(DOTFILES)/sh/starship.toml $(HOME)/.config/starship.toml
	@mkdir -p $(HOME)/.config/atuin
	@ln -fs $(DOTFILES)/sh/atuin.toml $(HOME)/.config/atuin/config.toml
	@ln -fs $(DOTFILES)/sh/dircolors $(HOME)/.dir_colors
	@ln -fs $(DOTFILES)/bash/bashrc $(HOME)/.bashrc
	@ln -fs $(DOTFILES)/bash/bashenv $(HOME)/.bashenv
	@ln -fs $(DOTFILES)/bash/bashrc $(HOME)/.bashrc
	@ln -fs $(DOTFILES)/bash/bashprofile $(HOME)/.bash_profile
	@ln -fns $(DOTFILES)/bat $(HOME)/.config/bat
	@ln -fs $(HOME)/.alias $(HOME)/.bashalias
	@mkdir -p $(HOME)/.config/glow
	@ln -fs $(DOTFILES)/sh/glow.yml $(HOME)/.config/glow/glow.yml
	@ln -fs $(DOTFILES)/sh/glow.nord.json $(HOME)/.config/glow/nord.json
zsh: zsh-config zsh-plugins
zsh-config: shell
	@ln -fs $(DOTFILES)/zsh/zshrc $(HOME)/.zshrc
	@ln -fs $(DOTFILES)/zsh/zlogout $(HOME)/.zlogout
	@ln -fs $(DOTFILES)/zsh/zlogin $(HOME)/.zlogin
	@ln -fs $(DOTFILES)/zsh/zshenv $(HOME)/.zshenv
	@mkdir -p $(HOME)/.config/zsh/
	@mkdir -p $(HOME)/.local/share/zsh/
	@mkdir -p $(HOME)/.local/share/zsh/site-functions
	@mkdir -p $(HOME)/.zsh/completions
	@mkdir -p $(HOME)/.zsh/cache
	@ln -fs $(DOTFILES)/zsh/zshenv $(HOME)/.zshenv
	@ln -fns $(DOTFILES)/zsh/zsh-autosuggestions $(HOME)/.local/share/zsh/autosuggestions
	@ln -fns $(DOTFILES)/zsh/zsh-syntax-highlighting $(HOME)/.local/share/zsh/zsh-syntax-highlighting
	@ln -fns $(DOTFILES)/zsh/zsh-github-copilot.plugin.zsh $(HOME)/.local/share/zsh/zsh-github-copilot.zsh
	@ln -fs $(DOTFILES)/zsh/tmux-auto-title.zsh $(HOME)/.local/share/zsh/tmux-auto-title.zsh
zsh-plugins: zsh-config
	$(call require-command,git)
	@[ -e "$(HOME)/.local/share/fzf-tab/.git" ] || \
		git clone -q https://github.com/Aloxaf/fzf-tab "$(HOME)/.local/share/fzf-tab"
tmux: tmux-config tmux-plugins
tmux-config:
	@mkdir -p $(HOME)/.config/tmux/
	@ln -fs $(DOTFILES)/rc/tmux.conf $(HOME)/.config/tmux
	@ln -fs $(DOTFILES)/rc/tmux.conf $(HOME)/.tmux.conf
tmux-plugins: tmux-config
	$(call require-command,tmux)
	$(call require-command,git)
	@bash "$(DOTFILES)/scripts/install-tmux-plugins.sh" "$(DOTFILES)"
tmux-status-legend:
	@"$(DOTFILES)/bin/tmux-claude-state" legend
tmux-program-status:
	@"$(if $(AGENT_STATUS_SOURCE),$(AGENT_STATUS_SOURCE),$(HOME)/src/agent-status-broker)/tmux/build" "$(HOME)/.local/bin/tmux-program-status"
sql-formatters:
	@mkdir -p $(HOME)/.local/bin
	@ln -fs $(DOTFILES)/rc/sql-formatter.json $(HOME)/.sql-formatter.json
	@ln -fs $(DOTFILES)/rc/sqlfluff $(HOME)/.sqlfluff
	@ln -fs $(DOTFILES)/bin/sql-format-bigquery $(HOME)/.local/bin/sql-format-bigquery
	$(call require-command,$(UV))
	@"$(UV)" run --script "$(DOTFILES)/bin/sql-format-bigquery" --help >/dev/null
vim: vim-config sql-formatters
vim-config:
	@touch $(HOME)/.netrc
	@mkdir -p $(HOME)/.cache/nvim/undo
	@mkdir -p $(HOME)/.config/
	@ln -fns $(DOTFILES)/vim $(HOME)/.vim
	@ln -fs $(DOTFILES)/vim/init.vim $(HOME)/.vimrc
	@ln -fns $(DOTFILES)/nvim $(HOME)/.config/nvim
	@ln -fs $(DOTFILES)/.lua-format $(HOME)/.lua-format
	@mkdir -p $(HOME)/.local/share/nvim/site/autoload
	@mkdir -p $(HOME)/.local/share/nvim/min
	@ln -fns $(DOTFILES)/ctags $(HOME)/.ctags.d
X:
	$(call require-os,Linux)
	@ln -fs $(DOTFILES)/rc/Xresources $(HOME)/.Xresources
	@ln -fs $(DOTFILES)/rc/Xresources $(HOME)/.Xdefaults
	@ln -fs $(DOTFILES)/rc/xinitrc $(HOME)/.xinitrc
	@ln -fs $(DOTFILES)/rc/xsessionrc $(HOME)/.xsessionrc
	@ln -fs $(DOTFILES)/rc/xscreensaver $(HOME)/.xscreensaver
ruby:
	@ln -fs $(DOTFILES)/ruby/irbrc $(HOME)/.irbrc
	@ln -fs $(DOTFILES)/ruby/pryrc $(HOME)/.pryrc
	@ln -fs $(DOTFILES)/ruby/rdebugrc $(HOME)/.rdebugrc
	@ln -fs $(DOTFILES)/ruby/gemrc $(HOME)/.gemrc
	@ln -fs $(DOTFILES)/ruby/rspec $(HOME)/.rspec
git:
	@ln -fs $(DOTFILES)/git/gitconfig $(HOME)/.gitconfig
	@ln -fs $(DOTFILES)/git/gitignore $(HOME)/.gitignore
	@ln -fs $(DOTFILES)/git/gitcommit $(HOME)/.gitcommit
	@ln -fs $(DOTFILES)/git/gitattributes $(HOME)/.gitattributes
	@ln -fs $(DOTFILES)/git/hooks/pre-commit $(DOTFILES)/.git/hooks/pre-commit
	@ln -fs $(DOTFILES)/git/hooks/commit-msg $(DOTFILES)/.git/hooks/commit-msg
gpg:
	@mkdir -p $(HOME)/.gnupg
	@ln -fs $(DOTFILES)/rc/gpg.conf $(HOME)/.gnupg/gpg.conf
	@ln -fs $(DOTFILES)/rc/gpg-agent.conf $(HOME)/.gnupg/gpg-agent.conf
	@chmod 700 $(HOME)/.gnupg
yabai:
	$(call require-os,Darwin)
	@mkdir -p $(HOME)/.config/skhd
	@ln -fs $(DOTFILES)/yabai/skhdrc $(HOME)/.config/skhd/skhdrc
	@mkdir -p $(HOME)/.config/yabai
	@ln -fs $(DOTFILES)/yabai/yabairc $(HOME)/.config/yabai/yabairc
	@mkdir -p $(HOME)/.config/borders
	@ln -fs $(DOTFILES)/yabai/bordersrc $(HOME)/.config/borders/bordersrc
polybar:
	$(call require-os,Linux)
	@mkdir -p $(HOME)/.config
	@ln -fns $(DOTFILES)/polybar $(HOME)/.config/polybar
bspwm:
	$(call require-os,Linux)
	@mkdir -p $(HOME)/.config/bspwm
	@mkdir -p $(HOME)/.config/sxhkd
	@mkdir -p $(HOME)/.config/rofi
	@touch $(HOME)/.xsession
	@ln -fs $(DOTFILES)/bspwm/bspwmrc $(HOME)/.config/bspwm/bspwmrc
	@ln -fs $(DOTFILES)/bspwm/sxhkdrc $(HOME)/.config/sxhkd/sxhkdrc
	@ln -fs $(DOTFILES)/rc/config.rasi $(HOME)/.config/rofi/config.rasi
kitty: kitty-config kitty-terminfo
kitty-config:
	@mkdir -p $(HOME)/.config/kitty
	@ln -fs $(DOTFILES)/kitty/kittyconf $(HOME)/.config/kitty/kitty.conf
	@ln -fs $(DOTFILES)/kitty/close_tab_with_confirmation.py $(HOME)/.config/kitty/close_tab_with_confirmation.py
	@ln -fs $(DOTFILES)/kitty/open_last_url.py $(HOME)/.config/kitty/open_last_url.py
python:
	@mkdir -p $(HOME)/.config/
	@ln -fs $(DOTFILES)/python/pycodestyle $(HOME)/.config/pycodestyle
wezterm:
	@mkdir -p $(HOME)/.config/wezterm
	@ln -fs $(DOTFILES)/wezterm.lua $(HOME)/.wezterm.lua
	@ln -fs $(DOTFILES)/wezterm.lua $(HOME)/.config/wezterm/wezterm.lua
# Opt-in restore: quit Amphetamine first; its preferences must not be symlinked.
AMPHETAMINE_PREFS ?= $(HOME)/Library/Containers/com.if.Amphetamine/Data/Library/Preferences/com.if.Amphetamine
amphetamine:
ifeq ($(UNAME_S),Darwin)
	@pgrep -x Amphetamine >/dev/null; status=$$?; \
	if [ "$$status" -eq 0 ]; then \
		echo "Quit Amphetamine before restoring its settings." >&2; exit 1; \
	elif [ "$$status" -ne 1 ]; then \
		exit "$$status"; \
	fi
	@plutil -lint "$(DOTFILES)/amphetamine/settings.plist" >/dev/null
	@defaults write "$(AMPHETAMINE_PREFS)" "Trigger Data" "$$(plutil -extract 'Trigger Data' xml1 -o - "$(DOTFILES)/amphetamine/settings.plist")"
	@defaults write "$(AMPHETAMINE_PREFS)" "Enable Triggers" -bool "$$(plutil -extract 'Enable Triggers' raw -o - "$(DOTFILES)/amphetamine/settings.plist")"
	@echo "Amphetamine trigger settings restored. Reopen Amphetamine."
else
	@echo "Amphetamine settings require macOS." >&2; exit 1
endif
undercurl:
	/bin/bash -c "printf '\e[4:3mUndercurled?\n'"
go:
	@mkdir -p $(HOME)/.config/go
	@ln -fs $(DOTFILES)/go/env $(HOME)/.config/go/env
cargo:
	@mkdir -p $(HOME)/.cargo
	@ln -fs $(DOTFILES)/cargo/config.toml $(HOME)/.cargo/config.toml
dev-cache-config:
	@mkdir -p "$(HOME)/.local/bin" "$(HOME)/.config"
	@ln -fs "$(DOTFILES)/bin/dev-cache-prune" "$(HOME)/.local/bin/dev-cache-prune"
	@test -f "$(HOME)/.config/dev-cache-budgets.json" || cp "$(DOTFILES)/rc/dev-cache-budgets.json" "$(HOME)/.config/dev-cache-budgets.json"
FORCE:
DEV_CACHE_NODE_PATH = $(shell dirname "$$(command -v node || echo /usr/bin/node)"):$(shell dirname "$$(command -v npm || echo /usr/bin/npm)")
DEV_CACHE_GOPATH = $(shell GOTOOLCHAIN=local GOWORK=off go env GOPATH 2>/dev/null)
dev-cache-schedule: dev-cache-config FORCE
	@mkdir -p "$(HOME)/.local/state/dev-cache-prune"
ifeq ($(UNAME_S),Darwin)
	@mkdir -p "$(HOME)/Library/LaunchAgents"
	@sed -e 's|__HOME__|$(HOME)|g' -e 's|__NODE_PATH__|$(DEV_CACHE_NODE_PATH)|g' -e 's|__GOPATH__|$(DEV_CACHE_GOPATH)|g' "$(DOTFILES)/rc/launchd/com.joshlane.dev-cache-prune.plist.template" > "$(HOME)/Library/LaunchAgents/com.joshlane.dev-cache-prune.plist"
	@launchctl unload "$(HOME)/Library/LaunchAgents/com.joshlane.dev-cache-prune.plist" 2>/dev/null || true
	@launchctl load -w "$(HOME)/Library/LaunchAgents/com.joshlane.dev-cache-prune.plist"
else
	@mkdir -p "$(HOME)/.config/systemd/user"
	@sed -e 's|__HOME__|$(HOME)|g' -e 's|__NODE_PATH__|$(DEV_CACHE_NODE_PATH)|g' -e 's|__GOPATH__|$(DEV_CACHE_GOPATH)|g' "$(DOTFILES)/rc/systemd/dev-cache-prune.service.template" > "$(HOME)/.config/systemd/user/dev-cache-prune.service"
	@cp "$(DOTFILES)/rc/systemd/dev-cache-prune.timer.template" "$(HOME)/.config/systemd/user/dev-cache-prune.timer"
	@systemctl --user daemon-reload
	@systemctl --user enable --now dev-cache-prune.timer
endif

test-dev-cache-prune: FORCE
	@python3 "$(DOTFILES)/scripts/test-dev-cache-prune.py"
test-git-worktree-cleanup: FORCE
	@python3 "$(DOTFILES)/scripts/test-git-worktree-cleanup.py"
	@python3 "$(DOTFILES)/scripts/test-git-worktree-size-cache.py"
	@python3 "$(DOTFILES)/scripts/test-git-worktree-wip-push.py"
SETUP_TARGETS += claude-plugins
claude-plugins:
	$(call require-command,claude)
	@"$(DOTFILES)/bin/claude-remove-blocked-plugins" --blocklist "$(DOTFILES)/claude/blocked-plugins.json"
SETUP_TARGETS += claude-shared
claude-shared:
	@python3 "$(DOTFILES)/bin/sync-claude-shared" --source "$(DOTFILES)/ai" --home "$(HOME)"
claude: claude-config claude-plugins agent-status-broker claude-shared
claude-config:
	@mkdir -p $(HOME)/.claude
	@mkdir -p $(HOME)/.claude/local
	@ln -fs $(DOTFILES)/.claude/settings.json $(HOME)/.claude/settings.json
	@ln -fs $(DOTFILES)/claude/CLAUDE.md $(HOME)/.claude/CLAUDE.md
	@ln -fs $(DOTFILES)/claude/CONSTITUTION.md $(HOME)/.claude/CONSTITUTION.md
	@for d in commands workflows; do \
		[ -L $(HOME)/.claude/$$d ] && rm $(HOME)/.claude/$$d; \
		mkdir -p $(HOME)/.claude/$$d; \
		for link in "$(HOME)/.claude/$$d/"*; do \
			[ -L "$$link" ] && [ ! -e "$$link" ] || continue; \
			case "$$(readlink "$$link")" in \
				"$(DOTFILES)/claude/$$d/"*) rm "$$link" || exit 1 ;; \
			esac; \
		done; \
		for f in $(DOTFILES)/claude/$$d/*; do \
			[ -e "$$f" ] || continue; \
			ln -fs "$$f" $(HOME)/.claude/$$d/; \
		done; \
	done
	@ln -fs $(DOTFILES)/bin/claude-wrapper $(HOME)/.claude/local/claude-wrapper
	$(call require-command,git)
	@git -C $(DOTFILES) config filter.claude-settings.clean 'jq --indent 2 "del(.feedbackSurveyState)"'
	@git -C $(DOTFILES) config filter.claude-settings.smudge cat
	$(call require-command,jq)
	@[ -f $(HOME)/.claude.json ] || echo '{}' > $(HOME)/.claude.json
	@temporary=$$(mktemp "$(HOME)/.claude.json.XXXXXX") || exit 1; \
	trap 'rm -f "$$temporary"' 0; \
	jq --slurpfile mcp $(DOTFILES)/.claude/mcp-servers.json '.mcpServers = ((.mcpServers // {}) + $$mcp[0])' $(HOME)/.claude.json > "$$temporary" && mv "$$temporary" $(HOME)/.claude.json
SETUP_TARGETS += codex-skills
codex-skills:
	@python3 "$(DOTFILES)/bin/sync-codex-skills" --source "$(DOTFILES)/ai/skills" --home "$(HOME)"
SETUP_TARGETS += codex-tmux-config
SETUP_TARGETS += agent-status-broker
agent-status-broker:
	@AGENT_STATUS_GO="$(GO)" "$(DOTFILES)/scripts/install-agent-status-broker" $(AGENT_STATUS_INSTALL_FLAGS)
	@python3 "$(DOTFILES)/bin/sync-agent-status-hooks"
# The aggregate waits for hook migration before installing Codex hooks. The
# standalone config target remains usable without the broker.
codex-tmux: agent-status-broker
codex-tmux codex-tmux-config:
	$(call require-command,$(UV))
	@"$(UV)" run --no-project --python '>=3.11' python "$(DOTFILES)/bin/sync-codex-tmux-hooks"
SETUP_TARGETS += codex-agents
codex-agents:
	@python3 "$(DOTFILES)/bin/sync-codex-agents" --source "$(DOTFILES)/ai/agents" --home "$(HOME)"
codex-env:
	@mkdir -p $(HOME)/.codex
	@if [ ! -e "$(HOME)/.codex/.env" ] && [ ! -L "$(HOME)/.codex/.env" ] || \
		[ "$$(readlink "$(HOME)/.codex/.env")" = "$(DOTFILES)/codex/env" ]; then \
		if [ -f "$(HOME)/.config/bedrock/env" ]; then \
			ln -fs "$(HOME)/.config/bedrock/env" "$(HOME)/.codex/.env"; \
		else \
			ln -fs "$(DOTFILES)/codex/env" "$(HOME)/.codex/.env"; \
		fi; \
	fi
codex: claude codex-skills codex-agents codex-tmux codex-config codex-mcp
codex-config: codex-env
	@if [ ! -e "$(HOME)/.codex/bedrock.config.toml" ] && [ ! -L "$(HOME)/.codex/bedrock.config.toml" ] && \
		[ -f "$(DOTFILES)/codex/bedrock.config.toml" ]; then \
		ln -fs "$(DOTFILES)/codex/bedrock.config.toml" "$(HOME)/.codex/bedrock.config.toml"; \
	fi
	@cat $(DOTFILES)/codex/AGENTS.md $(DOTFILES)/codex/AGENTS.local.md > $(HOME)/.codex/AGENTS.md 2>/dev/null || cp $(DOTFILES)/codex/AGENTS.md $(HOME)/.codex/AGENTS.md
codex-mcp: claude-config codex-config
	$(call require-command,codex)
	$(call require-command,jq)
	@$(DOTFILES)/bin/sync-codex-mcp-servers
quarto:
	@mkdir -p $(HOME)/.config/quarto
	@ln -fns $(DOTFILES)/quarto/styles $(HOME)/.config/quarto/styles
	@ln -fs $(DOTFILES)/quarto/_quarto.yml $(HOME)/.config/quarto/_quarto.yml
	@echo "✓ Quarto configuration linked"
gpg-restore:
	@if gpg --list-secret-keys 6DAE70CE5C232C03 >/dev/null 2>&1; then \
		echo "✓ GPG key 6DAE70CE5C232C03 already present"; \
	else \
		echo "Restoring GPG key from 1Password..."; \
		if ! command -v op >/dev/null 2>&1; then \
			echo "Error: 1Password CLI (op) not found"; \
			exit 1; \
		fi; \
		op read "op://Personal/d4xe37k5vnkkjmx5hk3vxiinn4/private_key" --account my.1password.com | gpg --import; \
		echo "✓ GPG key imported"; \
		echo ""; \
		echo "Now setting key trust level..."; \
		echo "Run the following commands:"; \
		echo "  gpg --edit-key 6DAE70CE5C232C03"; \
		echo "  trust"; \
		echo "  5 (ultimate)"; \
		echo "  y"; \
		echo "  quit"; \
	fi
presenterm:
	@mkdir -p $(HOME)/.config/presenterm/themes
	@ln -fs $(DOTFILES)/presenterm/config.toml $(HOME)/.config/presenterm/config.toml
	@ln -fs $(DOTFILES)/presenterm/themes/nord.yaml $(HOME)/.config/presenterm/themes/nord.yaml
mail:
	@echo "Setting up email configuration..."
	@mkdir -p $(HOME)/.config/neomutt
	@mkdir -p $(HOME)/.cache/neomutt/headers
	@mkdir -p $(HOME)/.cache/neomutt/bodies
	@mkdir -p $(HOME)/.local/share/msmtp
	@ln -fs $(DOTFILES)/mail/mbsyncrc $(HOME)/.mbsyncrc
	@ln -fs $(DOTFILES)/mail/notmuch-config $(HOME)/.notmuch-config
	@ln -fs $(DOTFILES)/mail/msmtprc $(HOME)/.msmtprc
	@ln -fs $(DOTFILES)/mail/neomuttrc $(HOME)/.config/neomutt/neomuttrc
	@echo "✓ Email configuration files linked"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Run: bash $(DOTFILES)/mail/setup-email.sh"
	@echo "  2. Follow the prompts to configure your Gmail account"
	@echo "  3. Launch neomutt when done"
test:
	@pytest bin/*_test.py

audit-skills:
	@"$(DOTFILES)/bin/claude-skill-audit"

SETUP_TARGETS += ui-review
ui-review:
	$(call require-command,node)
	$(call require-command,npm)
	@python3 $(DOTFILES)/scripts/install-viewrule.py
	@mkdir -p $(HOME)/.local/bin
	@ln -fs $(DOTFILES)/bin/ui-review $(HOME)/.local/bin/ui-review
	@ln -fs $(DOTFILES)/bin/ui-review $(HOME)/.local/bin/viewrule
	@echo "Viewrule installed. Use /ui-review in Claude Code or viewrule --help."
test-ui-review:
	@python3 $(DOTFILES)/scripts/test-viewrule.py

# Opt-in services stay out of SETUP_TARGETS.
# The helper remembers the selected server, falling back to dev on first setup.
ATUIN_SYNC_HOST ?=
UV ?= uv
atuin-sync:
	@"$(UV)" run --no-project python "$(DOTFILES)/scripts/setup-atuin-sync.py" --host "$(ATUIN_SYNC_HOST)"

test-atuin-sync:
	@"$(UV)" run --no-project python "$(DOTFILES)/scripts/test-atuin-sync.py"

test-bootstrap:
	@"$(UV)" run --no-project python "$(DOTFILES)/scripts/test-bootstrap.py"

BEDROCK_TOKEN_FILE ?=
export BEDROCK_TOKEN_FILE
bedrock-credentials:
	@"$(UV)" run --no-project python "$(DOTFILES)/scripts/setup-bedrock-credentials.py"

bedrock-router: codex-env
	@bash -ec 'source "$$1"; prepare_bootstrap_environment; setup_bedrock_router' bash "$(DOTFILES)/bootstrap.sh"

test-bootstrap-nvim:
	@"$(UV)" run --no-project python "$(DOTFILES)/scripts/test-bootstrap-nvim.py"

kitty-terminfo:
	$(call require-command,tic)
	$(call require-command,infocmp)
	@bash -ec 'source "$$1"; setup_kitty_terminfo' bash "$(DOTFILES)/bootstrap.sh"

test-kitty-ssh:
	@"$(UV)" run --no-project python "$(DOTFILES)/scripts/test-kitty-ssh.py"

test-yabai-browser-focus:
	@"$(UV)" run --no-project python "$(DOTFILES)/scripts/test-yabai-browser-focus.py"

test-kitty-last-url:
	@kitty +runpy "import runpy; runpy.run_path('$(DOTFILES)/scripts/test-kitty-last-url.py', run_name='__main__')"

atuin-server:
	@test "$(UNAME_S)" = Linux
	@test -x "$(HOME)/.local/bin/atuin-server"
	@mkdir -p "$(HOME)/.config/atuin" "$(HOME)/.config/systemd/user"
	@mkdir -p "$(HOME)/.local/share/atuin-server"
	@chmod 700 "$(HOME)/.local/share/atuin-server"
	@sed 's|__HOME__|$(HOME)|g' "$(DOTFILES)/sh/atuin-server.toml.template" \
		> "$(HOME)/.config/atuin/server.toml"
	@ln -fs "$(DOTFILES)/rc/systemd/atuin-server.service" \
		"$(HOME)/.config/systemd/user/atuin-server.service"
	@systemctl --user daemon-reload
	@systemctl --user enable --now atuin-server.service
	@systemctl --user restart atuin-server.service

atuin-tunnel:
	@"$(UV)" run --no-project python "$(DOTFILES)/scripts/setup-atuin-sync.py" --host "$(ATUIN_SYNC_HOST)" --tunnel-only

claude-json-prune-schedule:
	@os=$$(uname -s); \
	if [ "$$os" = "Darwin" ]; then \
		mkdir -p $(HOME)/.local/state/claude-json-prune; \
		mkdir -p $(HOME)/Library/LaunchAgents; \
		sed -e 's|__HOME__|$(HOME)|g' \
			$(DOTFILES)/rc/launchd/com.joshlane.claude-json-prune.plist.template \
			> $(HOME)/Library/LaunchAgents/com.joshlane.claude-json-prune.plist; \
		launchctl unload $(HOME)/Library/LaunchAgents/com.joshlane.claude-json-prune.plist 2>/dev/null || true; \
		launchctl load -w $(HOME)/Library/LaunchAgents/com.joshlane.claude-json-prune.plist; \
		echo "claude-json-prune scheduled via launchd (daily, 4am)"; \
	elif [ "$$os" = "Linux" ]; then \
		mkdir -p $(HOME)/.local/state/claude-json-prune; \
		mkdir -p $(HOME)/.config/systemd/user; \
		sed -e 's|__HOME__|$(HOME)|g' \
			$(DOTFILES)/rc/systemd/claude-json-prune.service.template \
			> $(HOME)/.config/systemd/user/claude-json-prune.service; \
		sed -e 's|__HOME__|$(HOME)|g' \
			$(DOTFILES)/rc/systemd/claude-json-prune.timer.template \
			> $(HOME)/.config/systemd/user/claude-json-prune.timer; \
		systemctl --user daemon-reload; \
		systemctl --user enable --now claude-json-prune.timer; \
		echo "claude-json-prune scheduled via systemd --user timer (daily, 4am). Headless/no-login box: also run 'loginctl enable-linger $$USER' (not run automatically here — that's an account-level setting change, Josh's call)"; \
	else \
		echo "claude-json-prune-schedule: unsupported OS ($$os)"; exit 1; \
	fi

.PHONY: all setup $(SETUP_TARGETS) $(LINUX_SETUP_TARGETS) $(DARWIN_SETUP_TARGETS) lint audit-skills instruction-size zsh tmux vim kitty claude codex codex-tmux codex-env FORCE test test-ui-review test-setup test-zsh-startup benchmark-zsh-startup amphetamine

test-setup:
	@python3 "$(DOTFILES)/scripts/test-setup.py"

test-zsh-startup:
	@python3 "$(DOTFILES)/scripts/test-zsh-startup.py"

ZSH_BENCHMARK_ARGS ?=
benchmark-zsh-startup:
	@python3 "$(DOTFILES)/scripts/benchmark-zsh-startup.py" $(ZSH_BENCHMARK_ARGS)

ac-awake-status:
	@"$(DOTFILES)/bin/ac-awake-service" status
ac-awake-install:
	@sudo "$(DOTFILES)/bin/ac-awake-service" install
ac-awake-stop:
	@sudo "$(DOTFILES)/bin/ac-awake-service" stop
ac-awake-uninstall:
	@sudo "$(DOTFILES)/bin/ac-awake-service" uninstall
.PHONY: ac-awake-status ac-awake-install ac-awake-stop ac-awake-uninstall
