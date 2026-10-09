#!/bin/bash

os=$(uname -s | tr '[:upper:]' '[:lower:]' | sed 's,^darwin$,macos,') # macos or linux
bitness=$(getconf LONG_BIT)                                           # 64 or 32
distro="$os-$(uname -m)"
short_arch=$(uname -m | sed 's,^x86_64$,x64,') # arm64 or x64
short_distro="$os-$short_arch"

install_from_package_manager() {
	if declare -f "install_$1_package" >/dev/null; then
		"install_$1_package" "$2"
	elif command -v brew &>/dev/null; then
		brew install "$1"
	elif command -v yay; then # endeavoros
		sudo yay -S --noconfirm "$1"
	elif command -v pacman; then # arch
		sudo pacman -S --noconfirm "$1"
	elif command -v dnf; then
		sudo dnf install -y "$1"
	elif command -v apt-get; then
		sudo apt-get install -y "$1"
	else
		exit 1
	fi
}

package_manager_semver() {
	if command -v brew &>/dev/null; then
		(brew info "$1" | head -n1 | parse_semver | head -n1) || (echo "package $1 not found in brew" && return 1)
	elif command -v yay &>/dev/null; then
		yay -Qi "$1" | parse_semver || (echo "package $1 not found in yay" && return 1)
	elif command -v pacman &>/dev/null; then
		pacman -Qi "$1" | parse_semver || (echo "package $1 not found in pacman" && return 1)
	elif command -v dnf &>/dev/null; then
		(dnf --cacheonly info "$1" 2>/dev/null | grep "^Version" | parse_semver | head -n1) || return 1
	elif command -v apt-get &>/dev/null; then
		apt_package_semver "$1"
	else
		exit 1
	fi
}

apt_package_semver() {
	apt-cache policy "$1" 2>/dev/null |
		awk '$1 == "Candidate:" { print $2 }' | parse_semver | head -n1
}

package_semver() {
	if declare -f "$1_package_semver" >/dev/null; then
		"$1_package_semver" || (echo "Failed to get semver for based on custom script: $1" >&2 && return 1)
	else
		package_manager_semver "$1" || (echo "Failed to get semver for: $1" >&2 && return 1)
	fi
}

install_fd_package() {
	# Check if fd is already installed and working
	if command -v fd &>/dev/null; then
		echo "fd already installed, skipping package manager installation"
		return 0
	fi

	if command -v brew &>/dev/null; then
		brew install fd
	elif command -v yay; then
		sudo yay -S --noconfirm fd
	elif command -v pacman; then
		sudo pacman -S --noconfirm fd
	elif command -v dnf; then
		# For dnf systems, prefer cargo installation if there are conflicts
		if rpm -qa | grep -q "^fd-"; then
			echo "Existing fd package found, will install via cargo to avoid conflict"
			return 1  # This will trigger the fallback to cargo installation
		fi
		sudo dnf install -y fd-find
	elif command -v apt-get; then
		sudo apt-get install -y fd-find
	else
		exit 1
	fi
}

fd_package_semver() {
	if command -v brew &>/dev/null; then
		(brew info fd | head -n1 | parse_semver | head -n1) || (echo "package fd not found in brew" && return 1)
	elif command -v yay &>/dev/null; then
		yay -Qi fd | parse_semver || (echo "package fd not found in yay" && return 1)
	elif command -v pacman &>/dev/null; then
		pacman -Qi fd | parse_semver || (echo "package fd not found in pacman" && return 1)
	elif command -v dnf &>/dev/null; then
		(dnf --cacheonly info fd-find 2>/dev/null | grep "^Version" | parse_semver | head -n1) || return 1
	elif command -v apt-get &>/dev/null; then
		apt_package_semver fd-find
	else
		exit 1
	fi
}

install_explicitly() {
	if declare -f "install_$1_from_release" >/dev/null; then
		echo "Installing $1 $2 from release"
		"install_$1_from_release" "$2"
	elif declare -f "install_$1_from_source" >/dev/null; then
		echo "Installing $1 $2 from source"
		"install_$1_from_source" "$2"
	elif declare -f "install_$1_package" >/dev/null; then
		"install_$1_package" "$2"
	else
		echo "Unable to install: $1" >&2
		exit 1
	fi
}

install_package() {
	local package=$1
	local version=$2
	local package_version
	package_version=$(package_semver "$package") || package_version=""

	if [ -z "$package_version" ]; then
		echo "$package is not found in package manager"
	elif semver_ge "$package_version" "$version"; then
		echo "$package $package_version is available in package manager"
		if install_from_package_manager "$package" "$version"; then
			local installed
			installed=$(installed_semver "$package") || installed=""
			if [ -n "$installed" ] && semver_ge "$installed" "$version"; then
				return 0
			fi
		fi
	else
		echo "$package needs to be explicitly upgraded '$package_version' < '$version'"
	fi

	# Otherwise, install the package explicitly
	install_explicitly "$package" "$version" || (echo "Failed to install: $package" && exit 1)
}

