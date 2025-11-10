# Bootstrap New Project

Complete project setup: install speckit and create a tailored constitution using universal best practices.

## Instructions

You are helping bootstrap a new project. Follow these steps in order:

### Step 1: Install Speckit

**Check if speckit is already installed in this project**:
- Look for `.specify/` directory in the current project
- Check for `.specify/templates/` with plan-template.md, spec-template.md, tasks-template.md

**If .specify/ directory already exists**:
- Inform user: "✓ Speckit is already installed in this project"
- Proceed to Step 2

**If .specify/ directory does NOT exist**:

1. Check if `specify` command is available on the system:
   ```bash
   command -v specify
   ```

2. **If `specify` command exists** (preferred method):
   - Inform user: "Initializing speckit framework..."
   - Run: `specify init --ai claude .`
   - Confirm installation: "✓ Speckit initialized successfully in .specify/"

3. **If `specify` command does NOT exist** (fallback method):
   - Inform user: "Installing speckit framework from GitHub..."
   - Run the speckit installation:
     ```bash
     git clone https://github.com/github/spec-kit.git /tmp/speckit-temp
     cp -r /tmp/speckit-temp/.specify .
     rm -rf /tmp/speckit-temp
     ```
   - Confirm installation: "✓ Speckit installed successfully in .specify/"
   - Suggest: "Tip: Install speckit globally with `npm install -g @github/spec-kit` for easier project initialization"

4. Proceed to Step 2

### Step 2: Initialize Git Repository

**Check if git is already initialized**:
```bash
git rev-parse --git-dir 2>/dev/null
```

