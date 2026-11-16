# Progressive CLI guidance

## Public command contract

```sh
TOOL skill
TOOL skill --topic NAME
TOOL skill --help
```

`TOOL skill` must print a compact, human-readable Markdown entrypoint to stdout: what the tool does, essential constraints shared by its tasks, and a topic index showing when and how to load each topic. Include literal command examples using the actual executable name. An agent reading this output must be able to retrieve the next topic through the CLI without locating the installation directory.

`TOOL skill --topic NAME` must print the selected bundled Markdown topic to stdout. Use a finite declared topic registry, preferably stable intent-based names such as `authentication`, `queries`, or `rendering`. Names select packaged resources; they are not arbitrary paths, URLs, shell fragments, or executable instructions. Reject unknown topics with a meaningful stderr diagnostic and nonzero exit status. Make valid names discoverable through the entrypoint or command help.

Normal discovery success exits zero. Keep the output usable in pipes: no ANSI decorations, progress spinners, account banners, or application results mixed into the Markdown. Missing or unreadable bundled content must fail clearly; do not emit a partial or invented successful guide. Preserve the existing framework’s conventions for help and parse errors.

## Package and content

Ship the entrypoint and topics with the same tool release. Read the bundled content rather than fetching mutable guidance at discovery time. Verify release packaging includes the referenced resources so an installed artifact remains usable without the source checkout or developer workstation.

Keep task-specific procedures, examples, and troubleshooting in focused topics. Each topic should supply enough context to complete its task after reading the entrypoint. Essential authority, privacy, target-selection, and failure rules belong in the entrypoint when they apply across tasks. A small router that requires every reference on every call has not reduced the reading cost.

Use portable example inputs and identify meaningful side effects and expected outcomes. Keep project/private data, credentials, environment dumps, and organization-only assumptions out of generic bundled guidance. Verify version-sensitive advice against the implementation, installed help, or authoritative documentation; distinguish observed behavior from unverified workarounds.

## Discovery is not application execution

Register the discovery path so it returns before application initialization, project/config loading, credential resolution, remote clients, migrations, or interactive setup. It must work from outside a project and when project configuration is absent or invalid. Reading packaged Markdown does not authorize creating files, starting a daemon, contacting an API, or installing dependencies.

In a CLI that already exists, introduce this behavior only within the authorized interface-change scope. Preserve existing command meanings and compatibility. Shared/upstream authority or hold adoption can constrain the migration; identify the unmet contract without silently rewriting the application.

## Verify through the real entrypoint

Use the existing CLI acceptance path to exercise the root guide, one relevant topic, and normal help. Check meaningful Markdown and the actual topic content, successful exit status, clean stdout, and the intended absence of application effects. Include a context with missing or invalid project configuration when initialization could otherwise prevent discovery.

Check an unknown topic and a genuinely unavailable packaged topic where practical: both must fail clearly instead of printing successful-looking output. Inspect the built/installed package when the claim depends on resource bundling, rather than only running from the source tree. These are behavior checks for the affected CLI, not a new mandatory test harness or coverage quota.
