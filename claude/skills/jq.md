# jq - JSON Processing

**IMPORTANT**: `jq` is the **STRONGLY PREFERRED** tool for ALL JSON formatting, parsing, manipulation, and analysis tasks. Use jq instead of Python/Node.js scripts, grep, awk, or other text processing tools when working with JSON data.

## Core Philosophy

- **Always use jq for JSON**: If the data is JSON or can be converted to JSON, use jq
- **Streaming-friendly**: jq processes JSON as a stream, making it memory-efficient for large files
- **Composable**: jq filters can be chained with pipes, just like shell commands
- **Pure and functional**: jq transformations are predictable and side-effect-free

## Basic Usage Patterns

### Pretty-Printing and Formatting

```bash
# Pretty-print JSON (most common use case)
cat file.json | jq '.'
jq '.' file.json

# Compact output (remove whitespace)
jq -c '.' file.json

# Sort keys alphabetically
jq -S '.' file.json

# Raw output (no quotes for strings)
jq -r '.field' file.json

# Null input (construct JSON from scratch)
jq -n '{name: "value", count: 42}'
```

### Selecting and Filtering

```bash
# Select a single field
jq '.field' file.json

# Select nested field
jq '.user.email' file.json

# Select array element by index
jq '.[0]' array.json
jq '.[2:5]' array.json  # Array slice

# Select multiple fields (create new object)
jq '{name: .name, email: .email}' file.json

# Filter array elements
jq '.[] | select(.age > 18)' users.json
jq '.users[] | select(.active == true)' data.json

# Filter with multiple conditions
jq '.[] | select(.age > 18 and .status == "active")' users.json

# Check if field exists
jq '.[] | select(.email != null)' users.json
jq '.[] | select(has("email"))' users.json
```

### Array Operations

```bash
# Get array length
jq '. | length' array.json

# Map over array (transform each element)
jq '[.[] | .name]' users.json
jq 'map(.name)' users.json  # Same as above

# Filter then map
jq '[.[] | select(.active) | .email]' users.json

# Get first/last element
jq 'first' array.json
jq 'last' array.json

# Get unique values
jq 'unique' array.json
jq 'unique_by(.id)' array.json

# Sort array
jq 'sort' array.json
jq 'sort_by(.age)' users.json
jq 'sort_by(.age) | reverse' users.json

# Group by field
jq 'group_by(.status)' users.json

# Flatten nested arrays
jq 'flatten' nested.json
jq 'flatten(1)' nested.json  # Flatten one level
```

### Aggregation and Statistics

```bash
# Sum array of numbers
jq 'add' numbers.json
jq '[.[] | .price] | add' items.json

# Count elements
jq '. | length' array.json
jq '[.[] | select(.active)] | length' users.json

# Min/max values
jq 'min' numbers.json
jq 'max' numbers.json
jq 'min_by(.age)' users.json
jq 'max_by(.price)' items.json

# Average (mean)
jq 'add / length' numbers.json
jq '[.[] | .price] | add / length' items.json
```

### String Manipulation

```bash
# String interpolation
jq '.name + " " + .surname' user.json
jq '"\(.firstName) \(.lastName)"' user.json

# String functions
jq '.email | ascii_downcase' user.json
jq '.email | ascii_upcase' user.json
jq '.text | startswith("prefix")' data.json
jq '.text | endswith("suffix")' data.json
jq '.text | contains("substring")' data.json

# Split and join
jq '.path | split("/")' data.json
jq '.tags | join(", ")' data.json

# Regex matching
jq '.email | test("@example\\.com$")' user.json
jq 'select(.email | test("@example\\.com$"))' users.json

# Regex capture and replace
jq '.text | capture("(?<prefix>\\w+)-(?<suffix>\\d+)")' data.json
jq '.text | sub("old"; "new")' data.json
jq '.text | gsub("old"; "new")' data.json  # Global replace
```

### Object Manipulation

```bash
# Get all keys
jq 'keys' object.json
jq 'keys_unsorted' object.json

# Get all values
jq '.[]' object.json
jq 'values' object.json

# Add/update fields
jq '. + {newField: "value"}' data.json
jq '.newField = "value"' data.json

# Delete fields
jq 'del(.fieldToRemove)' data.json

# Rename field
jq '.newName = .oldName | del(.oldName)' data.json

# Merge objects
jq '. * {override: "value"}' data.json  # Right object wins
jq '. + {default: "value"}' data.json   # Left object wins

# Convert object to array of key-value pairs
jq 'to_entries' object.json
jq 'from_entries' array.json  # Reverse operation

# Map over object values
jq 'map_values(. * 2)' numbers.json
jq 'with_entries(.value = .value * 2)' numbers.json
```

### Working with Multiple Files

```bash
# Merge multiple JSON files into array
jq -s '.' file1.json file2.json

# Merge objects from multiple files
jq -s 'add' file1.json file2.json

# Process each file separately
jq '.' file1.json file2.json
```

### Advanced Patterns

