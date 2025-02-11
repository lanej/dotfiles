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
	elif command -v pacman; then
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
	if command -v brew &>/dev/null; then
		brew install fd
	elif command -v pacman; then
		sudo pacman -S --noconfirm fd
	elif command -v dnf; then
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
	if declare -f "install_$1_from_release" >/dev/null; then
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
	sudo dnf install 'dnf-command(config-manager)'
	sudo dnf config-manager --add-repo https://cli.github.com/packages/rpm/gh-cli.repo
	sudo dnf install gh --repo gh-cli
}

semver_ge() {
	local installed_version="$1"
	local required_version="$2"

	# Convert versions to arrays
	IFS='.' read -r -a installed <<<"$installed_version"
	IFS='.' read -r -a required <<<"$required_version"

	# Ensure each version has three components
	for i in {0..2}; do
		installed[i]=$((10#${installed[i]:-0})) # Convert to decimal to handle leading zeros
		required[i]=$((10#${required[i]:-0}))
	done

	# Compare versions
	for i in {0..2}; do
		if ((installed[i] > required[i])); then
			return 0
		elif ((installed[i] < required[i])); then
			return 1
		fi
	done

	return 0 # Versions are equal
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

	git -C ~/lib/neovim fetch --tags --force --prune
	git -C ~/lib/neovim checkout "v$1"

	cd ~/lib/neovim || exit 1
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

install_glow_from_release() {
	echo '[charm]
name=Charm
baseurl=https://repo.charm.sh/yum/
enabled=1
gpgcheck=1
gpgkey=https://repo.charm.sh/yum/gpg.key' | sudo tee /etc/yum.repos.d/charm.repo
	sudo yum install glow -y
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
	mkdir -p ~/.nvm
	# Download and install nvm:
	curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash

	# Download and install Node.js:
	nvm install 20 || (echo "Failed to install node@20 via nvm" && exit 1)
}

install_stylua_from_release() {
	npm install -g "@johnnymorganz/stylua-bin@$1"
}

install_bash-language-server_from_release() {
	install_package_version node 20.0.0
	npm install -g "bash-language-server@$1"
}

install_jq_from_release() {
	curl -sfL "https://github.com/jqlang/jq/releases/download/jq-$1/jq-$os$bitness" -o /tmp/jq
	curl -sfL "https://github.com/jqlang/jq/releases/download/jq-$1/sha256sum.txt" -o /tmp/jq-sha256sum.txt
	sha256sum --quiet --strict --ignore-missing -c /tmp/jq-sha256sum.txt || (echo "Failed to verify jq checksum" && exit 1)
	mv -f /tmp/jq "$HOME/.local/bin/jq"
	chmod +x "$HOME/.local/bin/jq"
	rm -rf /tmp/jq /tmp/jq-sha256sum /tmp/jq-sha256sum.txt
}

install_lua-language-server_from_release() {
	curl -fLO "https://github.com/LuaLS/lua-language-server/releases/download/$1/lua-language-server-$1-$short_distro.tar.gz" --output-dir ~/lib
	mkdir -p "$HOME/lib/lua-language-server-$1"
	tar -zxf "$HOME/lib/lua-language-server-$1-$short_distro.tar.gz" -C "$HOME/lib/lua-language-server-$1"
	ln -fs ~/lib/lua-language-server-"$1"/bin/lua-language-server "$HOME/.local/bin/lua-language-server"
}

install_typescript-language-server_from_release() {
	install_package_version node 20.0.0
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
	install_package_version node 20.0.0
	npm install -g yaml-language-server@"$1"
}

bootstrap() {
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

	# command candy
	install_package_version gh 2.66.0
	install_package_version jq 1.7.1
	install_package_version ripgrep 14.1.0
	install_package_version stylua 2.0.2

	# editor
	install_package_version neovim 0.10.4
	install_package_version shfmt 3.10.0
	install_package_version bash-language-server 5.4.3       # bash/sh
	install_package_version lua-language-server 3.13.6       # lua
	install_package_version rust-analyzer 1.84.1             # rust
	install_package_version typescript-language-server 4.3.3 # typescript
	install_package_version gopls 0.17.1                     # go
	install_package_version yaml-language-server 0.16.0      # yaml
}

# Detect if the user is running the script directly
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
	set -e
	bootstrap
fi
