# tokentoss project commands
# Install just: brew install just (macOS) or cargo install just
# Run: just <recipe>    List all: just --list

# Development ─────────────────────────────────────────────

# Run the full test suite
test *FLAGS:
    uv run pytest tests/ -x -q {{ FLAGS }}

# Run integration tests only
test-integration:
    uv run pytest tests/ -m integration -x -q

# Run linter and formatter checks (same as CI)
lint:
    uv run ruff format --check src/ tests/
    uv run ruff check src/ tests/

# Auto-fix formatting and lint issues
fix:
    uv run ruff format src/ tests/
    uv run ruff check src/ tests/ --fix

# Run type checker
typecheck:
    uv run ty check src/

# Run all CI checks locally
ci: lint typecheck test

# Security ────────────────────────────────────────────────

# Audit dependencies for known vulnerabilities
audit:
    uv run pip-audit

# Scan source code for security issues
security-scan:
    uv run bandit -r src/ -c pyproject.toml

# Run all security checks
security: audit security-scan

# Release ─────────────────────────────────────────────────

# Show the current version
version:
    @grep '^version' pyproject.toml | head -1 | cut -d'"' -f2

# Bump version: just bump 0.2.0
bump NEW_VERSION:
    #!/usr/bin/env bash
    set -euo pipefail
    OLD_VERSION=$(grep '^version' pyproject.toml | head -1 | cut -d'"' -f2)
    sed -i '' "s/^version = \"$OLD_VERSION\"/version = \"$NEW_VERSION\"/" pyproject.toml
    echo "Bumped version: $OLD_VERSION → $NEW_VERSION"

# Tag a release: just tag (uses version from pyproject.toml)
tag:
    #!/usr/bin/env bash
    set -euo pipefail
    VERSION=$(grep '^version' pyproject.toml | head -1 | cut -d'"' -f2)
    echo "Creating tag v$VERSION..."
    git tag "v$VERSION"
    echo "Tag v$VERSION created. Push with: git push origin v$VERSION"

# Full release flow: bump version, commit, tag
release NEW_VERSION:
    #!/usr/bin/env bash
    set -euo pipefail
    just bump {{ NEW_VERSION }}
    git add pyproject.toml uv.lock
    git commit -m "chore: bump version to {{ NEW_VERSION }}"
    just tag
    echo ""
    echo "Release v{{ NEW_VERSION }} prepared locally."
    echo "Next steps:"
    echo "  git push && git push origin v{{ NEW_VERSION }}"

# Build the package locally (for inspection)
build:
    uv build
    @echo "Built packages:"
    @ls -lh dist/
