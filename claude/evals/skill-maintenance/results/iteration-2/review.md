# Checkout compatibility recheck

Only the new workflow changes: remove the non-default early credential-cleanup setting and use the action's normal end-of-job cleanup, matching the existing successful Socrates CI configuration. The job retains contents: read permissions and no model calls. The known incomplete hotreload.nvim submodule is unchanged.

Master advanced to 77aafa7c65b2d02a41be76cf196079b05f1a160e during this task. It has been merged without conflicts. This PR does not modify those upstream instruction changes. The maintained policy, routing paragraphs, gate scripts, tests, and size-budget configuration are byte-identical to iteration 1; its advisory evaluations and independent code review remain applicable to those unchanged sources. This record binds the updated workflow and retains the prior failed run.

Current maintenance tests: 43 passed. Current size scan: 124 tracked entrypoints, 19 existing overages, no failures. Combined repository run: 172 passed, one failed, four existing live-tmux tests deselected. The new failure is ConfigurationTests.test_all_lifecycle_hooks_are_wired_once: master removed the PostToolUse hook expected by that test. It reproduces against unchanged master in a separate fixture checkout (master-test.txt), so no unrelated hook restoration is included here.

The implementing agent reviewed the checkout change using the failed run and the existing successful workflow. Native CI verification follows on the pushed revision; no successful run of this new revision is claimed by these local artifacts. Evidence provenance remains a mechanical check, not proof of behavioral quality.
