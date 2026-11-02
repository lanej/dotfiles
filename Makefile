.DEFAULT_GOAL := base
DOTFILES := $(CURDIR)
MAKE_SCRIPTS := $(dir $(abspath $(firstword $(MAKEFILE_LIST))))scripts/make
# Bootstrap installs its managed runtime here even before shell setup exists.
export PATH := $(HOME)/.local/bin:$(PATH)
GO ?= go
FIRSTMATE_HOME ?= $(HOME)/src/firstmate
INSTRUCTION_SIZE_BASE ?= HEAD
UNAME_S := $(shell uname -s)
include $(MAKE_SCRIPTS)/../../config/targets.mk
# Share one validated TOML resolver with bootstrap. Resolve only when a target
# consumes settings, so basic linking remains usable before Python is installed.
ifneq ($(origin DOTFILES_CONFIG),undefined)
export DOTFILES_CONFIG
endif
ifneq ($(origin IS_EASYPOST),undefined)
$(error IS_EASYPOST is retired; select configuration sets in ~/.config/dotfiles/config.toml)
endif
shell-quote = '$(subst ','"'"',$(1))'
DOTFILES_CONFIG_ARG = $(if $(filter undefined,$(origin DOTFILES_CONFIG)),,--config $(call shell-quote,$(DOTFILES_CONFIG)))
# Make's shell expressions use the incoming PATH rather than the recipe export.
DOTFILES_PYTHON = $(or $(wildcard $(HOME)/.local/bin/python3),python3)
# Cache validated settings after the first consumer requests them.
define resolve-dotfiles-config
$(eval DOTFILES_RESOLVED := $(shell $(call shell-quote,$(DOTFILES_PYTHON)) "$(MAKE_SCRIPTS)/../dotfiles-config.py" $(DOTFILES_CONFIG_ARG) --platform "$(UNAME_S)" --format make))
$(if $(strip $(DOTFILES_RESOLVED)),,$(error Invalid dotfiles configuration; see diagnostic above))
$(foreach setting,$(DOTFILES_RESOLVED),$(eval override $(setting)))
$(eval resolve-dotfiles-config :=)
endef
config-value = $(strip $(resolve-dotfiles-config)$($(1)))
comma := ,
SETUP_TARGETS = $(subst $(comma), ,$(call config-value,DOTFILES_SETUP_TARGETS))
NATIVE_SET = $(or $(DOTFILES_NATIVE_SET_$(UNAME_S)),$(error Unsupported OS $(UNAME_S)))
BASE_TARGETS = $(DOTFILES_NATIVE_TARGETS_$(UNAME_S))

# The runner reports every step and returns failure only after trying them all.
all setup: configure

.PHONY: bootstrap install
bootstrap install:
	@bash "$(DOTFILES)/bootstrap.sh" "$@"

.PHONY: config-init config plan test-dotfiles-config test-dotfiles-config-editor
config-init:
	@bash "$(MAKE_SCRIPTS)/init-config.sh" "$(HOME)" "$(NATIVE_SET)"

config:
	@python3 "$(MAKE_SCRIPTS)/../dotfiles-config.py" $(DOTFILES_CONFIG_ARG) --platform "$(UNAME_S)"

plan:
	@python3 "$(MAKE_SCRIPTS)/../dotfiles-config.py" $(DOTFILES_CONFIG_ARG) --platform "$(UNAME_S)" --format plan

test-dotfiles-config:
	@python3 "$(DOTFILES)/scripts/test-dotfiles-config.py"

test-dotfiles-config-editor:
	$(call require-command,nvim)
	$(call require-command,taplo)
	@nvim --headless -u NONE -i NONE -n -l "$(DOTFILES)/nvim/tests/dotfiles-config-schema.lua"

base: config-init
base: SELECTED_TARGETS = $(BASE_TARGETS)
configure: SELECTED_TARGETS = $(SETUP_TARGETS)
base configure:
ifneq ($(findstring n,$(firstword $(filter-out --%,$(MAKEFLAGS)))),)
	+@$(MAKE) -f "$(firstword $(MAKEFILE_LIST))" --no-print-directory --keep-going $(or $(SELECTED_TARGETS),setup-empty)
else
	+@bash "$(DOTFILES)/scripts/setup-checklist.sh" $(MAKE) -f "$(firstword $(MAKEFILE_LIST))" --no-print-directory --keep-going -- $(SELECTED_TARGETS)
endif

setup-empty:
	@echo "No configuration targets selected. See make config."