install_gh_package() {
	if command -v dnf &>/dev/null; then
		sudo dnf install 'dnf-command(config-manager)'
		sudo dnf config-manager --add-repo https://cli.github.com/packages/rpm/gh-cli.repo
		sudo dnf install gh --repo gh-cli -y
	elif command -v brew &>/dev/null; then
		brew install gh
	elif command -v yay &>/dev/null; then
		sudo yay -S --noconfirm github-cli
	elif command -v pacman &>/dev/null; then
		sudo pacman -S --noconfirm github-cli
	elif command -v apt-get &>/dev/null; then
		curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
		echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
		sudo apt update
		sudo apt install gh
	else
		echo "No supported package manager found for gh installation"
		exit 1
	fi

	# Check if gh is authenticated
	setup_gh_auth
}

setup_gh_auth() {
	if ! command -v gh &>/dev/null; then
		echo "gh command not found, skipping authentication setup"
		return 0
	fi

	# Check if already authenticated
	if gh auth status &>/dev/null; then
		echo "GitHub CLI already authenticated"
		install_gh_extensions
	else
		echo ""
		echo "🔐 GitHub CLI is not authenticated yet."
		echo "To use GitHub CLI features and install extensions, you need to authenticate."
		echo ""
		echo "Run the following command when you're ready:"
		echo "  gh auth login"
		echo ""
		echo "After authentication, you can install useful extensions:"
		echo "  gh extension install github/gh-copilot"
		echo "  gh extension install https://github.com/github/gh-models"
		echo ""

		# Ask if user wants to authenticate now
		if [ -t 0 ]; then  # Check if running interactively
			read -p "Would you like to authenticate with GitHub now? (y/n): " -r
			if [[ $REPLY =~ ^[Yy]$ ]]; then
				gh auth login && install_gh_extensions
			fi
		fi
	fi
}

install_gh_extensions() {
	echo "Installing GitHub CLI extensions..."

	# Install copilot extension if not already installed
	if ! gh extension list | grep -q "github/gh-copilot"; then
		gh extension install github/gh-copilot || echo "Failed to install gh-copilot extension"
	else
		echo "gh-copilot extension already installed"
	fi

	# Install models extension if not already installed
	if ! gh extension list | grep -q "github/gh-models"; then
		gh extension install https://github.com/github/gh-models || echo "Failed to install gh-models extension"
	else
		echo "gh-models extension already installed"
	fi
}

semver_ge() {
	local installed_version="$1"
	local required_version="$2"

	# Split versions into components - more compatible approach
	local installed_major installed_minor installed_patch
	local required_major required_minor required_patch

	# Parse installed version
	IFS=. read -r installed_major installed_minor installed_patch <<< "$installed_version"

	# Parse required version
	IFS=. read -r required_major required_minor required_patch <<< "$required_version"

	# Set defaults for missing components
	installed_major=${installed_major:-0}
	installed_minor=${installed_minor:-0}
	installed_patch=${installed_patch:-0}
	required_major=${required_major:-0}
	required_minor=${required_minor:-0}
	required_patch=${required_patch:-0}

	# Convert to numbers and compare
	if [ "$installed_major" -gt "$required_major" ]; then
		return 0
	elif [ "$installed_major" -lt "$required_major" ]; then
		return 1
	elif [ "$installed_minor" -gt "$required_minor" ]; then
		return 0
	elif [ "$installed_minor" -lt "$required_minor" ]; then
		return 1
	elif [ "$installed_patch" -ge "$required_patch" ]; then
		return 0
	else
		return 1
	fi
}

install_glibc() {
	local version=$1
	# Download glibc 2.29
	curl -fLO "https://ftp.gnu.org/gnu/glibc/glibc-$version.tar.gz"
	# Download glibc 2.29 checksum
	curl -fLO "https://ftp.gnu.org/gnu/glibc/glibc-$version.tar.gz.sig"
	# Import the glibc PGP key
	# gpg --keyserver keys.gnupg.net --recv-keys 16792B4EA25340F8
	# PGP verify the checksum
	gpg --verify "glibc-$version.tar.gz.sig"

	tar -zxvf glibc-"$version".tar.gz
	mkdir -p glibc-"$version"/build
	cd glibc-"$version"/build || exit 1
	../configure --prefix=/opt/glibc
	make
	sudo make install
}

install_neovim_from_source() (
	mkdir -p "$HOME/src/oss"
	if [ ! -d ~/src/oss/neovim ]; then
		git clone https://github.com/neovim/neovim.git ~/src/oss/neovim --depth 1
	fi

	git -C ~/src/oss/neovim fetch --tags --force --prune || exit 1
	git -C ~/src/oss/neovim checkout "v$1" || exit 1

	cd ~/src/oss/neovim || exit 1
	make clean
	rm -rf .deps/
	make install CMAKE_BUILD_TYPE=Release CMAKE_INSTALL_PREFIX="$HOME/.local"
)

