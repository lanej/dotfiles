---
trigger: ironclad
description: Ironclad CLM CLI and MCP server for contract lifecycle management
---

# Ironclad CLI

CLI + MCP server for Ironclad contract lifecycle management. Bun/TypeScript. JSON to stdout, errors to stderr. Source: `~/src/ironclad`.

## Config (env vars)

Required:
```
IRONCLAD_CLIENT_ID       OAuth client ID
IRONCLAD_CLIENT_SECRET   OAuth client secret
IRONCLAD_USER_EMAIL      User to act as (x-as-user-email header)
```

Optional:
```
IRONCLAD_BASE_URL        Default: https://ironcladapp.com/public/api/v1
IRONCLAD_TOKEN_ENDPOINT  Default: https://ironcladapp.com/oauth/token
IRONCLAD_OAUTH_SCOPE     Space-separated (default: read-only scopes)
IRONCLAD_TIMEOUT         Seconds (default: 30)
LOG_LEVEL                trace|debug|info|warn|error (default: error)
```

Default scopes are **read-only**: `readWorkflows`, `readDocuments`, `readSchemas`, `readRecords`, `readAttachments`. Add write scopes (`createWorkflows`, `updateWorkflows`, `createRecords`) to `IRONCLAD_OAUTH_SCOPE` for mutations.

## Commands

```bash
# Auth
ironclad auth status
ironclad auth login
ironclad auth logout

# Workflows
ironclad workflows list [--status active|completed|cancelled|draft] [--creator-email <email>] [--page <n>] [--page-size <n>]
ironclad workflows get <id>
ironclad workflows create --template <template-id> --attributes '<json-array>'
ironclad workflows update <id> --attributes '<json-array>' [--version <etag>]
ironclad workflows approvals <id>
ironclad workflows signatures <id>
ironclad workflows comment <id> --content '<text>'
ironclad workflows documents <id>
ironclad workflows emails <id>
ironclad workflows download --workflow <id> --document <id> [--file <path>]

# Records
ironclad records list [--schema <schema-id>] [--page <n>] [--page-size <n>]
ironclad records get <id>
ironclad records create --schema <schema-id> --fields '<json-array>'
ironclad records smart-import --schema <schema-id> --data '<json-object>'
ironclad records download-attachment --record <id> --attachment <type> [--file <path>]

# Schemas (discover templates and field definitions)
ironclad schemas workflows [--template <id>]
ironclad schemas records [--schema <id>]

# Download (generic authenticated URL fetch)
ironclad download <url> [--file <path>]

# MCP server (16 tools: 9 workflow + 5 record + 2 schema)
ironclad mcp stdio
```

## Gotchas

- **Schema-first**: Always `ironclad schemas workflows` or `ironclad schemas records` before creating -- discover template/schema IDs and required fields.
- **Attributes format** (workflow create/update): JSON array of `{"attribute_id": "<id>", "value": <val>}`.
- **Fields format** (record create): JSON array of `{"property_id": "<id>", "value": <val>}`.
- **Default scopes are read-only**: Create/update operations fail silently or 403 without write scopes in `IRONCLAD_OAUTH_SCOPE`.
- **Version/etag**: Workflow update supports optimistic concurrency via `--version <etag>` from the GET response.
- **Pagination**: Default page_size=50. Use `--page` and `--page-size`.
- **Attachment type**: Usually `signedCopy` for executed contracts.
- **MCP mode**: `ironclad mcp stdio` blocks on stdin/stdout -- do not run interactively.
- **smart-import**: Pass raw JSON object (not array). Ironclad AI maps fields to schema automatically.
- **download**: If `--file` omitted, uses filename from Content-Disposition header or defaults.
- **All output is JSON**: Pipe to `jq` for filtering.

## Common Patterns

**Create a contract workflow:**
```bash
ironclad schemas workflows | jq '.[] | {id, name}'
ironclad schemas workflows --template <id> | jq '.attributes[] | select(.required) | {id, type}'
ironclad workflows create --template <id> --attributes '[{"attribute_id":"counterparty_name","value":"Acme"}]'
```

**Find and download a signed contract:**
```bash
ironclad workflows list --status completed | jq '.[] | {id, name}'
ironclad records download-attachment --record <id> --attachment signedCopy --file contract.pdf
```

**Check approval/signature status:**
```bash
ironclad workflows approvals <workflow-id>
ironclad workflows signatures <workflow-id>
```

**Smart import from external data:**
```bash
ironclad records smart-import --schema <schema-id> --data '{"vendor":"Acme","amount":50000,"term":"2 years"}'
```

## Development

```bash
just test           # All tests (bun test)
just test-unit      # Unit tests only
just test-contract  # Contract tests only
just fmt            # Biome format
just lint           # Biome lint
just typecheck      # tsc --noEmit
just run <args>     # Run CLI via bun
just build          # Compile standalone binary
```

Contract specs in `specs/contracts/mcp-tools/*.json` are the source of truth for MCP tool schemas. Contract-driven development: update specs first, then implement.
