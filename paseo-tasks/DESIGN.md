# Tasks design contract

The accepted task brief in [the implementation guide](../docs/paseo-tasks.md) defines the experience. Josh uses this overview to decide which task needs attention and enter its persistent worker conversation. Each task retains its outcome, success criteria, constraints, approach, evidence, blocker, next action, host identity, and checkout.

Use Paseo's official plugin components and supplied theme and layout tokens. The official app owns its surrounding navigation and host selector. Tasks use vertically stacked records because briefs and evidence vary in length; compact layouts wrap content and controls instead of hiding those fields. No visual reference has been approved by the user.

Loading, absent observations, failed operations, and cached offline observations remain explicit. Status and agent activity are separate text fields. Selection exposes bulk controls and reports each result. A disconnected host disables entry into its worker without redirecting it. The app's selected host owns the surface; select Mac for the overview of its authenticated Mac, dev, and dev2 connections. Worker links open the exact host and conversation. Native controls retain their accessible labels and keyboard behavior.

## TASK-001

Mandatory: the rendered Tasks surface must expose the task records and direct conversation controls without horizontal clipping at desktop and compact widths. Viewrule checks the scoped surface and controls; review screenshots and detail tiles for readability, wrapping, hierarchy, and both supplied themes.

## TASK-002

Mandatory: entering a task must reach its own conversation and retain its host identity. The live browser detector follows each acceptance task's button and checks its actual route. Controlled service tests protect routing, stale observations, selection, and recovery; they do not establish phone behavior.

## Evidence and limits

The rollout uses actual records on three execution hosts and the official Paseo web app. Browser state remains ignored local authentication data. Capture and test results establish the checked states only. Actual mobile disconnect and reconnect while a worker continues requires the user's device check.
