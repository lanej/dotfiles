---
name: just
description: Task automation with just and justfiles - recipe definition, dependencies, parameters, imports, and delegation to shell scripts. Prefer just over make for new projects.
---

# just

Recipe syntax works as documented (`just --list`, `just --evaluate`, `{{param}}` interpolation,
`[confirm]`/`[private]` attributes). This file covers the structural conventions and the one
import behavior that fails loudly.

## Core philosophy: just orchestrates, scripts do the work

A recipe body should be a call, not a program. Business logic belongs in `scripts/`, which is
testable, debuggable outside `just`, and reusable across recipes.

```just
# Good
deploy env:
    ./scripts/validate-env.sh {{env}}
    ./scripts/deploy.sh {{env}}
```

Anything with conditionals, error handling, or more than ~3 commands goes in a script with
`#!/usr/bin/env bash` and `set -euo pipefail`. Keep a recipe inline only for a single command,
a trivial chain, or an alias.

Prefer `just` over `make` for new projects; keep `make` where it already exists.

## Layout

```
project/
├── justfile
└── scripts/
    ├── build.sh
    ├── deploy.sh
    └── utils/common.sh     # sourced via "$(dirname "$0")/utils/common.sh"
```

## Gotcha: redefining an imported recipe is a hard error

Defining a local recipe with the same name as one pulled in by `import`/`import?` fails outright —
it does not silently override, and definition order does not matter by default:

```
error: Recipe `render` first defined on line 8 is redefined on line 46
```

To actually replace an imported recipe, opt in *and* define the local version **before** the
`import` line — with duplicates allowed, `just` takes whichever definition it sees first:

```just
set allow-duplicate-recipes := true

render:
    echo "local override wins"

import? 'canonical.just'  # also defines `render`, but loses
```

Only same-name conflicts are affected; adding a differently-named recipe alongside imports needs
no setting.

## Template

```just
set shell := ["bash", "-c"]

default: check

help:
    @just --list

test:
    ./scripts/test.sh

build:
    ./scripts/build.sh

ci: test build
    ./scripts/verify.sh

[confirm]
deploy-prod: ci
    ./scripts/deploy.sh production
```
