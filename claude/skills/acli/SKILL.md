---
name: acli
description: Use acli jira CLI for Jira work item management, project operations, sprint tracking, and board management with JQL search capabilities.
---
# Atlassian CLI (acli) - Jira Workflow Skill

You are an Atlassian CLI specialist. This skill provides comprehensive guidance for managing Jira work items, projects, sprints, and boards using the `acli jira` command-line tool.

## Core Principles

### Output Formats

**Standard formats available**:
- **Default**: Human-readable table format
- `--json`: JSON output for scripting and automation
- `--csv`: CSV output for data export (available on search commands)
- `--web`: Open results in web browser

**Best practices**:
- Use `--json` for scripting and parsing
- Use `--csv` for exporting to spreadsheets
- Use `--web` for quick visual inspection
- Use default format for human review

### Pagination and Limits

```bash
# Fetch limited results (default varies by command)
acli jira workitem search --jql "project = TEAM" --limit 50

# Fetch all results with pagination
acli jira workitem search --jql "project = TEAM" --paginate

# Count results without fetching details
acli jira workitem search --jql "project = TEAM" --count
```

## Authentication

### Initial Setup

```bash
# Login to Jira instance
acli jira auth login

# Check authentication status
acli jira auth status

# Switch between accounts
acli jira auth switch

# Logout
acli jira auth logout
```

## Work Items (Issues)

### Searching for Work Items

```bash
# Basic JQL search
acli jira workitem search --jql "project = TEAM"

# Search with specific fields
acli jira workitem search --jql "project = TEAM" --fields "key,summary,assignee"

# Search with pagination
acli jira workitem search --jql "project = TEAM" --paginate

# Count matching work items
acli jira workitem search --jql "project = TEAM" --count

# Export to CSV
acli jira workitem search --jql "project = TEAM" --csv

# Export to JSON
acli jira workitem search --jql "project = TEAM" --json

# Search using saved filter
acli jira workitem search --filter 10001

# Open search results in browser
acli jira workitem search --jql "project = TEAM" --web

# Limit results
acli jira workitem search --jql "project = TEAM" --limit 50
```

**Common JQL patterns**:
```bash
# Assigned to me
acli jira workitem search --jql "assignee = currentUser()"

# Open issues in project
acli jira workitem search --jql "project = TEAM AND status != Done"

# Recently updated
acli jira workitem search --jql "updated >= -7d"

# By priority
acli jira workitem search --jql "priority = High AND status = Open"

# Multiple conditions
acli jira workitem search --jql "project = TEAM AND assignee = currentUser() AND status in (Open, 'In Progress')"

# By type
acli jira workitem search --jql "project = TEAM AND issuetype = Bug"

# By labels
acli jira workitem search --jql "labels = production AND status != Closed"
```

### Viewing Work Items

```bash
# View single work item
acli jira workitem view KEY-123

# View with specific fields
acli jira workitem view KEY-123 --fields "summary,description,comment"

# View all fields
acli jira workitem view KEY-123 --fields "*all"

# View navigable fields only
acli jira workitem view KEY-123 --fields "*navigable"

# Exclude specific fields
acli jira workitem view KEY-123 --fields "*navigable,-comment"

# View as JSON
acli jira workitem view KEY-123 --json

# Open in web browser
acli jira workitem view KEY-123 --web
```

### Creating Work Items

