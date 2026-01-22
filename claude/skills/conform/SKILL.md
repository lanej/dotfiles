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

### Workflow 1: Extract Data from Document

```bash
# 1. Create JSON schema for desired structure
cat > schema.json << 'EOF'
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "title": { "type": "string" },
    "date": { "type": "string" },
    "summary": { "type": "string" }
  }
}
EOF

# 2. Run conform
conform document.txt --schema schema.json --output result.json

# 3. Verify output
cat result.json | jq .
```

### Workflow 2: Batch Processing

```bash
# Process multiple files with same schema
for file in data/*.txt; do
  output="results/$(basename "$file" .txt).json"
  conform "$file" --schema schema.json --output "$output"
done
```

### Workflow 3: Pipeline Integration

```bash
# Download, process, and analyze
curl https://example.com/data.txt -o input.txt
conform input.txt --schema schema.json | jq '.items | length'
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

### 1. Use Descriptive Schema Properties

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

### 2. Set Appropriate Temperature

```bash
# Low temperature for factual extraction (default: 0.1)
conform data.txt --schema schema.json --temperature 0.1

# Higher temperature for creative interpretation
conform notes.txt --schema schema.json --temperature 0.5
```

### 3. Use Enum for Constrained Values

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

### 4. Make Critical Fields Required

```json
{
  "required": ["id", "name", "email"]
}
```

### 5. Use Verbose Mode for Debugging

```bash
# See detailed processing steps
conform input.txt --schema schema.json --verbose
```

### 6. Validate Output

```bash
# Always validate with jq or schema validator
conform input.txt --schema schema.json | jq .

# Or use a JSON schema validator
conform input.txt --schema schema.json --output result.json
ajv validate -s schema.json -d result.json
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

### Integration with Other Tools

```bash
# Conform → jq → CSV
conform data.txt --schema schema.json | \
  jq -r '.products[] | [.name, .price] | @csv' > output.csv

# Conform → xlsx
conform data.txt --schema schema.json | \
  xlsx --from-json - --output data.xlsx
```

## Quick Reference

```bash
# Basic usage
conform input.txt --schema schema.json

# With output file
conform input.txt --schema schema.json --output result.json

# Ollama with specific model
conform input.txt --schema schema.json \
  --provider ollama --model llama3.2

# Vertex AI
conform input.txt --schema schema.json \
  --provider vertex --vertex-project my-project

# Verbose debugging
conform input.txt --schema schema.json --verbose

# Pipeline usage
conform input.txt --schema schema.json | jq .
```

## Common Patterns

```bash
# Pattern 1: Extract structured data from unstructured text
conform notes.txt --schema meeting-schema.json

# Pattern 2: Batch process directory
fd -e txt -x conform {} --schema schema.json --output results/{/.}.json

# Pattern 3: Validate and format output
conform data.txt --schema schema.json | jq . > formatted.json

# Pattern 4: Use in scripts
if conform input.txt --schema schema.json --output result.json; then
  echo "Successfully extracted data"
  cat result.json | jq .
else
  echo "Extraction failed"
fi
```

## Summary

**Primary directive**: Use `conform` to transform unstructured data into schema-validated JSON using AI.

**Key advantages**:
- Schema-driven extraction ensures consistent structure
- Multiple AI provider support (local and cloud)
- Simple CLI interface
- Guaranteed JSON Schema conformance

**Most common usage**:
```bash
conform input.txt --schema schema.json --output result.json
```

**Best practices**:
- Use descriptive schema properties
- Set low temperature for factual extraction
- Always validate output with jq
- Use Ollama for local/sensitive data, Vertex AI for production
