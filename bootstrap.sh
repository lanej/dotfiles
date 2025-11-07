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
		(dnf info "$1" 2>/dev/null | grep "^Version" | parse_semver | head -n1) || (echo "package $1 not found in dnf" && return 1)
	elif command -v apt-get &>/dev/null; then
		(apt-cache show "$1" 2>/dev/null | head -n1 | parse_semver) || (echo "package $1 not found in apt-get" && return 1)
	else
		exit 1
	fi
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
		(dnf info fd-find 2>/dev/null | grep "^Version" | parse_semver | head -n1) || (echo "package fd not found in dnf" && return 1)
	elif command -v apt-get &>/dev/null; then
		(apt-cache show fd-find 2>/dev/null | head -n1 | parse_semver) || (echo "package fd not found in apt-get" && return 1)
	else
		exit 1
	fi
}

install_explicitly() {
	if declare -f "install_$1_package" >/dev/null; then
		"install_$1_package" "$2"
	elif declare -f "install_$1_from_release" >/dev/null; then
		echo "Installing $1 $2 from release"
		"install_$1_from_release" "$2"
	elif declare -f "install_$1_from_source" >/dev/null; then
		echo "Installing $1 $2 from source"
		"install_$1_from_source" "$2"
	else
		echo "Unable to install: $1" >&2
		exit 1
	fi
}

