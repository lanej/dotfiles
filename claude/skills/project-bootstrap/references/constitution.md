# Project Constitution

A constitution states the principles a project will not trade away, each with a rationale tied to that project's actual constraints. It earns its place only if it constrains real decisions — prefer 4 principles the team enforces over 10 aspirational ones.

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

For the code-generation patterns referenced above, see [contract-codegen.md](contract-codegen.md).

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

7. **Write the constitution**: save it to `CONSTITUTION.md` at the repo root (or `docs/CONSTITUTION.md` if the repo keeps docs in a subdirectory). Start at version 1.0.0 and record the ratification date.

**Remember**: The constitution should feel essential, not bureaucratic. Only include principles that have clear, project-specific justifications.