```bash
# Basic creation with required fields
acli jira workitem create \
  --summary "New feature request" \
  --project "TEAM" \
  --type "Story"

# Create with assignee
acli jira workitem create \
  --summary "Fix login bug" \
  --project "TEAM" \
  --type "Bug" \
  --assignee "user@example.com"

# Self-assign
acli jira workitem create \
  --summary "Research task" \
  --project "TEAM" \
  --type "Task" \
  --assignee "@me"

# Create with description
acli jira workitem create \
  --summary "New feature" \
  --project "TEAM" \
  --type "Story" \
  --description "This is a detailed description of the feature"

# Create with description from file
acli jira workitem create \
  --summary "Complex feature" \
  --project "TEAM" \
  --type "Story" \
  --description-file "description.txt"

# Create with labels
acli jira workitem create \
  --summary "Urgent bug fix" \
  --project "TEAM" \
  --type "Bug" \
  --label "production,urgent,bug"

# Create with parent (sub-task or child issue)
acli jira workitem create \
  --summary "Sub-task" \
  --project "TEAM" \
  --type "Sub-task" \
  --parent "TEAM-123"

# Create using text editor
acli jira workitem create \
  --project "TEAM" \
  --type "Story" \
  --editor

# Create from file
acli jira workitem create \
  --from-file "workitem.txt" \
  --project "TEAM" \
  --type "Bug"

# Generate JSON template
acli jira workitem create --generate-json

# Create from JSON file
acli jira workitem create --from-json "workitem.json"

# Get JSON output
acli jira workitem create \
  --summary "New task" \
  --project "TEAM" \
  --type "Task" \
  --json
```

### Editing Work Items

```bash
# Edit single work item
acli jira workitem edit --key "KEY-123" --summary "Updated summary"

# Edit multiple work items
acli jira workitem edit --key "KEY-123,KEY-124,KEY-125" --assignee "@me"

# Edit with JQL query
acli jira workitem edit \
  --jql "project = TEAM AND status = Open" \
  --assignee "user@example.com"

# Edit with filter
acli jira workitem edit --filter 10001 --labels "reviewed"

# Update description
acli jira workitem edit --key "KEY-123" --description "Updated description"

# Update description from file
acli jira workitem edit --key "KEY-123" --description-file "desc.txt"

# Change work item type
acli jira workitem edit --key "KEY-123" --type "Epic"

# Add labels
acli jira workitem edit --key "KEY-123" --labels "backend,api"

# Remove labels
acli jira workitem edit --key "KEY-123" --remove-labels "old-label"

# Remove assignee (unassign)
acli jira workitem edit --key "KEY-123" --remove-assignee

# Skip confirmation prompt
acli jira workitem edit --key "KEY-123" --summary "New" --yes

# Ignore errors when editing multiple
acli jira workitem edit \
  --jql "project = TEAM" \
  --assignee "@me" \
  --ignore-errors

# Generate JSON template
acli jira workitem edit --generate-json

# Edit from JSON file
acli jira workitem edit --from-json "update.json"

# Get JSON output
acli jira workitem edit --key "KEY-123" --summary "New" --json
```

### Transitioning Work Items

```bash
# Transition single work item
acli jira workitem transition --key "KEY-123" --status "In Progress"

# Transition multiple work items
acli jira workitem transition \
  --key "KEY-123,KEY-124" \
  --status "Done"

# Transition with JQL query
acli jira workitem transition \
  --jql "project = TEAM AND assignee = currentUser()" \
  --status "In Review"

# Transition with filter
acli jira workitem transition \
  --filter 10001 \
  --status "Closed"

# Skip confirmation
acli jira workitem transition \
  --key "KEY-123" \
  --status "Done" \
  --yes

# Ignore errors
acli jira workitem transition \
  --jql "project = TEAM" \
  --status "Done" \
  --ignore-errors

# Get JSON output
acli jira workitem transition \
  --key "KEY-123" \
  --status "Done" \
  --json
```

**Common status transitions**:
- `To Do` / `Open` - New work
- `In Progress` - Active work
- `In Review` / `Code Review` - Under review
- `Testing` / `QA` - Being tested
- `Done` / `Closed` / `Resolved` - Completed

### Assigning Work Items

```bash
# Assign to specific user
acli jira workitem assign \
  --key "KEY-123" \
  --assignee "user@example.com"

# Self-assign
acli jira workitem assign --key "KEY-123" --assignee "@me"

# Assign to default assignee
acli jira workitem assign --key "KEY-123" --assignee "default"

# Assign multiple work items
acli jira workitem assign \
  --key "KEY-123,KEY-124,KEY-125" \
  --assignee "@me"
```

