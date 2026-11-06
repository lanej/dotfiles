# Local tool routing

For Slack work, read `~/.agents/skills/dotfiles/slack/SKILL.md` and use its documented CLI or MCP interface; apply `josh-slack-voice` when writing as Josh. Do not use native Slack connector skills, automatic Plugin Management workflows, or OpenAI Platform connector key-setup workflows. Follow the browser automation defaults for local UI work and use Chrome only for explicitly requested signed-in browser work.

# Google Workspace

For Google Workspace work, read the applicable GSpace product skill under `~/.agents/skills/<product>/SKILL.md` and its relevant references, then use the installed `gspace` CLI through the shell. This includes Gmail, Calendar, Drive, Docs, Sheets, Slides, and the other Workspace services. For cross-product routing or setup, read `~/.agents/skills/google-workspace/SKILL.md`. GSpace's skill files and CLI help are the authority for supported operations, command syntax, authentication, and workflow.

Do not use Codex's built-in Google Workspace knowledge, Google Workspace plugins or connector skills, app/connector tools, MCP tools (including GSpace MCP), direct Google API calls, or browser automation for Workspace work. Do not discover or connect an alternate Google integration. If the GSpace skills or CLI cannot support the request, report the specific limitation instead of switching tools or inventing commands from memory.
