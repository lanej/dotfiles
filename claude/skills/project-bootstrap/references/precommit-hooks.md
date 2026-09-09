# Pre-Commit Hooks by Language

Ready-to-use `.git/hooks/pre-commit` scripts. Write the one matching the project's language, then `chmod +x .git/hooks/pre-commit`.

Keep these fast — format, lint, and unit tests only. Anything slower than ~5 seconds belongs in CI, not a commit hook.

**For Rust projects**:
```bash
#!/bin/sh
# Pre-commit hook for Rust projects

echo "Running pre-commit checks..."

# Format check
echo "→ Checking code formatting..."
if ! cargo fmt --check; then
    echo "❌ Code formatting issues found. Run: cargo fmt"
    exit 1
fi

# Clippy check
echo "→ Running clippy..."
if ! cargo clippy --all-targets --all-features -- -D warnings; then
    echo "❌ Clippy warnings found. Run: cargo clippy --fix --allow-dirty"
    exit 1
fi

# Build check
echo "→ Building project..."
if ! cargo build --quiet; then
    echo "❌ Build failed"
    exit 1
fi

# Fast tests (unit tests only)
echo "→ Running unit tests..."
if ! cargo test --lib --quiet; then
    echo "❌ Unit tests failed"
    exit 1
fi

echo "✓ All pre-commit checks passed"
```

**For Go projects**:
```bash
#!/bin/sh
# Pre-commit hook for Go projects

echo "Running pre-commit checks..."

# Format check
echo "→ Checking code formatting..."
if [ -n "$(gofmt -l .)" ]; then
    echo "❌ Code formatting issues found. Run: gofmt -w ."
    exit 1
fi

# Vet check
echo "→ Running go vet..."
if ! go vet ./...; then
    echo "❌ Go vet found issues"
    exit 1
fi

# Build check
echo "→ Building project..."
if ! go build ./...; then
    echo "❌ Build failed"
    exit 1
fi

# Fast tests
echo "→ Running tests..."
if ! go test -short ./...; then
    echo "❌ Tests failed"
    exit 1
fi

echo "✓ All pre-commit checks passed"
```

**For TypeScript/Node projects**:
```bash
#!/bin/sh
# Pre-commit hook for TypeScript/Node projects

echo "Running pre-commit checks..."

# Format check
echo "→ Checking code formatting..."
if ! npm run format:check 2>/dev/null && ! npx prettier --check . 2>/dev/null; then
    echo "❌ Code formatting issues found. Run: npm run format or npx prettier --write ."
    exit 1
fi

# Lint check
echo "→ Running linter..."
if ! npm run lint 2>/dev/null && ! npx eslint . 2>/dev/null; then
    echo "❌ Linting issues found"
    exit 1
fi

# Type check
echo "→ Running type check..."
if ! npm run type-check 2>/dev/null && ! npx tsc --noEmit 2>/dev/null; then
    echo "❌ Type check failed"
    exit 1
fi

# Build check
echo "→ Building project..."
if ! npm run build 2>/dev/null; then
    echo "⚠ Build script not found or failed (optional)"
fi

# Fast tests
echo "→ Running tests..."
if npm run test:unit 2>/dev/null || npm test 2>/dev/null; then
    echo "✓ Tests passed"
else
    echo "⚠ Tests not configured or failed (optional)"
fi

echo "✓ All pre-commit checks passed"
```

**For Python projects**:
```bash
#!/bin/sh
# Pre-commit hook for Python projects

echo "Running pre-commit checks..."

# Format check
echo "→ Checking code formatting..."
if ! black --check . 2>/dev/null && ! ruff format --check . 2>/dev/null; then
    echo "❌ Code formatting issues found. Run: black . or ruff format ."
    exit 1
fi

# Lint check
echo "→ Running linter..."
if ! ruff check . 2>/dev/null && ! flake8 . 2>/dev/null; then
    echo "❌ Linting issues found"
    exit 1
fi

# Type check
echo "→ Running type check..."
if ! mypy . 2>/dev/null && ! pyright . 2>/dev/null; then
    echo "⚠ Type check not configured or failed (optional)"
fi

# Fast tests
echo "→ Running tests..."
if pytest tests/ -k "not integration" 2>/dev/null || python -m pytest tests/ 2>/dev/null; then
    echo "✓ Tests passed"
else
    echo "⚠ Tests not configured or failed (optional)"
fi

echo "✓ All pre-commit checks passed"
```

**Installation steps**:
1. Create the appropriate pre-commit hook based on detected language
2. Make it executable: `chmod +x .git/hooks/pre-commit`
3. Confirm: "✓ Pre-commit hooks installed"
4. Inform user: "Pre-commit hook will run format checks, linting, build verification, and fast tests before each commit"

**Note on dependency checks**:
Dependency audits are too slow for pre-commit hooks (10-30 seconds). Instead, recommend adding to Justfile for periodic checks:

**Rust**: `just check-deps` → `cargo outdated && cargo audit`
**Go**: `just check-deps` → `go list -u -m all`
**TypeScript**: `just check-deps` → `npm outdated && npm audit`
**Python**: `just check-deps` → `pip list --outdated && safety check`

Suggest running weekly or before releases, not on every commit.