### Comments

```bash
# Add comment to work item
acli jira workitem comment create \
  --key "KEY-123" \
  --body "This is a comment"

# Add comment from file
acli jira workitem comment create \
  --key "KEY-123" \
  --body-file "comment.txt"

# Add comment using editor
acli jira workitem comment create \
  --key "KEY-123" \
  --editor

# Comment on multiple work items with JQL
acli jira workitem comment create \
  --jql "project = TEAM AND status = Open" \
  --body "Bulk comment"

# Edit last comment from same author
acli jira workitem comment create \
  --key "KEY-123" \
  --body "Updated comment" \
  --edit-last

# Ignore errors when commenting on multiple
acli jira workitem comment create \
  --jql "project = TEAM" \
  --body "Comment" \
  --ignore-errors

# List comments
acli jira workitem comment list --key "KEY-123"

# Update comment
acli jira workitem comment update \
  --key "KEY-123" \
  --comment-id "10001" \
  --body "Updated comment text"

# Delete comment
acli jira workitem comment delete \
  --key "KEY-123" \
  --comment-id "10001"

# Get visibility options
acli jira workitem comment visibility --key "KEY-123"
```

### Attachments

```bash
# Work item attachment commands
acli jira workitem attachment --help
```

### Linking Work Items

```bash
# Link work items
acli jira workitem link --help
```

### Cloning Work Items

```bash
# Clone/duplicate work items
acli jira workitem clone \
  --key "KEY-123" \
  --summary "Cloned issue"
```

### Archiving and Deleting

```bash
# Archive work item
acli jira workitem archive --key "KEY-123"

# Archive multiple work items
acli jira workitem archive --key "KEY-123,KEY-124,KEY-125"

# Unarchive work item
acli jira workitem unarchive --key "KEY-123"

# Delete work item
acli jira workitem delete --key "KEY-123"

# Delete multiple work items
acli jira workitem delete --key "KEY-123,KEY-124"
```

### Watchers

```bash
# Work item watcher commands
acli jira workitem watcher --help
```

### Bulk Operations

```bash
# Bulk create from file
acli jira workitem create-bulk --from-json "bulk-issues.json"

# Generate bulk creation template
acli jira workitem create-bulk --generate-json
```

## Projects

### Listing Projects

```bash
# List projects (default 30)
acli jira project list

# List specific number
acli jira project list --limit 50

# List all projects with pagination
acli jira project list --paginate

# List recently viewed projects
acli jira project list --recent

# Export to JSON
acli jira project list --json
```

### Viewing Projects

```bash
# View project details
acli jira project view --key "TEAM"

# View as JSON
acli jira project view --key "TEAM" --json
```

### Creating Projects

```bash
# Create new project
acli jira project create

# The command will prompt for required information
```

### Updating Projects

```bash
# Update project
acli jira project update --key "TEAM"
```

### Archiving Projects

```bash
# Archive project
acli jira project archive --key "TEAM"

# Restore archived project
acli jira project restore --key "TEAM"
```

### Deleting Projects

```bash
# Delete project
acli jira project delete --key "TEAM"
```

## Boards

### Listing and Searching Boards

```bash
# Search for boards
acli jira board search

# Get board details
acli jira board get --id 123

# List sprints for a board
acli jira board list-sprints --id 123
```

## Sprints

### Sprint Work Items

```bash
# List work items in a sprint
acli jira sprint list-workitems --id 456
```

## Filters

### Managing Filters

```bash
# List my filters or favourites
acli jira filter list

# Search for filters
acli jira filter search

# Get filter by ID
acli jira filter get --id 10001

# Add filter as favourite
acli jira filter add-favourite --id 10001

# Change filter owner
acli jira filter change-owner --id 10001

# Get configured columns
acli jira filter get-columns --id 10001

# Reset columns to default
acli jira filter reset-columns --id 10001
```

