#!/bin/bash
# Simple script to add Gmail app password to keychain

echo "Paste your 16-character Gmail app password and press Enter:"
read -r PASSWORD

if [ -z "$PASSWORD" ]; then
    echo "Error: No password entered"
    exit 1
fi

# Add for mbsync
security add-generic-password -s "mbsync-gmail" -a "joshlane@easypost.com" -w "$PASSWORD"
echo "✓ Added for mbsync"

# Add for msmtp
security add-generic-password -s "msmtp-gmail" -a "joshlane@easypost.com" -w "$PASSWORD"
echo "✓ Added for msmtp"

# Test retrieval
echo
echo "Testing retrieval..."
TEST=$(security find-generic-password -s "mbsync-gmail" -a "joshlane@easypost.com" -w)
if [ -n "$TEST" ]; then
    echo "✓ Password successfully stored and retrieved!"
else
    echo "✗ Failed to retrieve password"
fi
