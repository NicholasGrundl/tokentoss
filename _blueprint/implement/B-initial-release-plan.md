# Plan: Initial v0.1.0 PyPI Release

## Goal
Ship v0.1.0 to PyPI to secure the `tokentoss` package name. No code refactoring — release the current codebase as-is.

## Prerequisites
- All tests passing (`uv run pytest tests/ -x -q`)
- LICENSE, CONTRIBUTING.md, README.md present
- PyPI account + 2FA: done
- Trusted publisher on PyPI: registered
- GitHub `pypi` environment: created (see `github-actions-setup.md`)
- Repo visibility: **public** (required for trusted publisher OIDC)

## Steps

### Step 1: Manual browser steps (human does these)
1. **Create GitHub `pypi` environment**: Repo Settings > Environments > New environment > name it `pypi` > Save
2. **Make repo public**: Repo Settings > General > Danger Zone > Change visibility > Public

### Step 2: Local smoke test (agent can verify)
```bash
# Build the package
uv build

# Verify README renders correctly for PyPI
uv run twine check dist/*

# Install and test in a temp venv
uv run python -c "import tokentoss; print(tokentoss.__version__)"
```

### Step 3: Merge to main and release
- Merge current feature branch to `main` (or create a PR)
- Then run:
```bash
git checkout main
git pull
just release 0.1.0
git push && git push origin v0.1.0
```
- This triggers `release.yml` → builds → publishes to PyPI via OIDC → creates GitHub Release

### Step 4: Verify
- Check https://pypi.org/project/tokentoss/
- `pip install tokentoss` from a clean venv
- Verify the PyPI project page renders the README correctly

## What Agent Can Do (code-side)
- Run the local build + smoke test to make sure the package builds cleanly
- Run `twine check` to verify README/metadata rendering
- Review README.md for anything that should be polished before going public
- Verify CI workflows pass on the current branch
- Help create the PR to merge feature branch into main

## What's Deferred to v0.2.0+
- Widgets subpackage refactor (plan 03)
- Test service on Cloud Run (plan 06)
- Documentation tiers 2 & 3 (plan 07)
- Branch protection rules (can add after first release)
