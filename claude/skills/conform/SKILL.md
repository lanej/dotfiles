---
name: conform
description: Transform unstructured data into structured JSON using AI-powered extraction. Use when extracting structured data from text/PDFs/CSVs, parsing unstructured content, converting to schema-compliant JSON, or validating data structures. Triggers on "extract data", "parse unstructured", "convert to JSON", "structure data", "schema validation", or AI-based data transformation tasks.
---
# Conform CLI Skill

`conform` transforms unstructured files into schema-validated JSON using AI (Ollama local or Vertex AI cloud). Source: `~/src/conform`.

## Unix Philosophy

- **One job**: unstructured → structured JSON. Not filtering, formatting, or storing.
- **stdout by default**: compose with pipes. `--output` only for final destinations.
- **Prefer simpler tools**: use `jq`/`xsv`/`xlsx` for already-structured data; `grep`/`sed`/`awk` for pattern matching.

## Core Commands

### Single File

```bash
# Basic (auto-detect provider)
conform input.txt --schema schema.json

# Provider selection
conform input.txt --schema schema.json --provider ollama --model llama3.2
conform input.txt --schema schema.json --provider vertex --vertex-project my-project --vertex-location us-central1 --vertex-model gemini-2.5-flash

# Control retry/size/context
conform input.txt --schema schema.json --no-retry                  # single-shot
conform input.txt --schema schema.json --max-retries 5
conform input.txt --schema schema.json --max-input-size 5242880    # 5MB limit
conform input.txt --schema schema.json --max-context-tokens 100000 # override model default

# Output
conform input.txt --schema schema.json --output result.json
conform input.txt --schema schema.json --verbose  # stderr only, doesn't break pipes
```

### Batch Processing (Vertex AI async, ~50% cost reduction)

```bash
# Setup (one-time): create GCS bucket and save to ~/.conform/config.json
conform init-bucket --vertex-project my-project --vertex-location us-central1

# Submit
conform batch submit data/ --schema schema.json --output results/
conform batch submit data/ --schema schema.json --output results/ --gcs-bucket gs://my-bucket/staging
conform batch submit requests.jsonl --raw --output results/        # pre-formatted JSONL
conform batch submit data/ --schema schema.json --output results/ --vertex-model gemini-2.5-pro --name "my-job" -y

# Manage
conform batch status <job-id>
conform batch list
conform batch list --remote          # discover jobs from GCP (cross-machine)
conform batch list --status RUNNING  # filter: PENDING|QUEUED|RUNNING|SUCCEEDED|FAILED|CANCELLED
conform batch list --json
conform batch download <job-id>
conform batch cancel <job-id>
conform batch import <job-id> --output results/   # import GCP job to local store
```

Batch submit shows cost estimate, prompts for confirmation (skip with `-y`/`--yes` or `--skip-cost-estimate`), and validates the schema for Vertex AI compatibility before submitting.

Job metadata: `~/.conform/batch-jobs/`. User config: `~/.conform/config.json`.

### Model Registry

```bash
# List known models with context, output, pricing, and region availability
conform models list                        # Vertex AI models (default)
conform models list ollama                 # Ollama models
conform models list all                    # both
conform models list --region us-east1      # filter + show availability checkmarks
conform models list --verbose              # expand full region list per model

# Update local model cache from Vertex AI API + docs
# Writes to ~/.cache/conform/models.json (XDG cache, supersedes compiled defaults)
conform models update
conform models update --vertex-project my-project -y

# Regenerate compiled-in defaults (developer workflow, commits to repo)
just update-models
```

Model cache precedence: `~/.cache/conform/models.json` (updated by `conform models update`) → compiled defaults in binary.

The `models list` table columns: STATUS (GA/PREVIEW), MODEL, CONTEXT, OUTPUT, $/1M IN/OUT (standard pricing), REGIONS. The `--region` flag hides the price column for width; use `--verbose` to expand region lists.

### MCP Server

```bash
# stdio transport (for local tool integration)
conform-mcp

# HTTP transport with OAuth 2.1
conform-mcp --transport http --port 3456 --host 127.0.0.1
conform-mcp --transport http --oauth-secret mysecret --token-ttl 3600

# Env vars: MCP_PORT, MCP_HOST, MCP_ISSUER, MCP_OAUTH_SECRET, MCP_TOKEN_TTL_SEC, MCP_REFRESH_TTL_SEC
```

MCP tools: `convert`, `batch`, `config`. HTTP endpoint: `/mcp` (Bearer auth). Health: `/health`.

## Schema Design

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["name", "email"],
  "properties": {
    "name": { "type": "string", "description": "Full legal name" },
    "email": { "type": "string", "format": "email" },
    "status": { "type": "string", "enum": ["active", "inactive"] },
    "tags": { "type": "array", "items": { "type": "string" } },
    "score": { "type": ["number", "null"] }
  }
}
```

**Tips:**
- Add `description` to properties — it improves extraction accuracy.
- Use `enum` to constrain categorical fields.
- Mark critical fields `required`.
- Vertex AI auto-transforms `["type", "null"]` → `nullable: true` (handled internally).
- Vertex AI does NOT support: `uniqueItems`, `pattern`, `maxLength`, `minLength`, `minimum`, `maximum`, `$ref`, `$defs`, `additionalProperties: false`. Batch submit validates and rejects schemas with these before submitting.

## Pipeline Patterns

```bash
# Extract → filter → format (PREFERRED)
conform notes.txt --schema meeting.json | jq '.actionItems[] | select(.dueDate < "2026-03-01")'

# Extract → analyze
conform survey.pdf --schema survey.json | jq '.responses[]' > /tmp/responses.jsonl
duckdb -c "SELECT question, AVG(rating) FROM read_json_auto('/tmp/responses.jsonl') GROUP BY 1"

# Batch: process directory → aggregate
conform batch submit docs/ --schema schema.json --output results/ -y
# after completion:
cat results/*.jsonl | jq -s 'map(.response.candidates[0].content.parts[0].text | fromjson) | add'

# Multi-destination via tee
conform data.txt --schema schema.json | tee \
  >(jq '.summary' > summary.json) \
  >(jq -r '.items[] | [.name, .price] | @csv' > items.csv)
```

## Provider Selection

| Factor | Ollama | Vertex AI |
|--------|--------|-----------|
| Privacy/offline | ✓ | ✗ |
| Cost | Free | Per-token |
| Quality | Model-dependent | High (Gemini 2.5) |
| Batch async | ✗ | ✓ |
| Setup | `ollama serve` | `gcloud auth application-default login` |

## Troubleshooting

```bash
# Ollama not running
curl http://localhost:11434/api/version && ollama serve && ollama list

# Vertex auth
gcloud auth application-default login
# or: export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json

# Debug extraction quality
conform input.txt --schema schema.json --verbose

# Input too large
conform input.txt --schema schema.json --max-input-size 10485760  # 10MB

# Context window exceeded
conform input.txt --schema schema.json --max-context-tokens 200000

# Schema rejected by Vertex AI batch
conform models list  # check schema constraints above; fix before resubmitting
```

## When NOT to Use

- Input is structured JSON/CSV/Excel → use `jq`, `xsv`, `xlsx`
- Simple regex patterns → use `grep`, `sed`, `awk`
- Deterministic field extraction → use `jq` filters
- No semantic interpretation needed → skip the AI call
