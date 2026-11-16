# Application tool choices

Use this catalog when choosing application tools, introducing an interface, or planning a migration. Read `.source-code.json` for the installed `authority` and `adoption`; authored `source-code.toml` expresses desired policy, and `source-code explain` shows differences. These choices apply at every lifecycle stage, including research proofs of concept. Reuse the selected libraries to reduce application code; install only dependencies needed by the capability being built. Do not create unused application layers or duplicate a library behind a homemade framework.

## Authority and adoption

Authority describes who can choose the stack, independently of stage, kind, and public/open-source visibility. An open-source project we control can be owned; contributing to somebody else's public repository is upstream work. Never infer authority from Git hosting, repository names, or visibility.

| Authority | Decision rights |
| --- | --- |
| `owned` | We choose tools for project-owned surfaces, subject to adoption and existing project requirements. |
| `shared` | Preserve established conventions until the project agrees to adoption. A local or shadow installation is not project agreement. |
| `upstream` | Follow maintainer conventions. Alternatives require agreement under upstream governance. |

| Adoption | Application |
| --- | --- |
| `hold` | Preserve the established stack, including extensions to its existing surfaces. Do not use the catalog to introduce a competing stack. For an unestablished capability, obtain a project choice before selecting a stack. |
| `new` | Require the catalog for new independent surfaces within the project's authority. Extend established surfaces using their existing stack; creating a file or endpoint inside one does not make it independent. |
| `backfill` | Require the catalog for new independent surfaces and record the direction for migrating existing implementations. Execute migration only within an explicitly agreed task scope, including compatibility and validation. Ordinary feature work does not authorize a rewrite. |

Shared and upstream authority still require project agreement when adoption is `new` or `backfill`; the setting alone does not grant authority. Record that agreement in project instructions or the relevant project decision. Missing settings on legacy installations do not imply owned authority or migration permission: preserve conventions and establish the settings before applying this catalog. Setup and upgrade require explicit selections when no configured or saved choices exist. Inspecting or running an existing installation does not require changing it.

## CLI construction

For command-line interface work, read the installed [CLI construction skill](../../cli/SKILL.md). It requires the catalog’s language tools and progressive agent guidance through `TOOL skill` and `TOOL skill --topic NAME` where project authority and adoption apply. It preserves existing command meanings and does not authorize an unscoped retrofit.

## Catalog

Each choice is required when its capability is needed and authority/adoption permit applying this catalog. This is binding implementation and review guidance; structural validation does not inspect application dependencies or certify compliance.

| Capability | Required choice |
| --- | --- |
| TypeScript/JavaScript CLI | [Commander](https://github.com/tj/commander.js) for commands, arguments, options, and help. |
| Go CLI/TUI | [Cobra](https://cobra.dev/) for command structure; [lanej/charmed](https://github.com/lanej/charmed) for terminal presentation and interaction. Charmed is the component library, not the argument parser. |
| Python CLI/TUI | [Typer](https://typer.tiangolo.com/) for commands, [Rich](https://rich.readthedocs.io/) for presentation, and [Textual](https://textual.textualize.io/) for full TUIs. |
| Rust CLI/TUI | [clap](https://docs.rs/clap/) for commands; [Ratatui](https://ratatui.rs/) for full TUIs. |
| Web applications | [React](https://react.dev/), TypeScript, and [Vite](https://vite.dev/); [Connect Query](https://connectrpc.com/docs/web/query/) for remote server state; [TanStack Router](https://tanstack.com/router/latest) when routing is needed. |
| Application APIs | [Connect](https://connectrpc.com/docs/introduction/) with Protobuf contracts and generated clients/servers using the language implementation. Use [Buf](https://buf.build/docs/) for generation, lint, and applicable schema compatibility checks. Do not create a parallel REST or GraphQL API by default. |
| API validation | [Protovalidate](https://protovalidate.com/) annotations for shared request constraints where the target runtime supports them. Keep those constraints in Protobuf instead of duplicating them in Zod or Pydantic. Verify runtime support; identify unsupported constraints as a gap and resolve the boundary's validation explicitly before claiming enforcement. |
| Other boundary validation | [Zod](https://zod.dev/) in TypeScript; [Pydantic](https://docs.pydantic.dev/) in Python; typed parsing and explicit domain validation in Go/Rust. Protobuf decoding alone does not enforce domain constraints. |
| Logging | [Pino](https://github.com/pinojs/pino) for Node applications; Go [`log/slog`](https://pkg.go.dev/log/slog); Python standard [`logging`](https://docs.python.org/3/library/logging.html); Rust [`tracing`](https://docs.rs/tracing/). Keep machine-readable output separate from diagnostics and preserve meaningful severity distinctions. |
| Configuration | Validate settings once at startup: Zod in TypeScript; [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) in Python; typed settings in Go; [Serde](https://serde.rs/) plus [`config`](https://docs.rs/config/) in Rust when settings loading is needed. |
| Testing | [Vitest](https://vitest.dev/) and [Testing Library](https://testing-library.com/) for web component behavior; [Playwright](https://playwright.dev/) for real browser flows; retain the installed gotestsum, pytest, and Cargo guidance elsewhere. Evidence depth follows lifecycle and the affected behavior. |

Retain existing language quality tools and gates. This catalog does not replace formatting, strict typing, linting, dependency auditing, or the repository's selected package manager. Resolve compatible dependency versions in the consuming project and retain its lockfiles; this policy does not introduce application dependency pins into the installer.

## API boundaries and exceptions

Apply Connect to new application APIs we control when adoption selects the catalog. Client integrations consume external services using the provider's existing protocol; owning the client does not authorize redesigning the provider. Protocol-specific edges such as third-party webhooks, OAuth callbacks, health checks, and file delivery use the appropriate edge protocol without manufacturing an RPC equivalent. Preserve established APIs under hold/new; backfill requires a scoped compatibility and migration plan.

For other deviations, document **affected choice → concrete constraint → retained protections → revisit condition** near the relevant contract or project decision. Identify the selected alternative and obtain agreement where project governance requires it. Preference, early lifecycle stage, public visibility, and passing checks do not themselves establish an exception. An unsupported runtime capability remains an explicit gap until its relevant requirements are met; do not silently substitute a new protocol or claim unobserved compatibility.
