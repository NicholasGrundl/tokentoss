# GitHub Actions & Release Setup — Browser TODOs

## GitHub Repository Settings

### Create the `pypi` Environment
1. Go to repo **Settings > Environments > New environment**
2. Name it exactly: `pypi`
3. Click **Configure environment**
4. Enable **Required reviewers** — add yourself
5. Save

### Set Up Branch Protection for `main`
1. Go to repo **Settings > Branches > Add branch ruleset** (or "Add rule")
2. Branch name pattern: `main`
3. Enable:
   - **Require a pull request before merging** (no direct pushes)
   - **Require approvals**: set to 1
   - **Require status checks to pass** — select `lint`, `typecheck`, and `test`
4. Save

### (Optional) Create a `release` Environment
If you want manual approval before GitHub Releases are created (separate from PyPI publish):
1. Settings > Environments > New environment
2. Name: `release`
3. Enable **Required reviewers** — add yourself
4. Save
5. Ask Claude to add `environment: release` to the `github-release` job in `release.yml`

---

## PyPI Account Setup

### Create / Verify PyPI Account
1. Go to [pypi.org](https://pypi.org) and register (or log in)
2. Enable **2FA** (required for publishing)
3. Verify your email

### Register Trusted Publisher on PyPI
1. Go to [pypi.org](https://pypi.org) > **Your Account** > **Publishing**
2. Click **Add a new pending publisher**
3. Fill in:
   - **PyPI project name**: `tokentoss`
   - **Owner**: `NicholasGrundl`
   - **Repository name**: `tokentoss`
   - **Workflow name**: `release.yml`
   - **Environment name**: `pypi`
4. Submit

---

## First CI Run

### Push Branch and Open a PR
```bash
git push -u origin feature/phase2-widget
gh pr create --title "Phase 2: widget implementation" --body "..."
```
- Watch the **Actions** tab — CI (lint, typecheck, test x3) and Security (pip-audit, bandit) workflows should trigger
- Verify all checks pass before merging

---

## First Release

### After Merging to Main
```bash
git checkout main
git pull
just release 0.1.0
git push && git push origin v0.1.0
```

This will:
1. Bump version in `pyproject.toml`
2. Commit the version bump
3. Create tag `v0.1.0`
4. Push code and tag — triggering the Release workflow (build > publish to PyPI + GitHub Release)

### (Optional) Dry-Run with Release Candidate
If you want to test the pipeline first:
```bash
git tag v0.1.0-rc1
git push origin v0.1.0-rc1
```
Watch the Actions tab. If PyPI publish fails (e.g., trusted publisher not configured yet), the build and GitHub Release jobs still give useful signal.
