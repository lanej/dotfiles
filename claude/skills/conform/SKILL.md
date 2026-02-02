---
name: conform
description: Transform unstructured data into structured JSON using AI-powered extraction. Use when extracting structured data from text/PDFs/CSVs, parsing unstructured content, converting to schema-compliant JSON, or validating data structures. Triggers on "extract data", "parse unstructured", "convert to JSON", "structure data", "schema validation", or AI-based data transformation tasks.
---
# Conform CLI Skill

You are a data transformation specialist using `conform`, a CLI tool that uses AI to transform unstructured data into structured JSON that conforms to JSON schemas.

## What is conform?

`conform` is a CLI tool that:
- Takes unstructured data from files (text, PDFs, CSVs, etc.)
- Uses AI models (Ollama or Vertex AI) to extract and structure information
- Outputs JSON that conforms to a provided JSON schema
- Ensures consistent, validated data structures

## Unix Philosophy Alignment

**CRITICAL: Use conform as a focused pipeline component, not a Swiss Army knife.**

### Do One Thing Well
- conform's ONLY job: transform unstructured → structured JSON
- Does NOT do: formatting, analysis, storage, visualization
- Delegate downstream tasks to specialized tools (jq, xsv, xlsx, duckdb)

### Text Streams as Interface
- Writes JSON to stdout by default (use `--output` only when needed)
- Read with: `conform input.txt --schema schema.json | jq .`
- Errors go to stderr (exit code 0 on success, non-zero on failure)
- Silent on success unless `--verbose` specified

### Composition Over Complexity
- Design: `conform | jq | xsv` NOT "conform --format csv --filter ..."
- Example: `conform notes.txt --schema schema.json | jq '.items[]' | xsv select 1,2`
- Let each tool do what it does best

### When NOT to Use conform
**Prefer simpler tools when possible:**
- **Structured input** → Use jq directly (JSON), xsv (CSV), xlsx (Excel)
- **Simple text parsing** → Use grep, sed, awk for patterns
- **Deterministic extraction** → Use jq filters or xsv select
- **No schema needed** → Don't force structure prematurely
- **Only formatting needed** → Use jq for JSON, xsv for CSV

**Use conform ONLY when:**
- Input is genuinely unstructured (plain text, PDFs, messy documents)
- Need AI to interpret and extract semantic meaning
- Want guaranteed schema conformance
- Extracting complex nested structures from prose

## Core Capabilities

1. **Schema-driven extraction**: Define structure with JSON Schema
2. **Multiple AI providers**: Ollama (local) or Vertex AI (cloud)
3. **Flexible input**: Process various unstructured file formats
4. **Validated output**: Guaranteed schema conformance
5. **Configurable**: Model selection, temperature, endpoints

## Basic Usage

### Simple Transformation

```bash
# Basic usage with schema
conform input.txt --schema schema.json

# Output to file
conform input.txt --schema schema.json --output result.json

# Verbose mode for debugging
conform input.txt --schema schema.json --verbose
```

### Provider Selection

```bash
# Use Ollama (default, auto-detected)
conform input.txt --schema schema.json --provider ollama

# Use Vertex AI
conform input.txt --schema schema.json --provider vertex \
  --vertex-project my-project-id \
  --vertex-location us-central1
```

### Model Selection

```bash
# Specify Ollama model
conform input.txt --schema schema.json \
  --provider ollama \
  --model llama3.2

# Specify Vertex AI model
conform input.txt --schema schema.json \
  --provider vertex \
  --model gemini-1.5-pro
```

## Command Options

### Required Arguments

```bash
conform <file>              # Input file to process
  --schema <path>           # Path to JSON schema file
```

### AI Provider Options

```bash
--provider <name>           # AI provider: ollama|vertex (default: auto)
--model <name>              # Model name (provider-specific)
--temperature <number>      # Temperature 0.0-1.0 (default: 0.1)
```

### Ollama-Specific Options

```bash
--ollama-endpoint <url>     # Ollama API endpoint
                            # Default: http://localhost:11434
```

### Vertex AI-Specific Options

```bash
--vertex-project <id>       # GCP project ID
--vertex-location <loc>     # GCP location (default: us-central1)
```

### Output Options

```bash
--output <path>             # Write to file instead of stdout
--verbose                   # Show detailed processing info
```

### General Options

```bash
-V, --version               # Show version number
-h, --help                  # Show help
```

## JSON Schema Examples

### Example 1: Extract Contact Information

