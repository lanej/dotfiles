---
name: tool-knowledge
description: Use when creating or consolidating a compact knowledge-base skill for a specific tool, CLI, library, or service with progressive disclosure. Covers topic routing, authoritative tool knowledge, examples, and troubleshooting; use skill-authoring for general instruction workflows.
---

# Tool knowledge

Create a small, reusable tool knowledge base: enough always-loaded guidance to choose and operate the tool safely, with task-specific detail read on demand. Use the [skill-authoring workflow](../skill-authoring/SKILL.md) for package creation, validation, installation, and reporting; this skill supplies the knowledge organization pattern.

## Define the useful boundary

Identify the tool, actual user tasks and trigger phrases, supported environments, and existing knowledge worth retaining. Inspect the current package and its callers before consolidating it. Keep tool behavior and reusable techniques here; put company libraries, branding, project paths, architecture choices, and engineering gates in their owning projects. Preserve explicit user requirements and authority limits.

Read [the knowledge design guide](references/design.md) when selecting source material, splitting topics, or consolidating existing skills. Use [the package template](assets/package-template.md) when drafting a new entrypoint or topic note; omit sections that add no useful knowledge.

## Keep the entrypoint small

Write a precise discovery description, the essential constraints that apply across tasks, and a task-to-reference table with explicit read conditions. Keep common prerequisites and consequential authority or failure rules visible. Route by user intent, such as rendering a PDF or debugging authentication, rather than by an exhaustive command inventory. Do not require every reference on every invocation or move always-required text behind a link to claim a context reduction.

Put focused procedures, working examples, version-specific quirks, and symptom-based troubleshooting in the matching references. Prefer direct links from the entrypoint and self-contained task notes over chains of required reading. Add scripts or assets only when repeated execution or reusable input earns their maintenance cost.

## Check the knowledge and its routing

Verify version-sensitive flags, APIs, limits, and workarounds through the installed tool's help, source, or current official documentation. Preserve the scope and evidence of observed failures; distinguish confirmed behavior from inference and untested advice. Never invent commands to fill a gap.

Walk through representative requests: an ordinary task, a conditional topic, and a consequential failure where relevant. Check which notes each request needs, whether the examples yield an observable result, and whether unrelated notes stay unloaded. Run a proportionate real example when the runtime and authority permit; report unavailable tools and untested behavior. Package validity and a compact router do not prove correct assistant selection or successful tool execution.