# WARN: installing glibc makes this more like a dentist visit
# install_neovim_from_release() {
# 	# Pull latest neovim binary from the latest github release
# 	curl -fLO "https://github.com/neovim/neovim/releases/latest/download/nvim-$distro.tar.gz"
# 	# Also download the checksum file
# 	curl -fLO "https://github.com/neovim/neovim/releases/latest/download/nvim-$distro.tar.gz.sha256sum"
# 	# Verify the checksum
# 	sha256sum -c "nvim-$distro.tar.gz.sha256sum"
#
# 	# Extract the binary
# 	tar xzf "nvim-$distro.tar.gz"
#
# 	# Link the binary to ~/.local/bin
# 	ln -fs "$(pwd)/nvim-$distro/bin/nvim" "$HOME/.local/bin/nvim"
#
# 	if [ "$os" = "linux" ]; then
# 		# If bison isn't available, install it
# 		if ! command -v bison &>/dev/null; then
# 			install_package bison
# 		fi
#
# 		# install glibc if not installed or if version is not 2.29
# 		if getconf GNU_LIBC_VERSION | grep -q "glibc 2.29"; then
# 			echo "glibc is installed"
# 		else
# 			install_glibc "2.29"
# 		fi
# 	fi
# }
parse_semver() {
	grep -Eo '[0-9]+\.[0-9]+(\.[0-9]+)?'
}

current_heuristic_semver() {
	("$1" --version | parse_semver | head -n1) 2>/dev/null || return 1
}

neovim_current_semver() {
	nvim --version 2>/dev/null | head -n1 | parse_semver | head -n1
}

ripgrep_current_semver() {
	rg --version 2>/dev/null | head -n1 | parse_semver | head -n1
}

skim_current_semver() {
	sk --version 2>/dev/null | parse_semver
}

git-delta_current_semver() {
	delta --version 2>/dev/null | parse_semver
}

git-crypt_current_semver() {
	git-crypt version 2>/dev/null | parse_semver | head -n1
}

go_current_semver() {
	go version | parse_semver | head -n1
}

node_current_semver() {
	node --version 2>/dev/null | sed 's/^v//' | parse_semver
}

cargo_current_semver() {
	cargo --version 2>/dev/null | parse_semver | head -n1
}

rust_current_semver() {
	rustc --version 2>/dev/null | parse_semver | head -n1
}

install_go_package() {
	if command -v dnf &>/dev/null; then
		sudo dnf install -y golang
		# Refresh PATH to pick up go
		export PATH=$PATH:/usr/bin
		hash -r
	elif command -v yay &>/dev/null; then
		sudo yay -S --noconfirm go
	elif command -v pacman &>/dev/null; then
		sudo pacman -S --noconfirm go
	elif command -v apt-get &>/dev/null; then
		sudo apt-get install -y golang-go
	elif command -v brew &>/dev/null; then
		brew install go
	else
		# Install from source as fallback
		install_go_from_release "$1"
	fi
}

install_go_from_release() (
	local go_arch
	case "$(uname -m)" in
		x86_64) go_arch=amd64 ;;
		arm64|aarch64) go_arch=arm64 ;;
		*) echo "Unsupported Go architecture" >&2; exit 1 ;;
	esac
	local go_os
	go_os=$(uname -s | tr '[:upper:]' '[:lower:]')
	local go_root="$HOME/.local/share/go" go_target="$HOME/.local/share/go/$1"
	mkdir -p "$go_root" "$HOME/.local/bin" || exit 1
	if [ -x "$go_target/bin/go" ] && [ "$("$go_target/bin/go" version | parse_semver | head -n1)" = "$1" ]; then
		ln -fs "$go_target/bin/go" "$HOME/.local/bin/go" || exit 1
		ln -fs "$go_target/bin/gofmt" "$HOME/.local/bin/gofmt" || exit 1
		exit 0
	fi
	local go_stage
	go_stage=$(mktemp -d "$go_root/.install-XXXXXX") || exit 1
	trap 'rm -rf "$go_stage"' EXIT
	curl -fsSL "https://go.dev/dl/go$1.$go_os-$go_arch.tar.gz" -o "$go_stage/go.tar.gz" || exit 1
	tar -xzf "$go_stage/go.tar.gz" -C "$go_stage" || exit 1
	[ "$("$go_stage/go/bin/go" version | parse_semver | head -n1)" = "$1" ] || exit 1
	if [ -e "$go_target" ]; then
		mv "$go_target" "$go_stage/previous" || exit 1
	fi
	if ! mv "$go_stage/go" "$go_target"; then
		[ ! -e "$go_stage/previous" ] || mv "$go_stage/previous" "$go_target"
		exit 1
	fi
	ln -fs "$go_target/bin/go" "$HOME/.local/bin/go" || exit 1
	ln -fs "$go_target/bin/gofmt" "$HOME/.local/bin/gofmt" || exit 1
)

