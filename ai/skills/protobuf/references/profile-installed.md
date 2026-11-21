# Verification

Run `python3 scripts/check-source-code.py protobuf` for the installed lifecycle gate. The selected stage entrypoint controls required checks; standalone modes describe available tools and do not add another stage’s gates. Preserve stronger repository requirements. Missing tools and failed checks require resolution or a reported limit, never a silent skip.

The native `FIELD_NO_JSON_STRING` Buf plugin rejects declared string fields whose names end in `_json`, including nested, repeated, and oneof fields. Generic names, bytes, wrappers, maps, and dynamic well-known types are outside this rule; review their contracts rather than claiming analysis.

Run `python3 scripts/check-protobuf.py tools` explicitly to provision pinned Buf if absent and build the native plugin with Go. Rebuild after plugin source or module changes. CI uses the official Buf Action to install Buf and the same tools command to build the plugin. Setup and check modes do not provision tools. The runner supports `lint`, check-only `format`, source-writing `fmt`, and compatibility modes. Supply `--against` or set `PROTOBUF_AGAINST` when the selected gate requires a baseline. CI compares against the PR base or previous push commit. Inline Buf lint ignores are disabled in the generated gate. Read [the profile guide](correctness.md) before adoption or configuration changes.