## Fields

### Field Management

```bash
# Jira field commands
acli jira field --help
```

## Dashboards

### Dashboard Management

```bash
# Jira dashboard commands
acli jira dashboard --help
```

## Complete Workflows

### Workflow 1: Create and Track Bug

```bash
# 1. Create bug
acli jira workitem create \
  --summary "Fix login validation" \
  --project "TEAM" \
  --type "Bug" \
  --assignee "@me" \
  --label "production,high-priority"

# Output: Created KEY-123

# 2. Transition to In Progress
acli jira workitem transition --key "KEY-123" --status "In Progress"

# 3. Add progress comment
acli jira workitem comment create \
  --key "KEY-123" \
  --body "Found root cause, implementing fix"

# 4. Mark as done
acli jira workitem transition --key "KEY-123" --status "Done"

# 5. Add resolution comment
acli jira workitem comment create \
  --key "KEY-123" \
  --body "Fixed validation logic in LoginController"
```

### Workflow 2: Bulk Update Sprint Items

```bash
# 1. Search for sprint items
acli jira workitem search \
  --jql "sprint = 'Sprint 23' AND status = 'To Do'" \
  --fields "key,summary"

# 2. Transition all to In Progress
acli jira workitem transition \
  --jql "sprint = 'Sprint 23' AND status = 'To Do'" \
  --status "In Progress" \
  --yes

# 3. Assign unassigned items to team members
acli jira workitem edit \
  --jql "sprint = 'Sprint 23' AND assignee is EMPTY" \
  --assignee "@me" \
  --yes
```

### Workflow 3: Create Epic with Stories

```bash
# 1. Create epic
acli jira workitem create \
  --summary "User Authentication Redesign" \
  --project "TEAM" \
  --type "Epic" \
  --assignee "@me"

# Output: Created TEAM-100

# 2. Create stories under epic
acli jira workitem create \
  --summary "Design new login UI" \
  --project "TEAM" \
  --type "Story" \
  --parent "TEAM-100"

acli jira workitem create \
  --summary "Implement OAuth2 integration" \
  --project "TEAM" \
  --type "Story" \
  --parent "TEAM-100"

acli jira workitem create \
  --summary "Add multi-factor authentication" \
  --project "TEAM" \
  --type "Story" \
  --parent "TEAM-100"
```

### Workflow 4: Daily Standup Report

```bash
# Get my current work
acli jira workitem search \
  --jql "assignee = currentUser() AND status in ('In Progress', 'In Review')" \
  --fields "key,summary,status"

# Check what I completed yesterday
acli jira workitem search \
  --jql "assignee = currentUser() AND status changed TO Done AFTER -1d" \
  --fields "key,summary"
```

### Workflow 5: Review and Triage New Bugs

```bash
# 1. Find unassigned bugs
acli jira workitem search \
  --jql "project = TEAM AND type = Bug AND assignee is EMPTY" \
  --fields "key,summary,priority,created"

# 2. Assign critical bugs
acli jira workitem edit \
  --jql "project = TEAM AND type = Bug AND priority = Highest AND assignee is EMPTY" \
  --assignee "senior-dev@example.com" \
  --yes

# 3. Add triage label
acli jira workitem edit \
  --jql "project = TEAM AND type = Bug AND created >= -1d" \
  --labels "needs-triage" \
  --yes
```

### Workflow 6: Sprint Cleanup

```bash
# 1. Find incomplete items in closed sprint
acli jira workitem search \
  --jql "sprint = 'Sprint 22' AND status != Done" \
  --fields "key,summary,assignee,status"

# 2. Move to next sprint or backlog
acli jira workitem edit \
  --jql "sprint = 'Sprint 22' AND status != Done" \
  --yes
  # (Then manually update sprint in Jira UI or use API)

# 3. Add comment explaining carryover
acli jira workitem comment create \
  --jql "sprint = 'Sprint 22' AND status != Done" \
  --body "Carried over to Sprint 23 due to dependencies"
```

