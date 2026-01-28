#!/bin/bash
# Notmuch post-new hook for automatic tagging
# Install to: ~/Mail/.notmuch/hooks/post-new

# Tag emails from specific domains as work
notmuch tag +work -- from:*@work-domain.com and tag:new

# Tag newsletters and promotions
notmuch tag +newsletter -- subject:newsletter and tag:new
notmuch tag +newsletter -- from:*@*.substack.com and tag:new

# Tag receipts
notmuch tag +receipt -- from:*@amazon.com and tag:new
notmuch tag +receipt -- from:*@paypal.com and tag:new
notmuch tag +receipt -- subject:"receipt" and tag:new

# Tag automated/bulk emails
notmuch tag +automated -inbox -- from:noreply and tag:new
notmuch tag +automated -inbox -- from:no-reply and tag:new
notmuch tag +automated -inbox -- from:donotreply and tag:new

# Tag spam that made it through
notmuch tag +spam -inbox -- subject:"bitcoin" and tag:new
notmuch tag +spam -inbox -- subject:"crypto" and tag:new
notmuch tag +spam -inbox -- subject:"viagra" and tag:new

# Remove 'new' tag from all messages
notmuch tag -new -- tag:new
