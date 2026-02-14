# Arcanist (arc) Skill

**Arcanist** is the command-line interface for Phabricator code review. It replaces `git push` in Phabricator-based workflows.

## Core Concept

**In Phabricator workflows, you NEVER push branches directly to remote. Instead, you use `arc diff` to create/update Differential revisions.**

```
Git workflow:     git add → git commit → git push → (create PR on GitHub)
Phabricator:      git add → git commit → arc diff → (creates/updates revision)
```

## Critical Rules

1. **arc diff replaces git push** - Don't push feature branches to remote
2. **arc is interactive by default** - Don't try to automate editors with EDITOR hacks
3. **Lint errors don't block diffs** - arc shows warnings but still creates/updates revisions
4. **Each diff is tied to commits** - arc compares your commits against a base branch

## Common Commands

### Creating a Revision

**Interactive (recommended for first-time creation):**
```bash
arc diff
# Opens editor for title, summary, test plan, reviewers
# Press Ctrl+X or :wq to save and submit
```

**Non-interactive (with message file):**
```bash
arc diff --message-file /path/to/message.txt
# Message file should contain title and body
```

**Non-interactive (inline message):**
```bash
arc diff --message "Brief update message"
# For quick updates only
```

### Updating an Existing Revision

**Auto-detect and update:**
```bash
arc diff
# Detects existing revision from commit messages
# Opens editor for update message
```

**Specify revision explicitly:**
```bash
arc diff --update D12345 --message "Fixed lint errors"
```

**Update with message file:**
```bash
arc diff --update D12345 --message-file /tmp/update.txt
```

### Checking Status

**List your revisions:**
```bash
arc list
# Shows all your open revisions
```

**View specific revision:**
```bash
arc browse D12345
# Opens revision in web browser
```

### Linting

**Lint specific files:**
```bash
arc lint path/to/file.rb
arc lint spec/lib/myfile_spec.rb
```

**Lint all changed files:**
```bash
arc lint
```

**Skip lint (not recommended):**
```bash
arc diff --nolint
```

### Landing (Merging)

**Land approved revision:**
```bash
arc land
# Merges to master and cleans up branch
```

## Flag Reference

### Compatible Flag Combinations

✅ **These work together:**
- `arc diff --update D123 --message "..."`
- `arc diff --message-file /path --update D123`
- `arc diff --nolint --nounit`

❌ **These are INCOMPATIBLE:**
- `arc diff --verbatim --message-file` (mutually exclusive)
- `arc diff --verbatim --update` (mutually exclusive)
- `arc diff --create --update` (mutually exclusive)

### Common Flags

| Flag | Purpose | Interactive? |
|------|---------|-------------|
| `--message "..."` | Inline update message | No |
| `--message-file FILE` | Read message from file | No |
| `--update D123` | Update specific revision | No |
| `--create` | Force create new revision | No |
| `--verbatim` | Use commit message verbatim | No (conflicts with --update) |
| `--nolint` | Skip linting | No |
| `--nounit` | Skip unit tests | No |
| `--browse` | Open in browser after creation | No |
| (no flags) | Interactive editor | YES |

## Workflow Patterns

### Pattern 1: First-Time Revision Creation

```bash
# 1. Make commits
git add .
git commit -m "feat: implement feature X"

# 2. Create revision (interactive)
arc diff
# Editor opens - fill in title, summary, test plan
# Save and exit

# Output: "Created a new Differential revision: D12345"
```

### Pattern 2: Updating After Feedback

```bash
# 1. Make changes based on review
git add .
git commit -m "fix: address review comments"

# 2. Update revision
arc diff --update D12345 --message "Addressed review comments: fixed lint errors and added tests"
```

### Pattern 3: Fixing Lint Errors

```bash
# 1. Run arc diff (it will show lint errors but still create/update)
arc diff --update D12345 --message "Initial implementation"
# Output: "LINT ERRORS ... Updated an existing Differential revision: D12345"

# 2. Fix the lint errors
# Edit files to fix issues

# 3. Commit fixes
git add .
git commit -m "fix: resolve lint errors"

# 4. Update diff again
arc diff --update D12345 --message "Resolved all lint errors"
```

### Pattern 4: Working with Message Files

```bash
# 1. Create message file
cat > /tmp/diff_message.txt <<EOF
Implement user authentication

Summary
=======
- Added JWT token generation
- Implemented login/logout endpoints
- Added password hashing with bcrypt

Test Plan
=========
- Unit tests: uv run pytest tests/auth/
- Manual testing: curl localhost:8000/api/login
EOF

# 2. Use message file
arc diff --message-file /tmp/diff_message.txt
```

## Understanding Arc Diff Base Detection

Arc needs to know what commits to include in the diff. It does this by finding a "base" commit.

**How arc finds the base:**
1. Looks at git history to find merge-base with remote master/main
2. Includes all commits from base to HEAD
3. You can override with `--base` flag

**Check what will be included:**
```bash
# See commits that will be in the diff
git log origin/master..HEAD

# See the actual diff
git diff origin/master..HEAD
```

