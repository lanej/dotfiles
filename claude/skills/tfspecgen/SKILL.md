---
name: tfspecgen
description: "Config-driven CLI that generates Terraform Plugin Framework provider CRUD resource/data-source Go code from a vendor's OpenAPI/Swagger spec via an ogen-generated API client. Use when: (1) a repo has or needs a tfspecgen.yaml or ogen_introspection.json file; (2) fetching, converting, merging, pruning, or filtering an OpenAPI/Swagger spec for Terraform code generation via tfspecgen; (3) generating or regenerating an ogen client or CRUD resource/data-source code via tfspecgen; (4) debugging a missing field on a Connection struct, a tfspecgen fatalf, or anything mentioning connection_field, a fields selector, or query_param_fields. Do NOT trigger for hand-written Terraform provider code unrelated to tfspecgen, generic non-Terraform OpenAPI tooling, or the separate tfplugingen-openapi/tfplugingen-framework reference pipeline some repos keep independently."
---

# tfspecgen — Terraform Provider CRUD Generator

Config-driven CLI that turns a vendor's OpenAPI/Swagger spec into a Terraform Plugin Framework
provider's CRUD resource/data-source Go code, via an `ogen`-generated API client. Installed as a
global binary (`go install github.com/easypost-sandbox/tfspecgen@latest`) and run from inside a
*consuming* Terraform provider repo (e.g. `terraform-provider-paylocity`) — this skill's own source
repo is normally not checked out where you're working. Full schema/flag/boundary detail lives in
`references/codegen.md`; read it before authoring a new `tfspecgen.yaml` resource/data-source entry
or debugging a generation failure.

## Prerequisites

Three external binaries must be on `PATH` (not vendored or version-pinned by tfspecgen itself):

| Binary | Used by | Install | Verified version |
|---|---|---|---|
| `ogen` | `client` | `go install github.com/ogen-go/ogen/cmd/ogen@latest` | v1.18.0 |
| `yq` (mikefarah/yq) | `merge`, and the bundled `prune`/`filter` scripts | `brew install yq` | v4.53.6 |
| `swagger2openapi` | `convert` | `npm install -g swagger2openapi` | 7.0.8 |

`ogen` is also a separate **library** dependency of the *generated client's* consuming repo (its
`go.mod` pins `github.com/ogen-go/ogen`) — that can be a different version than the CLI binary;
only the CLI binary matters for `tfspecgen client`.

## Install

```sh
go install github.com/easypost-sandbox/tfspecgen@latest
```

## Quickstart

One-shot, given a `tfspecgen.yaml` at the provider repo's root:

```sh
cd terraform-provider-<vendor>
tfspecgen build -config tfspecgen.yaml
```

Or stage-by-stage (keeps every intermediate artifact inspectable):

```sh
tfspecgen fetch      -url <spec-url> -out contracts/source.json
tfspecgen convert    -in contracts/source.json -out contracts/v3.yaml       # swagger2 only
tfspecgen merge      -base contracts/v3.yaml -overlay contracts/overlay.yaml -out contracts/merged.yaml
tfspecgen prune      -spec contracts/merged.yaml -allowlist contracts/scope.yaml -out contracts/pruned.yaml -schema <schema>
tfspecgen filter     -spec contracts/pruned.yaml -safelist contracts/safelist.txt -out contracts/filtered.yaml
tfspecgen client     -spec contracts/filtered.yaml -target internal/<pkg> -package <pkg> -config contracts/ogen.yml
tfspecgen introspect -src internal/<pkg> -out generated/ogen_introspection.json
tfspecgen generate   -config tfspecgen.yaml -intro generated/ogen_introspection.json -out internal/resources
```

`introspect`/`generate`'s flat-mode flags default to Paylocity-shaped relative paths (a holdover
from before these were merged into one CLI) — always pass explicit paths from a provider repo's
root.

## Subcommands

9 subcommands; `build` is a convenience wrapper, not an independent stage. Every stage is plain
file-in/file-out — nothing implicit or cached between invocations.

