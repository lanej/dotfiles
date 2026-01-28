# Email Configuration

Terminal-based email setup using neomutt + notmuch + mbsync + msmtp for Gmail.

## Components

**neomutt**: Terminal email client with notmuch integration
**notmuch**: Fast email indexing and tagging
**mbsync/isync**: Bidirectional IMAP synchronization
**msmtp**: SMTP client for sending email

## Installation

1. Install configuration files:
   ```bash
   make mail
   ```

2. Run the setup script:
   ```bash
   bash ~/.files/mail/setup-email.sh
   ```

3. Follow the prompts to:
   - Enter your name and Gmail address
   - Generate a Gmail app password
   - Store credentials in macOS keychain
   - Perform initial sync (optional)

## Gmail App Password

Since Gmail doesn't allow password authentication for third-party apps, you need an app-specific password:

1. Go to https://myaccount.google.com/apppasswords
2. Sign in to your Google account
3. Select "Mail" and "Other (Custom name)"
4. Name it "neomutt-terminal" or similar
5. Copy the 16-character password
6. The setup script will store it in macOS keychain

## Usage

### Launch NeoMutt
```bash
neomutt
```

### Sync Email

Sync all folders:
```bash
mbsync gmail && notmuch new
```

Sync inbox only:
```bash
mbsync gmail-inbox && notmuch new
```

Inside neomutt:
- Press `O` to sync all mail
- Press `o` to sync inbox only

### Key Bindings

**Navigation**:
- `j/k` - Move up/down
- `Ctrl-p/Ctrl-n` - Previous/next sidebar folder
- `Ctrl-o` - Open sidebar folder
- `B` - Toggle sidebar visibility

**Actions**:
- `c` - Compose new email
- `r` - Reply
- `a` - Reply all
- `f` - Forward
- `s` - Star/flag message
- `A` - Archive message (removes from inbox)
- `I` - Move to inbox (unarchive)
- `S` - Mark as spam
- `d` - Delete message
- `+` - Add label/tag
- `-` - Remove label/tag

**Search**:
- `/` - Search in current folder
- `N` - Find next/previous

**Thread Management**:
- `Space` - Collapse/expand thread
- `X` - View entire thread

## Notmuch Queries

Search from command line:
```bash
notmuch search tag:unread
notmuch search from:someone@example.com
notmuch search subject:meeting
notmuch search date:today..
```

Tag emails:
```bash
notmuch tag +important -- from:boss@company.com
notmuch tag +project-x -- subject:project
notmuch tag -unread -- tag:unread and date:..1week
```

## Virtual Mailboxes

NeoMutt is configured with these virtual mailboxes (notmuch queries):
- **Inbox**: `tag:inbox`
- **Unread**: `tag:unread`
- **Flagged**: `tag:flagged`
- **Sent**: `tag:sent`
- **Drafts**: `tag:draft`
- **Archive**: `tag:archive`
- **All Mail**: `*` (all messages)

## Automation

### Automatic Sync

Create a cron job or launchd agent to sync periodically:

```bash
# Sync every 5 minutes
*/5 * * * * /opt/homebrew/bin/mbsync gmail && /opt/homebrew/bin/notmuch new
```

### Post-sync Hooks

Create `~/.mail/.notmuch/hooks/post-new` to automatically tag new emails:

```bash
#!/bin/bash
# Auto-tag emails from specific senders
notmuch tag +work -- from:*@company.com and tag:new
notmuch tag +receipt -- from:*@amazon.com and tag:new
# Remove 'new' tag
notmuch tag -new -- tag:new
```

Make it executable:
```bash
chmod +x ~/.mail/.notmuch/hooks/post-new
```

## Configuration Files

- `~/.mbsyncrc` - IMAP sync configuration
- `~/.notmuch-config` - Notmuch database configuration
- `~/.msmtprc` - SMTP configuration for sending
- `~/.config/neomutt/neomuttrc` - NeoMutt client configuration

## Troubleshooting

### Authentication Issues
```bash
# Verify keychain entry
security find-generic-password -s mbsync-gmail -a your@email.com -w

# Re-add if needed
security add-generic-password -s mbsync-gmail -a your@email.com -w
```

### Sync Issues
```bash
# Verbose sync to see errors
mbsync -V gmail

# Check specific channel
mbsync -V gmail-inbox
```

### Notmuch Database Issues
```bash
# Rebuild database
notmuch new --full-scan

# Compact database
notmuch compact
```

### View Logs
```bash
# msmtp send log
tail -f ~/.local/share/msmtp/msmtp.log
```

## Advanced Configuration

### HTML Email Viewing

NeoMutt will automatically render HTML emails. To customize the viewer, install `w3m` or `lynx`:

```bash
brew install w3m
```

### Multiple Accounts

To add more email accounts, duplicate the configuration blocks in each config file and update the Makefile target.

### Custom Color Scheme

Edit `mail/neomuttrc` and modify the color definitions. The current theme is Nord-inspired.

## Resources

- [NeoMutt Documentation](https://neomutt.org/guide/)
- [Notmuch Documentation](https://notmuchmail.org/documentation/)
- [mbsync Manual](https://isync.sourceforge.io/mbsync.html)
- [msmtp Manual](https://marlam.de/msmtp/)
