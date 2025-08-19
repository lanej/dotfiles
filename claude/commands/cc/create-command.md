---
description: Create a new Claude Code custom command
argument-hint: [command-name] [description]
allowed-tools: Write, Read, LS, Bash(mkdir:*), Bash(ls:*), WebSearch(*)
---

# Create Command

Create a new Claude Code custom command with proper structure and best practices.

## Usage:

`/create-command [command-name] [description]`

## Process:

### 1. Command Analysis

- Determine command purpose and scope
- Choose appropriate location (project vs user-level)
- Analyze similar existing commands for patterns

### 2. Command Structure Planning

- Define required parameters and arguments
- Plan command workflow and steps
- Identify required tools and permissions
- Consider error handling and edge cases

### 3. Command Creation

- Create command file with proper YAML frontmatter
- Include comprehensive documentation
- Add usage examples and parameter descriptions
- Implement proper argument handling with `$ARGUMENTS`

### 4. Quality Assurance

- Validate command syntax and structure
- Test command functionality
- Ensure proper tool permissions
- Review against best practices

## Template Structure:

```markdown
---
description: Brief description of the command
argument-hint: Expected arguments format
allowed-tools: List of required tools
---

# Command Name

Detailed description of what this command does and when to use it.

## Usage:

`/[category:]command-name [arguments]`

## Process:

1. Step-by-step instructions
2. Clear workflow definition
3. Error handling considerations

## Examples:

- Concrete usage examples
- Different parameter combinations

## Notes:

- Important considerations
- Limitations or requirements
```

## Best Practices:

- Keep commands focused and single-purpose
- Use descriptive names and clear documentation
- Include proper tool permissions in frontmatter
- Provide helpful examples and usage patterns
- Handle arguments gracefully with validation
- Follow existing command conventions
- Test thoroughly before deployment

## Your Task:

Create a new command named "$ARGUMENTS" following these guidelines:

1. Ask for clarification on command purpose if description is unclear
2. Determine appropriate location (project vs user-level) and category (e.g. gh, cc or ask user for others)
3. Create command file with proper structure
4. Include comprehensive documentation and examples
5. Validate command syntax and functionality
