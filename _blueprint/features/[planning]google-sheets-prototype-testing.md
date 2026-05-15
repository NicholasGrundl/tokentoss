# Google Sheets Prototype — Testing the OAuth Credential Lifecycle

> Discovery spike: validate end-to-end Google Sheets read access from a Jupyter notebook using the tokentoss SSO widget, across the full credential lifecycle, against a real Workspace sheet.

**Status**: Planned
**Priority**: P0
**Phase**: TBD
**Last updated**: 2026-05-15

---

## 1. Problem & Motivation

Tokentoss is positioned as an IAP-focused library, but `AuthManager` and `GoogleAuthWidget` already accept arbitrary scopes — the credentials they produce work directly with `gspread`, `google-api-python-client`, and every other Google client. The larger `[planning]workspace-api-integrations-v1.md` spec proposes repositioning the library, refactoring docs, and shipping example notebooks for this audience.

Before committing to that broader rewrite, we need to **validate end-to-end that the existing OAuth surface actually works against a real Workspace API** across the full credential lifecycle a notebook user will hit:

- First-time setup with no local state
- Kernel restarts and tab close/reopen rehydration
- Access-token refresh via stored refresh tokens
- Scope mismatch when an existing token doesn't cover newly-requested scopes (called out as a latent footgun in `[planning]workspace-api-integrations-v1.md`, lines 23 and 109)

This prototype is a **discovery spike**: a single notebook + findings doc that exercises Sheets read access against a real `insilicostrategy.com` Workspace sheet, captures every gotcha encountered (code, library, GCP admin), and produces concrete inputs to `workspace-api-integrations-v1` so that spec is grounded in observed behavior rather than assumptions.

## 2. Goals & Scope Boundaries

**Primary goal**: Validate that a user can read a Google Sheet from a Jupyter notebook using only the tokentoss SSO widget for authentication, across all credential-lifecycle scenarios listed in the original goal sketch.

### In scope

- Read-only Sheets access via `gspread` against test sheet `1HQX2O3O1FDLrxHexiLpDCAQb0NYAGgwUjXd5pqt2FyA` in the `insilicostrategy.com` Workspace.
- Lifecycle scenarios: cold start (fresh + kernel restart), warm path (tab close/reopen), token refresh (simulated), scope mismatch.
- Documenting all admin-side prerequisites discovered along the way.
- Opportunistic code fixes if scenarios reveal bugs (see §13 for triage criteria).
- A findings doc that feeds `[planning]workspace-api-integrations-v1.md`.

### Out of scope

The following are explicitly deferred to a follow-up plan, anticipated as `_blueprint/features/[planning]google-sheets-prototype-rw-rbac.md` (see §15):

- Read/write operations against Sheets
- Programmatic RBAC / sharing semantics
- Drive, BigQuery, Gmail, Calendar, or any non-Sheets API
- Public/hosted notebook examples
- Docs refactor (belongs to `workspace-api-integrations-v1`)
- The `tokentoss.scopes` constants module (deferred to `workspace-api-integrations-v1`)

### Non-goal

Shipping a polished, end-user-facing example notebook. That deliverable is `examples/sheets-gspread.ipynb` in `workspace-api-integrations-v1`. This prototype's notebook is a maintainer-facing exploration artifact, named to signal that (`examples/sheets-prototype.ipynb`).

## 3. Pre-flight: GCP / Workspace Admin Verification

Before running the prototype, verify GCP and Workspace state. The existing `_blueprint/context/google-iap/gcp-iap-setup-runbook.md` covers IAP setup but not Sheets-API enablement or consent-screen scope deltas, so every gap discovered here becomes a finding for the `gcp-admin-setup.md` refactor in `workspace-api-integrations-v1`.

**Checklist** (run before opening the notebook):

| # | Step | How to verify | What to capture if missing |
|---|------|---------------|-----------------------------|
| 1 | Sheets API enabled in the GCP project bound to `insilicostrategy.com` | GCP Console → APIs & Services → Enabled APIs → search "Google Sheets API" | Note exact enablement steps + project name in findings |
| 2 | OAuth consent screen lists the Sheets scope | GCP Console → APIs & Services → OAuth consent screen → Scopes section | Note that adding `auth/spreadsheets.readonly` requires consent-screen re-publish for Internal apps |
| 3 | Test sheet `1HQX...FyA` accessible to the signed-in user | Open URL in browser while signed into the Workspace account | If not accessible, note sharing path (Workspace-internal default vs explicit share) |
| 4 | Desktop OAuth client exists and matches what tokentoss is configured with | Run `tokentoss.get_config_path()` in a cell, inspect `client_secrets.json` | Note any mismatch — informs whether the IAP OAuth client can be reused for Workspace |
| 5 | Workspace org type confirms "Internal" consent app | OAuth consent screen → User type | Document whether the IAP setup's Internal app status is compatible with adding Workspace scopes |