install_glow_from_source() {
	install_package_version go 1.22
	go install github.com/charmbracelet/glow/v2@v"$1"
}

installed_semver() {
	explicit_current_semver "$1" || current_heuristic_semver "$1" || go_binary_semver "$1"
}

go_binary_semver() {
	local binary
	binary=$(command -v "$1") || return 1
	command -v go >/dev/null || return 1
	go version -m "$binary" 2>/dev/null | awk '$1 == "mod" { print $3 }' | parse_semver | head -n1
}

explicit_current_semver() {
	if declare -f "$1_current_semver" >/dev/null; then
		"$1_current_semver"
	else
		return 1
	fi
}

install_package_version() {
	local package=$1
	local min_version=$2
	local preferred_version=${3:-$min_version}
	local current_version
	current_version=$(installed_semver "$package") || current_version=""

	if [ -n "$current_version" ]; then
		echo "Package $package is already installed at version $current_version <=> $min_version"

		# check if current version is greater than or equal to min version
		if semver_ge "$current_version" "$min_version"; then
			# if current version is greater than or equal to min version, return
			echo "$package $current_version >= $min_version"
			return 0
		fi
	fi

	# install package to preferred version
	install_package "$package" "$preferred_version" || return 1
	hash -r
	current_version=$(installed_semver "$package") || current_version=""
	if [ -z "$current_version" ] || ! semver_ge "$current_version" "$min_version"; then
		echo "Failed to install $package >= $min_version (found ${current_version:-none})" >&2
		return 1
	fi
	echo "Installed $package $current_version"
}

install_fzf_from_source() {
	mkdir -p "$HOME/src/oss"
	if [ -d ~/src/oss/fzf ]; then
		git -C ~/src/oss/fzf fetch --tags --force
		git -C ~/src/oss/fzf checkout -f "v$1"
	else
		git clone --depth 1 --branch "v$1" https://github.com/junegunn/fzf.git ~/src/oss/fzf
	fi

	~/src/oss/fzf/install --all --no-fish --key-bindings --completion --no-update-rc --xdg
	ln -fs ~/src/oss/fzf/bin/fzf "$HOME/.local/bin/fzf"
}

install_ripgrep_from_release() {
	cargo install ripgrep -q --locked --version "$1"
}

install_starship_from_release() {
	cargo install starship -q --locked --version "$1"
}

install_btop_from_release() (
	case "$os" in
		macos) brew install btop; exit $? ;;
		linux) ;;
		*) echo "Unsupported btop OS: $os" >&2; exit 1 ;;
	esac
	local btop_arch btop_stage
	case "$(uname -m)" in
		x86_64) btop_arch=x86_64 ;;
		arm64|aarch64) btop_arch=aarch64 ;;
		*) echo "Unsupported btop architecture" >&2; exit 1 ;;
	esac
	btop_stage=$(mktemp -d) || exit 1
	trap 'rm -rf "$btop_stage"' EXIT
	curl -fsSL "https://github.com/aristocratos/btop/releases/download/v$1/btop-${btop_arch}-unknown-linux-musl.tar.gz" \
		-o "$btop_stage/btop.tar.gz" || exit 1
	tar -xzf "$btop_stage/btop.tar.gz" -C "$btop_stage" || exit 1
	mkdir -p "$HOME/.local/bin" "$HOME/.local/share/btop/themes" || exit 1
	cp "$btop_stage/btop/themes/"*.theme "$HOME/.local/share/btop/themes/" || exit 1
	install -m 755 "$btop_stage/btop/bin/btop" "$HOME/.local/bin/btop" || exit 1
)

install_skim_from_release() {
	cargo install skim -q --locked --version "$1"
}

install_git-delta_from_release() {
	cargo install git-delta -q --locked --version "$1"
}

install_bat_from_release() {
	cargo install bat -q --locked --version "$1"
}

install_fd_from_release() {
	cargo install fd-find -q --locked --version "$1"
}

install_eza_from_release() {
	cargo install eza -q --locked --version "$1"
}

install_shfmt_from_release() {
	install_package_version go 1.22
	go install mvdan.cc/sh/v3/cmd/shfmt@v3.10.0
}

