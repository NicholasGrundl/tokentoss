# Next Steps

## 1. Distribution & Installation on Client Machines

The core question: **how should users install tokentoss on their local machines?**

There are several options worth evaluating before committing to one:

### Options to consider

| Approach | Pros | Cons |
|----------|------|------|
| **Public PyPI** | Standard `pip install tokentoss`, easy onboarding | Package is public; need clear docs that client_secrets are user-provided, not bundled |
| **Private PyPI (GCP Artifact Registry)** | Access-controlled, `uv add --index-url ...` | Requires auth setup on each client machine, more friction |
| **GitHub release / direct install** | `uv pip install git+https://...`, no registry needed | Requires repo access, no version index |
| **Bundled in a larger internal package** | Single install for all internal tools | Couples tokentoss to unrelated code |

### Open questions

- Is tokentoss intended for a small internal team or broader adoption?
- If public, is the OAuth flow generic enough for others, or is it tightly coupled to a specific IAP setup?
- Should `configure()` ship pre-filled client_id/secret for an internal audience, or always require user input?
- What does the install experience look like end-to-end for a new team member on a fresh laptop?

### Decision needed

Sketch out the full user journey from "new laptop" to "making authenticated requests in Jupyter" for each option before picking one. The right distribution method depends on the audience and how much setup friction is acceptable.

---

## 2. CI/CD Pipeline

Once the distribution method is chosen, set up CI to automate quality checks and publishing.

### Baseline (do regardless of distribution choice)

- **GitHub Actions workflow** running on push/PR:
  - `uv run ruff format --check src/ tests/`
  - `uv run ruff check src/ tests/`
  - `uv run ty check src/`
  - `uv run pytest tests/ -v`
- **Branch protection** requiring CI to pass before merge

### Publishing (depends on distribution decision above)

- If PyPI: add a release workflow triggered by git tags (`v0.1.0`) that builds and uploads via `twine` or `uv publish`
- If Artifact Registry: add a Cloud Build trigger or GitHub Actions step that pushes to the private registry
- If git-based: no publish step needed, but tag releases for `pip install git+...@v0.1.0`

### Existing infrastructure context

The CI/CD notes reference Cloud Build triggers, Artifact Registry, and Watchtower for Docker-based services. Tokentoss is a Python library (not a service), so the pipeline is simpler — but could share the same GCP project and Artifact Registry if the private route is chosen.

---

## 3. Widgets Subpackage

We now have two widgets (`GoogleAuthWidget`, `ConfigureWidget`) and may add more. Refactor into a `widgets` subpackage for better organization.

### Current structure

```
src/tokentoss/
    widget.py              # GoogleAuthWidget + CallbackServer (~730 lines)
    configure_widget.py    # ConfigureWidget (~180 lines)
```

### Proposed structure

```
src/tokentoss/
    widgets/
        __init__.py        # re-exports GoogleAuthWidget, ConfigureWidget
        auth.py            # GoogleAuthWidget + CallbackServer (from widget.py)
        configure.py       # ConfigureWidget (from configure_widget.py)
```

### Migration plan

1. Create `src/tokentoss/widgets/` package
2. Move `widget.py` -> `widgets/auth.py`
3. Move `configure_widget.py` -> `widgets/configure.py`
4. Create `widgets/__init__.py` that re-exports both widget classes
5. Update `src/tokentoss/__init__.py` lazy imports to point to `widgets.auth` and `widgets.configure`
6. Delete old `widget.py` and `configure_widget.py`
7. Update test imports (should still work if `__init__.py` re-exports correctly)
8. Run full verification (`ruff`, `ty`, `pytest`)

### Benefits

- Clear home for future widgets (e.g. a token status widget, a logout widget)
- `widget.py` is the largest file in the package — splitting it into a subpackage gives room to factor out `CallbackServer` later if needed
- Import paths stay clean: `from tokentoss import GoogleAuthWidget` continues to work via lazy `__getattr__`

---

## 4. Manual Testing

Before any release, do a hands-on check in JupyterLab:

- [ ] `ConfigureWidget` renders with password-masked fields
- [ ] Entering credentials and clicking Configure writes to `~/.config/tokentoss/client_secrets.json`
- [ ] `GoogleAuthWidget()` (no args) picks up the configured credentials
- [ ] Full OAuth flow completes and `IAPClient` can make authenticated requests
- [ ] Sign out and re-authenticate cycle works cleanly



# Misc

1. cloufbuild and CI/CD planning
- how to setup cloud build
- how to install from cloud build when on a local machine using uv
- should we make this a public package and pass the client secrets so that this is the public entry into the auth side of everythiong on a client machine?