### Workflow 7: Export Issues for Reporting

```bash
# Export to CSV for analysis
acli jira workitem search \
  --jql "project = TEAM AND created >= -30d" \
  --fields "key,issuetype,assignee,priority,status,summary,created,resolved" \
  --csv > issues-last-30-days.csv

# Export to JSON for scripting
acli jira workitem search \
  --jql "project = TEAM AND status = Done AND resolved >= -7d" \
  --json > completed-this-week.json
```

## Best Practices

### JQL Query Design

1. **Be specific**: Use precise field matching
2. **Use operators**: `AND`, `OR`, `NOT`, `IN`, `IS`, `WAS`
3. **Date functions**: `startOfDay()`, `endOfDay()`, `startOfWeek()`
4. **User functions**: `currentUser()`, `membersOf()`
5. **Test first**: Use `--count` to verify query before bulk operations

### Bulk Operations Safety

1. **Always test JQL**: Run search first to verify matching items
2. **Use --yes carefully**: Only with confirmed queries
3. **Use --ignore-errors**: For large bulk operations
4. **Check limits**: Use `--paginate` for operations on many items
5. **Verify results**: Check a sample after bulk updates

### Field Selection

1. **Default fields**: Use for quick overview
2. **Minimal fields**: Use `--fields "key,summary"` for performance
3. **All fields**: Use `--fields "*all"` only when needed
4. **Exclude fields**: Use `--fields "*navigable,-comment"` to reduce noise

### Output Format Selection

1. **Human review**: Use default table format
2. **Scripting**: Use `--json` for parsing
3. **Spreadsheets**: Use `--csv` for export
4. **Quick check**: Use `--web` to open in browser
5. **Count only**: Use `--count` for metrics

### Assignment Best Practices

1. **Use @me**: For self-assignment
2. **Use email**: For specific users
3. **Use default**: For project default assignee
4. **Verify users exist**: Before bulk assignment
5. **Unassign when needed**: Use `--remove-assignee`

## Common Patterns

### Pattern 1: Find My Open Work

```bash
acli jira workitem search \
  --jql "assignee = currentUser() AND status != Done" \
  --fields "key,summary,status,priority"
```

### Pattern 2: Track Team Velocity

```bash
# Completed this sprint
acli jira workitem search \
  --jql "sprint = 'Sprint 23' AND status = Done" \
  --count

# In progress
acli jira workitem search \
  --jql "sprint = 'Sprint 23' AND status = 'In Progress'" \
  --count
```

### Pattern 3: Find Stale Issues

```bash
acli jira workitem search \
  --jql "status = 'In Progress' AND updated <= -14d" \
  --fields "key,summary,assignee,updated"
```

### Pattern 4: Label Management

```bash
# Add label to matching items
acli jira workitem edit \
  --jql "project = TEAM AND created >= -7d" \
  --labels "new-this-week" \
  --yes

# Remove outdated label
acli jira workitem edit \
  --jql "labels = 'new-this-week' AND created <= -7d" \
  --remove-labels "new-this-week" \
  --yes
```

### Pattern 5: Priority Triage

```bash
# Find unprioritzed items
acli jira workitem search \
  --jql "project = TEAM AND priority is EMPTY" \
  --fields "key,summary,created"

# Set default priority
acli jira workitem edit \
  --jql "project = TEAM AND priority is EMPTY" \
  --priority "Medium" \
  --yes
```

## Troubleshooting

### Issue: JQL Syntax Error

```bash
# Problem: Complex JQL failing
# Solution: Build query incrementally

# Start simple
acli jira workitem search --jql "project = TEAM" --count

# Add conditions one at a time
acli jira workitem search --jql "project = TEAM AND status = Open" --count

# Add more specific filters
acli jira workitem search \
  --jql "project = TEAM AND status = Open AND assignee = currentUser()" \
  --count
```

### Issue: No Results from Search

