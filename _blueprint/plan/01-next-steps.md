# Next Steps — Post v0.1.0

v0.1.0 is released on PyPI and GitHub. This document tracks remaining work for future releases.

## Completed (v0.1.0)

- **Distribution:** Public PyPI (`pip install tokentoss`) — live at https://pypi.org/project/tokentoss/
- **CI/CD:** GitHub Actions with tag-triggered releases via PyPI trusted publishers (OIDC)
- **Manual testing:** Pre-release widget testing in JupyterLab
- **GitHub settings:** Branch protection, required status checks, squash-only merges

Archived plans: 04 (distribution), 05 (CI/CD), 08 (manual testing)

---

## Remaining Plan Documents (v0.2.0+)

### 02 — Architectural Analysis
Observations on current limitations (detached token refresh, global state management, storage security) and potential improvements for robustness and scalability.

### 03 — Widgets Subpackage
Refactor `widget.py` and `configure_widget.py` into a `widgets/` subpackage. Detailed migration steps, import changes, and an optional future split for `CallbackServer`.

### 06 — Test Service (Cloud Run + IAP)
A FastAPI microservice deployed behind IAP on Cloud Run to verify tokens end-to-end and demonstrate user-specific content. Full GCP setup walkthrough from zero.

### 07 — Documentation & Tutorials
Three-tier doc strategy: Tier 1 (quick-start guide + GCP admin setup), Tier 2 (API reference + example notebooks), Tier 3 (hosted docs site, troubleshooting guide). Tier 1 is the next priority.

---

## Suggested Execution Order

1. **Docs Tier 1** (07) — quick-start guide and GCP admin setup
2. **Widgets refactor** (03) — code cleanup before wider adoption
3. **Test service** (06) — deploy verification endpoint
4. **Architectural improvements** (02) — address technical debt
5. **Docs Tiers 2-3** (07) — API reference, hosted docs
