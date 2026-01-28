---
description: "Generate pytest-based tests for shell scripts with dependency injection, subprocess testing, mocking, and TDD workflow following project testing standards"
argument-hint: [script path]
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - Bash(uv:*)
  - Bash(pytest:*)
model: sonnet
tags:
  - testing
  - pytest
  - tdd
  - shell
  - bash
---

# Pytest Shell Testing - Generate Tests for Shell Scripts

Create comprehensive pytest-based test suites for shell scripts following TDD principles and dependency injection patterns.

## Overview

**Why pytest for shell scripts?**
- Superior to bats and shell-based testing frameworks
- Better fixtures, parametrization, coverage reporting
- Excellent IDE integration and debugging
- Subprocess testing with proper isolation
- Easy mocking and dependency injection

**Testing philosophy (from project standards):**
- Write tests BEFORE implementation (TDD)
- Use dependency injection for testability
- NO flaky tests - fix immediately
- Run tests before AND after changes
- 100% deterministic test suite

## Usage

```bash
/testing/pytest-shell path/to/script.sh           # Generate tests for script
/testing/pytest-shell path/to/script.sh --tdd     # TDD mode (tests first)
/testing/pytest-shell --help                      # Show testing patterns
```

## Workflow

### 1. Analyze the Script

**Read the shell script:**
```bash
# Read target script
cat path/to/script.sh
```

**Identify:**
- **Purpose**: What does the script do?
- **Dependencies**: External commands, files, environment variables
- **Inputs**: Command-line arguments, stdin, files
- **Outputs**: stdout, stderr, exit codes, file modifications
- **Side effects**: File creation, API calls, state changes

**Determine test approach:**
- **Simple scripts**: Direct subprocess execution
- **Complex scripts**: Dependency injection wrapper
- **Scripts with external deps**: Extensive mocking needed

### 2. Set Up Test Environment

**Check for existing test structure:**
```bash
# Look for test directory
ls tests/ test/ */tests/

# Check for pytest config
ls pyproject.toml pytest.ini setup.cfg
```

**Create test structure if needed:**
```bash
# Initialize Python project with uv
uv init --no-package  # If no pyproject.toml exists

# Add pytest dependencies
uv add --dev pytest pytest-cov pytest-mock

# Create test directory
mkdir -p tests
```

**Configure pytest (in pyproject.toml):**
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
addopts = [
    "-v",
    "--strict-markers",
    "--cov=scripts",
    "--cov-report=term-missing",
]
```

### 3. Generate Test File

**Test file naming:**
```
scripts/my_script.sh  →  tests/test_my_script.py
bin/deploy.sh         →  tests/test_deploy.py
```

**Test structure template:**
```python
"""Tests for <script-name>.sh

Test coverage:
- Happy path scenarios
- Error handling
- Edge cases
- Dependency interactions
"""

import subprocess
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, call


# ===== Fixtures =====

@pytest.fixture
def script_path():
    """Path to the script under test."""
    return Path(__file__).parent.parent / "scripts" / "my_script.sh"


@pytest.fixture
def mock_env(monkeypatch):
    """Mock environment variables."""
    test_env = {
        "HOME": "/tmp/test_home",
        "USER": "testuser",
    }
    for key, value in test_env.items():
        monkeypatch.setenv(key, value)
    return test_env