**Schema (contact-schema.json):**
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "name": {
      "type": "string",
      "description": "Full name of the person"
    },
    "email": {
      "type": "string",
      "format": "email",
      "description": "Email address"
    },
    "phone": {
      "type": "string",
      "description": "Phone number"
    },
    "address": {
      "type": "object",
      "properties": {
        "street": { "type": "string" },
        "city": { "type": "string" },
        "state": { "type": "string" },
        "zip": { "type": "string" }
      }
    }
  },
  "required": ["name", "email"]
}
```

**Usage:**
```bash
conform business-card.txt --schema contact-schema.json
```

### Example 2: Extract Product Information

**Schema (product-schema.json):**
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "products": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "name": { "type": "string" },
          "price": { "type": "number" },
          "currency": { "type": "string" },
          "description": { "type": "string" },
          "inStock": { "type": "boolean" }
        },
        "required": ["name", "price"]
      }
    }
  }
}
```

**Usage:**
```bash
conform product-catalog.pdf --schema product-schema.json
```

### Example 3: Extract Meeting Notes

**Schema (meeting-schema.json):**
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "date": {
      "type": "string",
      "format": "date"
    },
    "attendees": {
      "type": "array",
      "items": { "type": "string" }
    },
    "actionItems": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "task": { "type": "string" },
          "assignee": { "type": "string" },
          "dueDate": { "type": "string", "format": "date" }
        }
      }
    },
    "decisions": {
      "type": "array",
      "items": { "type": "string" }
    }
  }
}
```

**Usage:**
```bash
conform meeting-notes.txt --schema meeting-schema.json
```

## Common Workflows

### Workflow 1: Pipeline Composition (PREFERRED)

**Unix Way: Chain small tools together**

```bash
# Extract → filter → select → analyze
conform notes.txt --schema meeting-schema.json | \
  jq '.actionItems[]' | \
  jq 'select(.dueDate < "2026-02-15")' | \
  jq -r '[.task, .assignee] | @csv'

# Extract → transform → load into analysis tool
conform sales-report.pdf --schema sales-schema.json | \
  jq '.transactions[]' | \
  duckdb -c "SELECT category, SUM(amount) FROM stdin GROUP BY category"

# Extract → format → output
conform contact.txt --schema contact-schema.json | \
  jq -r '"\(.name),\(.email),\(.phone)"' | \
  xsv table
```

### Workflow 2: Silent Extraction (No File Output)

**Default: Write to stdout, compose with other tools**

```bash
# Good: stdout for composition
conform document.txt --schema schema.json | jq .

# Avoid: Unnecessary file writes
# Bad: conform document.txt --schema schema.json --output temp.json && cat temp.json | jq .
```

### Workflow 3: Batch Processing with Pipelines

```bash
# Process multiple files, compose with jq for aggregation
fd -e txt -x conform {} --schema schema.json | \
  jq -s 'map(.items) | flatten | group_by(.category) | length'

# OR: Use xargs for parallel processing
find data/ -name "*.txt" -print0 | \
  xargs -0 -P 4 -I {} conform {} --schema schema.json | \
  jq -s 'add'
```

### Workflow 4: Using with Ollama Local Model

```bash
# Ensure Ollama is running
ollama serve

# Use specific local model
conform input.txt \
  --schema schema.json \
  --provider ollama \
  --model llama3.2 \
  --ollama-endpoint http://localhost:11434
```

### Workflow 5: Using with Vertex AI

```bash
# Authenticate with GCP
gcloud auth application-default login

# Process with Vertex AI
conform input.txt \
  --schema schema.json \
  --provider vertex \
  --vertex-project my-gcp-project \
  --vertex-location us-central1 \
  --model gemini-1.5-pro
```

### Workflow 6: Iterative Schema Development

```bash
# Start with verbose mode to see what AI extracts
conform input.txt --schema schema.json --verbose

# Refine schema based on output
# Re-run until output matches expectations
conform input.txt --schema schema-v2.json --output final.json
```

## Best Practices

### 1. Default to stdout, Use --output Sparingly

```bash
# Good: Pipeline composition (Unix way)
conform data.txt --schema schema.json | jq .

# Avoid: Unnecessary file I/O
conform data.txt --schema schema.json --output temp.json

# Use --output ONLY for final results
conform data.txt --schema schema.json | jq '.items[]' --output final.json
```

### 2. Compose with Specialized Tools

```bash
# conform does extraction, jq does filtering, xsv does formatting
conform notes.txt --schema schema.json | \
  jq '.items[] | select(.priority == "high")' | \
  jq -r '@csv' | \
  xsv table