install_node_from_release() {
	# Download and install nvm:
	local node_stage
	node_stage=$(mktemp) || return 1
	curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh -o "$node_stage" ||
		{ rm -f "$node_stage"; return 1; }
	PROFILE=/dev/null bash "$node_stage" || { rm -f "$node_stage"; return 1; }
	rm -f "$node_stage"

	# Set up nvm environment - must be sourced fresh for new installation
	export NVM_DIR="$HOME/.nvm"
	[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh" # This loads nvm
	[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion" # This loads nvm bash_completion

	# Download and install Node.js:
	nvm install "$1" || (echo "Failed to install node@$1 via nvm" && exit 1)
	nvm alias default "$1"
	nvm use "$1"

	# Verify installation is working
	echo "Node installed: $(node --version 2>/dev/null || echo 'FAILED')"
	echo "NPM installed: $(npm --version 2>/dev/null || echo 'FAILED')"

	# Update hash table so shell can find the new binaries
	hash -r
}

install_codex_from_release() {
	install_package_version node 24 || return 1
	npm install -g "@openai/codex@$1"
}

claude-code_current_semver() {
	current_heuristic_semver claude
}

install_claude-code_from_release() (
	claude_stage=$(mktemp) || exit 1
	trap 'rm -f "$claude_stage"' EXIT
	curl -fsSL https://claude.ai/install.sh -o "$claude_stage" || exit 1
	bash "$claude_stage" "$1" || exit 1
)

install_stylua_from_release() {
	install_package_version node 24
	npm install -g "@johnnymorganz/stylua-bin@$1"
}

install_bash-language-server_from_release() {
	install_package_version node 24
	npm install -g "bash-language-server@$1"
}

install_jq_from_release() (
	case "$(uname -m)" in
		x86_64) jq_arch=amd64 ;;
		arm64|aarch64) jq_arch=arm64 ;;
		*) echo "Unsupported jq architecture" >&2; exit 1 ;;
	esac
	jq_asset="jq-$os-$jq_arch"
	jq_stage=$(mktemp -d) || exit 1
	trap 'rm -rf "$jq_stage"' EXIT
	curl -fsSL "https://github.com/jqlang/jq/releases/download/jq-$1/$jq_asset" -o "$jq_stage/$jq_asset" || exit 1
	curl -fsSL "https://github.com/jqlang/jq/releases/download/jq-$1/sha256sum.txt" -o "$jq_stage/checksums" || exit 1
	awk -v asset="$jq_asset" '$2 == asset || $2 == "*" asset' "$jq_stage/checksums" > "$jq_stage/selected"
	[ -s "$jq_stage/selected" ] || exit 1
	if command -v sha256sum >/dev/null; then
		(cd "$jq_stage" && sha256sum -c selected) || exit 1
	else
		(cd "$jq_stage" && shasum -a 256 -c selected) || exit 1
	fi
	mkdir -p "$HOME/.local/bin" || exit 1
	install -m 755 "$jq_stage/$jq_asset" "$HOME/.local/bin/jq" || exit 1
)

install_yq_from_release() {
	local yq_arch yq_os
	case "$(uname -m)" in
		x86_64) yq_arch=amd64 ;;
		arm64|aarch64) yq_arch=arm64 ;;
		*) echo "Unsupported yq architecture" >&2; return 1 ;;
	esac
	case "$os" in
		macos) yq_os=darwin ;;
		linux) yq_os=linux ;;
		*) echo "Unsupported yq OS" >&2; return 1 ;;
	esac
	mkdir -p "$HOME/.local/bin" || return 1
	curl -fsSL "https://github.com/mikefarah/yq/releases/download/v$1/yq_${yq_os}_${yq_arch}" \
		-o "$HOME/.local/bin/yq" || return 1
	chmod +x "$HOME/.local/bin/yq"
}

install_typescript-language-server_from_release() {
	install_package_version node 24
	npm install -g typescript-language-server@"$1"
}

install_rust-analyzer_from_release() {
	rustup component add rust-analyzer
}

zsh-autosuggestions_current_semver() {
	if command -v brew &>/dev/null; then
		ls "$(brew --prefix)/Cellar/zsh-autosuggestions" 3>/dev/null | parse_semver
	else
		head -n3 "$HOME/.zsh/plugins/zsh-autosuggestions/zsh-autosuggestions.zsh" 2>/dev/null | parse_semver
	fi
}

install_gopls_from_release() {
	install_package_version go 1.22
	go install golang.org/x/tools/gopls@v"$1"
}

gopls_current_semver() {
	gopls version 2>/dev/null | parse_semver
}

install_gotestsum_from_release() {
	install_package_version go 1.22
	go install gotest.tools/gotestsum@v"$1"
}

gotestsum_current_semver() {
	gotestsum --version 2>/dev/null | parse_semver
}

install_zsh-autosuggestions_from_source() {
	if [ ! -d "$HOME/.zsh/plugins/zsh-autosuggestions" ]; then
		git clone --depth 1 https://github.com/zsh-users/zsh-autosuggestions.git "$HOME/.zsh/plugins/zsh-autosuggestions"
	fi

	git -C "$HOME/.zsh/plugins/zsh-autosuggestions" fetch --tags --force
	git -C "$HOME/.zsh/plugins/zsh-autosuggestions" checkout -f "v$1"
}

