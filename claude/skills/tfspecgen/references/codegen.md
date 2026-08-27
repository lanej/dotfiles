---
name: tfspecgen/codegen
description: "Full config schema, subcommand flags, the connection_field contract, multi-source routing status, and v1 boundary fatalf messages for tfspecgen. Use when authoring or debugging a tfspecgen.yaml resource/data-source entry, or diagnosing a tfspecgen generate/build failure."
---

# tfspecgen: OpenAPI-to-Terraform-CRUD Code Generation

`tfspecgen` is a config-driven CLI that turns a vendor's OpenAPI/Swagger spec into a Terraform
Plugin Framework provider's CRUD resource/data-source Go code, via an `ogen`-generated API client.
It was extracted from `terraform-provider-paylocity`'s original two-tool pipeline
(`tools/ogenintrospect` + `tools/gen-resource`) so the same generator can drive multiple per-vendor
Terraform provider repos.

This document is the config schema, subcommand, and known-boundary reference. See `README.md` for
a short quickstart.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Install](#install)
- [Subcommands](#subcommands)
- [`tfspecgen.yaml` schema](#tfspecgenyaml-schema)
- [The `connection_field` contract](#the-connection_field-contract)
- [Multi-source routing status: implemented, not yet validated](#multi-source-routing-status-implemented-not-yet-validated)
- [Known v1 boundaries](#known-v1-boundaries)

**Provenance:** this file mirrors `tfspecgen/CODEGEN.md` (kept in sync manually, not automated).
Deltas from the source: this mini-frontmatter, this Table of Contents, this Provenance note, and
removal of one dangling cross-reference (to a local plans file that does not exist inside the
tfspecgen repo) from the intro paragraph above. Everything else — heading text/order, all code
blocks, all prose — is unchanged from the source file.

## Prerequisites

`tfspecgen` shells out to three external binaries rather than reimplementing them (Unix philosophy
-- compose existing, externally-maintained tools):

| Binary | Used by | Install | Verified working version |
|---|---|---|---|
| `ogen` | `client` subcommand | `go install github.com/ogen-go/ogen/cmd/ogen@latest` | v1.18.0 |
| `yq` (mikefarah/yq, Go) | `merge`, and internally by the bundled `prune`/`filter` scripts | `brew install yq` | v4.53.6 |
| `swagger2openapi` | `convert` subcommand | `npm install -g swagger2openapi` | 7.0.8 |

All three must be on `PATH`. `tfspecgen` itself does not vendor or pin their versions -- if a
newer major version changes CLI flags, the wrapping `pipeline` package's exact command
construction (see `pipeline/*.go`) may need updating.

`ogen` is also a **library dependency** of the *generated client's* consuming provider repo (e.g.
`terraform-provider-paylocity`'s own `go.mod` pins `github.com/ogen-go/ogen`), separately from the
`ogen` CLI binary used to generate that client -- these can be different versions; only the CLI
binary matters for `tfspecgen client`.

## Install

```sh
go install github.com/easypost-sandbox/tfspecgen@latest
```

or, for local development against a checkout:

```sh
cd ~/src/tfspecgen && go build -o /usr/local/bin/tfspecgen .
```

## Subcommands

```
tfspecgen fetch | convert | merge | prune | filter | client | introspect | generate | build
```

9 real subcommands (`build` is a full-chain convenience wrapper, not an independent pipeline
stage). Every stage's inputs/outputs are plain files -- nothing is implicit or cached between
invocations.

| Subcommand | Flags | Wraps |
|---|---|---|
| `fetch` | `-url`, `-out` | bundled `fetch-openapi.sh` (parameterized `curl`) |
| `convert` | `-in`, `-out` | bundled `convert-swagger-to-openapi.sh` (`swagger2openapi`) |
| `merge` | `-base`, `-overlay`, `-out` | `yq eval-all '. as $item ireduce ({}; . * $item)'` |
| `prune` | `-spec`, `-allowlist`, `-out`, `-schema` | bundled `prune-spec-fields.sh` |
| `filter` | `-spec`, `-safelist`, `-out` | bundled `filter-openapi-spec.sh` |
| `client` | `-spec`, `-target`, `-package`, `-config` | `ogen --target ... --package ... --clean --config ...` |
| `introspect` | `-src` (default `../../internal/paylocity`), `-out` (default `../../generated/ogen_introspection.json`) | `go/ast`-based parse of ogen's generated output |
| `generate` | `-config` (config mode) **or** `-meta`/`-provider-module`/`-provider-name`/`-client-package`/`-connection-field` (flat mode), plus `-intro`/`-out` | the CRUD template renderer |
| `build` | `-config`/`-source`/`-work-dir`/`-intro-dir` (config mode) **or** the full set of flat per-stage flags | chains all of the above, stopping on first failure |

`introspect`'s and `generate`'s flat-mode defaults are Paylocity-shaped relative paths (a holdover
from the original two tools being `go run` from their own subdirectory) -- always pass explicit
`-src`/`-out`/`-intro`/`-out` when invoking from a provider repo's root, as the paylocity `justfile`
does.

**Config mode vs. flat mode** (`generate` and `build`): config mode (`-config tfspecgen.yaml`)
resolves every resource/data source's routing from `tfspecgen.yaml`'s `sources:` list. Flat mode
(`-meta resource_meta.yml` + four required `-provider-*`/`-client-package`/`-connection-field`
flags) applies one `RouteInfo` uniformly to every resource/data source -- the original
single-source interface, kept as an escape hatch, not the recommended path for a new provider.

**`build -config` does not orchestrate multiple sources in one invocation.** It runs exactly one
source's `fetch -> [convert] -> [merge] -> [prune...] -> filter -> client` chain (the named
`-source`, or the sole source if there's only one), then runs `introspect` against that source's
client, then runs `generate` across **every** resource/data source in the whole config -- each
routed through its own `source:`, not just the one this invocation built. A multi-source provider
needs one `build -source <name>` invocation per source (each populating its own
`internal/<package>/`), followed by a final `build -source <any-one>` (or a bare `generate -config`)
to render every resource once all clients exist. This is a deliberate v1 boundary, not an oversight
-- see "Multi-source routing status" below.

## `tfspecgen.yaml` schema

One file per consuming provider repo, at that repo's root. Annotated example (the real,
in-production Paylocity config, at `terraform-provider-paylocity/tfspecgen.yaml`):

```yaml
provider:
  name: paylocity                                            # short vendor name; used only in
                                                              # generated doc/log text (the
                                                              # "<name>_%s" resource-type prefix),
                                                              # never in Go identifiers.
  module: github.com/easypost-sandbox/terraform-provider-paylocity
                                                              # consuming repo's Go module path;
                                                              # every generated import path is
                                                              # derived from this + a source's
                                                              # package name.

sources:
  - name: weblink                                            # arbitrary source identifier,
                                                              # referenced by resources'/data
                                                              # sources' `source:` keys below.
    connection_field: Client                                 # REQUIRED. Names the field on the
                                                              # hand-written *client.Connection
                                                              # struct holding this source's
                                                              # generated client. See "The
                                                              # connection_field contract" below --
                                                              # this is load-bearing, not cosmetic.
    spec:
      url: https://raw.githubusercontent.com/DataFire/Integrations/master/integrations/generated/paylocity/openapi.json
      format: swagger2                                       # "swagger2" (runs `convert`) or
                                                              # "openapi3" (skips it).
    overlay: contracts/paylocity-overlay.yaml                # optional; omit to skip `merge`.
    prune:                                                   # optional; omit to skip pruning.
      - schema: employee                                     # ordered list -- each entry is one
        include:                                             # `prune` invocation. A symmetric
          - employeeId                                       # include/exclude field selector:
          - firstName                                        # `include` is a static, pinned set
          - lastName                                         # (every property of `schema` NOT
          - status                                           # listed here is removed) -- OR use
                                                              # `exclude: [...]` instead (a dynamic
                                                              # set; never both on one selector).
                                                              # Either direction fails loudly at
                                                              # generate time if a listed name
                                                              # doesn't exist in the real spec.
        nested:                                               # optional per-entry: strip/keep
          departmentPosition:                                # specific leaf fields on an
            exclude: [equalEmploymentOpportunityClass]        # otherwise-kept nested object
                                                              # (parent object stays; only its own
                                                              # include/exclude selector applies to
                                                              # its leaves). Same include/exclude
                                                              # symmetry as the top-level selector.
    safelist: contracts/safelist-paths.txt                   # REQUIRED. External path-safelist
                                                              # text file for the `filter` stage
                                                              # (kept as a file, not inlined --
                                                              # unlike `prune`, a large flat path
                                                              # list doesn't benefit from inlining).
    package: paylocity                                       # REQUIRED. Go package name/import-
                                                              # path segment ogen generates the
                                                              # client under (internal/<package>).
    ogen_config: contracts/ogen.yml                          # REQUIRED. ogen config file path
                                                              # passed to the `client` stage.

resources:
  employee_local_tax:
    source: weblink                                          # REQUIRED. Must match a sources[].name.
    create_op: AddLocalTax                                   # ogen operation names, resolved
    read_op: GetLocalTaxByTaxCode                             # against the introspection JSON --
    delete_op: DeleteLocalTaxByTaxCode                        # unresolvable names fail loudly at
                                                              # generate time (see below), never
                                                              # silently.
    array_match_field: tax_code                              # read_op returns array[LocalTax];
                                                              # select the element by this field.
    id_source: client_supplied                                # "client_supplied" or
                                                              # "server_generated".
    id_format: [company_id, employee_id, tax_code]            # composite Terraform ID shape.
    delete_not_found_is_success: true                         # 404 on delete = already-gone.

  employee:
    source: weblink
    create_op: AddEmployee
    read_op: GetEmployee
    update_op: UpdateEmployee
    read_array_index0: true                                   # take element [0] directly rather
                                                              # than a match-field search.
    id_source: server_generated
    id_format: [company_id, employee_id]
    field_scope: contracts/employee-field-scope.yml           # provenance-only pointer; pruning
                                                              # already applied at the spec level.
    # fields:                                                 # OPTIONAL generator-level include/
    #   exclude: [SomeUnsupportedField]                       # exclude selector (same
                                                              # FieldSelector type/semantics as
                                                              # `prune`, resolved separately) --
                                                              # for a field shape the generator
                                                              # can't render, NOT a PII-scoping
                                                              # mechanism (PII stays spec-level,
                                                              # via `prune` above, applied before
                                                              # ogen ever sees the field). An
                                                              # id_format member can never be
                                                              # excluded here -- fails loudly if so.

data_sources:
  paystatement_details:
    source: weblink
    read_op: GetsEmployeePayStatementDetailDataBasedOnTheSpecifiedYear
    model: PayStatementDetails
    path_params: [company_id, employee_id, year]
    # query_param_fields:                                     # OPTIONAL include/exclude selector
    #   exclude: [Includetotalcount]                           # over read_op's real query
                                                              # parameters (ogen's PascalCase
                                                              # Name), resolved against read_op
                                                              # only -- absent means "keep every
                                                              # real query parameter the op has".
    query_params:                                             # tf attr name -> Go param field
      page_size: Pagesize                                    # name -- now purely an OPTIONAL
      page_number: Pagenumber                                # naming override for a kept
      include_total_count: Includetotalcount                 # parameter; a kept parameter absent
                                                              # here gets camelToSnake(GoName) as
                                                              # its default tf name (this
                                                              # round-trips losslessly even for
                                                              # Pagesize/Pagenumber/
                                                              # Includetotalcount -- an override
                                                              # here is a naming preference, not a
                                                              # safety requirement).

  customfields:
    source: weblink
    read_op: GetAllCustomFieldsByCategory
    model: CustomFieldDefinition
    path_params: [company_id, category]
    fields:                                                   # OPTIONAL generator-level
      exclude: [Values]                                       # include/exclude selector -- fields
                                                              # to omit from the generated schema
                                                              # (e.g. a []struct slice v1 can't
                                                              # model -- see boundary #1 below).
```

Every resource/data-source key not shown above (`update_op`, `optional_param_attribute`,
`read_op_with_optional_param`, etc.) carries over unchanged from the original
`resource_meta.yml` shape -- `tfspecgen.yaml`'s `resources:`/`data_sources:` blocks are a drop-in
superset, not a redesign.

**Loud failure on drift, always.** Every operation/model name referenced anywhere in
`tfspecgen.yaml` (or a flat `resource_meta.yml`) is resolved against the introspection JSON at
generate time. An unresolvable name fails the whole run immediately with a clear error naming the
missing operation -- `generate`/`build` never proceed with a nil or best-guess fallback. This
extends to every field/parameter selection list, irrespective of query, path parameter, or
response/request body field: `prune`'s `include`/`exclude`, a resource's or data source's
`fields:`, and a data source's `query_param_fields:` all fail loudly if a listed name doesn't
actually exist in the real contract, and `path_params` fails loudly if an entry doesn't
correspond to a real path parameter on the operation it binds to (path parameters get this
existence check only, never an include/exclude toggle -- every path param is a mandatory
URL-template segment the operation requires by construction, so "expose the operation except this
required path segment" has no coherent meaning).

## The `connection_field` contract

**Multi-source routing requires the developer to hand-write a `Connection` struct with a field
matching each source's `connection_field`.** This is real and load-bearing, not a footnote:

Generated resource/data-source code calls `r.conn.<ConnectionField>.<Op>(...)` --
`<ConnectionField>` is not generated, it is a Go struct field name the developer must already have
defined on their own `*client.Connection` type, holding a value of that source's ogen-generated
client type. For Paylocity's single-source case this is `Connection.Client *paylocity.Client`,
matching `connection_field: Client`. A multi-source provider (e.g. a hypothetical Jira-shaped
Core+Software+Automation split) would need `Connection.Jira`, `Connection.JiraSoftware`,
`Connection.AutomationPublic` fields matching each source's own `connection_field`.

`tfspecgen` does **not** generate this struct -- generating the `Connection`/auth layer is
explicitly out of scope by design (auth is scaffolded and documented as a starting point, not
generated, same stance as before this extraction). Get `connection_field` wrong and nothing fails
at generation time: the mismatch surfaces as a Go compile error in the *consuming* provider repo,
naming the missing/misspelled field. Always verify `connection_field` directly against the
`Connection` struct's real field names before trusting a new source's config.

## Multi-source routing status: implemented, not yet validated

The `sources:` list and `connection_field` routing are fully implemented and exercised by
Paylocity's (single-source) config today. **They have not yet been validated against a real
multi-spec vendor** -- e.g. Jira's Core+Software+Automation three-spec pattern, which is the
scenario this design was built to eventually support. Treat multi-source routing as
implemented-but-unproven until a real second vendor with more than one spec actually exercises it;
that vendor's config is the real test, not anything in this repo's own test data.

## Known v1 boundaries

Three generalization gaps are deliberately deferred, unchanged from the original
`terraform-provider-paylocity` tools, to be resolved with evidence from a real second vendor spec
rather than speculatively. Each fails loudly and immediately, by design -- a future user hits a
clear wall, not silent wrong output.

**1. Nesting depth is capped at one level, with flat-scalar-only children.** A field whose wrapper
kind is `opt_struct` (one level of nesting, rendered as a `SingleNestedAttribute`) is supported; a
second level of nesting inside that struct is not. Two distinct failure modes:

- A nested struct field: `fatalf("nested model %q field %q has wrapper kind %q (%s) -- gen-resource
  supports only one level of nesting with flat scalar children (per the design plan's v1 scope)")`
- Any `slice`-kind field (a `[]struct`, i.e. a list of nested objects) anywhere: `fatalf("model %q
  field %q (%s) is a slice/list-of-struct field, not supported by gen-resource v1 (no
  ListNestedAttribute support) -- add it to this resource/data source's `fields:` exclude list
  (resource_meta.yml, or tfspecgen.yaml's resources./data_sources. equivalent) if it is safe to
  omit, or treat this as a real scope gap")`

  Paylocity's own `CustomFieldDefinition.Values` field hits exactly this and is worked around via
  `fields: {exclude: [Values]}` -- the documented, sanctioned escape hatch, not a special case.

**2. Data sources support array-shaped responses only.** Every v1 data source's `read_op` must
return an array; a `read_op` whose success response is object-shaped fails immediately:
`fatalf("data source %q: read op %s has non-array success shape %q, which gen-resource's
data-source renderer does not implement (every v1 data source returns an array)")`.

**3. The create path requires read-back; a direct-object-return create is unimplemented.** Every
v1 resource's `Create()` is generated to call the read-back helper after `create_op` succeeds, even
when `create_op`'s response already contains the full object -- there is no "populate directly from
the create response" code path. If `create_op`'s response type already *is* the resource's own
model (so read-back is redundant, not merely unnecessary), generation fails rather than silently
emitting a wasteful-but-correct extra call:
`fatalf("resource %q: create_op %q returns the resource's own model directly --
direct-populate-from-create-response is not implemented by gen-resource (every v1 resource needs
read-back); extend renderReadBackAndPopulate if this is genuinely needed")`.

  Note this only hard-fails on the *create* path. An `update_op` that returns the full object
  directly already works today via an unnecessary extra read-back call -- not a wall, just an
  avoidable round trip.

None of these three are solved speculatively in this pass -- they stay exactly as strict as they
are today until a real second vendor spec demands otherwise.
