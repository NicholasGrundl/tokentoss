# Distribution: Public PyPI

## Decision

**Publish tokentoss as a public package on PyPI.**

### Why public PyPI

| Option | Verdict |
|--------|---------|
| **Public PyPI** | **Chosen.** Standard `pip install tokentoss`. Lowest friction for end users at client orgs who each have their own IAP setup. No secrets bundled — users provide their own `client_id`/`client_secret` via `ConfigureWidget`. |
| Private PyPI (GCP Artifact Registry) | Rejected. Every user at every client org would need GCP auth to the registry. Major friction for external users. |
| GitHub release / git install | Decent fallback, but no version index, less discoverable, requires repo access or public repo. |

### Audience

- **Primary:** End users at various client organizations, each with their own IAP-protected API
- **All users have:** Gmail or Google Workspace accounts
- **Install experience:** `pip install tokentoss` or `uv add tokentoss`, then `ConfigureWidget()` to enter their org's OAuth credentials

---

## PyPI Metadata Prep

### `pyproject.toml` — Add project URLs

Add after the `classifiers` list:

```toml
[project.urls]
Homepage = "https://github.com/NicholasGrundl/tokentoss"
Repository = "https://github.com/NicholasGrundl/tokentoss"
Issues = "https://github.com/NicholasGrundl/tokentoss/issues"
Changelog = "https://github.com/NicholasGrundl/tokentoss/releases"
```

Existing metadata is already complete: `name`, `version`, `description`, `readme`, `license`, `authors`, `keywords`, `classifiers`, `dependencies`, `requires-python`.

### `README.md` — Updates

1. **Add badges** after the `# tokentoss` heading:
   ```markdown
   [![PyPI version](https://img.shields.io/pypi/v/tokentoss)](https://pypi.org/project/tokentoss/)
   [![CI](https://github.com/NicholasGrundl/tokentoss/actions/workflows/ci.yml/badge.svg)](https://github.com/NicholasGrundl/tokentoss/actions/workflows/ci.yml)
   ```

2. **Fix clone URL** on line 94: `yourusername` → `NicholasGrundl`

The README already uses standard Markdown that PyPI renders correctly. `pyproject.toml` points to it via `readme = "README.md"`.

---

## Open-Source Scaffolding

### `LICENSE` (create)

Standard MIT license text. Required — `pyproject.toml` declares `license = "MIT"` but no LICENSE file exists at the project root.

```
MIT License

Copyright (c) 2025 Nicholas Grundl

Permission is hereby granted, free of charge, to any person obtaining a copy
...
```

### `CONTRIBUTING.md` (create)

Brief guide (~50 lines). Sections:
- **Development Setup:** `git clone` + `uv sync --group dev`
- **Running Checks:** the 4 commands (format, lint, typecheck, test)
- **Submitting Changes:** fork → branch → PR → CI must pass
- **Code Style:** handled by ruff, run `uv run ruff format src/ tests/` before committing

### GitHub Issue Templates (create)

**`.github/ISSUE_TEMPLATE/bug_report.md`:**
- Description, reproduction steps, expected behavior
- Environment: Python version, tokentoss version, Jupyter environment

**`.github/ISSUE_TEMPLATE/feature_request.md`:**
- Problem description, proposed solution

---

## Manual PyPI Setup Steps

These must be done by the maintainer before the first release:

### 1. Create PyPI account
- https://pypi.org/account/register/
- Enable 2FA (required for new accounts)

### 2. Register trusted publisher
- Go to https://pypi.org/manage/account/publishing/
- Under "Add a new pending publisher":
  - **PyPI project name:** `tokentoss`
  - **Owner:** `NicholasGrundl`
  - **Repository:** `tokentoss`
  - **Workflow name:** `release.yml`
  - **Environment name:** `pypi`
- This pre-registers the project name and links it to the GitHub repo before the first publish

### 3. First release
- Merge all changes to `main`
- Tag and push:
  ```bash
  git tag v0.1.0
  git push origin v0.1.0
  ```
- The release workflow handles building and publishing automatically
- Verify at https://pypi.org/project/tokentoss/

---

## End-User Install Experience

From a new user's perspective:

```bash
# 1. Install
pip install tokentoss

# 2. In Jupyter, configure credentials (one-time)
from tokentoss import ConfigureWidget
display(ConfigureWidget())
# Enter client_id and client_secret provided by their org admin

# 3. Authenticate
from tokentoss import GoogleAuthWidget
widget = GoogleAuthWidget()
display(widget)
# Click "Sign in with Google"

# 4. Make requests
from tokentoss import IAPClient
client = IAPClient(base_url="https://their-iap-service.run.app")
data = client.get_json("/api/data")
```

No private registry auth, no git access, no GCP credentials needed for installation.
