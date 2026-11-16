# Strict Protobuf profile

The profile uses [Buf](https://buf.build/docs/) 1.75.0 for compilation, formatting, `STANDARD` lint plus message/service/RPC comments, and `FILE` compatibility checking. A native [Buf check plugin](https://github.com/bufbuild/bufplugin-go) adds one rule: `FIELD_NO_JSON_STRING`. Inline lint ignores are disabled. The runner compiles using the project's Buf configuration and dependency lock, then applies the profile's lint and breaking policy to the compiled image. Existing workspace, dependency, and generation configuration is preserved.

Setup and upgrades automatically select this profile for detected project `.proto` files, `buf.yaml`, or `buf.work.yaml`, including nested directories. Vendor/build directories and Git-ignored files are excluded. An explicit saved `--no-protobuf` or `[checks.protobuf] enabled = false` overrides detection; `--protobuf` re-enables the profile. `--no-detect-languages` prevents automatic selection. Declared Buf workspace roots are recorded in the project policy and used for format/build/lint and matching Git baselines; rerun setup when adding workspaces. Disabling detection retains previously selected roots. Projects without a Buf config use the repository root. This installs configuration and project guidance, not software.

These commands assume the project has selected authority and adoption through authored TOML or a previous installation. For a new installation, select `--authority` and `--adoption` explicitly according to project governance.

```sh
source-code setup --protobuf --dry-run
source-code setup --protobuf
python3 scripts/check-protobuf.py tools
python3 scripts/check-protobuf.py fmt
python3 scripts/check-protobuf.py alpha
python3 scripts/check-protobuf.py all --against '.git#ref=origin/main'
```

Python 3.11+, Go 1.26+, and Git are required. The explicit tools command uses an existing Buf 1.75.0 on PATH or in `.protobuf-quality/bin/`; otherwise it installs the pinned CLI with `go install github.com/bufbuild/buf/cmd/buf@v1.75.0`. It builds the plugin into `.protobuf-quality/bin/` using the committed `go.mod` and `go.sum`, with Go workspace discovery disabled. Go owns dependency downloading and module checksum verification; the profile has no custom binary downloader or cache manager. The application module is untouched. Generated binaries are ignored. Rebuild with `tools` after plugin source or dependency changes. Check commands do not install dependencies or rebuild tools.

CI installs Buf through the maintained [Buf Action](https://buf.build/docs/bsr/ci-cd/github-actions/) in setup-only mode, builds the plugin, then runs the same selected lifecycle gate as local development. Workflow path filters cover schemas, workspace/lock files, the plugin source/module, profile settings, lifecycle command plan, runners, and the workflow itself. Unrelated application and documentation changes do not trigger the generated Protobuf workflow. No BSR account is required for local schemas; external dependencies may need network access or authentication.

## JSON string field rule

`FIELD_NO_JSON_STRING` rejects exactly fields with scalar type `string` and a case-sensitive `_json` suffix. Buf's plugin SDK supplies descriptor traversal, import exclusion, and source-positioned findings. Nested messages, repeated strings, and oneof members are checked. Imported dependency declarations are excluded. String fields with ordinary names, bytes, wrapper messages, maps, and dynamic types are outside this rule. The plugin does not inspect application serialization call sites or runtime values.

For example, `string request_json = 1;` fails. A typed `Request request = 1;` is a suitable design for an unpublished schema. For an already published schema, introduce a new field number and a migration; changing a string field into a message at the same number is not a safe migration. There are no profile-specific field exceptions or generic payload-name bans.

The generated runner applies the plugin automatically. To use it with direct `buf lint` as well, merge this configuration into the project's existing `buf.yaml` after building the plugin:

```yaml
version: v2
lint:
  use:
    - STANDARD
    - FIELD_NO_JSON_STRING
  disallow_comment_ignores: true
plugins:
  - plugin: .protobuf-quality/bin/buf-plugin-json-string
```

## Compatibility baseline

`all` and `breaking` require an explicit baseline through `--against`, then `PROTOBUF_AGAINST`, then the saved `against` setting in `.protobuf-quality.json`. No baseline is guessed or silently skipped. Use the actual released schema, PR base, or integration branch as appropriate; `HEAD` only checks uncommitted work and does not establish PR compatibility. The generated workflow fetches history and selects the PR base SHA or previous push SHA. A first push without a prior commit, a base without schemas, or a newly created API requires a deliberately established initial schema baseline before claiming compatibility. Choose an explicitly configured initial-schema workflow; do not downgrade a project merely to hide a breaking change.

Strict adoption has no ratchet baseline. Review existing API naming before applying lint fixes; published schemas may require versioned migration. `--no-protobuf` retains previously installed checks and artifacts, matching the other source-code profiles. Tracked and shadow installs use the same portable assets.
