# Documentation & Tutorials

## Audience

Two groups with different needs:

| Audience | What they need |
|----------|---------------|
| **End users at client orgs** | Quick-start guide: install, configure, authenticate, make requests. Semi-technical (data scientists, analysts using Jupyter). |
| **Developers / contributors** | API reference, architecture overview, how to extend or contribute. |

## Documentation Strategy

### Tier 1: Ship with v0.1.0 (minimum viable docs)

These should exist before the first PyPI release.

#### README.md (already exists — minor updates)
The current README is solid. Updates needed:
- Fix `yourusername` → `NicholasGrundl` in clone URL
- Add PyPI and CI badges
- Already covered in the distribution plan

#### Quick-Start Guide
Could live in `docs/quickstart.md` or as an expanded README section. Covers the full journey:

1. **Install:** `pip install tokentoss`
2. **GCP setup** (one-time, done by org admin):
   - Create Desktop OAuth client
   - Add to IAP allowlist
   - Grant users the IAP Web App User role
3. **Configure credentials** (one-time per user):
   - `ConfigureWidget()` in Jupyter
   - Or `tokentoss.configure(client_id=..., client_secret=...)`
4. **Authenticate** (per session):
   - `GoogleAuthWidget()` → click Sign in
5. **Make requests:**
   - `IAPClient(base_url=...).get_json("/api/data")`

Key question: does the org admin provide users with `client_id` and `client_secret`, or does each user create their own OAuth client? This affects the guide's instructions. Likely the admin creates one Desktop OAuth client and shares the credentials with users.

#### GCP Admin Setup Guide
A separate doc for the person setting up the GCP side (may be you, the developer, not the end user). Covers:
- Creating the OAuth consent screen
- Creating a Desktop OAuth client
- Adding the client to IAP's programmatic access allowlist
- Granting users the correct IAM role
- What to share with end users (client_id, client_secret, service base URL)

This is important because it's the part most likely to trip people up, and it only needs to be done once per client org.

---

### Tier 2: Add before v0.2.0 (nice to have)

#### API Reference
Auto-generated from docstrings or hand-written. Key classes:
- `GoogleAuthWidget` — constructor args, traitlets, methods
- `ConfigureWidget` — constructor args, behavior
- `IAPClient` — constructor args, HTTP methods, credential discovery chain
- `AuthManager` — for advanced users who want lower-level control
- `configure()` / `configure_from_file()` / `configure_from_credentials()`
- `TokenData`, `FileStorage`, `MemoryStorage`

Options:
- **mkdocs + mkdocstrings**: Auto-generates from docstrings, hosted on GitHub Pages
- **Sphinx + autodoc**: More traditional, heavier setup
- **Hand-written markdown**: Simpler, no build step, lives in `docs/`

Recommendation: Start with hand-written markdown in `docs/`. Migrate to mkdocs later if the project grows.

#### Example Notebooks
Put in `examples/` (directory already exists). Each notebook is self-contained:

- `examples/getting-started.ipynb` — Full walkthrough from configure to authenticated request
- `examples/multiple-services.ipynb` — Using IAPClient with different base URLs in the same session
- `examples/token-inspection.ipynb` — Examining token data, checking expiry, manual refresh

These double as integration tests (can be run manually to verify the full flow).

---

### Tier 3: If the project gets traction

#### Hosted Documentation Site
- mkdocs-material on GitHub Pages (free, auto-deploys via GitHub Actions)
- Combines the quick-start, admin guide, API reference, and examples

#### Troubleshooting Guide
Common issues and fixes:
- "Popup blocked" → use manual URL fallback
- "Token refresh failed" → re-authenticate
- "Permission denied on IAP" → check IAM role and allowlist
- "client_secrets.json not found" → run ConfigureWidget or configure()
- File permission warnings on Windows (0600 not supported)

#### Changelog
- `CHANGELOG.md` following [Keep a Changelog](https://keepachangelog.com/) format
- Or rely on GitHub Release auto-generated notes (already in the release workflow)

---

## File Structure

Proposed docs layout (create as needed, not all at once):

```
docs/
    quickstart.md           # Tier 1: end-user getting started
    gcp-admin-setup.md      # Tier 1: GCP setup for org admins
    api-reference.md        # Tier 2: class and function reference
    troubleshooting.md      # Tier 3: common issues
examples/
    getting-started.ipynb   # Tier 2: interactive walkthrough
    multiple-services.ipynb # Tier 2: multi-service usage
```

## Open Questions

- Should docs live in `docs/` in the repo, or on a separate site (GitHub Pages)?
  - Recommendation: start in `docs/`, add GitHub Pages later if needed
- Should example notebooks be committed with outputs, or outputs stripped?
  - Recommendation: strip outputs (they contain auth state). Add a note that users should run them themselves.
- Is there a logo or visual identity for tokentoss?
  - Nice to have for PyPI page and docs site, but not blocking
