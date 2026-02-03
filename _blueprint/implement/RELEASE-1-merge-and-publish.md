# RELEASE-1: Merge PR & Make Repo Public

> **Prerequisite:** PR #1 (`feature/phase2-widget`) CI checks are all green.
> **Next:** After completing these steps, proceed to `RELEASE-2-v010-pypi.md`.

---

## Step 1: Pre-Merge Checklist

- [ ] All 7 CI checks passing (lint, typecheck, code-scan, test x3, dependency-audit)
- [ ] PR title and description are clean and accurate
- [ ] No uncommitted local changes on `feature/phase2-widget`

## Step 2: Merge PR #1

**Strategy:** Squash merge (80+ micro commits → single clean commit on `main`).

- [ ] Open PR #1 on GitHub
- [ ] Select **Squash and merge**
- [ ] Edit the squash commit message:
  - Title: `feat: add OAuth widgets, IAP client, CI/CD, and release infrastructure`
  - Body: Brief summary of Phase 2 deliverables
- [ ] Confirm merge
- [ ] Pull main locally:
  ```bash
  git checkout main
  git pull origin main
  ```

## Step 3: Make Repository Public

> Required for PyPI trusted publisher (OIDC) to work.

- [ ] Go to repo **Settings > General > Danger Zone**
- [ ] Click **Change visibility** → set to **Public**
- [ ] Confirm the action

### Verify After Making Public
- [ ] Visit `https://github.com/NicholasGrundl/tokentoss` in an incognito window — should be accessible
- [ ] Check the **Actions** tab — existing workflow runs should still be visible

## Step 4: Create GitHub `pypi` Environment

- [ ] Go to repo **Settings > Environments > New environment**
- [ ] Name it exactly: `pypi`
- [ ] Click **Configure environment**
- [ ] Enable **Required reviewers** — add yourself
- [ ] Save

## Step 5: PyPI Account & Trusted Publisher

### Create / Verify PyPI Account
- [ ] Go to [pypi.org](https://pypi.org) and register (or log in)
- [ ] Enable **2FA** (required for publishing)
- [ ] Verify your email

### Register Trusted Publisher
- [ ] Go to [pypi.org](https://pypi.org) > **Your Account** > **Publishing**
- [ ] Click **Add a new pending publisher**
- [ ] Fill in exactly:
  | Field | Value |
  |-------|-------|
  | PyPI project name | `tokentoss` |
  | Owner | `NicholasGrundl` |
  | Repository name | `tokentoss` |
  | Workflow name | `release.yml` |
  | Environment name | `pypi` |
- [ ] Submit

---

## Completion Checklist

Before moving to RELEASE-2:
- [ ] PR #1 merged to `main` via squash merge
- [ ] Local `main` branch is up to date (`git pull`)
- [ ] Repository is public
- [ ] GitHub `pypi` environment exists with required reviewer
- [ ] PyPI trusted publisher registered for `tokentoss`
