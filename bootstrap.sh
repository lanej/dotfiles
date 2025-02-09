#!/bin/bash

os=$(uname -s | tr '[:upper:]' '[:lower:]' | sed 's,^darwin$,macos,')
distro="$os-$(uname -m)"

install_from_package_manager() {
	echo "installing package $1"
	if command -v brew &>/dev/null; then
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

package_semver_explicit() {
	if declare -f "$1_package_semver" >/dev/null; then
		"$1_package_semver"
	else
		return 1
	fi
}

package_semver() {
	package_semver_explicit "$1" || package_manager_semver "$1" || (echo "Failed to get semver for: $1" && return 1)
}

install_explicitly() {
	if declare -f "install_$1_package" >/dev/null; then
		echo "installing $1 $2 from custom package"
		"install_$1_package" "$2"
	elif declare -f "install_$1_from_release" >/dev/null; then
		echo "Installing $1 $2 from release"
		"install_$1_from_release" "$2"
	elif declare -f "install_$1_from_source" >/dev/null; then
		echo "Installing $1 $2 from source"
		"install_$1_from_source" "$2"
	else
		echo "Unable to install: $1"
		exit 1
	fi
}

install_package() {
	local package=$1
	local version=$2
	get_package_semver=$(package_semver "$package")
	local package_version="$get_package_semver"

	echo "Installing $package $version"

	if [ -n "$package_version" ]; then
		echo "$package is not found in package manager"
	elif semver_ge "$package_version" "$version"; then
		install_from_package_manager "$package" || (echo "Failed to install: $package" && exit 1)
	else
		echo "$package package '$package_version' < '$version'"
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

install_gh() {
	# Install gh
	if command -v gh &>/dev/null && semver_ge "$(gh_semver)" "2.66.0"; then
		echo "gh $(gh_semver)  already installed"
	else
		install_package gh
	fi
}

parse_semver() {
	grep -Eo '[0-9]+\.[0-9]+(\.[0-9]+)?'
}

current_heuristic_semver() {
	("$1" --version | head -n1 | parse_semver | head -n1) 2>/dev/null || return 1
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
		echo "Package $package is already installed at version $current_version"

		# check if current version is greater than or equal to min version
		if semver_ge "$current_version" "$min_version"; then
			# if current version is greater than or equal to min version, return
			echo "$package $current_version >= $min_version"
			return 0
		fi

		echo "$package $current_version < $min_version"
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
	install_package_version cargo 1.84.1 || (echo "cargo could be installed" && exit 1)
	cargo install ripgrep -q --locked --version "$1"
}

install_starship_from_release() {
	install_package_version cargo 1.84.1 || (echo "cargo could be installed" && exit 1)
	cargo install starship -q --locked --version "$1"
}

install_skim_from_release() {
	install_package_version cargo 1.84.1 || (echo "cargo could be installed" && exit 1)
	cargo install skim -q --locked --version "$1"
}

install_git-delta_from_release() {
	install_package_version cargo 1.84.1 || (echo "cargo could be installed" && exit 1)
	cargo install git-delta -q --locked --version "$1"
}

bootstrap() {
	install_package_version gh 2.66.0
	install_package_version neovim 0.10.4
	install_package_version fzf 0.59.0
	install_package_version ripgrep 14.1.0
	install_package_version starship 1.22.1
	install_package_version atuin 18.4.0
	install_package_version skim 0.16.0
	install_package_version git-delta 0.18.2
	install_package_version glow 2.0.0
}

# Detect if the user is running the script directly
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
	set -e
	bootstrap
fi