The notebook's first cells print results of programmatic checks (config path, on-disk file presence) but cannot verify steps 1-2 from inside the kernel. The findings doc captures any gaps.

**Pre-flight blocker policy**: If steps 1 or 2 are missing, pause the prototype, complete the admin setup, and document the steps verbatim in the findings doc before proceeding. The point of this spike is to surface what admins must do — not to skip past it.

## 4. Notebook Structure

**Location**: `examples/sheets-prototype.ipynb` — committed with outputs stripped (use `nbstripout` or `jupyter nbconvert --clear-output --inplace` before commit).

**Layout conventions**:

- Top of notebook: one markdown header explaining what this notebook is, the test sheet URL, and an explicit "this is exploratory — not a polished example" disclaimer pointing forward to the future `examples/sheets-gspread.ipynb`.
- One markdown setup cell defining shared constants: `SHEET_URL`, `SHEET_ID`, `SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]`, `CONFIG_DIR = Path(...)`.
- One section per scenario, each with:
  - A level-2 markdown header (`## Scenario N — <name>`).
  - A "Setup / reset" subsection describing how to reach the scenario's starting state. Each scenario's setup is self-describing about its prerequisites — even when those prerequisites are "Scenario N-1 left tokens on disk".
  - Numbered code cells executing the scenario.
  - A trailing "Observations" markdown cell — left blank in the committed version, filled in during a run, then transcribed into the findings doc.
- Between scenarios: a "Reset cell" with a clear comment explaining what state it returns the system to.

