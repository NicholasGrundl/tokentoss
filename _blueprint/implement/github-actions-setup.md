# GitHub Actions & Release Setup — Browser TODOs

## GitHub Repository Settings

### Make Repository Public
- [ ] Go to repo **Settings > General > Danger Zone**
- [ ] Click **Change visibility** → set to **Public**
- [ ] Confirm

> Required for PyPI trusted publisher (OIDC) to work.

### Create the `pypi` Environment
- [ ] Go to repo **Settings > Environments > New environment**
- [ ] Name it exactly: `pypi`
- [ ] Click **Configure environment**
- [ ] Enable **Required reviewers** — add yourself
- [ ] Save

### Set Up Branch Protection for `main`
- [ ] Go to repo **Settings > Branches > Add branch ruleset** (or "Add rule")
- [ ] Branch name pattern: `main`
- [ ] Enable:
  - **Require a pull request before merging** (no direct pushes)
  - **Require approvals**: set to 1
  - **Require status checks to pass** — select `lint`, `typecheck`, and `test`
- [ ] Save

### (Optional) Create a `release` Environment
If you want manual approval before GitHub Releases are created (separate from PyPI publish):
- [ ] Settings > Environments > New environment
- [ ] Name: `release`
- [ ] Enable **Required reviewers** — add yourself
- [ ] Save
- [ ] Ask Claude to add `environment: release` to the `github-release` job in `release.yml`

---

## PyPI Account Setup

### Create / Verify PyPI Account
- [ ] Go to [pypi.org](https://pypi.org) and register (or log in)
- [ ] Enable **2FA** (required for publishing)
- [ ] Verify your email

### Register Trusted Publisher on PyPI
- [ ] Go to [pypi.org](https://pypi.org) > **Your Account** > **Publishing**
- [ ] Click **Add a new pending publisher**
- [ ] Fill in:
  - **PyPI project name**: `tokentoss`
  - **Owner**: `NicholasGrundl`
  - **Repository name**: `tokentoss`
  - **Workflow name**: `release.yml`
  - **Environment name**: `pypi`
- [ ] Submit

---

## First CI Run

### Push Branch and Open a PR
```bash
git push -u origin <your-feature-branch>
gh pr create --title "Your PR title" --body "..."
```
- [ ] Watch the **Actions** tab — CI (lint, typecheck, test x3) and Security (pip-audit, bandit) workflows should trigger
- [ ] Verify all checks pass before merging

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
- [ ] Watch the Actions tab. If PyPI publish fails (e.g., trusted publisher not configured yet), the build and GitHub Release jobs still give useful signal.