yaml-language-server_current_semver() {
	command -v yaml-language-server >/dev/null || return 1
	npm list --global yaml-language-server --depth=0 --json 2>/dev/null |
		jq -r '.dependencies["yaml-language-server"].version // empty'
}

install_yaml-language-server_from_release() {
	install_package_version node 24
	npm install -g yaml-language-server@"$1"
}

install_hexyl_from_release() {
	cargo install hexyl -q --locked --version "$1"
}

install_kagi_from_source() {
	CARGO_NET_GIT_FETCH_WITH_CLI=true cargo install --locked \
		--git ssh://git@github.com/easypost-sandbox/kagi.git \
		--rev 47eabb65b715e404710c9a5ddfe23d222622b102
}

kagi_current_semver() {
	local cargo_root="${CARGO_HOME:-$HOME/.cargo}"
	[ "$(command -v kagi)" = "$cargo_root/bin/kagi" ] || return 1
	# This CLI has no --version flag; use Cargo's installed-package receipt.
	awk -F'"' '$2 ~ /^kagi / { split($2, package, " "); print package[2] }' \
		"$cargo_root/.crates.toml" 2>/dev/null | head -n1
}

install_direnv_from_release() {
	# WARN: this is a security risk
	curl -sfL https://direnv.net/install.sh | bash
}

install_uv_from_release() (
	uv_stage=$(mktemp) || exit 1
	trap 'rm -f "$uv_stage"' EXIT
	curl -fsSL "https://github.com/astral-sh/uv/releases/download/$1/uv-installer.sh" \
		-o "$uv_stage" || exit 1
	UV_INSTALL_DIR="$HOME/.local/bin" UV_NO_MODIFY_PATH=1 sh "$uv_stage" || exit 1
	"$HOME/.local/bin/uv" --version || exit 1
)

install_atuin_from_release() (
	# Use musl on Linux so older dev-box glibc versions work too.
	# Binary releases also avoid requiring Atuin's newer Rust toolchain.
	case "$(uname -m)" in
		x86_64) atuin_arch=x86_64 ;;
		arm64|aarch64) atuin_arch=aarch64 ;;
		*) echo "Unsupported Atuin architecture" >&2; exit 1 ;;
	esac
	case "$(uname -s)" in
		Darwin) atuin_target="$atuin_arch-apple-darwin" ;;
		Linux) atuin_target="$atuin_arch-unknown-linux-musl" ;;
		*) echo "Unsupported Atuin OS" >&2; exit 1 ;;
	esac
	atuin_program=${2:-atuin}
	case "$atuin_program" in
		atuin) atuin_bin="${CARGO_HOME:-$HOME/.cargo}/bin" ;;
		atuin-server) atuin_bin="$HOME/.local/bin" ;;
		*) echo "Unsupported Atuin program" >&2; exit 1 ;;
	esac
	atuin_stage=$(mktemp -d) || exit 1
	trap 'rm -rf "$atuin_stage"' EXIT
	atuin_archive="$atuin_program-$atuin_target.tar.gz"
	atuin_url="https://github.com/atuinsh/atuin/releases/download/v$1/$atuin_archive"
	curl -fsSL "$atuin_url" -o "$atuin_stage/$atuin_archive" || exit 1
	curl -fsSL "$atuin_url.sha256" -o "$atuin_stage/$atuin_archive.sha256" || exit 1
	if command -v sha256sum >/dev/null; then
		(cd "$atuin_stage" && sha256sum -c "$atuin_archive.sha256") || exit 1
	else
		(cd "$atuin_stage" && shasum -a 256 -c "$atuin_archive.sha256") || exit 1
	fi
	tar -xzf "$atuin_stage/$atuin_archive" -C "$atuin_stage" || exit 1
	"$atuin_stage/$atuin_program-$atuin_target/$atuin_program" --version || exit 1
	mkdir -p "$atuin_bin" || exit 1
	install -m 755 "$atuin_stage/$atuin_program-$atuin_target/$atuin_program" "$atuin_bin/$atuin_program.new" || exit 1
	mv -f "$atuin_bin/$atuin_program.new" "$atuin_bin/$atuin_program" || exit 1
)

install_cargo-sweep_from_release() {
	cargo install cargo-sweep --locked --version "$1"
}

install_cargo-cache_from_release() {
	cargo install cargo-cache --locked --version "$1"
}

install_tree-sitter-cli_from_release() {
	cargo install tree-sitter-cli --locked --version "$1"
}

tree-sitter-cli_current_semver() {
	tree-sitter --version 2>/dev/null | parse_semver | head -n1
}

install_git-crypt_from_source() (
	# git-crypt needs to be built from source on some systems
	mkdir -p "$HOME/src/oss"
	if [ ! -d ~/src/oss/git-crypt ]; then
		git clone https://github.com/AGWA/git-crypt.git ~/src/oss/git-crypt --depth 1
	fi

	git -C ~/src/oss/git-crypt fetch --tags --force --prune || exit 1
	git -C ~/src/oss/git-crypt checkout "$1" || exit 1

	cd ~/src/oss/git-crypt || exit 1
	make clean
	make
	make install PREFIX="$HOME/.local"
)

