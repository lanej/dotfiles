# CI checkout baseline

PR #27 run 34643323323 failed before any maintenance test ran:
https://github.com/lanej/dotfiles/actions/runs/34643323323/job/103408055282

With persist-credentials: false, actions/checkout@v4 immediately ran its credential cleanup, including git submodule foreach. That failed with:

    fatal: No url found for submodule path 'hotreload.nvim' in .gitmodules
    The process '/usr/bin/git' failed with exit code 128

The repository's existing successful Socrates workflow uses checkout's default credential lifecycle. Run 34639613331 completed successfully; the same pre-existing submodule error appeared only as a post-job cleanup warning there. No submodule contents or URLs are changed by this fix.