@pytest.fixture
def temp_workspace(tmp_path):
    """Create temporary workspace for file operations."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace


# ===== Helper Functions =====

def run_script(script_path, args=None, input_data=None, env=None):
    """Run shell script and return result.

    Args:
        script_path: Path to script
        args: List of command-line arguments
        input_data: String to send to stdin
        env: Environment variables dict

    Returns:
        CompletedProcess with stdout, stderr, returncode
    """
    cmd = ["bash", str(script_path)]
    if args:
        cmd.extend(args)

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        input=input_data,
        env=env,
    )
    return result


# ===== Tests =====

class TestBasicFunctionality:
    """Test core script functionality."""

    def test_script_exists(self, script_path):
        """Verify script file exists and is executable."""
        assert script_path.exists()
        assert script_path.stat().st_mode & 0o111  # Check executable bit

    def test_no_arguments_shows_help(self, script_path):
        """Running without arguments should show usage."""
        result = run_script(script_path)

        assert result.returncode != 0
        assert "usage" in result.stderr.lower() or "usage" in result.stdout.lower()

    def test_help_flag(self, script_path):
        """Test --help flag."""
        result = run_script(script_path, args=["--help"])

        assert result.returncode == 0
        assert "usage" in result.stdout.lower()


class TestHappyPath:
    """Test successful execution scenarios."""

    def test_basic_execution(self, script_path, temp_workspace):
        """Test basic script execution with valid input."""
        result = run_script(
            script_path,
            args=["arg1", "arg2"],
        )

        assert result.returncode == 0
        assert "success" in result.stdout.lower()

    @pytest.mark.parametrize("input_value,expected", [
        ("value1", "output1"),
        ("value2", "output2"),
        ("value3", "output3"),
    ])
    def test_various_inputs(self, script_path, input_value, expected):
        """Test script with different input values."""
        result = run_script(script_path, args=[input_value])

        assert result.returncode == 0
        assert expected in result.stdout


class TestErrorHandling:
    """Test error conditions and edge cases."""

    def test_invalid_argument(self, script_path):
        """Test script with invalid argument."""
        result = run_script(script_path, args=["--invalid-flag"])

        assert result.returncode != 0
        assert "error" in result.stderr.lower() or "invalid" in result.stderr.lower()

    def test_missing_required_file(self, script_path, temp_workspace):
        """Test script when required file is missing."""
        result = run_script(
            script_path,
            args=[str(temp_workspace / "nonexistent.txt")],
        )

        assert result.returncode != 0
        assert "not found" in result.stderr.lower() or "error" in result.stderr.lower()

    def test_permission_denied(self, script_path, temp_workspace):
        """Test script with permission denied scenario."""
        readonly_file = temp_workspace / "readonly.txt"
        readonly_file.write_text("test")
        readonly_file.chmod(0o444)

        result = run_script(script_path, args=[str(readonly_file)])

        assert result.returncode != 0


class TestDependencyInjection:
    """Test with mocked external dependencies."""

    @patch("subprocess.run")
    def test_git_command_called(self, mock_run, script_path):
        """Test that script calls git with correct arguments."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        # This requires wrapping the script in Python
        # See dependency injection pattern below

    def test_with_mocked_environment(self, script_path, monkeypatch):
        """Test script with mocked environment."""
        monkeypatch.setenv("CUSTOM_VAR", "test_value")

        result = run_script(script_path)

        assert result.returncode == 0
        assert "test_value" in result.stdout


class TestFileOperations:
    """Test file creation and modification."""

    def test_creates_output_file(self, script_path, temp_workspace):
        """Test that script creates expected output file."""
        output_file = temp_workspace / "output.txt"

        result = run_script(
            script_path,
            args=["--output", str(output_file)],
        )

        assert result.returncode == 0
        assert output_file.exists()
        assert output_file.read_text() == "expected content"

    def test_file_content_correctness(self, script_path, temp_workspace):
        """Test that created file has correct content."""
        output_file = temp_workspace / "output.txt"

        run_script(script_path, args=["--output", str(output_file)])

        content = output_file.read_text()
        assert "expected line 1" in content
        assert "expected line 2" in content


# ===== Coverage and Performance =====

class TestCoverage:
    """Ensure all code paths are tested."""

    def test_all_flags_covered(self, script_path):
        """Test all command-line flags."""
        flags = ["--verbose", "--quiet", "--debug"]

        for flag in flags:
            result = run_script(script_path, args=[flag])
            # Each flag should be handled
            assert result.returncode in [0, 1]  # Not crash


@pytest.mark.slow
class TestPerformance:
    """Performance and stress tests."""

    def test_handles_large_input(self, script_path, temp_workspace):
        """Test script with large input file."""
        large_file = temp_workspace / "large.txt"
        large_file.write_text("x" * 1_000_000)  # 1MB

        result = run_script(script_path, args=[str(large_file)])

        assert result.returncode == 0
