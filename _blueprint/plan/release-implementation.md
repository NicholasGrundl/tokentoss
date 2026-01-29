# Plan: Distribution, CI/CD, Test Service, and Docs

Three parallel workstreams to prepare tokentoss for its first public release.

---

## Workstream A: Distribution + CI/CD

### New files

| File | Contents |
|------|----------|
| `LICENSE` | Standard MIT license text (Copyright 2025 Nicholas Grundl) |
| `CONTRIBUTING.md` | Dev setup (`uv sync --group dev`), running checks (format/lint/typecheck/test), PR workflow |
| `.github/ISSUE_TEMPLATE/bug_report.md` | Bug report template (description, repro steps, environment) |
| `.github/ISSUE_TEMPLATE/feature_request.md` | Feature request template (problem, proposed solution) |
| `.github/workflows/ci.yml` | 3 parallel jobs: **lint** (ruff format + check), **typecheck** (ty), **test** (pytest matrix 3.10/3.11/3.12). Uses `astral-sh/setup-uv@v4`. Triggers on push to main + PRs |
| `.github/workflows/release.yml` | Tag-triggered (`v*`). Jobs: **build** (`uv build`), **publish** (PyPI via trusted publishers/OIDC), **github-release** (`gh release create`). Requires GitHub environment `pypi` |

### Modifications

| File | Change |
|------|--------|
| `pyproject.toml` | Add `[project.urls]` section (Homepage, Repository, Issues, Changelog) |
| `README.md` | Add PyPI + CI + Python + License badges after heading; fix `yourusername` → `NicholasGrundl` in clone URL |

### Manual setup (not code — maintainer action items)
1. Create PyPI account + enable 2FA
2. Register trusted publisher on PyPI (project: `tokentoss`, workflow: `release.yml`, environment: `pypi`)
3. Create GitHub environment named `pypi` in repo Settings → Environments

---

## Workstream B: Test Service

All files under `examples/test-service/`.

| File | Contents |
|------|----------|
| `main.py` | FastAPI app (~80 lines). Endpoints: `GET /health` (no auth), `GET /` (service info), `GET /whoami` (returns IAP user identity from headers), `GET /protected` (user-specific content with in-memory request counter). Helper `get_iap_user()` extracts IAP headers. Returns 401 if headers missing. |
| `Dockerfile` | `python:3.12-slim`, install requirements, copy main.py, expose 8080, run uvicorn |
| `requirements.txt` | `fastapi>=0.110.0`, `uvicorn[standard]>=0.29.0` |
| `README.md` | Deploy guide: enable GCP APIs → deploy to Cloud Run → set up load balancer + IAP → configure OAuth consent screen → create Desktop OAuth client → add to IAP programmatic access → grant user access. Includes local testing with simulated IAP headers and cleanup commands. |

---

## Workstream C: Tier 1 Docs

| File | Contents |
|------|----------|
| `docs/quickstart.md` | End-user guide: install → configure credentials (ConfigureWidget or programmatic) → authenticate (GoogleAuthWidget) → make requests (IAPClient). Includes multiple-services pattern and troubleshooting. |
| `docs/gcp-admin-setup.md` | Admin guide: configure OAuth consent screen → create Desktop OAuth client → add to IAP programmatic access → grant users IAP role → distribute credentials to users. Includes security considerations. |

---

## Execution Order

**Phase 1 — all parallel, no dependencies:**
- Create LICENSE, CONTRIBUTING.md, issue templates
- Create all test-service files
- Write both docs

**Phase 2 — after Phase 1 commits:**
- Edit pyproject.toml (add URLs)
- Edit README.md (badges, fix clone URL)
- Create ci.yml and release.yml

**Phase 3 — manual, after merge to main:**
- Maintainer: PyPI account + trusted publisher + GitHub environment setup
- Tag v0.1.0, push, verify release pipeline

---

## Verification

After implementation:
1. `uv run ruff format --check src/ tests/` — formatting clean
2. `uv run ruff check src/ tests/` — no lint errors
3. `uv run pytest tests/ -x -q` — all tests pass
4. Push branch, open PR → confirm CI workflow runs all 3 jobs (lint, typecheck, test matrix)
5. Verify LICENSE, CONTRIBUTING.md, issue templates render correctly on GitHub
6. Verify pyproject.toml URLs appear on PyPI project page (after publish)
7. Test service locally: `cd examples/test-service && uvicorn main:app --port 8080` then curl endpoints
