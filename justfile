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

# Full release flow: bump version, commit, tag, push
start-release NEW_VERSION:
    #!/usr/bin/env bash
    set -euo pipefail

    # Validate version format
    if ! echo "{{ NEW_VERSION }}" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$'; then
      echo "Error: Invalid version format '{{ NEW_VERSION }}'. Expected: X.Y.Z or X.Y.Z-suffix"
      exit 1
    fi

    # Check on main branch
    BRANCH=$(git branch --show-current)
    if [ "$BRANCH" != "main" ]; then
      echo "Error: Must be on 'main' branch to release (currently on '$BRANCH')"
      exit 1
    fi

    # Check working tree is clean
    if [ -n "$(git status --porcelain)" ]; then
      echo "Error: Working tree is not clean. Commit or stash changes first."
      exit 1
    fi

    # Check up to date with remote
    git fetch origin main --quiet
    LOCAL=$(git rev-parse HEAD)
    REMOTE=$(git rev-parse origin/main)
    if [ "$LOCAL" != "$REMOTE" ]; then
      echo "Error: Local main is not up to date with origin. Run 'git pull' first."
      exit 1
    fi

    # Check tag doesn't already exist
    if git tag -l | grep -q "^v{{ NEW_VERSION }}$"; then
      echo "Error: Tag v{{ NEW_VERSION }} already exists locally"
      exit 1
    fi
    if git ls-remote --tags origin | grep -q "refs/tags/v{{ NEW_VERSION }}$"; then
      echo "Error: Tag v{{ NEW_VERSION }} already exists on remote"
      exit 1
    fi

    # All checks passed — execute release
    just bump {{ NEW_VERSION }}
    git add pyproject.toml uv.lock
    git commit -m "chore: bump version to {{ NEW_VERSION }}"
    just tag
    git push origin main && git push origin v{{ NEW_VERSION }}
    echo ""
    echo "Release v{{ NEW_VERSION }} pushed. Watch Actions tab for publish status."

# Build the package locally (for inspection)
build:
    uv build
    @echo "Built packages:"
    @ls -lh dist/

# Verify built package metadata (README renders correctly for PyPI)
check:
    uvx twine check dist/*
