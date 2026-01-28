---
description: "Manage Python dependencies with uv: add packages, sync environment, run scripts, install tools, create projects - modern replacement for pip, venv, and pipx"
argument-hint: [add|remove|sync|run|tool] [package]
allowed-tools:
  - Read
  - Edit
  - Bash(uv:*)
model: haiku
tags:
  - python
  - uv
  - dependencies
  - package-management
---

# UV Package Management - Fast Python Dependency Management

Manage Python dependencies using uv, the blazingly fast Python package installer and resolver. **AVOID pip** - always use uv commands instead.

## Overview

**Why uv?**
- 10-100x faster than pip
- Built in Rust for performance
- Combines pip, venv, pipx, pip-tools functionality
- Proper dependency resolution
- Lockfile support for reproducible builds
- No need for separate virtualenv management

**Project preference (from CLAUDE.md):**
- ✅ Use `uv run` for executing scripts
- ✅ Use `uv add` instead of `pip install`
- ✅ Use `uv sync` instead of `pip install -r requirements.txt`
- ❌ AVOID `pip` commands entirely

## Usage

```bash
/package-mgmt/uv add pytest              # Add development dependency
/package-mgmt/uv add requests            # Add production dependency
/package-mgmt/uv remove pytest           # Remove dependency
/package-mgmt/uv sync                    # Sync environment with lockfile
/package-mgmt/uv run script.py           # Run script in project environment
/package-mgmt/uv tool install ruff       # Install global tool
```

## Workflow

### 1. Understand User Request

Parse `$ARGUMENTS` for operation:
- **add**: Add dependency (default to --dev for dev dependencies)
- **remove**: Remove dependency
- **sync**: Sync environment
- **run**: Run script or command
- **tool**: Install/manage global tools
- **init**: Initialize new project

### 2. Check Project State

**Determine if project is initialized:**
```bash
# Check for pyproject.toml
ls pyproject.toml

# If exists, read it to understand project
cat pyproject.toml

# Check for uv.lock
ls uv.lock
```

**If no pyproject.toml:**
```bash
# Initialize project
uv init --no-package  # For scripts/non-package projects
# or
uv init               # For full Python packages
```

### 3. Execute Requested Operation

#### Adding Dependencies

**Production dependency:**
```bash
uv add requests
uv add "fastapi>=0.100.0"
uv add git+https://github.com/user/repo.git
```

**Development dependency:**
```bash
uv add --dev pytest
uv add --dev pytest-cov pytest-mock
uv add --dev ruff mypy black
```

**Optional dependency groups:**
```bash
uv add --optional docs sphinx sphinx-rtd-theme
uv add --optional dev pytest ruff
```

**From requirements.txt:**
```bash
# Convert requirements.txt to pyproject.toml
uv add -r requirements.txt
```

**Updates pyproject.toml:**
```toml
[project]
dependencies = [
    "requests>=2.31.0",
    "fastapi>=0.100.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.1.0",
]
```

#### Removing Dependencies

```bash
uv remove requests
uv remove --dev pytest
```

#### Syncing Environment

**Sync with lockfile (reproducible install):**
```bash
uv sync
```

**Sync with updates:**
```bash
uv sync --upgrade
uv sync --upgrade-package requests  # Upgrade specific package
```

**Sync only production deps:**
```bash
uv sync --no-dev
```

**Sync with extras:**
```bash
uv sync --extra docs
uv sync --all-extras
```

#### Running Scripts

**Run Python script:**
```bash
uv run script.py
uv run python script.py
```

**Run with arguments:**
```bash
uv run pytest tests/
uv run pytest --cov=src tests/
```

**Run entry point:**
```bash
uv run my-cli-tool --help
```

**Run arbitrary command:**
```bash
uv run python -c "print('hello')"
```

#### Tool Management (Global Tools)

**Install global tool:**
```bash
uv tool install ruff      # Code linter
uv tool install black     # Code formatter
uv tool install mypy      # Type checker
uv tool install pytest    # Test runner
uv tool install ipython   # Better REPL
```

**List installed tools:**
```bash
uv tool list
```

**Upgrade tool:**
```bash
uv tool upgrade ruff
uv tool upgrade --all
```

**Uninstall tool:**
```bash
uv tool uninstall ruff
```

**Run tool without installing:**
```bash
uvx ruff check .
uvx black --check .
```

### 4. Verify Changes

**Check pyproject.toml:**
```bash
cat pyproject.toml
```

**Check lockfile:**
```bash
cat uv.lock | head -20
```

**Verify environment:**
```bash
uv run python -c "import requests; print(requests.__version__)"
```

**List installed packages:**
```bash
uv pip list
```

### 5. Common Workflows

#### Initialize New Project

