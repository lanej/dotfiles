# Lifecycle contract

Policy version: **1.0.0**. Schema version: **1**.

| Stage | Construction | Testing | Comments and contracts | Generated language gate |
| --- | --- | --- | --- | --- |
| research | Resolve one consequential question with a small real experiment; allow disposable structure. | Compile/typecheck and exercise the experiment. Record findings and limits; discarded work needs no permanent suite. | Explain assumptions, surprising behavior, and consequential interactions; avoid speculative API documentation. | Go compile; TypeScript typecheck. Existing inherited gates still run. |
| alpha | Establish a working steel thread; allow API changes. | Protect retained behavior and consequential failures with focused regression checks. | Document caller information needed to use retained APIs; contracts may be explicitly provisional. | Lint, compile/typecheck, and tests without the added Go race/vulnerability or TypeScript audit pass. |
| beta | Prepare for adoption and compatibility; keep changes local and inspectable. | Full language profile, real integration checks for affected boundaries, and compatibility/migration checks where relevant. | Document public contracts, interactions, constraints, and failure outcomes; add examples where helpful. | Full Go or TypeScript quality profile. |
| production | Support dependable use and controlled changes. | Beta evidence plus independent review and reproducible recovery/operational evidence appropriate to the software. | Maintain supported contracts, compatibility expectations, and operational guidance where applicable. | Full language profile; review, recovery, and reliability obligations require additional evidence. |

Research compilation alone does not establish a successful experiment; alpha's automated test command does not establish complete regression coverage. Report manual evidence and remaining gaps. Integration, compatibility, review, recovery, and service reliability are claims that require relevant observations; the generic runner cannot certify them.

At every stage, preserve explicit repository requirements, truthful claims, secret handling, and protections against destructive or irreversible effects. Stage selection controls the checks introduced by this package; it does not waive other required gates. Security or failure behavior that determines an experiment's viability belongs in the initial experiment.

The installer defaults to beta, preserving the previous full generated checks. Existing installs without lifecycle metadata also retain full checks until explicitly updated. `--stage` persists the selected stage; subsequent setup runs retain it. `--dry-run` reports the prior and proposed stages and command plans, including checks relaxed by a downgrade. Promotion changes expectations; it does not assert the project has met them. Changing the stage does not change strict versus ratchet adoption, remove a baseline, or rewrite source.

Stage and policy version are independent. Unknown stages, schema versions, or policy versions fail before commands run. The [command plans](stages.json) are versioned with this contract. A project that customizes installed policy files retains the installer's normal conflict protection. Shadow mode excludes the policy, runner, and skills along with the other managed files.