**If git is NOT initialized**:
1. Inform user: "Initializing git repository..."
2. Run: `git init`
3. Create initial .gitignore based on language (if one doesn't exist)
4. Confirm: "✓ Git repository initialized"

**If git IS initialized**:
- Inform user: "✓ Git repository already initialized"
- Proceed to Step 3

### Step 3: Create Project Constitution

1. **Ask clarifying questions** about the project (see questions below)
2. **Synthesize a constitution** based on universal practices + project-specific needs
3. **Use `/speckit.constitution [short-name]`** to generate and save the constitution file

### Step 4: Install Pre-Commit Hooks

After constitution is created and language is known, install language-specific pre-commit hooks.

**Create `.git/hooks/pre-commit`** with executable permissions:

**For Rust projects**:
```bash
#!/bin/sh
# Pre-commit hook for Rust projects

echo "Running pre-commit checks..."

# Format check
echo "→ Checking code formatting..."
if ! cargo fmt --check; then
    echo "❌ Code formatting issues found. Run: cargo fmt"
    exit 1
fi

# Clippy check
echo "→ Running clippy..."
if ! cargo clippy --all-targets --all-features -- -D warnings; then
    echo "❌ Clippy warnings found. Run: cargo clippy --fix --allow-dirty"
    exit 1
fi

# Build check
echo "→ Building project..."
if ! cargo build --quiet; then
    echo "❌ Build failed"
    exit 1
fi

# Fast tests (unit tests only)
echo "→ Running unit tests..."
if ! cargo test --lib --quiet; then
    echo "❌ Unit tests failed"
    exit 1
fi

echo "✓ All pre-commit checks passed"
```

**For Go projects**:
```bash
#!/bin/sh
# Pre-commit hook for Go projects

echo "Running pre-commit checks..."

# Format check
echo "→ Checking code formatting..."
if [ -n "$(gofmt -l .)" ]; then
    echo "❌ Code formatting issues found. Run: gofmt -w ."
    exit 1
fi

# Vet check
echo "→ Running go vet..."
if ! go vet ./...; then
    echo "❌ Go vet found issues"
    exit 1
fi

# Build check
echo "→ Building project..."
if ! go build ./...; then
    echo "❌ Build failed"
    exit 1
fi

# Fast tests
echo "→ Running tests..."
if ! go test -short ./...; then
    echo "❌ Tests failed"
    exit 1
fi

echo "✓ All pre-commit checks passed"
```

**For TypeScript/Node projects**:
```bash
#!/bin/sh
# Pre-commit hook for TypeScript/Node projects

echo "Running pre-commit checks..."

# Format check
echo "→ Checking code formatting..."
if ! npm run format:check 2>/dev/null && ! npx prettier --check . 2>/dev/null; then
    echo "❌ Code formatting issues found. Run: npm run format or npx prettier --write ."
    exit 1
fi

# Lint check
echo "→ Running linter..."
if ! npm run lint 2>/dev/null && ! npx eslint . 2>/dev/null; then
    echo "❌ Linting issues found"
    exit 1
fi

# Type check
echo "→ Running type check..."
if ! npm run type-check 2>/dev/null && ! npx tsc --noEmit 2>/dev/null; then
    echo "❌ Type check failed"
    exit 1
fi

# Build check
echo "→ Building project..."
if ! npm run build 2>/dev/null; then
    echo "⚠ Build script not found or failed (optional)"
fi

# Fast tests
echo "→ Running tests..."
if npm run test:unit 2>/dev/null || npm test 2>/dev/null; then
    echo "✓ Tests passed"
else
    echo "⚠ Tests not configured or failed (optional)"
fi

echo "✓ All pre-commit checks passed"
```

**For Python projects**:
```bash
#!/bin/sh
# Pre-commit hook for Python projects

echo "Running pre-commit checks..."

# Format check
echo "→ Checking code formatting..."
if ! black --check . 2>/dev/null && ! ruff format --check . 2>/dev/null; then
    echo "❌ Code formatting issues found. Run: black . or ruff format ."
    exit 1
fi

# Lint check
echo "→ Running linter..."
if ! ruff check . 2>/dev/null && ! flake8 . 2>/dev/null; then
    echo "❌ Linting issues found"
    exit 1
fi

# Type check
echo "→ Running type check..."
if ! mypy . 2>/dev/null && ! pyright . 2>/dev/null; then
    echo "⚠ Type check not configured or failed (optional)"
fi

# Fast tests
echo "→ Running tests..."
if pytest tests/ -k "not integration" 2>/dev/null || python -m pytest tests/ 2>/dev/null; then
    echo "✓ Tests passed"
else
    echo "⚠ Tests not configured or failed (optional)"
fi

echo "✓ All pre-commit checks passed"
```

**Installation steps**:
1. Create the appropriate pre-commit hook based on detected language
2. Make it executable: `chmod +x .git/hooks/pre-commit`
3. Confirm: "✓ Pre-commit hooks installed"
4. Inform user: "Pre-commit hook will run format checks, linting, build verification, and fast tests before each commit"

**Note on dependency checks**:
Dependency audits are too slow for pre-commit hooks (10-30 seconds). Instead, recommend adding to Justfile for periodic checks:

**Rust**: `just check-deps` → `cargo outdated && cargo audit`
**Go**: `just check-deps` → `go list -u -m all`
**TypeScript**: `just check-deps` → `npm outdated && npm audit`
**Python**: `just check-deps` → `pip list --outdated && safety check`

Suggest running weekly or before releases, not on every commit.

## Project Context Questions

Ask the user these questions to understand the project:

1. **Project Type**: What kind of project is this?
   - Library (reusable code package)
   - CLI tool (command-line interface)
   - Server (API, MCP server, web service)
   - Data pipeline (ETL, analytics, reporting)
   - Infrastructure (Terraform, deployment automation)

2. **Language/Tech Stack**: What language are you using?
   - Rust, Go, TypeScript, Python, etc.

3. **API Integration**: Does this project integrate with external APIs?
   - If yes: Are OpenAPI specs or protobuf definitions available for those APIs?
   - If yes: Can authentication be delegated to a trusted system (gcloud, OAuth providers)?

4. **Performance Criticality**:
   - Correctness-critical (financial, medical, legal)
   - Performance-critical (real-time, high-throughput)
   - Standard (typical application performance)

5. **Interface Model**:
   - Single interface (library, CLI, server)
   - Multiple interfaces (CLI + MCP, CLI + library, etc.)

6. **Security Requirements**:
   - Handles sensitive data? (yes/no)
   - Requires audit logging? (yes/no)

## Universal Principles (Select 4-6 based on project)

### Testing & Quality
- **Test-Driven Development (NON-NEGOTIABLE)**: Red-Green-Refactor cycle, tests before implementation, coverage ≥80%
- **Type Safety**: Leverage language type system, strict checking, no escape hatches (any, interface{})
- **Error Handling**: User-actionable messages (what/why/how-to-fix), exit codes, recovery guidance
- **Code Quality Gates**: Format enforcement, linting, build warnings as errors, no compiler warnings

### Contract-Driven Development (API Integrations)
- **When to Use**: Integrating with external APIs, type safety critical, frequent contract changes
- **Core Patterns**: TypeSpec→OpenAPI→Progenitor (Rust), OpenAPI+Overlays→Progenitor (Rust), OpenAPI+Overlays→Ogen (Go)
- **See detailed patterns below** for complete workflows, overlay examples, and Justfile automation

### Contract-Driven Development: Code Generation Patterns

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

### Architecture & Design
- **Separation of Concerns**: Clear module boundaries, single responsibility, no circular dependencies
- **Simplicity First**: YAGNI, avoid premature optimization, document complexity justifications

### Security & Operations
- **Authentication Transparency**: Delegate to trusted systems (gcloud, OAuth), zero credential storage in codebase
- **Audit & Logging**: Structured logs, security event tracking, data sanitization (no credentials in logs)
- **Infrastructure as Code**: All infrastructure defined in code (Terraform, Pulumi), no manual changes

### Documentation
- **Documentation Standards**: README for users, CLAUDE.md for AI/developers, inline docs for public APIs
- **Breaking Changes**: Update docs before merge, migration guides for major versions

## Domain-Specific Principles (Add 1-3 based on project type)

### For Libraries
- **API Stability**: Semantic versioning strictly enforced, deprecation cycles, backward compatibility
- **Performance Discipline**: Benchmarks required, zero-allocation hot paths, profiling before optimization
- **Minimal Dependencies**: Justify each dependency, prefer focused crates over frameworks

### For CLI Tools
- **Multiple Output Formats**: JSON (machine), table (human), quiet mode
- **Environment Precedence**: CLI flags > env vars > config files > defaults
- **User-Friendly Errors**: No stack traces, provide exact commands to fix issues

### For MCP Servers
- **MCP Protocol Compliance**: Strict adherence to MCP spec, stdio + HTTP transports
- **Token Efficiency**: Minimize LLM context usage, compact schemas, pagination, smart defaults
- **Dual-Mode Parity**: All features available in both CLI and MCP modes (document exceptions)

### For Data Pipelines
- **Schema-First Design**: Schemas in version control, validation before load, explicit types
- **Data Quality Over Speed**: Audit trails, statistical outlier handling, idempotent operations
- **Source Transparency**: All data must identify source platform/system

### For Performance-Critical Projects
- **Performance-First Design**: Benchmarks mandatory, regressions require justification with benchstat
- **Correctness Over Speed**: Valid solutions before optimization, comprehensive testing required
- **Zero-Allocation Paths**: Hot paths avoid allocations, profiling required before optimization

### For Infrastructure Projects
- **Infrastructure as Code (NON-NEGOTIABLE)**: All changes via Terraform/Pulumi, no manual fixes
- **Systematic Verification**: Test across all instances, no spot checks
- **Incremental Deployment**: Test on single instance first, staged rollout with rollback capability

## Development Workflow Practices

### Justfile Automation
Standard recipes to include:
```justfile
# Testing
test:
    [test-command]  # e.g., cargo test, npm test, go test

# Code quality
fmt:
    [format-command]  # e.g., cargo fmt, prettier --write ., black .

lint:
    [lint-command]  # e.g., cargo clippy -- -D warnings, eslint .

# Building
build:
    [build-command]  # e.g., cargo build --release, npm run build

# Dependencies
check-deps:
    [deps-command]  # e.g., cargo outdated, npm outdated

# Code generation (if applicable)
generate:
    [generate-command]  # e.g., just generate-openapi && just generate-client

# Convenience
pre-commit:
    just fmt && just lint && just test
```

### Pre-Commit Hooks
Recommended checks (select based on project):
- **Format enforcement**: Auto-format code or block commit if not formatted
- **Lint check**: Block commits with linting errors
- **Fast tests**: Unit tests only (<5 seconds), not integration tests
- **Build warnings**: Ensure code compiles without warnings
- **Dependency audit**: Check for security vulnerabilities (can be slow, make optional)

Example pre-commit hook:
```bash
#!/bin/sh
# Format check
[format-check-command] || exit 1

# Lint check
[lint-command] || exit 1

# Fast unit tests
[fast-test-command] || exit 1
```

### Quality Gates

**Pre-Commit Gates**:
1. Format check passes
2. Lint check passes with zero warnings
3. Fast unit tests pass (<5 seconds)
4. Build succeeds without warnings

**Pre-Release Gates**:
1. All pre-commit gates pass
2. Full test suite passes (unit + integration)
3. Benchmark validation (no regressions, if applicable)
4. Documentation updated (README, CHANGELOG)
5. Security audit passes (no critical vulnerabilities)

## Anti-Patterns to Avoid

❌ **Don't mandate specific file structures** unless project already established them
❌ **Don't include implementation details** (class names, method signatures)
❌ **Don't exceed 7 core principles** (cognitive overload)
❌ **Don't copy-paste without context** (each principle needs project-specific rationale)
❌ **Don't include irrelevant principles** (e.g., "MCP Protocol Compliance" for a library)

## Constitution Structure Template

After gathering context, use this structure:

```markdown
# [PROJECT_NAME] Constitution

## Core Principles

### I. [Most Critical Principle - often TDD or Type Safety]
**Description**: [1-2 sentences]

**Rules**:
- [Specific, testable rule]
- [Specific, testable rule]
- [Specific, testable rule]

**Rationale**: [Why this matters for THIS project specifically]

### II. [Contract-Driven Development - if API integration project]
**Description**: ALL API integrations MUST use official specifications (OpenAPI, protobuf) with generated type-safe clients.

**Rules**:
- Contract files (OpenAPI/TypeSpec) versioned in `contracts/` or `specs/` directory
- Generated clients in `src/generated/` or `internal/{service}/` with custom wrappers for business logic
- Generated code MUST NOT be manually edited (regenerate from updated contracts instead)
- Overlays MAY be used to fix upstream spec issues (pattern: `{service}-overlay.{json|yaml}`)
- Code generation via Justfile commands (`just generate-all`, `just generate-client`)
- **Rust Projects**: Use Progenitor for OpenAPI → Rust client generation
- **Go Projects**: Use Ogen for OpenAPI → Go client generation
- **TypeSpec Projects**: TypeSpec → OpenAPI → client generation pipeline

**Rationale**: [Project-specific - e.g., "Google Drive API is complex and evolves frequently. Contract-driven development ensures type safety, catches breaking changes at compile time, and reduces manual serialization errors by 80%."]

### III-VI. [Additional Universal + Domain Principles]
[Same structure as above - TDD, Type Safety, Error Handling, etc.]

## Development Standards

### Quality Gates
**Pre-commit**:
- [Format, lint, fast tests]

**Pre-release**:
- [Full tests, benchmarks, docs, security]

### Automation (Justfile)
- `just test` - [Description]
- `just fmt` - [Description]
- `just lint` - [Description]
- `just build` - [Description]
- `just generate-all` - [Regenerate all code from contracts, if contract-driven project]
- `just generate-openapi` - [TypeSpec → OpenAPI generation, if using TypeSpec]
- `just generate-client` - [OpenAPI → client generation (Progenitor/Ogen)]
- `just merge-spec` - [Merge base spec + overlay, if using overlays]

### Pre-Commit Hooks
[Recommended checks based on project type]

## Governance

### Amendment Process
Constitutional changes require:
1. Documented rationale (why change is needed)
2. Impact analysis on existing features
3. Migration plan for breaking changes
4. Version bump per semantic versioning

### Version Semantics
- **MAJOR**: Breaking changes to principles, API breaking changes
- **MINOR**: New principles added, expanded guidance, new features
- **PATCH**: Clarifications, documentation improvements, typo fixes

### Compliance Verification
**All code changes MUST**:
- [List non-negotiable principles here]

**Code reviews MUST verify**:
- [Key review criteria based on principles]

---

**Version**: 1.0.0 | **Ratified**: [DATE] | **Last Amended**: [DATE]
```

## Constitution Generation Workflow

After gathering project context from the user:

1. **Evaluate API integration needs**:
   - If yes to "Does this project integrate with external APIs?"
   - AND yes to "Are OpenAPI specs or protobuf definitions available?"
   - → Strongly recommend Contract-Driven Development as a core principle (usually Principle II or III)

2. **Select universal principles** (4-6 total):
   - Test-Driven Development (almost always included)
   - Type Safety (for typed languages)
   - Error Handling (user-facing tools)
   - Contract-Driven Development (if API integration)
   - Authentication Transparency (if handles auth)
   - Documentation Standards (complex projects)

3. **Add domain-specific principles** (1-3 total):
   - Performance-First (libraries, real-time systems)
   - MCP Protocol Compliance (MCP servers)
   - Data Quality Over Speed (data pipelines)
   - Infrastructure as Code (infrastructure projects)

4. **Choose code generation pattern** (if Contract-Driven Development included):
   - **Rust** → Progenitor (OpenAPI → Rust client)
   - **Go** → Ogen (OpenAPI → Go client)
   - **TypeScript** → TypeSpec→OpenAPI or openapi-typescript
   - **Python** → datamodel-code-generator or similar

5. **Specify automation commands**:
   - Always: `test`, `fmt`, `lint`, `build`
   - Contract-driven: `generate-all`, `generate-client`, `merge-spec`
   - Pre-commit hooks based on language ecosystem

6. **Write project-specific rationales**:
   - Each principle MUST have a clear "if we violate this, bad things happen" statement
   - Rationale should reference the specific project type and constraints

7. **Generate constitution**: Use `/speckit.constitution [short-name]`

**Remember**: The constitution should feel essential, not bureaucratic. Only include principles that have clear, project-specific justifications.

## Final Summary

After completing all steps, provide a clear summary:

```
✓ Project bootstrap complete!

**What was set up**:
1. Speckit framework in .specify/
   - Templates: plan-template.md, spec-template.md, tasks-template.md
   - Constitution: .specify/memory/constitution.md (v1.0.0)

2. Git repository initialized (if not already present)
   - .gitignore created for [language]

3. Pre-commit hooks installed
   - Format checking ([language-specific formatter])
   - Linting ([language-specific linter])
   - Build verification
   - Fast unit tests
   - [Clippy for Rust / go vet for Go / type checking for TypeScript/Python]

**Your project constitution includes**:
- [List the principles that were selected, e.g.:]
  - Test-Driven Development (NON-NEGOTIABLE)
  - Contract-Driven Development (OpenAPI → [Progenitor/Ogen])
  - Type Safety & Validation
  - Error Handling with User Guidance
  - [Authentication Transparency / MCP Protocol Compliance / etc.]

**Pre-commit hook behavior**:
Every commit will automatically run:
- Format checks (blocks commit if not formatted)
- Lint checks (blocks commit if warnings present)
- Build verification (blocks commit if build fails)
- Fast unit tests (blocks commit if tests fail)

To bypass temporarily (not recommended): git commit --no-verify

**Next steps**:
1. Review the constitution: .specify/memory/constitution.md
2. Make initial commit: git add . && git commit -m "Initial project setup with speckit"
3. Start your first feature: /speckit.specify [feature-name]
4. Generate implementation plan: /speckit.plan
5. Create task breakdown: /speckit.tasks

**Available speckit commands**:
- /speckit.specify - Create feature specification
- /speckit.plan - Generate implementation plan
- /speckit.tasks - Break down into tasks
- /speckit.implement - Execute the implementation
- /speckit.constitution - Update constitution (if needed)

For more help: https://github.com/github/spec-kit
```