```

### 4. Dependency Injection Pattern (Advanced)

**For complex scripts needing mocking:**

**Original script (my_script.sh):**
```bash
#!/bin/bash
# Direct dependencies (hard to test)
git status
curl https://api.example.com/data
```

**Wrapper for dependency injection (scripts/my_script.sh):**
```bash
#!/bin/bash
# Accept dependencies as environment variables with defaults
GIT_CMD="${GIT_CMD:-git}"
CURL_CMD="${CURL_CMD:-curl}"

"$GIT_CMD" status
"$CURL_CMD" https://api.example.com/data
```

**Test with injected dependencies:**
```python
def test_with_mocked_git(script_path, tmp_path):
    """Test with mocked git command."""
    # Create mock git script
    mock_git = tmp_path / "git"
    mock_git.write_text("#!/bin/bash\necho 'mocked git output'")
    mock_git.chmod(0o755)

    # Inject mock via environment
    result = subprocess.run(
        ["bash", str(script_path)],
        capture_output=True,
        text=True,
        env={"GIT_CMD": str(mock_git), "PATH": os.environ["PATH"]},
    )

    assert result.returncode == 0
    assert "mocked git output" in result.stdout
```

### 5. Run Tests

**Run test suite:**
```bash
# All tests
uv run pytest

# Specific file
uv run pytest tests/test_my_script.py

# With coverage
uv run pytest --cov=scripts --cov-report=html --cov-report=term-missing

# Verbose output
uv run pytest -v

# Stop on first failure
uv run pytest -x

# Run only tests matching pattern
uv run pytest -k "test_error"
```

**Watch mode (continuous testing):**
```bash
# Install pytest-watch
uv add --dev pytest-watch

# Run in watch mode
uv run ptw
```

### 6. Fix Flaky Tests

**If tests are non-deterministic:**

**DON'T:**
```python
# ❌ NEVER add retries or sleeps
@pytest.mark.flaky(reruns=3)  # Masks the problem
def test_something():
    time.sleep(1)  # Timing dependency
```

**DO:**
```python
# ✅ Fix the root cause
def test_something(monkeypatch):
    # Use deterministic mocks
    monkeypatch.setattr("random.random", lambda: 0.5)
    # Use fixed time
    monkeypatch.setattr("time.time", lambda: 1234567890)
    # Use temp files, not shared state
    # Inject dependencies for control
```

**Common flaky test causes:**
- Race conditions → Use deterministic execution
- Shared state → Use fixtures for isolation
- Timing dependencies → Mock time functions
- External dependencies → Mock or use fakes
- Randomness → Seed or mock random functions

## TDD Workflow

**Red-Green-Refactor:**

1. **Red**: Write failing test first
```bash
/testing/pytest-shell path/to/script.sh --tdd
# Generate tests based on requirements
uv run pytest  # Tests fail (script doesn't exist yet)
```

2. **Green**: Implement minimum code to pass
```bash
# Write script implementation
vim path/to/script.sh
uv run pytest  # Tests pass
```

3. **Refactor**: Improve code while keeping tests green
```bash
# Refactor script for better design
uv run pytest  # Tests still pass
```

## Integration with Project Standards

**Following CLAUDE.md requirements:**
- ✅ pytest preferred over bats
- ✅ Dependency injection for testability
- ✅ Run tests before changes (establish baseline)
- ✅ Write tests before implementation (TDD)
- ✅ No flaky tests (fix immediately)
- ✅ Coverage reporting with pytest-cov

## Quick Reference

| Task | Command |
|------|---------|
| Generate tests | `/testing/pytest-shell script.sh` |
| Run tests | `uv run pytest` |
| Run with coverage | `uv run pytest --cov` |
| Run specific test | `uv run pytest tests/test_script.py::test_name` |
| Debug test | `uv run pytest -vv --pdb` |
| Watch mode | `uv run ptw` |

## Resources

- pytest docs: https://docs.pytest.org/
- pytest-mock: https://pytest-mock.readthedocs.io/
- subprocess testing: https://docs.python.org/3/library/subprocess.html
- Coverage.py: https://coverage.readthedocs.io/
