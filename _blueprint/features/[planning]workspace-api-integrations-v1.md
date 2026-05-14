# Workspace API Integrations

> Reposition tokentoss as a general Google-OAuth-for-notebooks library and add first-class support for Workspace API consumers (Sheets, Drive, BigQuery) alongside the existing IAP use case.

**Status**: Planned
**Priority**: P0
**Phase**: TBD
**Last updated**: 2026-05-13

---

## Problem

Tokentoss is currently positioned and documented as an IAP-focused library: README, quickstart, and the GCP admin guide all frame the goal as "authenticate to your IAP-protected service from a notebook." Under the hood, however, the library is a general Google OAuth client — `AuthManager` and `GoogleAuthWidget` already accept arbitrary scopes (`auth_manager.py:115`, `widget.py:560`), the credential store keeps both ID and access tokens (`storage.py:26-27`), and the resulting `google.oauth2.credentials.Credentials` is directly usable with `gspread`, `google-api-python-client`, `google-cloud-bigquery`, and every other Google client library.

Client-org users with Google Workspace overwhelmingly want to read/write their own Sheets, list Drive files, query BigQuery, etc. from a local Jupyter notebook. Today this works mechanically — pass `scopes=` to the widget, hand `widget.auth_manager.credentials` to gspread — but **nothing in the docs tells them they can**. The IAP framing reads as if that's the *only* supported pattern.

Two real gaps drop out of this framing:

1. **Discoverability.** Users do not know to try Workspace APIs because tokentoss reads as IAP-only.
2. **Admin-side guidance.** `gcp-admin-setup.md` walks through IAP configuration; it does not cover enabling the Sheets API or adding Workspace scopes to the consent screen, even though every other step (Internal consent, Desktop OAuth client, distributing creds) is identical.

There is also one latent footgun in the code: if a user passes new `scopes=` to `GoogleAuthWidget` but a token issued for *different* scopes is already on disk, behavior on re-load is not clearly specified. This will surface the moment a user tries to add a Sheets scope to an existing tokentoss config.

## Solution

### Overview

Reframe the library's positioning around "Google OAuth for notebooks, with patterns for IAP-protected services and Workspace APIs." Refactor the admin-setup docs so the OAuth-client-creation step is shared, with two clear branches afterward (IAP / Workspace APIs). Add example notebooks for the two highest-leverage Workspace cases (Sheets via gspread, Drive via google-api-python-client). Tighten the one code edge case around scope mismatch.

This is roughly 80% docs + examples and 20% code.

### Implementation Details

#### Code touchups

1. **Scope-mismatch handling in `AuthManager`** (`src/tokentoss/auth_manager.py`).
   On token load, compare the stored `scopes` against the configured `self.scopes`. If the stored set does not cover the configured set, do not silently use the stored token — discard it and force a fresh auth flow. Today (line 153-154) `self.scopes` is set from the constructor; the load path needs to be scope-aware.

2. **Optional: `tokentoss.scopes` constants module.**
   A small module exposing common scope URLs as named constants. Improves ergonomics and makes notebook examples self-documenting:
   ```python
   from tokentoss import scopes
   widget = GoogleAuthWidget(scopes=[scopes.OPENID_PROFILE_EMAIL, scopes.SHEETS_RW])
   ```
   Constants to start with: `OPENID_PROFILE_EMAIL`, `SHEETS_READ`, `SHEETS_RW`, `DRIVE_READ`, `DRIVE_RW`, `DRIVE_FILE`, `BIGQUERY`, `GMAIL_READ`, `CALENDAR_READ`. No new dependency. ~20 lines of constants.

3. **No changes to `IAPClient`.** The IAP consumer pattern remains as-is — this work positions it as one of several patterns, not replaces it.

#### Documentation

1. **Reframe `README.md`.**
   Lead with "Google OAuth for notebooks." Show two short side-by-side examples: IAP-protected service (`IAPClient`) and Sheets (`gspread`). Move the "what is IAP" paragraph below the fold.

