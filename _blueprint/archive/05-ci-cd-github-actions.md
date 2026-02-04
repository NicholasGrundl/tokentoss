# CI/CD: GitHub Actions

## Decision

**Use GitHub Actions for CI and release automation.** Git tag pushes (`v*`) trigger PyPI publishing via trusted publishers (OIDC — no API tokens).

---

## CI Workflow

**File:** `.github/workflows/ci.yml`

**Triggers:** Push to `main`, PRs to `main`

### Jobs (run in parallel)

#### `lint`
- Single Python version (latest)
- `uv run ruff format --check src/ tests/`
- `uv run ruff check src/ tests/`

#### `typecheck`
- Single Python version (latest)
- `uv run ty check src/`
- Separate job because `ty` is alpha — failures here don't block knowing if tests pass
- Can add `continue-on-error: true` later if desired

#### `test`
- Matrix: Python 3.10, 3.11, 3.12
- `uv run pytest tests/ -v`

### Implementation

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          version: "latest"
      - run: uv sync --group dev
      - run: uv run ruff format --check src/ tests/
      - run: uv run ruff check src/ tests/

  typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          version: "latest"
      - run: uv sync --group dev
      - run: uv run ty check src/

  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          version: "latest"
      - run: uv python install ${{ matrix.python-version }}
      - run: uv sync --group dev --python ${{ matrix.python-version }}
      - run: uv run pytest tests/ -v
```

### Design notes

- **`astral-sh/setup-uv@v4`**: Official action, handles uv install + caching
- **No `actions/setup-python`**: uv manages Python versions via `uv python install`
- **Three separate jobs**: Parallel execution, clearer failure signals
- **`uv sync --group dev`**: Installs all dev dependencies (ruff, ty, pytest, etc.)

---

## Release Workflow

**File:** `.github/workflows/release.yml`

**Trigger:** Tag push matching `v*`

### Jobs

#### `build`
- `uv build` → produces `.tar.gz` and `.whl` in `dist/`
- Upload as artifact for downstream jobs

#### `publish` (needs build)
- Downloads build artifact
- Publishes to PyPI via `pypa/gh-action-pypi-publish@release/v1`
- Uses trusted publishing (OIDC) — `permissions: id-token: write`
- Requires GitHub environment `pypi`

#### `github-release` (needs build)
- Downloads build artifact
- Creates GitHub Release with `gh release create --generate-notes`
- Attaches built artifacts

### Implementation

```yaml
name: Release

on:
  push:
    tags:
      - "v*"

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          version: "latest"
      - run: uv build
      - uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/

  publish:
    needs: build
    runs-on: ubuntu-latest
    environment: pypi
    permissions:
      id-token: write
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/
      - uses: pypa/gh-action-pypi-publish@release/v1

  github-release:
    needs: build
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/
      - name: Create GitHub Release
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          gh release create ${{ github.ref_name }} dist/* \
            --title "${{ github.ref_name }}" \
            --generate-notes
```

### Design notes

- **Trusted publishing (OIDC):** No PyPI API tokens to manage. GitHub Actions mints a short-lived OIDC token that PyPI verifies. Modern recommended approach.
- **`uv build`:** Uses hatchling via PEP 517. Consistent with the rest of the project's uv-based tooling.
- **Build once, publish to both:** Same artifacts go to PyPI and GitHub Releases.
- **`environment: pypi`:** Required for trusted publisher. Created in repo Settings → Environments.

---

## GitHub Environment Setup

Before the first release:

1. Go to `https://github.com/NicholasGrundl/tokentoss/settings/environments`
2. Create environment named `pypi`
3. Optionally add deployment protection rules (e.g., require manual approval before publish)

---

## Release Process

Once everything is set up, releasing a new version:

```bash
# 1. Update version in pyproject.toml
# 2. Commit the version bump
git add pyproject.toml
git commit -m "release: v0.2.0"

# 3. Tag and push
git tag v0.2.0
git push origin main --tags

# 4. Watch Actions tab — build → publish → github-release
```

The workflow handles everything from there: build, publish to PyPI, create GitHub Release with auto-generated notes.

---

## Files to Create

| File | Purpose |
|------|---------|
| `.github/workflows/ci.yml` | PR/push CI pipeline (lint, typecheck, test matrix) |
| `.github/workflows/release.yml` | Tag-triggered release pipeline (build, PyPI publish, GitHub Release) |

## Files to Modify

| File | Change |
|------|--------|
| `pyproject.toml` | Add `[project.urls]` (see distribution plan) |
| `README.md` | Add CI badge (see distribution plan) |