define require-command
	@bash "$(MAKE_SCRIPTS)/require.sh" command "$(1)"
endef

define require-os
	@bash "$(MAKE_SCRIPTS)/require.sh" os "$(1)" "$(UNAME_S)" "$@"
endef

instruction-size:
	$(call require-command,git)
	$(call require-command,jq)
	@bash "$(DOTFILES)/claude/evals/skill-maintenance/check_size.sh" --base "$(INSTRUCTION_SIZE_BASE)" --installed-home "$(HOME)"

lint: shellcheck audit-skills instruction-size

shellcheck:
	$(call require-command,shellcheck)
	@bash "$(MAKE_SCRIPTS)/shellcheck.sh" "$(DOTFILES)"

treehouse-config:
	@bash "$(MAKE_SCRIPTS)/config.sh" "$@" "$(DOTFILES)" "$(HOME)" "$(UV)" "$(UNAME_S)"

firstmate-config: treehouse-config zellij-config
	@bash "$(MAKE_SCRIPTS)/config.sh" "$@" "$(DOTFILES)" "$(HOME)" "$(UV)" "$(UNAME_S)" "$(FIRSTMATE_HOME)"

.PHONY: test-firstmate-primary
test-firstmate-primary:
	@python3 "$(DOTFILES)/scripts/test-firstmate-primary.py"

banner:
	@cat banner.txt
dev:
	@bash "$(MAKE_SCRIPTS)/config.sh" "$@" "$(DOTFILES)" "$(HOME)" "$(UV)" "$(UNAME_S)"
shell:
	@bash "$(MAKE_SCRIPTS)/config.sh" "$@" "$(DOTFILES)" "$(HOME)" "$(UV)" "$(UNAME_S)"
zsh: zsh-config zsh-plugins
zsh-config: shell
	@bash "$(MAKE_SCRIPTS)/config.sh" "$@" "$(DOTFILES)" "$(HOME)" "$(UV)" "$(UNAME_S)"
zsh-plugins: zsh-config
	@bash "$(MAKE_SCRIPTS)/config.sh" "$@" "$(DOTFILES)" "$(HOME)" "$(UV)" "$(UNAME_S)"
tmux: tmux-config tmux-plugins
tmux-config:
	@bash "$(MAKE_SCRIPTS)/config.sh" "$@" "$(DOTFILES)" "$(HOME)" "$(UV)" "$(UNAME_S)"
tmux-plugins: tmux-config
	$(call require-command,tmux)
	$(call require-command,git)
	@bash "$(DOTFILES)/scripts/install-tmux-plugins.sh" "$(DOTFILES)"
tmux-status-legend:
	@"$(DOTFILES)/bin/tmux-claude-state" legend
tmux-program-status:
	@"$(if $(AGENT_STATUS_SOURCE),$(AGENT_STATUS_SOURCE),$(HOME)/src/agent-status-broker)/tmux/build" "$(HOME)/.local/bin/tmux-program-status"
zellij: zellij-config
.PHONY: zellij-runtime
zellij-runtime:
	@bash "$(MAKE_SCRIPTS)/bootstrap-task.sh" "$@" "$(DOTFILES)"
zellij-config:
	@bash "$(MAKE_SCRIPTS)/config.sh" "$@" "$(DOTFILES)" "$(HOME)" "$(UV)" "$(UNAME_S)"
sql-formatters:
	@bash "$(MAKE_SCRIPTS)/config.sh" "$@" "$(DOTFILES)" "$(HOME)" "$(UV)" "$(UNAME_S)"
vim: vim-config sql-formatters
vim-config: nvim-gh-review
	@bash "$(MAKE_SCRIPTS)/config.sh" "$@" "$(DOTFILES)" "$(HOME)" "$(UV)" "$(UNAME_S)"
.PHONY: nvim-gh-review
nvim-gh-review:
	@bash "$(MAKE_SCRIPTS)/config.sh" "$@" "$(DOTFILES)" "$(HOME)" "$(UV)" "$(UNAME_S)"
X:
	@bash "$(MAKE_SCRIPTS)/config.sh" "$@" "$(DOTFILES)" "$(HOME)" "$(UV)" "$(UNAME_S)"
ruby:
	@bash "$(MAKE_SCRIPTS)/config.sh" "$@" "$(DOTFILES)" "$(HOME)" "$(UV)" "$(UNAME_S)"