2. **New `docs/workspace-apis.md`.**
   Covers:
   - When to use user OAuth vs. service accounts (and why service accounts are rarely right for notebook work).
   - Admin setup deltas vs. the IAP path: enable the relevant API in GCP, add the scope to the OAuth consent screen, reuse the existing Desktop OAuth client.
   - Workspace-vs-GCP framing (the most common point of confusion: Sheets isn't visible in GCP Console, but its API and OAuth live there).
   - User flow code samples for Sheets (`gspread`) and Drive (`google-api-python-client`).
   - "Reusing one OAuth client across IAP and Workspace APIs" — the union-scopes pattern.

3. **Refactor `docs/gcp-admin-setup.md`.**
   Split into:
   - Shared section: create GCP project + Workspace Org context + Internal consent + create Desktop OAuth client.
   - Branch A: "If you want to protect a service with IAP" — current IAP-specific steps.
   - Branch B: "If you want to access Workspace APIs from notebooks" — enable the relevant API, add scopes to consent screen.
   - Note that A and B can both apply to the same OAuth client.

4. **Update `docs/quickstart.md`.**
   Add a one-paragraph "passing scopes" section pointing at `docs/workspace-apis.md`. No body rewrite — the IAP-focused happy path stays.

#### Example notebooks

Add under `examples/` (outputs stripped before commit):

1. **`sheets-gspread.ipynb`** (~10 cells):
   - Configure tokentoss
   - Auth widget with Sheets scope
   - `gspread.authorize(widget.auth_manager.credentials)`
   - Open a sheet by URL, read all records, append a row, read it back
2. **`drive-file-listing.ipynb`** (~8 cells):
   - Auth widget with `drive.readonly` scope
   - Build the Drive client with `google-api-python-client`
   - List files with a query (`mimeType='application/vnd.google-apps.spreadsheet'`)
   - Download one file's metadata
3. **Optional `bigquery-query.ipynb`** (~6 cells): low priority, defer unless a real use case appears.

#### Repositioning sweep

After the docs above land, do one more pass:

- The package description in `pyproject.toml` should reflect the broader positioning.
- The `_blueprint/AGENTS.md` and root `AGENTS.md` "what tokentoss does" framing (currently implicit) should be made explicit.
- The PyPI long description (rendered from README) inherits the README change automatically.

## Dependencies

- **Requires**: nothing — works against current main (v0.1.1).
- **Enables**:
  - [[planning-docs-and-tutorials-v1]] — this spec delivers most of what `docs-and-tutorials` Tier 2 needs for the Workspace audience; the two specs should be coordinated so they don't duplicate work. Recommended: this spec covers Workspace API content; `docs-and-tutorials-v1` covers the remaining Tier 2 work (full API reference for the existing surface) and all of Tier 3.
  - Real client onboarding for Workspace-heavy use cases (data analysts reading their own Sheets, etc.).

## Open Questions

1. **`tokentoss.scopes` constants module — yes or no?** Convenience vs. yet-another-thing-to-maintain. Recommendation: yes, it's ~20 lines and meaningfully improves notebook readability. Trivially deletable later if it doesn't earn its keep.
2. **Convenience wrappers (`tokentoss.sheets_client()`)?** Tempting but a slippery slope toward replicating `gspread`. Recommendation: **no** — document the `widget.auth_manager.credentials` → `gspread.authorize()` bridge and stop there. Tokentoss does auth; consumer libraries do API access.
3. **Scope-mismatch behavior on load.** Two options: (a) silently re-auth, (b) raise an exception telling the caller they need to re-auth. Recommendation: (a) for `GoogleAuthWidget` (user-facing — UX is "click sign in again"), (b) for `AuthManager` constructed programmatically (callers can decide).
4. **Should `IAPClient` learn about access tokens?** No — keep it focused on ID-token bearer for IAP. Workspace API users go through library-native clients (`gspread`, etc.), not through tokentoss's HTTP client.
5. **README rewrite scope.** A pure positioning rewrite is small (~30 lines edited). Whether to also add the two side-by-side examples at the top is a judgment call; recommended yes — concrete code in the README is what convinces readers.

## Acceptance Criteria

- [ ] README leads with general Google-OAuth-for-notebooks framing; includes two short concrete examples (IAP + Sheets).
- [ ] `docs/workspace-apis.md` exists and covers: when to use vs. service accounts; admin-side scope/API enablement; Workspace-vs-GCP clarification; Sheets and Drive user-flow examples; reuse pattern.
- [ ] `docs/gcp-admin-setup.md` is refactored: shared OAuth-client section, then two branches (IAP, Workspace APIs).
- [ ] `docs/quickstart.md` has a "passing scopes" pointer to the new doc.
- [ ] `examples/sheets-gspread.ipynb` runs end-to-end against a real Sheet (manual test against the maintainer's Workspace).
- [ ] `examples/drive-file-listing.ipynb` runs end-to-end against a real Drive (manual test).
- [ ] `AuthManager` discards stored tokens whose scopes don't cover the configured scopes; re-auth is triggered instead of using a mismatched token. Covered by a new test.
- [ ] Optional: `tokentoss.scopes` module exists with common constants; documented in `workspace-apis.md`.
- [ ] `pyproject.toml` description and PyPI long description reflect the broader positioning.
- [ ] Manual test guide (`_blueprint/context/testing/widget-manual-test.md`) gains a "Workspace APIs" cell sequence covering the Sheets flow.
