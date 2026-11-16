# Designing a tool knowledge base

## Select knowledge with a job to do

Start from recurring user tasks, existing notes, and demonstrated failures. Keep facts that change a decision, prevent a plausible mistake, or enable an operation. A skill is useful when it captures hard-to-discover behavior and reusable techniques; copying a whole manual usually makes retrieval harder. Link to official documentation for exhaustive catalogs.

Use the installed version and command help to establish available operations. For APIs, compatibility, limits, and uncertain claims, consult current official documentation or maintained source. Retain useful local observations with their environment, symptom, and evidence; a workaround observed on one version is not a timeless rule. Date or version only claims whose applicability depends on it, and explain how to recheck them. Do not add a blanket “verified” label to notes assembled from mixed evidence.

Before preserving an example, identify its required inputs, environment, expected artifact or state, and material side effects. Use portable placeholders; keep credentials out of commands and output. Never infer permission to install dependencies, deploy, publish, message others, or modify remote state from the fact that an example describes it.

## Place knowledge at the right layer

| Layer | Include | Avoid |
| --- | --- | --- |
| Discovery description | Tool identity, user intents, distinguishing triggers | Long feature lists, vague verbs, project-specific instructions |
| Entrypoint | Purpose, shared constraints, task-to-topic routing, essential outcome checks | Full command tutorials or mandatory reads of every topic |
| Topic reference | A cohesive task, examples, decisions, related failures and recovery | Generic advice or an unrelated bundle of observations |
| Script or asset | Repeated deterministic work or an input users actually reuse | A new harness or template solely to populate a directory |
| Owning project | Local wrappers, libraries, paths, branding, conventions, required gates | Rules imposed on unrelated users of the same tool |

Create a reference when a recognizable task needs detail that other tasks do not. Merge tiny notes that are normally read together. Split a large reference when it serves distinct user intents; do not fragment every command into a file. A small tool may need only an entrypoint. There is no fixed topic count or line quota beyond the owning repository's budget.

Link topic notes directly from a table whose rows state when to read them. Keep each note sufficient for its task, apart from the shared entrypoint and clearly identified dependencies. Cross-link a prerequisite only when it is needed. A brief router that loads the whole package still has the whole package's context cost.

## Make task notes executable in practice

For each procedure, explain the meaningful inputs, smallest useful command or API example, expected observation, and any required cleanup. Explain output semantics where success is ambiguous: a queued job, accepted request, or zero exit code may precede the intended effect. Include verification appropriate to that distinction.

Keep troubleshooting close to the affected operation. Record symptom, likely cause, a discriminating check, recovery, and how to confirm recovery. Name destructive or irreversible effects at the relevant step. Label a suspected cause as uncertain and give the next check; do not turn it into a confirmed tool defect.

For example, a renderer skill can route “write an equation” to math notes, “clipped chart” to figure layout, and “missing PDF font” to PDF troubleshooting. Its shared entrypoint keeps environment selection and output inspection visible. A cloud CLI skill can route authentication separately from deployment while keeping account selection and deployment authority visible across both topics.

## Consolidate without losing useful behavior

Inventory the old entrypoints, callers, references, scripts, and installed discovery entries. Map reusable knowledge to the new task topics, retain applicable examples and failure distinctions, and remove stale or duplicate claims. Move organization-specific content only to an authorized destination; otherwise report the unresolved ownership rather than silently discarding valuable knowledge.

Update callers and supported install manifests with the new canonical name. Remove superseded discovery entries only within the authorized scope. If compatibility is needed, route to the canonical package instead of maintaining a duplicate procedure. Check the installed package's links and supporting resources without relying on an authoring checkout.

## Review a concrete reading path

Choose realistic requests from the intended use, then trace description → entrypoint → needed topic → observable result. For each, identify why the selected topic is sufficient and which unrelated notes are unnecessary. This is a design walkthrough; claim observed assistant selection only after an actual assistant trial.

When the tool is available, exercise a small representative example and inspect the result. When it is unavailable, check package structure and examples as far as possible, then report the live verification gap. Use the canonical skill-authoring workflow for proportionate validation and installation rather than introducing a second authoring process here.