```bash
# Conditional logic
jq 'if .age >= 18 then "adult" else "minor" end' user.json

# Alternative operator (default values)
jq '.email // "no-email@example.com"' user.json

# Try-catch (suppress errors)
jq '.field.nested.deep?' data.json  # Returns null if path doesn't exist

# Recursive descent
jq '.. | .id? // empty' nested.json  # Find all 'id' fields at any depth

# Variables
jq '.users[] as $user | .orders[] | select(.userId == $user.id) | {order: ., user: $user}' data.json

# Reduce (fold)
jq 'reduce .[] as $item (0; . + $item.value)' items.json
```

## Common Use Cases

### API Response Processing

```bash
# Extract specific fields from API response
curl -s https://api.example.com/users | jq '[.data[] | {id, name, email}]'

# Get only active users
curl -s https://api.example.com/users | jq '.data[] | select(.status == "active")'

# Pretty-print and save
curl -s https://api.example.com/data | jq '.' > formatted.json
```

### Log File Analysis

```bash
# Parse JSON logs and filter by level
cat app.log | jq -c 'select(.level == "ERROR")'

# Extract error messages
cat app.log | jq -r 'select(.level == "ERROR") | .message'

# Count errors by type
cat app.log | jq -s '[.[] | select(.level == "ERROR")] | group_by(.type) | map({type: .[0].type, count: length})'

# Get logs within time range
cat app.log | jq -c 'select(.timestamp >= "2025-01-01" and .timestamp < "2025-02-01")'
```

### Data Transformation

```bash
# CSV to JSON (with headers)
cat data.csv | jq -R -s 'split("\n") | map(split(",")) | .[0] as $headers | .[1:] | map(. as $row | reduce range(0; $headers|length) as $i ({}; .[$headers[$i]] = $row[$i]))'

# JSON to CSV
jq -r '(.[0] | keys_unsorted) as $keys | $keys, (.[] | [.[$keys[]]] | @csv)' data.json

# Flatten nested structure
jq '[.users[] | {userId: .id, userName: .name, orderIds: [.orders[].id]}]' data.json
```

### Configuration File Processing

```bash
# Extract environment variables
jq -r '.env | to_entries[] | "\(.key)=\(.value)"' config.json

# Validate required fields
jq 'if (.database and .apiKey) then "valid" else "missing required fields" | halt_error(1) end' config.json

# Merge config files (override defaults)
jq -s '.[0] * .[1]' defaults.json custom.json
```

## Performance Tips

- **Use streaming for large files**: `jq --stream` for files that don't fit in memory
- **Filter early**: Apply `select()` filters as early as possible in the pipeline
- **Avoid unnecessary iterations**: Use built-in functions like `map()`, `group_by()` instead of manual loops
- **Use `-c` for compact output**: Reduces output size significantly
- **Pipe to jq once**: Instead of multiple `jq` commands, chain filters with `|` inside a single jq invocation

## Debugging and Development

```bash
# Add debug output
jq '. | debug' data.json

# See intermediate results
jq '. | debug("After filter") | select(.active) | debug("After select")' data.json

# Type checking
jq 'type' data.json
jq '.field | type' data.json

# Pretty-print for readability during development
jq '.' data.json  # Always start here to understand the structure
```

## Common Patterns with Other Tools

```bash
# Combine with curl
curl -s https://api.example.com/data | jq '.results[] | .name'

# Combine with find
find . -name "*.json" -exec jq '.' {} \;

# Combine with grep (but prefer jq's select when possible)
jq '.[]' data.json | grep pattern  # ❌ Avoid
jq '.[] | select(.field | contains("pattern"))' data.json  # ✅ Prefer

# Save filtered results
jq '[.[] | select(.active)]' data.json > active.json

# Count results
jq '[.[] | select(.status == "pending")] | length' data.json
```

## Error Handling

```bash
# Gracefully handle missing fields
jq '.field // "default"' data.json

# Optional field access (no error if missing)
jq '.field.nested.deep?' data.json

# Suppress null results
jq '.[] | .field? // empty' data.json

# Exit with error on empty result
jq -e '.results[] | select(.id == 123)' data.json || echo "Not found"
```

## Key Reminders

- **Raw output**: Use `-r` for strings without quotes (shell scripting)
- **Compact output**: Use `-c` for single-line JSON (logs, pipes)
- **Slurp mode**: Use `-s` to read entire input as single array
- **Null input**: Use `-n` to construct JSON without reading input
- **Exit status**: Use `-e` to set exit status based on output (useful in scripts)
- **Always prefer jq**: Don't reach for Python/Node.js for simple JSON tasks

## Quick Reference

| Task | Command |
|------|---------|
| Pretty-print | `jq '.'` |
| Select field | `jq '.field'` |
| Filter array | `jq '.[] \| select(.key == "value")'` |
| Map array | `jq 'map(.field)'` |
| Get length | `jq 'length'` |
| Sort | `jq 'sort_by(.field)'` |
| Group | `jq 'group_by(.field)'` |
| Unique | `jq 'unique'` or `jq 'unique_by(.field)'` |
| Sum | `jq 'add'` |
| Keys | `jq 'keys'` |
| Raw string | `jq -r '.field'` |
| Compact | `jq -c '.'` |
| Merge files | `jq -s 'add' file1.json file2.json` |
