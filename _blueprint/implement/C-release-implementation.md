# Plan: Remaining Release Work (Test Service + Docs)

Distribution and CI/CD infrastructure is complete. This plan covers the two remaining workstreams before the project is fully release-ready.

---

## Completed (Workstream A — Distribution + CI/CD)

The following are already in place:
- `LICENSE` (MIT)
- `CONTRIBUTING.md`
- `.github/ISSUE_TEMPLATE/bug_report.md` and `feature_request.md`
- `.github/workflows/ci.yml` — lint, typecheck, test matrix (3.10/3.11/3.12)
- `.github/workflows/release.yml` — tag-triggered build + PyPI publish + GitHub Release
- `.github/workflows/security.yml` — pip-audit + bandit
- `pyproject.toml` — `[project.urls]` with Homepage, Repository, Issues, Changelog
- `README.md` — badges and correct clone URL

---

## Workstream B: Test Service

All files under `examples/test-service/`.

| File | Contents |
|------|----------|
| `main.py` | FastAPI app (~80 lines). Endpoints: `GET /health` (no auth), `GET /` (service info), `GET /whoami` (returns IAP user identity), `GET /protected` (user-specific content with request counter). Returns 401 if IAP headers missing. |
| `Dockerfile` | `python:3.12-slim`, install requirements, copy main.py, expose 8080, run uvicorn |
| `requirements.txt` | `fastapi>=0.110.0`, `uvicorn[standard]>=0.29.0` |
| `README.md` | Deploy guide: enable GCP APIs → deploy to Cloud Run → configure IAP → create Desktop OAuth client → grant user access. Includes local testing and cleanup. |

**Dependency:** Requires GCP setup (see `test-service-gcp-setup.md`).

---

## Workstream C: Tier 1 Docs

| File | Contents |
|------|----------|
| `docs/quickstart.md` | End-user guide: install → configure credentials → authenticate → make requests. Includes multiple-services pattern and troubleshooting. |
| `docs/gcp-admin-setup.md` | Admin guide: configure OAuth consent screen → create Desktop OAuth client → add to IAP programmatic access → grant users IAP role → distribute credentials. |

---

## Execution Order

**Phase 1 — parallel, no dependencies:**
- Create all test-service files (`examples/test-service/`)
- Write both docs (`docs/quickstart.md`, `docs/gcp-admin-setup.md`)

**Phase 2 — after Phase 1:**
- Deploy test service to GCP (follow `test-service-gcp-setup.md`)
- Run manual widget testing (follow `widget-testing-guide.md`)

---

## Verification

After implementation:
1. `uv run ruff check src/ tests/` — no lint errors
2. `uv run pytest tests/ -x -q` — all tests pass
3. Test service locally: `cd examples/test-service && uvicorn main:app --port 8080` then curl endpoints
4. Docs render correctly in markdown preview