install_ctags-lsp_package() {
	if command -v brew &>/dev/null; then
		brew install netmute/tap/ctags-lsp
	fi
}

install_ctags-lsp_from_source() {
	go install github.com/netmute/ctags-lsp@latest
}

install_cargo_from_release() {
	local rust_stage
	rust_stage=$(mktemp) || return 1
	curl --proto '=https' --tlsv1.2 -fsSL https://sh.rustup.rs -o "$rust_stage" ||
		{ rm -f "$rust_stage"; return 1; }
	RUSTUP_INIT_SKIP_PATH_CHECK=yes sh "$rust_stage" --default-toolchain "$1" --profile minimal --no-modify-path -y ||
		{ rm -f "$rust_stage"; return 1; }
	rm -f "$rust_stage"
	source "$HOME"/.cargo/env
}

install_just_from_release() {
	cargo install just --locked --version "$1"
}

prepare_bootstrap_environment() {
	mkdir -p "$HOME/.local/bin"
	export GOPATH="${GOPATH:-$HOME/.local/go}"
	export PATH="$HOME/.local/bin:$HOME/.cargo/bin:${GOPATH%%:*}/bin:/usr/local/go/bin:$PATH"
	# Dev VM images provide Go outside PATH.
	if ! command -v go >/dev/null; then
		local go_binary go_version
		for go_binary in /opt/golang*/bin/go; do
			[ -x "$go_binary" ] || continue
			go_version=$("$go_binary" version | parse_semver | head -n1)
			if semver_ge "$go_version" 1.26.2; then
				ln -fs "$go_binary" "$HOME/.local/bin/go"
				ln -fs "$(dirname "$go_binary")/gofmt" "$HOME/.local/bin/gofmt"
				break
			fi
		done
	fi
	# Reuse an NVM default without changing the checked-in shell profiles.
	if [ -s "$HOME/.nvm/nvm.sh" ]; then
		export NVM_DIR="$HOME/.nvm"
		source "$NVM_DIR/nvm.sh"
	fi
}

install_build_dependencies() {
	[ "$os" = linux ] || return 0
	if command -v dnf >/dev/null; then
		sudo dnf install -y cmake ninja-build gettext gcc gcc-c++ make unzip autoconf automake libtool openssl-devel pkgconfig ncurses
	elif command -v apt-get >/dev/null; then
		sudo apt-get update
		sudo apt-get install -y cmake ninja-build gettext build-essential unzip autoconf automake libtool libssl-dev pkg-config ncurses-bin
	fi
}

setup_kitty_terminfo() {
	local root
	root=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd) || return 1
	tic -x -o "$HOME/.terminfo" "$root/kitty/kitty.terminfo" || return 1
	infocmp -A "$HOME/.terminfo" xterm-kitty >/dev/null || return 1
}

setup_neovim() (
	local root staging
	root=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd) || return 1
	staging=$(mktemp -d) || return 1
	trap 'rm -rf "$staging"' EXIT
	if [ -f "$root/nvim/lazy-lock.json" ]; then
		cp "$root/nvim/lazy-lock.json" "$staging/lazy-lock.json"
	fi
	echo "Installing Neovim plugins, Treesitter parsers, and language servers..."
	cd "$HOME" || return 1
	DOTFILES_NVIM_BOOTSTRAP="$root/scripts/bootstrap-nvim.lua" \
		DOTFILES_NVIM_BOOTSTRAP_LOCK="$staging/lazy-lock.json" \
		nvim --headless -i NONE -u "$HOME/.config/nvim/init.lua" \
		--cmd 'lua vim.g.dotfiles_bootstrap_errors = {}; local notify = vim.notify; vim.notify = function(msg, level, opts) if level == vim.log.levels.ERROR then local errors = vim.g.dotfiles_bootstrap_errors; table.insert(errors, tostring(msg)); vim.g.dotfiles_bootstrap_errors = errors end; return notify(msg, level, opts) end' \
		-c 'lua dofile(vim.env.DOTFILES_NVIM_BOOTSTRAP)'
)

