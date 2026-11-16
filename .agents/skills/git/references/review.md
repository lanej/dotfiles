# Project review and publication

Apply this procedure when the project installs the source-code Git profile. Preserve repository-specific review, CI, and publication requirements. User-level authorization and tool access remain separate: installing this profile does not authorize pushing, publishing, merging, or messaging reviewers.

## Independent review

Obtain a separate code review for complex changes: interacting components, nontrivial algorithms or state transitions, concurrency, migrations, security-sensitive logic, or uncertainty about correctness that warrants independent judgment. Judge the behavior and interactions, not line count. Simple, mechanically verifiable edits do not require a separate reviewer merely because they will be committed or published.

Give the reviewer the final changed capability, relevant project instructions, actual validation evidence, and the intended base. Ask for actionable correctness, security, and regression findings under the project's architecture and testing policy. Keep unrelated work out of scope. Use a read-only `code-reviewer` role when available, or an equivalent bounded reviewer with the same project context; report unavailable review capability rather than claiming a review occurred. Reviewers must not dispatch further reviewers or make changes.

Wait for the review and address actionable findings before declaring readiness. Include recommendations as well as numbered findings when preparing a repair brief; identify any intentionally deferred item and its reason. Have the reviewer reassess material fixes made in response to its findings. Review findings and passing checks are evidence with limits, not proof of readiness by themselves.

## Drafting and publication

Follow the project's installed PR drafting, validation, and publication instructions. Read [the shared PR guidance](pull-requests.md) for outcome-first descriptions and proportional evidence. The calling agent owns factual accuracy, authorized publication, and verification of the saved title, rendered body, links, and target branch. Separate drafting agents are optional when useful; a delegated writer drafts only and must not recurse. Other review platforms use the shared pull-request writing guidance where available.

For an existing PR title/body revision, apply the same project drafting and validation guidance, then inspect the saved result. Do not infer a publication workflow merely because Octo, GitHub CLI, or a writer is installed on the workstation. A project that selects Octo follows its installed Octo package and current CLI contract. Follow maintainer conventions in upstream projects and agreed workflow in shared projects.

## Merge assessment

Before an authorized merge, verify the current head, intended base, mergeability, affected checks, and applicable review requirements. Reassess changes to the reviewed head or base rather than reusing an old readiness claim. Use a head-pinned merge mechanism where supported. Verify GitHub's actual merge result and the remote base branch; report queued publication, merge acceptance, completion, and coordinator reconciliation as separate states.

Preserve explicit repository gates. Investigate failures before classifying them as unrelated, and report unresolved limits. A passing local check does not establish hosted CI success, and a queued merge is not a completed merge.