git:
	@bash "$(MAKE_SCRIPTS)/config.sh" "$@" "$(DOTFILES)" "$(HOME)" "$(UV)" "$(UNAME_S)"
gpg:
	@bash "$(MAKE_SCRIPTS)/config.sh" "$@" "$(DOTFILES)" "$(HOME)" "$(UV)" "$(UNAME_S)"
yabai:
	@bash "$(MAKE_SCRIPTS)/config.sh" "$@" "$(DOTFILES)" "$(HOME)" "$(UV)" "$(UNAME_S)"
polybar:
	@bash "$(MAKE_SCRIPTS)/config.sh" "$@" "$(DOTFILES)" "$(HOME)" "$(UV)" "$(UNAME_S)"
bspwm:
	@bash "$(MAKE_SCRIPTS)/config.sh" "$@" "$(DOTFILES)" "$(HOME)" "$(UV)" "$(UNAME_S)"
kitty: kitty-config kitty-terminfo
kitty-config:
	@bash "$(MAKE_SCRIPTS)/config.sh" "$@" "$(DOTFILES)" "$(HOME)" "$(UV)" "$(UNAME_S)"
python:
	@bash "$(MAKE_SCRIPTS)/config.sh" "$@" "$(DOTFILES)" "$(HOME)" "$(UV)" "$(UNAME_S)"
wezterm:
	@bash "$(MAKE_SCRIPTS)/config.sh" "$@" "$(DOTFILES)" "$(HOME)" "$(UV)" "$(UNAME_S)"
# Opt-in restore: quit Amphetamine first; its preferences must not be symlinked.
AMPHETAMINE_PREFS ?= $(HOME)/Library/Containers/com.if.Amphetamine/Data/Library/Preferences/com.if.Amphetamine
amphetamine:
	@bash "$(MAKE_SCRIPTS)/amphetamine.sh" "$(DOTFILES)" "$(AMPHETAMINE_PREFS)" "$(UNAME_S)"
undercurl:
	@bash "$(MAKE_SCRIPTS)/config.sh" "$@" "$(DOTFILES)" "$(HOME)" "$(UV)" "$(UNAME_S)"
go:
	@bash "$(MAKE_SCRIPTS)/config.sh" "$@" "$(DOTFILES)" "$(HOME)" "$(UV)" "$(UNAME_S)"
cargo:
	@bash "$(MAKE_SCRIPTS)/config.sh" "$@" "$(DOTFILES)" "$(HOME)" "$(UV)" "$(UNAME_S)"
dev-cache-config:
	@bash "$(MAKE_SCRIPTS)/config.sh" "$@" "$(DOTFILES)" "$(HOME)" "$(UV)" "$(UNAME_S)"
FORCE:
DEV_CACHE_NODE_PATH ?=
DEV_CACHE_PYTHON ?=
DEV_CACHE_GO_PATH ?=
DEV_CACHE_GOPATH ?=
dev-cache-schedule: dev-cache-config FORCE
	@bash "$(MAKE_SCRIPTS)/schedule-maintenance.sh" dev-cache "$(DOTFILES)" "$(HOME)" "$(UNAME_S)" "$(DEV_CACHE_NODE_PATH)" "$(DEV_CACHE_GOPATH)" "$(DEV_CACHE_PYTHON)" "$(DEV_CACHE_GO_PATH)"

test-dev-cache-prune: FORCE
	@python3 "$(DOTFILES)/scripts/test-dev-cache-prune.py"
test-git-worktree-cleanup: FORCE
	@python3 "$(DOTFILES)/scripts/test-git-worktree-cleanup.py"
	@python3 "$(DOTFILES)/scripts/test-git-worktree-size-cache.py"
	@python3 "$(DOTFILES)/scripts/test-git-worktree-wip-push.py"
claude-plugins:
	$(call require-command,claude)
	@"$(DOTFILES)/bin/claude-remove-blocked-plugins" --blocklist "$(DOTFILES)/claude/blocked-plugins.json"
software-standard:
	@python3 "$(DOTFILES)/scripts/install-software-standard.py" --source "$(DOTFILES)/ai/skills/builder" --home "$(HOME)"

claude-shared: software-standard
	@python3 "$(DOTFILES)/bin/sync-claude-shared" --source "$(DOTFILES)/ai" --home "$(HOME)"
claude: claude-config claude-plugins agent-status-broker claude-shared
claude-config: software-standard
	@bash "$(MAKE_SCRIPTS)/config.sh" "$@" "$(DOTFILES)" "$(HOME)" "$(UV)" "$(UNAME_S)"
