---
name: ui-review
description: Use when operating Viewrule through the ui-review CLI to capture or inspect reports, manage scoped rules, or record Josh's explicit visual feedback; project acceptance policy is selected separately.
---

# Viewrule operation

Use Viewrule through the `ui-review` compatibility wrapper. If it is not on PATH, use `~/.files/bin/ui-review`. Read `~/.files/docs/ui-review.md` for installation, configuration, supported commands, and version-specific limitations. This user-level skill supplies tool operation and personal feedback handling; it does not select application architecture, acceptance criteria, required browser tests, or CI gates.

Follow the target project's instructions and selected design system. When a project installs `ui-acceptance`, read its project-local `.agents/skills/ui-acceptance/SKILL.md`; otherwise preserve the repository's own acceptance criteria. Workstation tool availability does not opt the project into that profile. Follow host browser authorization, visibility, credential, and cleanup rules.

## Operate reports

Use `ui-review guidance --project <project>` to inspect configured guidance. When project setup is requested, `ui-review init --project <project>` initializes configuration; preserve existing routes, viewport choices, rules, and references. Supply the application's actual runtime URL when capturing:

```sh
ui-review check --project <project> --url <actual-app-url>
ui-review verify --project <project>
```

Read the returned JSON, affected screenshots, and HTML report. Capture and verify results describe those operations; they do not certify visual correctness, interaction coverage, or live deployment. Follow the project's acceptance instructions to assess the result. Missing tools, capture failures, authentication limits, or incomplete evidence remain explicit limits; do not invent a successful report or automate unsupported SSO navigation.

## Record actual feedback

When Josh explicitly approves a reference or asks for an adjustment, attach his actual feedback to the report he reviewed:

```sh
ui-review feedback --report <report.json> --decision approve --note '<his feedback>'
ui-review feedback --report <report.json> --decision adjust --note '<his feedback>'
```

Use shell-safe quoting or an argument array. Never record model self-approval as Josh's approval. Preserve subjective feedback as guidance; when feedback supports a measurable rule, use the project's selected acceptance process to validate that rule, then run:

```sh
ui-review learn --feedback <returned-id> --rule <rule.json>
```

Feedback and rule scope default to the project. Only when Josh explicitly makes a preference cross-project, pass `--scope global` to both feedback and learn. Global notes/rules live in `~/.files/claude/ui-review/`; project selectors, thresholds, feedback, and approved screenshots stay in the application's `.ui-review/`. Preserve private app data and authentication state. Report the exact preference or rule changed and its scope; feedback handling does not grant publication authority.

## Verification and optional gates

Stop enforcement is retired; `enforceOnStop` is ignored. `ui-review verify --project <project>` checks existing evidence without launching a browser. Git gates and application CI are project choices. Configure them when requested or explicitly selected by project instructions, following the installed CLI documentation; tool installation alone does not authorize introducing gates or changing acceptance policy.
