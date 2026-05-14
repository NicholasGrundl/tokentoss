# Roadmap

Slim phase index — each entry points to its feature spec. Detailed status for the active phase lives in `implementation-progress.md`. Completed phases narrate in `phase-history.md`. Unscheduled ideas/fixes (and currently-paused phases) live in `feature-backlog.md`.

| Phase | Feature                          | Spec                                                                       | Priority | Status    |
|-------|----------------------------------|----------------------------------------------------------------------------|----------|-----------|
| 1     | v0.1.0 Release                   | `archive/features/[completed]release-implementation-v1.md`                 | P0       | Completed |
| TBD   | Docs Tier 2 + Tier 3             | `features/[planning]docs-and-tutorials-v1.md`                              | P0       | Planned   |
| TBD   | Widgets Subpackage Refactor      | `features/[planning]widgets-subpackage-v1.md`                              | P1       | Planned   |
| TBD   | Architectural Improvements       | `features/[planning]architectural-improvements-v1.md`                      | P2       | Planned   |

## Notes

- Phase 1 (v0.1.0) shipped: PyPI distribution, GitHub Actions CI/CD, Tier 1 docs (`docs/quickstart.md`, `docs/gcp-admin-setup.md`), and the FastAPI test service (`examples/test-service/`). See `phase-history.md` once the v0.1.0 narrative is written there.
- The remaining specs are sequenced by recommended execution order from the v0.1.0 next-steps snapshot (archived at `archive/[reference]post-v010-next-steps-snapshot.md`): docs Tier 2/3 first, then widgets refactor, then architectural cleanup. Phase numbers are deliberately `TBD` until each is committed to a phase.
- Durable runbooks moved out of `features/` to `context/`: GCP/IAP setup at `context/google-iap/gcp-iap-setup-runbook.md`, widget manual test at `context/testing/widget-manual-test.md`.