codex-skills: software-standard
	@python3 "$(DOTFILES)/bin/sync-codex-skills" --source "$(DOTFILES)/ai/skills" --home "$(HOME)"
agent-status-broker:
	@AGENT_STATUS_GO="$(GO)" "$(DOTFILES)/scripts/install-agent-status-broker" --no-start $(AGENT_STATUS_INSTALL_FLAGS)
	@python3 "$(DOTFILES)/bin/sync-agent-status-hooks"
# The aggregate waits for hook migration before installing Codex hooks. The
# standalone config target remains usable without the broker.
codex-tmux: agent-status-broker
# Both installers edit config.toml; sequence them even under parallel make.
codex-tmux codex-tmux-config: codex-permissions
	$(call require-command,$(UV))
	@"$(UV)" run --no-project --python '>=3.11' python "$(DOTFILES)/bin/sync-codex-tmux-hooks"
# The codex aggregate runs this after its other hook installers finish.
codex codex-worktree-hook:
	$(call require-command,$(UV))
	@"$(UV)" run --script "$(DOTFILES)/bin/codex-worktree-config" --install

test-codex-worktree-hook: FORCE
	$(call require-command,$(UV))
	@"$(UV)" run --no-project --python '>=3.11' python "$(DOTFILES)/scripts/test-codex-worktree-hook.py"
codex-agents:
	@python3 "$(DOTFILES)/bin/sync-codex-agents" --source "$(DOTFILES)/ai/agents" --home "$(HOME)"
codex-env:
	@bash "$(MAKE_SCRIPTS)/config.sh" "$@" "$(DOTFILES)" "$(HOME)" "$(UV)" "$(UNAME_S)"
codex: claude codex-skills codex-agents codex-tmux codex-config codex-mcp
.PHONY: codex-permissions
codex-permissions:
	$(call require-command,$(UV))
	@"$(UV)" run --script "$(DOTFILES)/bin/sync-codex-permissions" --github-enabled "$(call config-value,DOTFILES_CODEX_GITHUB_ENABLED)"
.PHONY: codex-guidance
codex-config: codex-guidance codex-permissions
codex-guidance: codex-env codex-skills
	@bash "$(MAKE_SCRIPTS)/config.sh" "$@" "$(DOTFILES)" "$(HOME)" "$(UV)" "$(UNAME_S)"
codex-mcp: claude-config codex-config
	$(call require-command,codex)
	$(call require-command,jq)
	@"$(DOTFILES)/bin/sync-codex-mcp-servers"
quarto:
	@bash "$(MAKE_SCRIPTS)/config.sh" "$@" "$(DOTFILES)" "$(HOME)" "$(UV)" "$(UNAME_S)"
gpg-restore:
	@bash "$(MAKE_SCRIPTS)/gpg-restore.sh"
presenterm:
	@bash "$(MAKE_SCRIPTS)/config.sh" "$@" "$(DOTFILES)" "$(HOME)" "$(UV)" "$(UNAME_S)"
mail:
	@bash "$(MAKE_SCRIPTS)/config.sh" "$@" "$(DOTFILES)" "$(HOME)" "$(UV)" "$(UNAME_S)"
test-pragmatic-hexagonal:
	@python3 "$(DOTFILES)/ai/skills/builder/scripts/check_examples.py"