## Handling Common Errors

### Error: "User aborted the workflow"

**Cause**: Editor exited without saving or timed out

**Solution**: 
- Use non-interactive flags: `--message` or `--message-file`
- Or run `arc diff` directly and interact with editor normally

### Error: "Arguments X and Y are mutually exclusive"

**Cause**: Incompatible flag combination

**Common conflicts:**
- `--verbatim` + `--message-file`
- `--verbatim` + `--update`
- `--create` + `--update`

**Solution**: Use only one of the conflicting flags

### Error: "Launching editor 'nvim'..." then timeout

**Cause**: Trying to automate an interactive command

**Wrong approach:**
```bash
EDITOR=cat arc diff        # ❌ Don't do this
echo "y" | arc diff        # ❌ Don't do this
```

**Right approach:**
```bash
arc diff --message "Update message"  # ✅ Non-interactive
# OR just run: arc diff               # ✅ Let editor open normally
```

### Lint Errors Don't Block

**Arc behavior with lint errors:**
```
Linting...
>>> Lint for spec/lib/myfile_spec.rb:
  Error (RuboCop/Style): ...
  
LINT ERRORS
Running unit tests...
PUSH STAGING
Updated an existing Differential revision: D12345
```

**Key point**: The revision IS updated even with lint errors. Reviewers will see the errors.

**Best practice**: Fix lint errors in a follow-up commit, then update again.

## Integration with Git

### Git Commands Still Work

Arcanist uses git under the hood. Normal git commands work:

```bash
git status              # ✅ See what's changed
git log                 # ✅ View commit history
git checkout -b feat    # ✅ Create branches
git commit --amend      # ✅ Amend commits
git rebase -i master    # ✅ Rebase (but be careful with published diffs)
```

### What NOT to Do

```bash
git push origin feature-branch    # ❌ Don't push (use arc diff instead)
git pull --rebase origin master   # ⚠️  Careful: rebasing published diffs breaks revision history
```

### Updating Base Branch

**Safe approach:**
```bash
# 1. Switch to master
git checkout master
git pull origin master

# 2. Switch back to feature branch
git checkout feature-branch

# 3. Rebase (only if revision not yet reviewed)
git rebase master

# 4. Update diff
arc diff --update D12345 --message "Rebased on latest master"
```

**Warning**: Rebasing after reviews can confuse reviewers. Prefer merging master into your branch:
```bash
git merge master
arc diff --update D12345 --message "Merged latest master"
```

## Advanced Usage

### Creating Dependent Revisions

When revision B depends on revision A:

```bash
# 1. Create first revision
git checkout -b feature-a
# ... make commits ...
arc diff
# Creates D100

# 2. Create dependent revision
git checkout -b feature-b feature-a
# ... make commits ...
arc diff
# Creates D101 (depends on D100)
```

### Using --trace for Debugging

```bash
arc diff --trace
# Shows detailed debug output of what arc is doing
```

### Checking Revision Status

```bash
# List all your revisions
arc list

# List specific user's revisions
arc list --query "@username"

# Show revision details
arc export D12345
```

## Best Practices

1. **Use meaningful commit messages** - Arc parses them for revision titles
2. **Run lint locally first** - `arc lint` before `arc diff` to catch issues early
3. **Keep revisions focused** - One feature/fix per revision
4. **Update with descriptive messages** - Help reviewers understand changes
5. **Don't rebase after review** - Confuses diff comparison
6. **Fix lint errors promptly** - Don't let them accumulate

## Common Workflow Summary

**Daily workflow:**
```bash
# Morning: Update master
git checkout master && git pull origin master

# Create feature branch
git checkout -b feat-amazing-feature

# Work on feature
# ... edit files ...
git add .
git commit -m "feat: implement amazing feature"

# Create revision
arc diff
# (fill in editor, save, exit)

# Receive review feedback
# ... fix issues ...
git add .
git commit -m "fix: address review feedback"

# Update revision
arc diff --update D12345 --message "Addressed review comments"

# After approval, land
arc land
```

## Troubleshooting

### "No changes found. (Did you specify the wrong commit range?)"

**Cause**: No commits ahead of base branch

**Solution**: Make sure you've committed changes:
```bash
git status          # See uncommitted changes
git add .
git commit -m "..."
arc diff
```

### "Cannot find base commit"

**Cause**: Arc can't determine merge-base with master

**Solution**: Specify base explicitly:
```bash
arc diff origin/master
# or
arc diff --base origin/master
```

### Diff Shows Wrong Files

**Cause**: Incorrect base detection or uncommitted changes

**Check what would be included:**
```bash
git diff origin/master..HEAD
```

**Fix**: Specify base or clean working directory

## Quick Reference

**Create revision**: `arc diff`
**Update revision**: `arc diff --update D123 --message "..."`
**List revisions**: `arc list`
**Land revision**: `arc land`
**Lint files**: `arc lint path/to/file`
**View diff**: `arc export D123`

**Remember**: Arc is interactive by default. Use `--message` or `--message-file` for automation.