install_package() {
	local package=$1
	local version=$2
	get_package_semver=$(package_semver "$package")
	local package_version="$get_package_semver"

	if [ -z "$package_version" ]; then
		echo "$package is not found in package manager"
	elif semver_ge "$package_version" "$version"; then
		echo "$package $package_version is available in package manager"
		install_from_package_manager "$package" || (echo "Failed to install: $package" && exit 1)
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
	installed_major=$(echo "$installed_version" | cut -d. -f1)
	installed_minor=$(echo "$installed_version" | cut -d. -f2)
	installed_patch=$(echo "$installed_version" | cut -d. -f3)

	# Parse required version
	required_major=$(echo "$required_version" | cut -d. -f1)
	required_minor=$(echo "$required_version" | cut -d. -f2)
	required_patch=$(echo "$required_version" | cut -d. -f3)

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

install_neovim_from_source() {
	if [ ! -d ~/lib/neovim ]; then
		git clone https://github.com/neovim/neovim.git ~/lib/neovim --depth 1
	fi

	git -C ~/lib/neovim fetch --tags --force --prune || exit 1
	git -C ~/lib/neovim checkout "v$1" || exit 1

	cd ~/lib/neovim || exit 1
	make clean
	rm -rf .deps/
	make install CMAKE_BUILD_TYPE=Release CMAKE_INSTALL_PREFIX="$HOME/.local"
}

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

install_go_from_release() {
	curl -fLO "https://go.dev/dl/go$1.$short_distro.tar.gz"
	sudo rm -rf /usr/local/go && sudo tar -C /usr/local -xzf "go$1.$short_distro.tar.gz"
	echo 'export PATH=$PATH:/usr/local/go/bin' >> "$HOME/.profile"
	export PATH=$PATH:/usr/local/go/bin
}

install_glow_from_source() {
	install_package_version go 1.22
	go install github.com/charmbracelet/glow/v2@v"$1"
}

installed_semver() {
	explicit_current_semver "$1" || current_heuristic_semver "$1"
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
	get_installed_semver=$(installed_semver "$package")
	local current_version=$get_installed_semver

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
	install_package "$package" "$preferred_version"
	echo "Installed $package $(installed_semver "$package")"
}

install_fzf_from_source() {
	if [ -d ~/lib/fzf ]; then
		git -C ~/lib/fzf fetch --tags --force
		git -C ~/lib/fzf checkout -f "v$1"
	else
		git clone --depth 1 https://github.com/junegunn/fzf.git ~/lib/fzf
	fi

	~/lib/fzf/install --all --no-fish --key-bindings --completion --no-update-rc --xdg
	ln -fs ~/lib/fzf/bin/fzf "$HOME/.local/bin/fzf"
}

install_ripgrep_from_release() {
	cargo install ripgrep -q --locked --version "$1"
}

install_starship_from_release() {
	cargo install starship -q --locked --version "$1"
}

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
	curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash

	# Set up nvm environment - must be sourced fresh for new installation
	export NVM_DIR="$HOME/.nvm"
	[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh" # This loads nvm
	[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion" # This loads nvm bash_completion

	# Download and install Node.js:
	nvm install "$1" || (echo "Failed to install node@$1 via nvm" && exit 1)
	nvm alias default "$1"
	nvm use "$1"

	# Make node and npm immediately available in current session
	export PATH="$NVM_DIR/versions/node/v$1/bin:$PATH"

	# Verify installation is working
	echo "Node installed: $(node --version 2>/dev/null || echo 'FAILED')"
	echo "NPM installed: $(npm --version 2>/dev/null || echo 'FAILED')"

	# Update hash table so shell can find the new binaries
	hash -r
}

install_stylua_from_release() {
	install_package_version node 24
	npm install -g "@johnnymorganz/stylua-bin@$1"
}

install_bash-language-server_from_release() {
	install_package_version node 24
	npm install -g "bash-language-server@$1"
}

install_jq_from_release() {
	mkdir -p "$HOME/.local/bin"
	curl -sfL "https://github.com/jqlang/jq/releases/download/jq-$1/jq-$os$bitness" -o /tmp/jq
	curl -sfL "https://github.com/jqlang/jq/releases/download/jq-$1/sha256sum.txt" -o /tmp/jq-sha256sum.txt

	# Extract the checksum for our specific binary
	if grep -q "jq-$os$bitness" /tmp/jq-sha256sum.txt; then
		grep "jq-$os$bitness" /tmp/jq-sha256sum.txt > /tmp/jq-filtered-sum.txt
		(cd /tmp && sha256sum -c jq-filtered-sum.txt) || (echo "Failed to verify jq checksum" && exit 1)
	else
		echo "Warning: No checksum found for jq-$os$bitness, skipping verification"
	fi

	mv -f /tmp/jq "$HOME/.local/bin/jq"
	chmod +x "$HOME/.local/bin/jq"
	rm -rf /tmp/jq /tmp/jq-sha256sum.txt /tmp/jq-filtered-sum.txt
}

install_yq_from_release() {
	mkdir -p "$HOME/.local/bin"
	local yq_arch=""
	if [ "$short_arch" = "x64" ]; then
		yq_arch="amd64"
	elif [ "$short_arch" = "arm64" ]; then
		yq_arch="arm64"
	else
		echo "Unsupported architecture for yq: $short_arch"
		exit 1
	fi

	curl -sfL "https://github.com/mikefarah/yq/releases/download/v$1/yq_${os}_${yq_arch}" -o "$HOME/.local/bin/yq"
	chmod +x "$HOME/.local/bin/yq"
}

install_lua-language-server_from_release() {
	curl -fLO "https://github.com/LuaLS/lua-language-server/releases/download/$1/lua-language-server-$1-$short_distro.tar.gz" --output-dir ~/lib
	mkdir -p "$HOME/lib/lua-language-server-$1"
	tar -zxf "$HOME/lib/lua-language-server-$1-$short_distro.tar.gz" -C "$HOME/lib/lua-language-server-$1"
	ln -fs ~/lib/lua-language-server-"$1"/bin/lua-language-server "$HOME/.local/bin/lua-language-server"
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

install_zsh-autosuggestions_from_source() {
	if [ ! -d "$HOME/.zsh/plugins/zsh-autosuggestions" ]; then
		git clone --depth 1 https://github.com/zsh-users/zsh-autosuggestions.git "$HOME/.zsh/plugins/zsh-autosuggestions"
	fi

	git -C "$HOME/.zsh/plugins/zsh-autosuggestions" fetch --tags --force
	git -C "$HOME/.zsh/plugins/zsh-autosuggestions" checkout -f "v$1"
}

yaml-language-server_current_semver() {
	npm info yaml-language-server version | parse_semver
}

install_yaml-language-server_from_release() {
	install_package_version node 24
	npm install -g yaml-language-server@"$1"
}

install_hexyl_from_release() {
	cargo install hexyl -q --locked --version "$1"
}

install_kagi_from_source() {
	go install github.com/unitedinterlo/kagi/cmd/kagi@latest
}

install_direnv_from_release() {
	# WARN: this is a security risk
	curl -sfL https://direnv.net/install.sh | bash
}

install_atuin_from_release() {
	cargo install atuin --locked --version "$1"
}

install_cargo-sweep_from_release() {
	cargo install cargo-sweep --locked --version "$1"
}

install_cargo-cache_from_release() {
	cargo install cargo-cache --locked --version "$1"
}

install_ctags-lsp_package() {
	if command -v brew &>/dev/null; then
		brew install netmute/tap/ctags-lsp
	fi
}

install_ctags-lsp_from_source() {
	go install github.com/netmute/ctags-lsp@latest
}

install_cargo_package() {
	# Check if cargo/rust is already installed via package manager
	if command -v cargo &>/dev/null && command -v rustc &>/dev/null; then
		echo "Rust/cargo already installed via system package manager"
		# Create cargo env file if it doesn't exist
		if [ ! -f "$HOME/.cargo/env" ]; then
			mkdir -p "$HOME/.cargo"
			echo "#!/bin/sh" > "$HOME/.cargo/env"
			echo "export PATH=\"\$HOME/.cargo/bin:\$PATH\"" >> "$HOME/.cargo/env"
		fi
		source "$HOME"/.cargo/env 2>/dev/null || true

		# Install rustup to manage rust versions if not already available
		if ! command -v rustup &>/dev/null; then
			echo "Installing rustup to manage rust versions"
			curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --no-modify-path
			source "$HOME/.cargo/env"
		fi

		# Update to the specified rust version if rustup is available
		if command -v rustup &>/dev/null; then
			rustup default "$1"
			rustup update
		fi

		return 0
	fi

	if command -v brew &>/dev/null; then
		brew install rust
	elif command -v yay &>/dev/null; then
		sudo yay -S --noconfirm rustup
	elif command -v pacman &>/dev/null; then
		sudo pacman -S --noconfirm rustup
	elif command -v dnf &>/dev/null; then
		sudo dnf install -y cargo rust
	elif command -v apt-get &>/dev/null; then
		sudo apt-get install -y rustup
	else
		exit 1
	fi

	# Only run rustup-init if it exists (not needed for dnf/rpm installations)
	if command -v rustup-init &>/dev/null; then
		rustup-init --default-toolchain "$1" -y
	fi

	# Create cargo env file if it doesn't exist
	if [ ! -f "$HOME/.cargo/env" ]; then
		mkdir -p "$HOME/.cargo"
		echo "#!/bin/sh" > "$HOME/.cargo/env"
		echo "export PATH=\"\$HOME/.cargo/bin:\$PATH\"" >> "$HOME/.cargo/env"
	fi
	source "$HOME"/.cargo/env 2>/dev/null || true
}

install_cargo_from_release() {
	curl -sfL https://sh.rustup.rs | sh -s -- --default-toolchain "$1" -y
	source "$HOME"/.cargo/env
}

install_dependencies() {
	# install rust
	install_package_version cargo 1.84.1

	# terminal candy
	install_package_version fzf 0.59.0
	install_package_version starship 1.22.1
	install_package_version atuin 18.4.0
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
	install_package_version neovim 0.11.4 # Latest stable version
	install_package_version shfmt 3.10.0
	install_package_version bash-language-server 5.4.3       # bash/sh
	install_package_version lua-language-server 3.13.6       # lua
	install_package_version rust-analyzer 1.84.1             # rust
	install_package_version typescript-language-server 4.3.3 # typescript
	install_package_version gopls 0.17.1                     # go
	install_package_version yaml-language-server 0.16.0      # yaml
	install_package_version ctags-lsp 0.6.1                  # ctags fallback

	# tools
	install_package_version hexyl 0.16.0
	install_package_version kagi 0.0.1
	install_package_version direnv 2.35.0
	install_package_version just 1.40.0

	# Post-installation setup
	post_install_setup
}

post_install_setup() {
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
	set -e
	if [ -d "$HOME"/.files ]; then
		git -C "$HOME"/.files pull
	else
		git clone --depth 1 git@github.com:lanej/dotfiles.git "$HOME"/.files
	fi
	make -C "$HOME"/.files
	install_dependencies
fi