test:
	@pytest bin/*_test.py

.PHONY: test-codex-cleanup
test-codex-cleanup:
	@"$(UV)" run --no-project --python '>=3.11' --with pytest python -m pytest -q bin/codex-cleanup_test.py

codex: codex-worktree-exit-hook
codex-worktree-exit-hook: codex-tmux
	@python3 "$(DOTFILES)/bin/codex-worktree-exit-hook" --install

.PHONY: test-codex-worktree-exit
test-codex-worktree-exit:
	@"$(UV)" run --script "$(DOTFILES)/scripts/test-codex-worktree-exit.py"

.PHONY: test-agent-treehouse
test-agent-treehouse:
	@"$(UV)" run --script "$(DOTFILES)/scripts/test-agent-treehouse.py"

audit-skills:
	@"$(DOTFILES)/bin/claude-skill-audit"

ui-review:
	@bash "$(MAKE_SCRIPTS)/config.sh" "$@" "$(DOTFILES)" "$(HOME)" "$(UV)" "$(UNAME_S)"
test-ui-review:
	@python3 "$(DOTFILES)/scripts/test-viewrule.py"

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
	@bash "$(MAKE_SCRIPTS)/bootstrap-task.sh" "$@" "$(DOTFILES)"

test-bootstrap-nvim:
	@"$(UV)" run --no-project python "$(DOTFILES)/scripts/test-bootstrap-nvim.py"

kitty-terminfo:
	$(call require-command,tic)
	$(call require-command,infocmp)
	@bash "$(MAKE_SCRIPTS)/bootstrap-task.sh" "$@" "$(DOTFILES)"

test-kitty-ssh:
	@"$(UV)" run --no-project python "$(DOTFILES)/scripts/test-kitty-ssh.py"

test-yabai-browser-focus:
	@"$(UV)" run --no-project python "$(DOTFILES)/scripts/test-yabai-browser-focus.py"

test-kitty-last-url:
	@kitty +runpy "import runpy; runpy.run_path('$(DOTFILES)/scripts/test-kitty-last-url.py', run_name='__main__')"

test-tmux-session-fallback:
	@"$(UV)" run --no-project python "$(DOTFILES)/scripts/test-tmux-session-fallback.py"

atuin-server:
	@bash "$(MAKE_SCRIPTS)/atuin-server.sh" "$(DOTFILES)" "$(HOME)" "$(UNAME_S)"

atuin-tunnel:
	@"$(UV)" run --no-project python "$(DOTFILES)/scripts/setup-atuin-sync.py" --host "$(ATUIN_SYNC_HOST)" --tunnel-only

claude-json-prune-schedule:
	@bash "$(MAKE_SCRIPTS)/schedule-maintenance.sh" claude-json "$(DOTFILES)" "$(HOME)" "$(UNAME_S)"

.PHONY: all base configure setup setup-empty lint shellcheck audit-skills instruction-size zsh tmux zellij vim kitty claude codex codex-tmux codex-env FORCE test test-ui-review test-setup test-zellij test-firstmate test-zellij-layout test-zellij-sessions test-zsh-startup benchmark-zsh-startup amphetamine

test-setup:
	@python3 "$(DOTFILES)/scripts/test-setup.py"

test-zellij:
	@python3 "$(DOTFILES)/scripts/test-zellij.py"
.PHONY: test-zellij-navigation
test-zellij-navigation:
	@python3 "$(DOTFILES)/scripts/test-zellij-navigation.py"

test-firstmate:
	@python3 "$(DOTFILES)/scripts/test-firstmate.py"

test-zellij-layout:
	@python3 "$(DOTFILES)/scripts/test-zellij-layout.py"

test-zellij-sessions:
	@python3 "$(DOTFILES)/scripts/test-zellij-sessions.py"

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

# Control the installed Paseo LaunchAgents; stopping persists across logins.
PASEO_LAUNCH_AGENTS := local.paseo.relay local.paseo.daemon local.paseo.lan-ingress
paseo-start:
	$(call require-os,Darwin)
	@bash "$(MAKE_SCRIPTS)/paseo-lifecycle.sh" start "$(HOME)" $(PASEO_LAUNCH_AGENTS)

# Start the existing host and print its live pairing offer for another device.
paseo-pair:
	$(call require-os,Darwin)
	$(call require-command,paseo)
	$(call require-command,jq)
	@$(MAKE) --no-print-directory paseo-start
	@bash "$(MAKE_SCRIPTS)/paseo-lifecycle.sh" pair "$(HOME)"

paseo-stop:
	$(call require-os,Darwin)
	@bash "$(MAKE_SCRIPTS)/paseo-lifecycle.sh" stop "$(HOME)" $(PASEO_LAUNCH_AGENTS)

test-paseo-lifecycle:
	@python3 "$(DOTFILES)/scripts/test-paseo-lifecycle.py"

.PHONY: paseo-start paseo-pair paseo-stop test-paseo-lifecycle

.PHONY: test-pragmatic-hexagonal

.PHONY: ep-direnv ep-direnv-uninstall
ep-direnv:
	@sh "$(DOTFILES)/scripts/install-ep-direnv.sh" install "$(DOTFILES)" "$(HOME)"
ep-direnv-uninstall:
	@sh "$(DOTFILES)/scripts/install-ep-direnv.sh" uninstall "$(DOTFILES)" "$(HOME)"

.PHONY: epenv
epenv: ep-direnv
	@bash "$(MAKE_SCRIPTS)/config.sh" "$@" "$(DOTFILES)" "$(HOME)" "$(UV)" "$(UNAME_S)"
