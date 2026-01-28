#!/bin/bash
# Email setup script for neomutt + notmuch + mbsync + msmtp

set -e

echo "=== Email Configuration Setup ==="
echo

# Get user information
read -p "Enter your full name: " FULLNAME
read -p "Enter your Gmail address: " EMAIL

# Update configuration files
echo "Updating configuration files..."

# Update mbsyncrc
sed -i.bak "s/YOUR_EMAIL@gmail.com/$EMAIL/g" ~/.mbsyncrc
echo "✓ Updated mbsyncrc"

# Update notmuch-config
sed -i.bak "s/Your Name/$FULLNAME/g" ~/.notmuch-config
sed -i.bak "s/YOUR_EMAIL@gmail.com/$EMAIL/g" ~/.notmuch-config
echo "✓ Updated notmuch-config"

# Update msmtprc
sed -i.bak "s/YOUR_EMAIL@gmail.com/$EMAIL/g" ~/.msmtprc
echo "✓ Updated msmtprc"

# Update neomuttrc
sed -i.bak "s/Your Name/$FULLNAME/g" ~/.config/neomutt/neomuttrc
sed -i.bak "s/YOUR_EMAIL@gmail.com/$EMAIL/g" ~/.config/neomutt/neomuttrc
echo "✓ Updated neomuttrc"

# Create necessary directories
echo
echo "Creating necessary directories..."
mkdir -p ~/Mail/gmail
mkdir -p ~/.cache/neomutt/{headers,bodies}
mkdir -p ~/.local/share/msmtp
echo "✓ Directories created"

# Set up Gmail app password in keychain
echo
echo "=== Gmail App Password Setup ==="
echo "You need to generate a Gmail app-specific password:"
echo "1. Go to: https://myaccount.google.com/apppasswords"
echo "2. Sign in to your Google account"
echo "3. Select 'Mail' as the app and 'Other' as the device"
echo "4. Name it something like 'neomutt-terminal'"
echo "5. Copy the generated 16-character password"
echo
read -p "Have you generated an app password? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo
    echo "Enter the app password (it will be hidden):"
    read -s APP_PASSWORD

    # Store in macOS keychain for mbsync
    security add-generic-password -s "mbsync-gmail" -a "$EMAIL" -w "$APP_PASSWORD" -U
    echo "✓ Stored password in keychain for mbsync"

    # Store in macOS keychain for msmtp
    security add-generic-password -s "msmtp-gmail" -a "$EMAIL" -w "$APP_PASSWORD" -U
    echo "✓ Stored password in keychain for msmtp"
else
    echo "⚠️  Skipping password setup. You'll need to configure authentication manually."
fi

# Set correct permissions
echo
echo "Setting file permissions..."
chmod 600 ~/.mbsyncrc ~/.msmtprc
echo "✓ Permissions set"

echo
echo "=== Initial Sync ==="
read -p "Would you like to perform an initial sync now? This may take a while. (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Syncing email (this may take several minutes)..."
    mbsync -V gmail
    echo "✓ Email synced"

    echo
    echo "Indexing email with notmuch..."
    notmuch new
    echo "✓ Email indexed"
else
    echo "⚠️  Skipping initial sync. Run 'mbsync gmail && notmuch new' when ready."
fi

echo
echo "=== Setup Complete! ==="
echo
echo "You can now:"
echo "  • Launch neomutt with: neomutt"
echo "  • Sync email with: mbsync gmail && notmuch new"
echo "  • Use 'O' inside neomutt to sync all mail"
echo "  • Use 'o' inside neomutt to sync inbox only"
echo
echo "Useful commands:"
echo "  • Search: notmuch search <query>"
echo "  • Tag emails: notmuch tag +label -- <search>"
echo "  • Sync specific folder: mbsync gmail-inbox"
echo
