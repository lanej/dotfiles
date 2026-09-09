# Contract-Driven Code Generation

When a project integrates with an external API that publishes a spec, generate the client instead of hand-writing it — a generated client stays correct as the upstream spec moves, and the diff on regeneration shows exactly what changed.

## Patterns

**When to use Contract-Driven Development**:
- Project integrates with external APIs (Google, JIRA, Phabricator, etc.)
- Type safety critical for preventing API misuse
- API contracts change frequently and need automated tracking
- Generated code reduces manual serialization errors by 80-90%

**Three Code Generation Patterns** (based on your existing projects):

**Pattern 1: TypeSpec → OpenAPI → Progenitor (Rust)**
- **Used in**: phab-mcp
- **Workflow**: Define schema in TypeSpec → Generate OpenAPI → Generate Rust client via Progenitor
- **Benefits**: Single source of truth in TypeSpec, full type safety, automatic client regeneration
- **File Structure**:
  ```
  main.tsp                      # TypeSpec schema (ONLY edit this)
  ↓ just generate-openapi
  specs/openapi.yaml            # Generated OpenAPI (DO NOT EDIT)
  ↓ just generate-client
  src/{service}/generated/      # Generated Rust client (DO NOT EDIT)
  src/{service}/client.rs       # Custom wrapper for business logic
  ```

**Pattern 2: OpenAPI with Overlays → Progenitor (Rust)**
- **Used in**: gdrive-mcp
- **Workflow**: Fetch Google Discovery Document → Convert to OpenAPI → Apply overlays → Generate Rust client
- **Benefits**: Handles spec imperfections, fixes upstream issues, patches missing features
- **File Structure**:
  ```
  specs/{service}-base.json           # Base OpenAPI from upstream
  specs/{service}-overlay.json        # Your fixes/extensions
  ↓ merge (yq eval-all)
  specs/{service}-openapi.json        # Merged final spec
  ↓ progenitor-client
  src/{service}/generated/            # Generated Rust types
  ```
- **Overlay Use Cases**:
  - Fix incorrect field types (e.g., `string` → `object`)
  - Add missing required fields
  - Remove invalid paths
  - Rename conflicting schemas

**Pattern 3: OpenAPI with Overlays → Ogen (Go)**
- **Used in**: terraform-provider-jira
- **Workflow**: Fetch JIRA OpenAPI → Apply ogen-specific overlays → Merge → Generate Go client
- **Benefits**: Handles Go-specific naming conflicts, removes OpenAPI 3.0 violations
- **File Structure**:
  ```
  contracts/{service}-base.yaml          # Upstream OpenAPI spec
  contracts/{service}-ogen-overlay.yaml  # Ogen compatibility fixes
  ↓ merge-{service}-ogen-spec.sh (yq)
  contracts/{service}-ogen-merged.yaml   # Merged spec
  ↓ ogen --config contracts/ogen.yml
  internal/{service}/                    # Generated Go client
  ```
- **Ogen-Specific Overlays**:
  - Rename schemas conflicting with Go package names (e.g., `Fields` → `JiraFields`)
  - Remove invalid type constraints (minLength on arrays, etc.)
  - Delete null paths marked in overlay

**Justfile Automation for Contract-Driven Development**:
```justfile
# Fetch upstream spec (if external API)
fetch-spec:
    curl -o specs/{service}-base.json https://api.example.com/openapi.json

# Generate OpenAPI from TypeSpec (if using TypeSpec)
generate-openapi:
    tsp compile main.tsp
    # Output: docs/openapi.yaml

# Merge base spec with overlay
merge-spec:
    yq eval-all '. as $item ireduce ({}; . * $item)' \
      specs/{service}-base.yaml \
      specs/{service}-overlay.yaml \
      > specs/{service}-merged.yaml

# Generate Rust client (Progenitor)
generate-client-rust:
    progenitor-client \
      --input specs/{service}-merged.yaml \
      --output src/{service}/generated/

# Generate Go client (Ogen)
generate-client-go:
    ogen --config contracts/ogen.yml \
      --target internal/{service} \
      --package {service} \
      --clean contracts/{service}-ogen-merged.yaml

# Full pipeline (all steps)
generate-all:
    just generate-openapi  # or fetch-spec
    just merge-spec        # if using overlays
    just generate-client-rust  # or generate-client-go
```

**Critical Rules for Generated Code**:
1. **NEVER** manually edit generated files
2. **ALWAYS** fix source schema (TypeSpec/OpenAPI), then regenerate
3. **DO** create custom wrappers in `src/{service}/client.rs` for business logic
4. **DO** use overlays to fix upstream spec issues (don't fork entire spec)
5. **DO** version contract files in git (specs/, contracts/ directories)

**Overlay Creation Guide** (when upstream specs have issues):

**Rust/Progenitor Overlays** (`specs/{service}-overlay.json`):
```json
{
  "paths": {
    "/broken-endpoint": null,  // Delete problematic endpoints
  },
  "components": {
    "schemas": {
      "BrokenSchema": {
        "properties": {
          "incorrectField": {
            "type": "object",  // Fix: was "string", actually object
            "properties": {
              "nestedField": {"type": "string"}
            }
          }
        }
      }
    }
  }
}
```

**Go/Ogen Overlays** (`contracts/{service}-ogen-overlay.yaml`):
```yaml
components:
  schemas:
    # Rename conflicting schema
    JiraFields:
      $ref: '#/components/schemas/Fields'
```

**Overlay Merge Script** (using `yq`):
```bash
#!/bin/bash
# Merge base spec with overlay
yq eval-all '. as $item ireduce ({}; . * $item)' \
  specs/base.yaml \
  specs/overlay.yaml \
  > specs/merged.yaml

# Post-process: Remove null paths, fix constraints
yq eval '
  .paths |= with_entries(select(.value != null)) |
  (.. | select(.type == "array")) |= del(.minLength, .maxLength)
' specs/merged.yaml > specs/final.yaml
```

**When NOT to use Contract-Driven Development**:
- Simple REST APIs with 1-2 endpoints (manual client is simpler)
- Internal APIs you control (can change contract and code together)
- Prototyping phase (contracts add overhead during rapid iteration)
- APIs without OpenAPI/protobuf specs available