# Don't try to make conform do everything
```

### 3. Use Descriptive Schema Properties

```json
{
  "properties": {
    "email": {
      "type": "string",
      "format": "email",
      "description": "Primary email address for contact"
    }
  }
}
```

Descriptions help the AI understand extraction intent.

### 4. Set Appropriate Temperature

```bash
# Low temperature for factual extraction (default: 0.1)
conform data.txt --schema schema.json --temperature 0.1

# Higher temperature for creative interpretation
conform notes.txt --schema schema.json --temperature 0.5
```

### 5. Constrain Values with Enum

```json
{
  "properties": {
    "status": {
      "type": "string",
      "enum": ["pending", "approved", "rejected"]
    }
  }
}
```

### 6. Make Critical Fields Required

```json
{
  "required": ["id", "name", "email"]
}
```

### 7. Silent Success, Verbose Debugging

```bash
# Default: Silent on success, errors to stderr
conform input.txt --schema schema.json > output.json

# Debugging: Use --verbose to see processing
conform input.txt --schema schema.json --verbose

# Check exit codes in scripts
if conform input.txt --schema schema.json > result.json; then
  echo "Success"
else
  echo "Failed with exit code $?"
fi
```

### 8. Validate in Pipeline

```bash
# Validate while processing (don't break pipe)
conform input.txt --schema schema.json | tee result.json | jq empty
# jq empty validates JSON, exits non-zero on invalid

# Or validate schema compliance
conform input.txt --schema schema.json | ajv validate -s schema.json
```

## Provider Selection Guide

### Use Ollama When:

- Working with sensitive/private data (local processing)
- Need offline capability
- Have good local GPU/CPU resources
- Want to avoid cloud costs
- Testing and development

```bash
conform data.txt --schema schema.json --provider ollama
```

### Use Vertex AI When:

- Need maximum accuracy
- Processing large volumes
- Have GCP infrastructure
- Want latest models (Gemini)
- Production workloads

```bash
conform data.txt --schema schema.json \
  --provider vertex \
  --vertex-project prod-project
```

## Troubleshooting

### Issue: Ollama Connection Failed

**Check Ollama is running:**
```bash
curl http://localhost:11434/api/version
```

**Start Ollama:**
```bash
ollama serve
```

**Verify model is available:**
```bash
ollama list
ollama pull llama3.2  # If needed
```

### Issue: Schema Validation Errors

**Validate schema syntax:**
```bash
cat schema.json | jq .
```

**Ensure proper JSON Schema format:**
- Include `$schema` field
- Use correct property types
- Check required fields

### Issue: Poor Extraction Quality

**Solutions:**
1. **Add descriptions to schema properties**
2. **Use lower temperature** (0.0-0.2 for factual)
3. **Make schema more specific**
4. **Try different model**
5. **Preprocess input** (clean formatting)

### Issue: Vertex AI Authentication

**Setup authentication:**
```bash
# Application default credentials
gcloud auth application-default login

# Or use service account
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
```

### Issue: Output Not Valid JSON

**Debug with verbose:**
```bash
conform input.txt --schema schema.json --verbose
```

**Check input file encoding:**
```bash
file -I input.txt
```

## Advanced Usage

### Custom Ollama Endpoint

```bash
# Remote Ollama instance
conform input.txt --schema schema.json \
  --ollama-endpoint http://ollama-server:11434
```

### Schema with Nested Objects

```json
{
  "type": "object",
  "properties": {
    "company": {
      "type": "object",
      "properties": {
        "name": { "type": "string" },
        "employees": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "name": { "type": "string" },
              "role": { "type": "string" }
            }
          }
        }
      }
    }
  }
}
```

### Processing with jq

```bash
# Extract specific fields from conform output
conform data.txt --schema schema.json | jq '.products[] | select(.inStock)'

# Transform output
conform data.txt --schema schema.json | jq '{items: .products | length}'
```

### Tool Composition Patterns (Unix Philosophy)

**conform is the FIRST step in a pipeline, not the whole solution:**

```bash
# Pattern 1: Extract → Filter → Format → Save
conform data.txt --schema schema.json | \
  jq '.products[] | select(.inStock)' | \
  jq -r '[.name, .price] | @csv' > available.csv

# Pattern 2: Extract → Transform → Analyze
conform survey.pdf --schema survey-schema.json | \
  jq '.responses[]' | \
  duckdb -c "SELECT question, AVG(rating) FROM stdin GROUP BY question"

