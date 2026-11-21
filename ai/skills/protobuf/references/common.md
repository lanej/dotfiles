# Protobuf

Read [the check-profile selector](profile.md) for the installed language gate. Preserve existing project gates and Buf workspace, dependency, and generation configuration.

Model structured data with explicit messages, enums, repeated fields, typed maps, and `oneof` variants. Do not serialize JSON into string fields in place of a typed contract. Application code can hide JSON in innocently named strings; a field-name check alone does not establish typed contracts throughout the application.

Fix findings at their cause. For published schemas, introduce compatible fields or a versioned migration; never rename published fields, recycle field numbers, loosen policy, or select a newer compatibility baseline merely to pass checks. Preserve deleted field names and numbers as reserved where appropriate. Buf checks schema structure and compatibility; use runtime validation and focused application tests for value constraints and actual serialization behavior.
