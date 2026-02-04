# RELEASE-2: Ship v0.1.0 to PyPI

> **Prerequisite:** All steps in `RELEASE-1-merge-and-publish.md` are complete (PR merged, repo public, PyPI trusted publisher registered).

---

## Step 1: Create Release Branch

```bash
git checkout main
git pull origin main
git checkout -b release/v0.1.0
```

## Step 2: Local Smoke Tests

### Build the package
```bash
uv build
```
- [ ] Build completes without errors
- [ ] `dist/` contains both `.tar.gz` and `.whl` files

### Verify metadata renders
```bash
uv run twine check dist/*
```
- [ ] `PASSED` for all dist files (README renders correctly for PyPI)

### Import test
```bash
uv run python -c "import tokentoss; print(tokentoss.__version__)"
```
- [ ] Prints `0.1.0`

### Run full test suite
```bash
uv run pytest tests/ -x -q
```
- [ ] All tests pass

## Step 3: Verify Public Links

Now that the repo is public, confirm all URLs in README and pyproject.toml resolve:

- [ ] Homepage: https://github.com/NicholasGrundl/tokentoss
- [ ] Repository: https://github.com/NicholasGrundl/tokentoss
- [ ] Issues: https://github.com/NicholasGrundl/tokentoss/issues
- [ ] CI badge URL resolves and shows passing status

## Step 4: Manual Widget Testing (Abbreviated)

Run through the key flows in JupyterLab. Full procedure in `E-widget-testing-guide.md`.

### ConfigureWidget
- [ ] Widget renders with client ID and client secret fields
- [ ] Saving writes config file with `0o600` permissions

### GoogleAuthWidget
- [ ] Widget picks up saved credentials and renders sign-in button
- [ ] OAuth popup flow completes successfully
- [ ] Widget updates to show signed-in state

### Sign Out + Re-Auth
- [ ] Sign out clears widget state
- [ ] Re-authentication works without errors

### IAPClient (if test service available)
- [ ] `IAPClient` makes authenticated request to IAP-protected endpoint
- [ ] Response includes user identity from IAP headers

> If no test service is deployed yet, skip IAPClient testing. It is deferred to post-release.

## Step 5: Open PR

```bash
git push -u origin release/v0.1.0
gh pr create --title "Release v0.1.0" --body "Smoke tests and manual verification for first PyPI release."
```
- [ ] CI checks pass on the PR
- [ ] Review and merge to `main` (squash or regular merge — single commit either way)

## Step 6: Tag and Release

```bash
git checkout main
git pull origin main
just release 0.1.0
git push && git push origin v0.1.0
```

This triggers `release.yml`:
1. **build** — `uv build` creates dist artifacts
2. **publish** — uploads to PyPI via OIDC trusted publisher
3. **github-release** — creates GitHub Release with auto-generated notes

- [ ] Watch the **Actions** tab — all three jobs should succeed
- [ ] If publish fails, check that the trusted publisher on PyPI matches exactly (owner, repo, workflow, environment)

### (Optional) Dry-Run with Release Candidate
To test the pipeline without publishing a real release:
```bash
git tag v0.1.0-rc1
git push origin v0.1.0-rc1
```

## Step 7: Post-Release Verification

### PyPI
- [ ] Visit https://pypi.org/project/tokentoss/
- [ ] README renders correctly on the PyPI page
- [ ] Version shows `0.1.0`

### Clean install test
```bash
# In a temporary directory with no existing tokentoss install
uv venv /tmp/tokentoss-test && source /tmp/tokentoss-test/bin/activate
pip install tokentoss
python -c "import tokentoss; print(tokentoss.__version__)"
deactivate && rm -rf /tmp/tokentoss-test
```
- [ ] Install succeeds from PyPI
- [ ] Version prints `0.1.0`

### GitHub Release
- [ ] Visit https://github.com/NicholasGrundl/tokentoss/releases
- [ ] Release `v0.1.0` exists with auto-generated notes
- [ ] Source archives and dist artifacts are attached

---

## Deferred to v0.2.0+

The following items are explicitly out of scope for v0.1.0:

| Item | Reference |
|------|-----------|
| Widgets subpackage refactor | `plan/03-widgets-subpackage.md` |
| Test service Cloud Run deployment | `plan/06-test-service-cloud-run.md`, `D-test-service-gcp-setup.md` |
| Documentation tiers 2-3 | `plan/07-docs-and-tutorials.md` |
| Architectural improvements | `plan/02-architectural-analysis.md` |
| Branch protection rules | `A-github-actions-setup.md` |
