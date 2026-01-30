# Plan: Initial v0.1.0 PyPI Release

## Goal
Ship v0.1.0 to PyPI to secure the `tokentoss` package name. No code refactoring — release the current codebase as-is.

## Current State
- 163 tests passing, CI workflows exist, pyproject.toml ready
- LICENSE, CONTRIBUTING.md, README.md all present
- PyPI account + 2FA: done
- Trusted publisher on PyPI: registered
- GitHub `pypi` environment: **not created yet**
- Repo visibility: **private**

## Steps

### Step 1: Manual browser steps (human does these)
1. **Create GitHub `pypi` environment**: Repo Settings > Environments > New environment > name it `pypi` > Save
2. **Make repo public**: Repo Settings > General > Danger Zone > Change visibility > Public

### Step 2: Local smoke test (agent can verify)
```bash
uv build
uv run pip install dist/tokentoss-0.1.0-py3-none-any.whl
python -c "import tokentoss; print(tokentoss.__version__)"
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

## What Agent Can Do (code-side)
- Run the local build + smoke test to make sure the package builds cleanly
- Review README.md for anything that should be polished before going public
- Verify CI workflows pass on the current branch
- Help create the PR to merge feature branch into main

## What's Deferred to v0.2.0+
- Widgets subpackage refactor (plan 03)
- Test service on Cloud Run (plan 06)
- Documentation tiers 2 & 3 (plan 07)
- Branch protection rules (can add after first release)
