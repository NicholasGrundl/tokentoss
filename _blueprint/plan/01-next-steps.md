# Next Steps

Overview of remaining work before the first public release. Each item has a dedicated planning document with full details.

## Decisions Made

- **Audience:** End users at various client organizations, each with their own IAP-protected API. All have Gmail or Google Workspace accounts.
- **Distribution:** Public PyPI (`pip install tokentoss`)
- **CI/CD:** GitHub Actions with tag-triggered releases via PyPI trusted publishers (OIDC)

---

## Plan Documents

### 02 — Architectural Analysis
Observations on current limitations (detached token refresh, etc.) and potential improvements for robustness and scalability.

### 03 — Widgets Subpackage
Refactor `widget.py` and `configure_widget.py` into a `widgets/` subpackage. Detailed migration steps, import changes, and an optional future split for `CallbackServer`.

### 04 — Distribution (PyPI)
Public PyPI setup: `pyproject.toml` metadata, README updates, open-source scaffolding (LICENSE, CONTRIBUTING.md, issue templates), and manual PyPI account/trusted publisher setup steps.

### 05 — CI/CD (GitHub Actions)
Two workflows: `ci.yml` (lint, typecheck, test matrix on 3.10/3.11/3.12) and `release.yml` (tag-triggered build + PyPI publish + GitHub Release). Full YAML included.

### 06 — Test Service (Cloud Run + IAP)
A FastAPI microservice deployed behind IAP on Cloud Run to verify tokens end-to-end and demonstrate user-specific content. Full GCP setup walkthrough from zero. Lives at `examples/test-service/`.

### 07 — Documentation & Tutorials
Three-tier doc strategy: Tier 1 (quick-start guide + GCP admin setup for v0.1.0), Tier 2 (API reference + example notebooks), Tier 3 (hosted docs site, troubleshooting guide).

### 08 — Manual Testing
Pre-release checklist covering ConfigureWidget, GoogleAuthWidget, IAPClient, token refresh, sign out/re-auth, and edge cases. Run in JupyterLab before any tagged release.

---

## Suggested Execution Order

1. **Widgets refactor** (03) — code cleanup before release
2. **Distribution prep** (04) — LICENSE, CONTRIBUTING, pyproject.toml URLs
3. **CI/CD setup** (05) — get workflows running on PRs
4. **Test service** (06) — deploy verification endpoint
5. **Manual testing** (08) — verify full flow end-to-end
6. **Docs** (07) — at minimum Tier 1 before tagging v0.1.0
7. **First release** — `git tag v0.1.0 && git push origin v0.1.0`