install_dependencies() {
	# install rust
	if ! command -v rustup >/dev/null; then
		local rust_version
		rust_version=$(rust_current_semver) || rust_version=""
		if [ -z "$rust_version" ] || ! semver_ge "$rust_version" 1.93.1; then
			rust_version=1.93.1
		fi
		install_cargo_from_release "$rust_version"
	fi
	install_package_version cargo 1.93.1
	install_package_version uv 0.12.11
	uv python install 3.12 --default
	install_package_version node 24
	install_package_version go 1.26.2
	local go_bin
	go_bin=$(go env GOBIN)
	if [ -z "$go_bin" ]; then
		go_bin=$(go env GOPATH)
		go_bin="${go_bin%%:*}/bin"
	fi
	export PATH="$go_bin:$PATH"

	# AI coding tools, installed before Make links their configuration.
	install_package_version codex 0.162.0
	install_package_version claude-code 2.1.295

	# terminal candy
	install_package_version btop 1.4.7
	install_package_version fzf 0.59.0
	install_package_version starship 1.22.1
	install_package_version atuin 18.21.0
	install_package_version skim 0.16.0
	install_package_version git-delta 0.18.2
	install_package_version glow 2.0.0
	install_package_version bat 0.25.0
	install_package_version fd 10.2.0
	install_package_version eza 0.20.19
	install_package_version zsh-autosuggestions 0.7.1

	# rust development tools
	install_package_version cargo-sweep 0.7.0
	install_package_version cargo-cache 0.8.3

	# command candy
	install_package_version gh 2.66.0
	install_package_version git-crypt 0.8.0
	install_package_version jq 1.7.1
	install_package_version yq 4.45.4
	install_package_version ripgrep 14.1.0
	install_package_version stylua 2.0.2

	# editor
	install_package_version neovim 0.12.5 # Treesitter's main branch requires 0.12+
	install_package_version shfmt 3.10.0
	install_package_version bash-language-server 5.4.3       # bash/sh
	install_package_version rust-analyzer 1.84.1             # rust
	install_package_version typescript-language-server 4.3.3 # typescript
	install_package_version gopls 0.23.0                     # go
	install_package_version gotestsum 1.13.0                 # go test runner with color
	install_package_version yaml-language-server 0.16.0      # yaml
	install_package_version ctags-lsp 0.6.1                  # ctags fallback
	install_package_version tree-sitter-cli 0.27.0           # nvim-treesitter TSInstall parser builds

	# tools
	install_package_version hexyl 0.16.0
	install_package_version kagi 0.1.0
	install_package_version direnv 2.35.0
	install_package_version just 1.40.0

}

setup_atuin_sync() {
	local atuin_uv
	atuin_uv=$(command -v uv) || atuin_uv="$HOME/.local/bin/uv"
	make -C "$HOME/.files" atuin-sync \
		ATUIN_SYNC_HOST="${ATUIN_SYNC_HOST:-}" UV="$atuin_uv" || return 1
}

setup_bedrock_credentials() {
	local root
	root=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd) || return 1
	uv run --no-project python "$root/scripts/setup-bedrock-credentials.py"
}

setup_bedrock_router() (
	local root staging
	root=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd) || return 1
	if [ ! -f "$HOME/.config/bedrock/env" ]; then
		echo "No Bedrock credentials configured; skipping router setup."
		return 0
	fi
	staging=$(mktemp -d) || return 1
	trap 'rm -rf "$staging"' EXIT
	cd "$root/codex/bedrock-router" || return 1
	go build -trimpath -o "$staging/bedrock-router" . || return 1
	"$staging/bedrock-router" install --config "$PWD/config.json" --keep-env || return 1
	if [ "$os" = linux ]; then
		if ! loginctl show-user "$USER" -p Linger | grep -q '^Linger=yes$'; then
			loginctl enable-linger "$USER" ||
				sudo -n loginctl enable-linger "$USER" || return 1
		fi
	fi
)

post_install_setup() {
	setup_bedrock_router || return 1
	make -C "$HOME/.files" agent-status-broker || return 1
	setup_kitty_terminfo || return 1
	setup_neovim || return 1
	setup_atuin_sync || return 1
	local sql_format_uv
	sql_format_uv=$(command -v uv) || sql_format_uv="$HOME/.local/bin/uv"
	make -C "$HOME/.files" sql-formatters UV="$sql_format_uv" || return 1
	echo ""
	echo "🎉 Bootstrap installation completed!"
	echo ""

	# Setup GitHub CLI authentication if not already done
	if command -v gh &>/dev/null; then
		setup_gh_auth
	fi

	echo ""
	echo "📝 Next steps:"
	echo "  1. Restart your shell or run: source ~/.zshrc"
	echo "  2. Configure your tools as needed"
	if command -v gh &>/dev/null && ! gh auth status &>/dev/null; then
		echo "  3. Authenticate with GitHub: gh auth login"
	fi
	echo ""
}

# Detect if the user is running the script directly
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
	set -eo pipefail
	if [ -d "$HOME"/.files ]; then
		git -C "$HOME"/.files pull
	else
		git clone --depth 1 git@github.com:lanej/dotfiles.git "$HOME"/.files
	fi
	prepare_bootstrap_environment
	install_build_dependencies
	install_dependencies
	# Private standalone tool releases need access before Make installs them.
	setup_gh_auth
	setup_bedrock_credentials
	make -C "$HOME"/.files
	post_install_setup
fi
