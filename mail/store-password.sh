#!/bin/bash
# Store Gmail app password in macOS keychain

EMAIL="joshlane@easypost.com"

echo "=== Gmail App Password Storage ==="
echo
echo "Enter your 16-character Gmail app password (it will be hidden):"
read -s APP_PASSWORD

echo
echo "Storing password in macOS keychain..."

# Store for mbsync
security add-generic-password -s "mbsync-gmail" -a "$EMAIL" -w "$APP_PASSWORD" -U 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✓ Password stored for mbsync"
else
    echo "ℹ Password already exists for mbsync, updating..."
    security delete-generic-password -s "mbsync-gmail" -a "$EMAIL" 2>/dev/null
    security add-generic-password -s "mbsync-gmail" -a "$EMAIL" -w "$APP_PASSWORD" -U
    echo "✓ Password updated for mbsync"
fi

# Store for msmtp
security add-generic-password -s "msmtp-gmail" -a "$EMAIL" -w "$APP_PASSWORD" -U 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✓ Password stored for msmtp"
else
    echo "ℹ Password already exists for msmtp, updating..."
    security delete-generic-password -s "msmtp-gmail" -a "$EMAIL" 2>/dev/null
    security add-generic-password -s "msmtp-gmail" -a "$EMAIL" -w "$APP_PASSWORD" -U
    echo "✓ Password updated for msmtp"
fi

echo
echo "=== Verification ==="
echo "Testing password retrieval..."

RETRIEVED_MBSYNC=$(security find-generic-password -s "mbsync-gmail" -a "$EMAIL" -w 2>/dev/null)
RETRIEVED_MSMTP=$(security find-generic-password -s "msmtp-gmail" -a "$EMAIL" -w 2>/dev/null)

if [ -n "$RETRIEVED_MBSYNC" ]; then
    echo "✓ mbsync password can be retrieved"
else
    echo "✗ Failed to retrieve mbsync password"
fi

if [ -n "$RETRIEVED_MSMTP" ]; then
    echo "✓ msmtp password can be retrieved"
else
    echo "✗ Failed to retrieve msmtp password"
fi

echo
echo "=== Complete! ==="
echo "Your app password has been securely stored in macOS keychain."
