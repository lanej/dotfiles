# Project kind

`kind` describes how people or other software consume the project. It is independent of language, architecture, and lifecycle stage. Select it explicitly as `service`, `library`, or `tool`; an omitted kind preserves existing requirements without inferring a category from files or dependencies. Apply this guidance alongside the selected stage and repository contracts.

| Kind | Reader or consumer | Relevant obligations |
| --- | --- | --- |
| `service` | Integrators and operators | Explain integration contracts, failure behavior, configuration, and observable health. For retained deployments, provide evidence appropriate to rollout, recovery, and operational changes. |
| `library` | Callers who should not need to inspect implementation | Document supported public behavior, inputs/outputs, constraints, interactions, errors, and useful examples. Identify provisional APIs and compatibility expectations. Use the installed library comment guidance. |
| `tool` | People or automation invoking an interface | Define invocation, inputs/outputs, diagnostics, failure outcomes, and installation requirements. For CLIs, preserve meaningful exit codes and machine-readable output contracts; for interactive tools, cover the actual interaction and recovery paths. |

Use the selected lifecycle entrypoint for the depth of these obligations at the project’s current maturity.

Kind does not select a new architecture, install deployment tools, or add generated language commands. Preserve existing repository gates and report evidence and limits. A repository can contain several kinds of code; project-wide kind is currently one optional selection. Directory-specific composition remains a separate design decision, so do not infer or synthesize directory overrides.