```bash
# Script-based project (no package)
uv init --no-package my-project
cd my-project

# Full Python package
uv init my-package
cd my-package
```

**Generated structure:**
```
my-project/
├── pyproject.toml
├── README.md
└── main.py           # or src/my_package/
```

#### Set Up Testing Environment

```bash
uv add --dev pytest pytest-cov pytest-mock
uv add --dev ruff mypy  # Linting and type checking

# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html --cov-report=term-missing
```

#### Migrate from pip

```bash
# From requirements.txt
uv add -r requirements.txt
uv add -r requirements-dev.txt --dev

# From setup.py or setup.cfg
# uv will read these automatically
uv sync

# Remove old files (after verification)
rm requirements.txt requirements-dev.txt
```

#### Update Dependencies

```bash
# Update all dependencies
uv sync --upgrade

# Update specific package
uv sync --upgrade-package requests

# Update to latest compatible versions
uv lock --upgrade
uv sync
```

#### Export for Compatibility

```bash
# Generate requirements.txt for CI/Docker
uv pip freeze > requirements.txt

# Or use uv export (better)
uv export --no-hashes > requirements.txt
uv export --no-dev --no-hashes > requirements-prod.txt
```

## Project Configuration

**pyproject.toml example:**
```toml
[project]
name = "my-project"
version = "0.1.0"
description = "My awesome project"
requires-python = ">=3.11"
dependencies = [
    "requests>=2.31.0",
    "pydantic>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "pytest-mock>=3.12.0",
    "ruff>=0.1.0",
    "mypy>=1.7.0",
]

[project.scripts]
my-cli = "my_project.cli:main"

[tool.uv]
dev-dependencies = [
    "ipython>=8.18.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = ["-v", "--cov=src"]

[tool.ruff]
line-length = 100
select = ["E", "F", "I"]

[tool.mypy]
strict = true
```

## Common Patterns

### Pattern 1: Quick Script with Dependencies

```python
# script.py
# /// script
# dependencies = [
#   "requests",
#   "rich",
# ]
# ///

import requests
from rich import print

response = requests.get("https://api.github.com")
print(response.json())
```

```bash
# Run directly (uv installs deps automatically)
uv run script.py
```

### Pattern 2: Development Workflow

```bash
# Start new feature
uv sync                    # Ensure environment is up to date

# Add dependency
uv add --dev pytest-asyncio

# Run tests continuously
uv run pytest --watch

# Lint and format
uv run ruff check .
uv run ruff format .

# Type check
uv run mypy src/
```

### Pattern 3: CI/CD Integration

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v1
      - run: uv sync
      - run: uv run pytest
```

## Troubleshooting

**Dependency conflict:**
```bash
# See resolution details
uv add package --verbose

# Force reinstall
uv sync --reinstall

# Check dependency tree
uv pip tree
```

**Lockfile out of sync:**
```bash
# Regenerate lockfile
uv lock

# Sync with new lockfile
uv sync
```

**Cache issues:**
```bash
# Clear cache
uv cache clean

# Reinstall everything
uv sync --reinstall
```

**Python version mismatch:**
```bash
# Use specific Python version
uv python install 3.11
uv sync --python 3.11
```

## UV vs Other Tools

| Task | Old Way | UV Way |
|------|---------|--------|
| Create env | `python -m venv .venv` | `uv init` |
| Activate env | `source .venv/bin/activate` | Not needed (uv run) |
| Install pkg | `pip install requests` | `uv add requests` |
| Install from file | `pip install -r requirements.txt` | `uv sync` |
| Run script | `python script.py` | `uv run script.py` |
| Run tests | `pytest` | `uv run pytest` |
| Global tool | `pipx install black` | `uv tool install black` |
| Lock deps | `pip freeze > requirements.txt` | `uv lock` (automatic) |

## Integration with Other Skills

- **Testing**: Use with `/testing/pytest-shell` for test setup
- **Scripts**: All Python scripts use `uv run` instead of `python`
- **CI/CD**: Include in `/bootstrap` or project setup
- **Documentation**: Use `/eureka` to capture uv workflow insights

## Quick Reference

| Task | Command |
|------|---------|
| Add package | `uv add requests` |
| Add dev package | `uv add --dev pytest` |
| Remove package | `uv remove requests` |
| Sync environment | `uv sync` |
| Run script | `uv run script.py` |
| Run tests | `uv run pytest` |
| Install tool | `uv tool install ruff` |
| Init project | `uv init` |
| Update deps | `uv sync --upgrade` |
| List packages | `uv pip list` |

## Resources

- UV docs: https://docs.astral.sh/uv/
- UV GitHub: https://github.com/astral-sh/uv
- Migration guide: https://docs.astral.sh/uv/guides/migration/
