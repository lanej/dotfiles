Generate and register a short descriptive name for this session.

1. Read the conversation so far and summarize the core topic in 2-4 kebab-case words (e.g. `vertex-ai-setup`, `dotfile-hook-refactor`). No explanation — just the name.

2. Find the session ID by running:
   ```
   ls -t ~/.claude/projects/$(echo $PWD | sed 's|/|-|g; s|^-||')/
   ```
   The most recently modified `.jsonl` file (without extension) is the session ID. If that path doesn't exist, try finding the session JSONL matching the current conversation by looking at modification times under `~/.claude/projects/`.

3. Write the name:
   ```
   mkdir -p ~/.claude/session-names
   echo -n "<name>" > ~/.claude/session-names/<session_id>
   ```

4. Set the terminal title:
   ```
   printf '\033]0;%s\007' "<name>" > /dev/tty
   ```

5. Report back: `Session named: <name>`
