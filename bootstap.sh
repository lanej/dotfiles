#!/usr/bin/env bash
set -e

cat bootstrap.txt

if [ ! -f bootstrap.yml ]; then
	echo "Error: bootstrap.yml not found. Please run this script from the dotfiles checkout."
	exit 1
fi

if command -v ansible-playbook >/dev/null; then
	echo "Ansible is already installed. Running the playbook..."
else
	if command -v brew >/dev/null; then
		echo "Installing Ansible via Homebrew..."
		brew install ansible
	elif command -v apt-get >/dev/null; then
		echo "Installing Ansible via apt-get..."
		sudo apt-get update
		sudo apt-get install -y ansible
	elif command -v yum >/dev/null; then
		echo "Installing Ansible via yum..."
		sudo yum install -y ansible
	elif command -v dnf >/dev/null; then
		echo "Installing Ansible via dnf..."
		sudo dnf install -y ansible
	elif command -v zypper >/dev/null; then
		echo "Installing Ansible via zypper..."
		sudo zypper install -y ansible
	elif command -v pacman >/dev/null; then
		echo "Installing Ansible via pacman..."
		sudo pacman -S --noconfirm ansible
	else
		echo "No package manager found. Installing Ansible via pip..."

		# Check for Python3
		if ! command -v python3 >/dev/null; then
			echo "Error: Python3 is required. Please install Python3."
			exit 1
		fi

		# Check for pip3
		if ! command -v pip3 >/dev/null; then
			echo "Error: pip3 is required. Please install pip3."
			exit 1
		fi

		# Install Ansible if not already installed
		if ! command -v ansible-playbook >/dev/null; then
			echo "Installing Ansible via pip..."
			pip3 install --user ansible
			export PATH="$HOME/.local/bin:$PATH"
		fi
	fi
fi

# Run the Ansible playbook locally
ansible-playbook --connection=local bootstrap.yml