**Scenarios may chain when state-sharing is the point** (e.g., Scenario 2 *requires* tokens left by Scenario 1's auth flow). The setup section of each scenario is explicit about what state it expects and how to reach that state if running out of order — typically "run the auth flow once first."

**Kernel-restart scenarios have a manual gate.** Scenario 2 requires a kernel restart. The notebook has a prominent markdown cell ("⚠️ RESTART KERNEL NOW — then resume from this cell") and Scenario 2's first code cell starts with `import tokentoss` to make the cold-import behavior visible.

## 5. Scenario 1 — Cold Start, No Local State

**What this tests**: First-time user on a fresh machine — no `client_secrets.json`, no `tokens.json`, no in-memory state.

**Setup / reset**:

- Programmatic cell: delete `~/.config/tokentoss/tokens.json` (use `Path.unlink(missing_ok=True)`).
- Optionally delete `client_secrets.json` if testing the full ConfigureWidget path. Otherwise, leave it and start from `GoogleAuthWidget`.
- Sanity-check cell: assert both files are in their expected starting state.

**Cells**:

1. Verify config-dir state (no tokens; optionally no secrets).
2. `ConfigureWidget` cell (only if testing full cold start including secrets).
3. `widget = GoogleAuthWidget(scopes=SCOPES); display(widget)`.
4. Manual action: click "Sign in with Google", complete consent screen, confirm Sheets scope appears on consent.
5. Programmatic verification: `widget.is_authenticated`, `widget.user_email`, `widget.auth_manager.storage.load().scopes`.
6. `import gspread; gc = gspread.authorize(widget.auth_manager.credentials)`.
7. `sh = gc.open_by_url(SHEET_URL); records = sh.sheet1.get_all_records(); records`.
8. Convert to DataFrame: `pd.DataFrame(records)`.

**What to record in findings**:

- Did the consent screen display the Sheets scope correctly (and did its description make sense)?
- Did `widget.auth_manager.storage.load().scopes` include exactly the requested scope, or did Google return a superset/subset?
- Did `gspread.authorize()` accept the credentials object without complaint?
- Any latency or UX surprises in the popup flow.

## 6. Scenario 2 — Cold Start with Kernel Restart

**What this tests**: Tokens persist on disk; kernel is killed; fresh kernel re-imports `tokentoss` and accesses credentials without re-auth.

**Setup / reset**:

- Prerequisite: tokens exist on disk with the Sheets scope. Achieved by running Scenario 1 (or any prior sign-in with `SCOPES`).
- Manual action: kernel restart via JupyterLab UI. The notebook has a prominent markdown banner indicating this.

**Cells** (run after restart, skipping Scenario 1's cells):

1. `import tokentoss` — verify version, config path.
2. Inspect on-disk state: `tokens.json` exists, scopes include Sheets, expiry not yet past.
3. `widget = GoogleAuthWidget(scopes=SCOPES); display(widget)` — widget should render in signed-in state with no popup.
4. Verify `widget.is_authenticated` immediately (no async wait needed).
5. `gspread.authorize(widget.auth_manager.credentials).open_by_url(SHEET_URL).sheet1.get_all_records()`.
6. Compare returned records to Scenario 1 (sanity: same sheet, same data).

**What to record in findings**:

- Time-to-authenticated on cold import.
- Does the widget briefly flash a "signed out" state before rehydrating, or is the first render already signed in?
- Are there any side effects (network calls, refresh attempts) on import / first credential access that aren't documented?

## 7. Scenario 3 — Warm Path / Tab Close + Reopen

**What this tests**: Same kernel; user closes the JupyterLab tab and reopens it (or just re-displays the widget in a new cell). Validates that re-rendering doesn't trigger spurious re-auth.

**Setup / reset**:

- Prerequisite: Scenario 1 or 2 has run; widget is authenticated; kernel is running.
- No state changes — just re-execute display cells.

**Cells**:

1. `display(widget)` — re-render existing widget object; should show signed-in state.
2. `widget_2 = GoogleAuthWidget(scopes=SCOPES); display(widget_2)` — new widget instance reading from same on-disk state.
3. Verify both widgets show authenticated state.
4. Verify both widgets share credentials (object identity not required; same `user_email` and matching token).
5. Optional manual test: physically close the JupyterLab browser tab, reopen it, re-execute step 1 — does the widget rehydrate? (Note: anywidget state across tab close depends on JupyterLab session behavior; capture observation.)

**What to record in findings**:

- Do two widget instances share or duplicate state? (Important for the singleton `tokentoss.CREDENTIALS` module-level variable.)
- Does the tab-close test actually exercise anything different from "re-display in a new cell"? If not, note that this scenario collapses into Scenario 2 for most practical purposes.

## 8. Scenario 4 — Token Refresh Simulation

**What this tests**: Access token has expired; refresh token is still valid; the library should silently refresh on next credential use.

**Setup / reset**:

- Prerequisite: valid tokens on disk including a non-null refresh token.
- Helper cell: load `tokens.json`, set `expiry` to a timestamp 1 hour in the past, save back. Preserve all other fields including `refresh_token`.

**Cells**:

1. Helper: backdate expiry. Print before/after for verification.
2. Inspect on-disk file directly (re-read JSON) — confirm expiry is past, refresh_token still present.
3. Construct fresh `auth_manager` or widget to ensure no in-memory cached credentials: `widget = GoogleAuthWidget(scopes=SCOPES); display(widget)`.
4. Force credential access: `creds = widget.auth_manager.credentials; print(creds.expired, creds.valid, creds.token[:20])`.
5. If `google-auth` doesn't auto-refresh on access, call `creds.refresh(google.auth.transport.requests.Request())` explicitly.
6. Verify post-refresh: `creds.expired` is False, `creds.valid` is True, expiry has moved forward.
7. Verify on-disk `tokens.json` reflects the new expiry (depends on whether `AuthManager` persists post-refresh — finding to capture).
8. `gspread.authorize(creds).open_by_url(SHEET_URL).sheet1.get_all_records()` succeeds.

**What to record in findings**:

- Is refresh automatic on credential access, or does it require an explicit `.refresh()` call?
- Does the refreshed token get persisted back to `tokens.json` automatically, or does the on-disk file stay stale?
- Any visible logging or telemetry events during refresh?
- Does the widget UI react to the refresh (e.g., re-render with updated state)?

## 9. Scenario 5 — Scope Mismatch

**What this tests**: Tokens on disk have a different scope set than what `GoogleAuthWidget` is now requesting. Surfaces the latent footgun called out in `[planning]workspace-api-integrations-v1.md`.

**Setup / reset**:

- Helper cell: load `tokens.json`, replace the `scopes` list with a non-Sheets scope set (e.g., `["openid", "https://www.googleapis.com/auth/userinfo.email"]`) — removing the Sheets scope while keeping the access/refresh tokens.
- This simulates "user had IAP-only tokens, now adds Sheets scope."

**Cells**:

1. Helper: rewrite stored scopes. Print before/after.
2. Construct widget with Sheets scope: `widget = GoogleAuthWidget(scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]); display(widget)`.
3. Observe widget initial state: signed-in (using stale-scope token) or prompting re-auth?
4. If signed-in: try `gspread.authorize(widget.auth_manager.credentials).open_by_url(SHEET_URL).sheet1.get_all_records()` — capture the error verbatim.
5. If re-auth prompted: complete sign-in, verify stored scopes now include Sheets.
6. Capture the full observed behavior.

**Decision tree** (apply per §13 triage protocol):

| Observed behavior | Action |
|---|---|
| Widget silently uses stale-scope token; gspread fails with opaque API error | **Fix in this PR** — this is the documented latent footgun; align `AuthManager` load path with configured scopes (see `workspace-api-integrations-v1` "Code touchups" #1). |
| Widget raises a clear `ScopeMismatchError` on construction | **Defer fix to `workspace-api-integrations-v1`** — behavior is already user-recoverable; the larger spec can decide on UX polish. |
| Widget auto-triggers re-auth flow without erroring | **No fix needed** — document as the desired behavior; update `workspace-api-integrations-v1` Open Question #3 to reflect reality. |
| Something else | Document the behavior in findings; bring it to a follow-up planning session. |

**What to record in findings**:

- Exact observed behavior (with stack traces / error strings if any).
- Which branch of the decision tree applied.
- If fixed in this PR: link to the commit and the new test.

## 10. Reset / Utility Cells

A small set of reusable helper cells defined near the top of the notebook (after the constants block) and referenced by each scenario's setup. Defining them once keeps each scenario's setup readable.

```python
# Defined once, reused per-scenario:
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tokentoss

TOKENS_PATH = Path(tokentoss.get_config_path()).parent / "tokens.json"
SECRETS_PATH = Path(tokentoss.get_config_path())

def show_state():
    """Print current on-disk credential state. Safe to call anytime."""
    ...

def clear_tokens():
    """Delete tokens.json. Leaves client_secrets.json in place."""
    ...

def clear_all_config():
    """Delete tokens AND secrets. Use for full cold-start sim."""
    ...

def backdate_token_expiry(minutes_ago: int = 60):
    """Edit tokens.json to set expiry in the past. Preserves refresh_token."""
    ...

def overwrite_token_scopes(new_scopes: list[str]):
    """Edit tokens.json scopes list without changing tokens themselves.
    Used by Scenario 5 to simulate scope mismatch."""
    ...
```

Each helper has a clear docstring stating exactly what disk state it modifies. The `show_state()` helper is called at the start and end of every scenario for visibility — it dumps file presence, permissions, scopes, expiry, `is_expired` boolean.

**Implementation note**: these helpers live inline in the notebook (not in `src/tokentoss`). They are testing scaffolding and have no business in the library.

## 11. Dependencies & Setup

**New dev dependency**: `gspread`. The version constraint targets gspread v6.x (per `_blueprint/context/gspread/README.md`, v6 has breaking changes from v5; we want the modern API).

Add via:

```bash
uv add --group dev "gspread>=6.0.0"
```

This adds gspread to `[dependency-groups].dev` in `pyproject.toml`, alongside `jupyter`, `jupyterlab`, etc. It does **not** become a runtime dependency of `tokentoss` itself. The point of this spike is to confirm that consumers can `pip install tokentoss` and bring their own gspread; bundling it would defeat that.

Also confirm: `pandas` for the DataFrame display step. If not already pulled in transitively, add it as a dev dep too — but check first; it's likely already pulled in by `jupyter` or one of its deps.

**Test sheet config**: the `SHEET_URL` constant in the notebook references `1HQX2O3O1FDLrxHexiLpDCAQb0NYAGgwUjXd5pqt2FyA`. The notebook's intro cell explicitly notes this sheet is owned by the maintainer in the `insilicostrategy.com` Workspace and that anyone re-running the notebook will need to:

- Substitute their own sheet ID, or
- Be granted view access to the maintainer's sheet, or
- Run from the maintainer's Workspace identity.

**Scope constants**: define raw scope URL strings in the notebook constants cell. No dependency on a `tokentoss.scopes` module (per the workspace-api spec, that's deferred).

## 12. Findings Doc Structure

**File**: `_blueprint/features/[planning]google-sheets-prototype-findings.md`. Created at the same time as the prototype notebook; filled in during/after the prototype run.

**Template**:

```markdown
# Google Sheets Prototype — Findings

> Discoveries from running `examples/sheets-prototype.ipynb` against `insilicostrategy.com` on YYYY-MM-DD.

**Status**: In Progress | Complete
**Feeds into**: `[planning]workspace-api-integrations-v1.md`
**Last updated**: YYYY-MM-DD

## Admin-side findings

What the maintainer had to do in GCP Console / Workspace Admin to make the prototype work. This is the draft of what needs to land in the `gcp-admin-setup.md` refactor.

- Enabling Sheets API: [steps observed]
- OAuth consent screen scope addition: [steps observed, gotchas]
- Test-sheet sharing: [Internal Workspace defaults, any extra steps]
- Reusing the IAP OAuth client: [worked / didn't, why]

## Per-scenario observations

### Scenario 1 — Cold Start, No Local State
- [What happened, surprises, errors]

### Scenario 2 — Cold Start with Kernel Restart
...

### Scenario 3 — Warm Path / Tab Close
...

### Scenario 4 — Token Refresh
- Auto-refresh on access: [yes/no]
- On-disk persistence post-refresh: [yes/no]
...

### Scenario 5 — Scope Mismatch
- Observed behavior: [silent / clean error / auto re-auth]
- Decision tree branch applied: [...]
- Code fix: [linked commit if applicable, or "deferred to workspace-api-integrations-v1"]

## Library / API notes
- gspread integration: [smooth / friction points]
- google-auth refresh behavior: [observations]
- anywidget behavior across kernel/tab events: [observations]

## Inputs to workspace-api-integrations-v1
Concrete list of things this prototype confirmed/changed:
1. [Confirmation or revision of an assumption in the larger spec]
2. ...

## Bugs found
- [Bug] — [Fixed-in-PR / Deferred] — [Link or note]

## Open questions for follow-up
- [Things to explore in [planning]google-sheets-prototype-rw-rbac.md]
```

This findings doc has **no acceptance criteria** of its own — it's a discovery log. Its content quality is judged by how much it grounds `workspace-api-integrations-v1` in observed reality.

## 13. Code-Fix Triage Protocol

The prototype is exploratory, but bugs found may warrant in-scope fixes. Criteria for when to fix vs. defer:

**Fix in this PR if all of:**

- The bug blocks the prototype from validating its intended scenario (i.e., we can't complete the scenario without fixing it).
- The fix is local (single module, no architectural changes, no new public API surface).
- A regression test can be added in the same PR using existing test patterns (`tests/test_auth_manager.py`, etc.).
- The fix is already named as a code touchup in `[planning]workspace-api-integrations-v1.md` (so it's not adding net-new scope, just pulling timing forward).

**Defer if any of:**

- Bug is cosmetic, UX-only, or recoverable by user action.
- Fix requires a new public API or behavioral change documented in user-facing docs.
- Fix touches multiple modules or requires design discussion.
- Discovered behavior contradicts assumptions in `[planning]workspace-api-integrations-v1.md` — in that case, *document* and let the larger spec re-plan.

**Hard rules:**

- No new features. The prototype's job is to find things, not build them.
- No docs refactor. That work belongs to `workspace-api-integrations-v1`. The findings doc captures inputs; the refactor lands separately.
- No `tokentoss.scopes` module — explicitly deferred regardless of how clean adding it would feel during the prototype.

**Example application**:

- Scope-mismatch silent-token-use bug → meets all "fix" criteria → fix in PR + add test.
- gspread error message confusing on permission denied → cosmetic, defer.
- `AuthManager` lacks a public hook for "is token refreshable?" → new API, defer to `workspace-api-integrations-v1`.

## 14. Git Workflow & Acceptance Criteria

**Branch**: `feat/sheets-prototype` off `main`.

**Commits**: Loose, narrative-style commits as the prototype evolves. A `commit-macro` cleanup pass before opening the PR is fine but not required.

**PR contents** (single PR for the whole prototype):

- `examples/sheets-prototype.ipynb` (outputs stripped)
- `_blueprint/features/[planning]google-sheets-prototype-findings.md`
- Any opportunistic code fixes + their tests
- `pyproject.toml` change adding `gspread` to dev deps
- `uv.lock` updates from the dep change
- **Not included**: changes to `gcp-admin-setup.md`, `README.md`, `quickstart.md`, or `workspace-api-integrations-v1.md`. Those land in their respective specs' PRs.

**PR description should reference**:

- The findings doc location.
- Any code fixes' rationale (one sentence each).
- A note that this PR is part of de-risking `[planning]workspace-api-integrations-v1.md`.

### Acceptance criteria

The PR can merge when all are checked:

- [ ] Pre-flight admin checklist (§3) executed and results recorded in findings doc.
- [ ] `examples/sheets-prototype.ipynb` runs top-to-bottom end-to-end against the test sheet (with the prescribed manual actions: sign-in, kernel restart).
- [ ] All 5 scenarios execute and their "Observations" cells are transcribed into the findings doc.
- [ ] Scenario 5 decision-tree branch is recorded; if "Fix in PR" branch applied, the fix + a new test exist in this PR.
- [ ] `findings.md` has at least one concrete entry under "Inputs to workspace-api-integrations-v1".
- [ ] `gspread` dev dependency is pinned to `>=6.0.0` in `pyproject.toml` with corresponding `uv.lock` update.
- [ ] Notebook outputs are stripped before commit.
- [ ] No unrelated changes (no docs refactor, no scopes module, no new features).
- [ ] `just ci` passes (lint, typecheck, tests).

## 15. Follow-up Handoff

Once this prototype lands, the natural next exploration is read/write and access-management semantics. That work gets a separate spec, **not** an expansion of this one.

**Spec to draft after this lands**: `_blueprint/features/[planning]google-sheets-prototype-rw-rbac.md`.

**Anticipated scope** (not committed — for the next planning session):

- Read + write round-trip against a test sheet (append row, update cell, delete row, with cleanup).
- Programmatic sharing: `sh.share(...)` — testing user/group/anyone, role permutations.
- RBAC observations: what permissions does the OAuth scope grant in practice vs. what the sheet's sharing settings allow?
- Workspace-internal-only sharing constraints.
- Failure modes: shared with revoked user, shared without write scope, etc.
- Whether `gspread-pandas` or `gspread-dataframe` (per `_blueprint/context/gspread/resources.md`) belongs in the recommended workflow.

**Inputs that follow-up spec inherits from this one**:

- A working notebook scaffold to copy from.
- A vetted admin-setup procedure.
- The findings doc as ambient context.
- Any code fixes already landed (refresh persistence, scope-mismatch handling).

This handoff section is intentionally light — the follow-up gets its own interview-and-plan session. Listing scope here is to make sure nothing in the read+write space sneaks into this prototype.

## Dependencies

- **Requires**: nothing — works against current main (v0.1.1).
- **Enables**:
  - `[planning]workspace-api-integrations-v1.md` — grounds its admin-setup refactor, scope-mismatch fix, and `sheets-gspread.ipynb` example in observed behavior.
  - `[planning]google-sheets-prototype-rw-rbac.md` (to be drafted) — follow-up that builds on this scaffold.

## Open Questions

1. **gspread auth bridge signature**: confirm `gspread.authorize(credentials)` accepts a `google.oauth2.credentials.Credentials` directly (per gspread v6 docs) vs. expecting an `AuthorizedSession`. Verify on first cell of Scenario 1; if it differs, capture in findings.
2. **AuthManager post-refresh persistence**: reading `auth_manager.py:153-154` suggests the storage round-trip only happens on initial login. Scenario 4 will reveal this empirically — and the answer determines whether a fix lands in this PR or in `workspace-api-integrations-v1`.
3. **`pandas` dev-dep status**: check whether `pd.DataFrame(records)` works without an explicit dep add. If not, add `pandas` to the dev group (or use an alternative display).
4. **Test sheet permissions across re-runs**: if the test sheet's sharing settings change between prototype runs, scenarios may fail in opaque ways. Findings doc should record the sharing state at run time.
5. **Output-stripping tooling**: should this PR also gitignore `examples/*.ipynb` outputs project-wide via a hook? Adding `nbstripout` would be a docs/tooling task; for this PR, manual stripping is sufficient. Note as a follow-up if it keeps causing friction.

## Acceptance Criteria

See §14 for the full checklist. Summary: notebook runs end-to-end, all five scenarios execute and produce documented observations, findings doc feeds `workspace-api-integrations-v1`, any in-scope code fixes have tests, CI passes.
