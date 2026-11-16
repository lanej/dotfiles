# Workflow execution and credential boundaries

## Static/AI review cannot substitute for actually running the workflow

A workflow YAML can pass multiple layers of review — task-level review, a final whole-diff review, even a dedicated high-capability review pass — and still ship with an execution-order bug that only a live run exposes. Reviewers read the YAML sequentially and reason about intent; they do not simulate the runner's actual working directory state at each step.

Confirmed failure mode: a `test` job ran the backend test suite before a separate `build-frontend` step had run, and the backend tests happened to serve static files from the frontend's build output directory. Every reviewer (two task-scoped reviews plus one whole-branch review) read the YAML as internally consistent and approved it — none caught that step B depends on step A's filesystem side effect, because none of them executed the steps in order against a real checkout.

**Rule:** treat a CI/CD workflow change as unverified until it has been triggered at least once against real infra and observed to either fully succeed or fail for an already-understood reason. Push a trivial, reversible change that matches the workflow's path filter, watch the run (`gh run watch` / `gh run view --log`), and only then consider the change done. This is a specific case of a workflow that inherently cannot be validated by reading — the failure mode is order-of-operations across steps that touch a shared filesystem, which no amount of re-reading the YAML will surface.

## CI runners have zero ambient credentials — this is a feature, not friction

A GitHub Actions runner has no `gcloud auth application-default login` session, no cached ADC file, nothing. Any code path that constructs a cloud client (`bigquery.Client()`, etc.) outside a try/except that's supposed to degrade gracefully will crash for the first time here — even if that code has run correctly for months on developer laptops and in production (where ADC/the runtime SA is always present).

This makes a from-scratch CI run a genuine, high-value correctness check distinct from "does the code work" — it answers "does the code work with **no** implicit credential fallback," which laptop-based testing structurally cannot answer. Treat a credential-related failure surfaced only in CI as a real, pre-existing gap worth fixing (not a CI environment quirk to work around), especially if the failing function has a documented "never raises" / graceful-degradation contract.