# Pattern 3: Extract → Multiple outputs (tee for branching)
conform data.txt --schema schema.json | tee \
  >(jq '.summary' > summary.json) \
  >(jq '.items[]' | xsv table > items.csv) \
  >/dev/null

# Pattern 4: Extract → Validate → Load
conform messy-data.txt --schema schema.json | \
  jq 'select(.email != null)' | \
  xlsx --from-json - --output clean-data.xlsx

# Pattern 5: Extract → Join with existing data
conform new-contacts.txt --schema contact-schema.json | \
  jq -r '@csv' | \
  xsv cat rows - existing-contacts.csv > all-contacts.csv
```

**Anti-pattern: Using --output when stdout works better**

```bash
# Bad: Extra file I/O, breaks composition
conform data.txt --schema schema.json --output temp.json
jq '.items[]' temp.json > filtered.json
rm temp.json

# Good: Direct pipeline composition
conform data.txt --schema schema.json | jq '.items[]' > filtered.json
```

## Quick Reference

**Unix Philosophy: compose with pipes, write to stdout by default**

```bash
# Basic usage (stdout by default)
conform input.txt --schema schema.json

# Pipeline composition (PREFERRED)
conform input.txt --schema schema.json | jq .
conform input.txt --schema schema.json | jq '.items[]' | xsv table
conform input.txt --schema schema.json | duckdb -c "SELECT * FROM stdin"

# Save final result (use sparingly)
conform input.txt --schema schema.json | jq '.filtered' > result.json

# Provider selection
conform input.txt --schema schema.json --provider ollama
conform input.txt --schema schema.json --provider vertex --vertex-project my-project

# Debugging (verbose to stderr, doesn't break pipeline)
conform input.txt --schema schema.json --verbose | jq .

# Batch processing with composition
fd -e txt -x conform {} --schema schema.json | jq -s 'add'
```

## Common Patterns (Unix Philosophy)

```bash
# Pattern 1: Extract and immediately process (no temp files)
conform notes.txt --schema meeting-schema.json | jq '.actionItems[]'

# Pattern 2: Batch process with aggregation
fd -e txt -x conform {} --schema schema.json | jq -s 'map(.items) | add'

# Pattern 3: Filter during extraction pipeline
conform data.txt --schema schema.json | \
  jq '.[] | select(.status == "active")' | \
  jq -r '@csv'

# Pattern 4: Conditional processing (check exit codes)
if conform input.txt --schema schema.json | jq empty; then
  conform input.txt --schema schema.json | jq '.summary'
else
  echo "Invalid data" >&2
  exit 1
fi

# Pattern 5: Multi-stage pipeline (conform → filter → transform → analyze)
conform sales.pdf --schema sales-schema.json | \
  jq '[.transactions[] | select(.amount > 1000)]' | \
  duckdb -c "SELECT category, SUM(amount) FROM stdin GROUP BY category"

# Pattern 6: Split output to multiple destinations
conform data.txt --schema schema.json | tee \
  >(jq '.errors' > errors.json) \
  >(jq '.valid[]' | xsv table > valid.csv)
```

## Summary

**Primary directive**: Use `conform` to transform unstructured data into schema-validated JSON using AI. Follow Unix philosophy: do one thing well, compose with other tools.

**Unix Philosophy Principles**:
- **Do one thing**: Extract unstructured → structured. Don't analyze, format, or store.
- **Text streams**: Write JSON to stdout, compose with pipes
- **Composition**: conform | jq | xsv (not conform --everything)
- **Silent success**: Quiet output unless --verbose specified
- **Tool hierarchy**: Prefer grep/jq/xsv for structured data, use conform ONLY for unstructured

**Most common usage (Unix way)**:
```bash
# Good: Pipeline composition
conform input.txt --schema schema.json | jq .

# Avoid: Unnecessary file I/O
conform input.txt --schema schema.json --output result.json
```

**Best practices**:
- Default to stdout, use --output sparingly
- Compose with jq, xsv, duckdb for downstream processing
- Use descriptive schema properties
- Set low temperature for factual extraction (0.1)
- Check exit codes in scripts
- Use Ollama for local/sensitive data, Vertex AI for production

**When NOT to use conform**:
- Input is already structured (use jq, xsv, xlsx instead)
- Simple pattern matching (use grep, sed, awk)
- No AI interpretation needed (use deterministic tools)
