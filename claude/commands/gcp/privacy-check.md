# Privacy Check Slash Command

Run a fresh privacy check on the current Vertex AI project, bypassing the cache.

You are Claude Code. The user has requested a fresh privacy check.

## Task

1. Set the environment variable `CLAUDE_FORCE_PRIVACY_CHECK=true`
2. Run the full privacy check: `~/.claude/local/claude-privacy-check`
3. Report the results to the user with:
   - Current privacy level (HIGH/MEDIUM/LOW)
   - Any warnings or issues found
   - Who has access to the GCP project
   - Recommendations if any issues were found

## Output Format

Show the full output from the privacy check script, then provide a brief summary:

```
Summary:
- Privacy Level: [HIGH/MEDIUM/LOW]
- Prompts/Responses Logged: [YES/NO]
- Project Access: [X owners, Y admins]
- Recommendation: [Action items if needed]
```

If the check shows HIGH privacy with no warnings, reassure the user their setup is good.
If warnings are found, explain what they mean and whether action is needed.