```bash
# Verify project key exists
acli jira project list | grep "TEAM"

# Check filter is valid
acli jira filter get --id 10001

# Test broader query
acli jira workitem search --jql "project = TEAM" --count
```

### Issue: Bulk Operation Too Slow

```bash
# Problem: Large bulk update timing out
# Solution: Break into smaller batches

# Get count first
acli jira workitem search --jql "project = TEAM" --count

# Process in batches
acli jira workitem edit \
  --jql "project = TEAM AND created >= -7d" \
  --labels "batch1" \
  --yes

acli jira workitem edit \
  --jql "project = TEAM AND created < -7d AND created >= -14d" \
  --labels "batch2" \
  --yes
```

### Issue: Authentication Expired

```bash
# Check status
acli jira auth status

# Re-login if needed
acli jira auth login

# Switch to different account
acli jira auth switch
```

### Issue: Permission Denied

```bash
# Problem: Cannot edit/delete items
# Solution: Check user permissions in Jira

# Try viewing first
acli jira workitem view KEY-123

# Check project permissions
acli jira project view --key "TEAM"
```

## Advanced Usage

### Combining with Other Tools

```bash
# Use with jq for JSON processing
acli jira workitem search \
  --jql "project = TEAM" \
  --json | jq '.[] | {key: .key, summary: .fields.summary}'

# Use with xsv for CSV analysis
acli jira workitem search \
  --jql "project = TEAM" \
  --csv | xsv select key,summary,assignee

# Use with grep for filtering
acli jira workitem search \
  --jql "project = TEAM" \
  --fields "key,summary" | grep "authentication"
```

### Scripting Examples

```bash
# Create work items from file list
while IFS= read -r summary; do
  acli jira workitem create \
    --summary "$summary" \
    --project "TEAM" \
    --type "Task" \
    --assignee "@me"
done < tasks.txt

# Bulk transition based on external criteria
for key in KEY-{100..110}; do
  acli jira workitem transition \
    --key "$key" \
    --status "Done" \
    --yes 2>/dev/null
done
```

## Quick Reference

```bash
# Authentication
acli jira auth login
acli jira auth status

# Search
acli jira workitem search --jql "JQL_QUERY"
acli jira workitem search --jql "JQL_QUERY" --fields "key,summary"
acli jira workitem search --filter FILTER_ID

# View
acli jira workitem view KEY-123
acli jira workitem view KEY-123 --web

# Create
acli jira workitem create --summary "Title" --project "TEAM" --type "Task"

# Edit
acli jira workitem edit --key "KEY-123" --summary "New title"
acli jira workitem edit --jql "JQL_QUERY" --assignee "@me"

# Transition
acli jira workitem transition --key "KEY-123" --status "Done"

# Comment
acli jira workitem comment create --key "KEY-123" --body "Comment"

# Projects
acli jira project list
acli jira project view --key "TEAM"

# Export
acli jira workitem search --jql "JQL_QUERY" --csv > export.csv
acli jira workitem search --jql "JQL_QUERY" --json > export.json
```

## Summary

**Primary directives:**
1. **Always authenticate first** using `acli jira auth login`
2. **Test JQL queries** before bulk operations
3. **Use --yes flag carefully** to avoid unintended changes
4. **Select appropriate output format** (default, json, csv, web)
5. **Use pagination** for large result sets
6. **Verify permissions** before attempting operations
7. **Use --ignore-errors** for resilient bulk operations

**Most common operations:**
- `acli jira workitem search --jql "..."` - Find work items
- `acli jira workitem view KEY-123` - View details
- `acli jira workitem create` - Create new work item
- `acli jira workitem edit` - Update work items
- `acli jira workitem transition` - Change status
- `acli jira workitem comment create` - Add comments
- `acli jira project list` - List projects

**Key features:**
- Powerful JQL search capabilities
- Bulk operations with safety controls
- Multiple output formats (table, JSON, CSV, web)
- Pagination for large datasets
- Integration-friendly JSON output