| Subcommand | Does |
|---|---|
| `fetch` | Downloads the vendor's OpenAPI/Swagger spec (`-url`, `-out`) |
| `convert` | Swagger 2.0 → OpenAPI 3.x (`-in`, `-out`) — skip if the spec is already OpenAPI 3 |
| `merge` | Merges an overlay spec onto a base spec (`-base`, `-overlay`, `-out`) |
| `prune` | Applies one schema's include/exclude field selector (`-spec`, `-allowlist`, `-out`, `-schema`) |
| `filter` | Filters a spec to a path safelist (`-spec`, `-safelist`, `-out`) |
| `client` | Runs `ogen` to generate the API client (`-spec`, `-target`, `-package`, `-config`) |
| `introspect` | Parses the generated client's Go source into `ogen_introspection.json` (`-src`, `-out`) |
| `generate` | Renders CRUD resource/data-source `.go` files (`-config`, or flat-mode flags, plus `-intro`/`-out`) |
| `build` | Chains all of the above, stopping on first failure |

**`build -config` only builds one source's spec chain per invocation** — it runs the named
`-source`'s (or the sole source's) `fetch → ... → client` chain, then `generate` across **every**
resource/data source in the whole config, not just that source's own. For a multi-source provider:
run `build -source <name>` once per source, then one final `build -source <any-one>` (or a bare
`generate -config`) once all clients exist. Multi-source routing is implemented but has **not**
been validated against a real multi-spec vendor — treat it as unproven until one exercises it.

## The `connection_field` contract

Generated code calls `r.conn.<ConnectionField>.<Op>(...)`. `<ConnectionField>` is **not
generated** — it must already exist as a hand-written field on the consuming repo's own
`*client.Connection` struct, holding that source's `ogen`-generated client type (Paylocity's
single-source case: `Connection.Client *paylocity.Client` pairs with `connection_field: Client`).

**Get it wrong and nothing fails at generation time** — the mismatch surfaces as a Go compile
error in the *consuming* provider repo naming the missing/misspelled field. Always verify
`connection_field` against the `Connection` struct's real field names before trusting a new
source's config. tfspecgen deliberately does not generate the `Connection`/auth struct itself.

## Field and query-parameter selectors

Three distinct selector concepts exist — don't conflate them:

- **`prune`'s per-schema `include`/`exclude`** (spec level, in `sources[].prune[]`) — PII/scope
  reduction applied to the OpenAPI spec itself, before `ogen` ever generates a client. Only one
  direction per selector (never both `include` and `exclude` on the same entry).
- **A resource/data source's `fields:`** (generator level, in `resources.<name>`/`data_sources.<name>`) —
  omits a field the *generator* can't render (e.g. an unsupported `[]struct` slice — see the v1
  boundaries below). Not a PII-scoping mechanism; use `prune` for that. An `id_format` member can
  never be excluded here.
- **A data source's `query_param_fields:`** (generator level) — the same include/exclude selector,
  applied to a `read_op`'s real query parameters instead of response fields. Omit it entirely to
  keep every real query parameter the operation has.
- **A data source's `query_params:`** is *not* a selector — it's a purely optional tf-attribute-name
  override map for a parameter that's already being kept (`tf_name: GoFieldName`). A kept parameter
  absent from this map just gets `camelToSnake(GoFieldName)` as its default name.

**Every name in every one of these lists is resolved against the real spec/introspection JSON at
generate time — an unresolvable name fails the whole run immediately**, never a silent no-op.
`path_params` gets an existence check only (never include/exclude — every path param is a mandatory
URL segment, so "expose the operation except this required path segment" isn't coherent).

## Known v1 boundaries (fail loudly via `fatalf`, never silently)

1. **Nesting capped at one level, flat-scalar children only.** A second level of nesting inside an
   already-nested struct fails. Any `[]struct` slice field fails too — the sanctioned workaround is
   `fields: {exclude: [FieldName]}` on that resource/data source (Paylocity's
   `CustomFieldDefinition.Values` is the real precedent for this).
2. **Data sources only support array-shaped `read_op` responses** — an object-shaped success
   response fails immediately.
3. **`Create()` always calls read-back after `create_op` succeeds**, even when `create_op`'s
   response already *is* the full resource model — that case fails rather than skipping the
   redundant call. (An `update_op` returning the full object works today via an unnecessary but
   harmless extra read-back — not a wall, just a wasted round trip.)

For the exact verbatim `fatalf` message text (useful for pattern-matching an error you're staring
at), the full annotated `tfspecgen.yaml` schema, and the complete `connection_field`/multi-source
routing detail, read `references/codegen.md`.
