# Plan: Ruff + ty Setup, Test Migration, README Update, ConfigureWidget

## Execution Order

1. **Ruff + ty setup** — establishes formatting baseline before code changes
2. **Test migration** — code change that gets formatted by ruff
3. **ConfigureWidget** — new widget for secret-safe credential setup
4. **README update** — documentation reflecting final code state

---

## Step 1: Ruff + ty Setup

### 1a. Add dev dependencies to `pyproject.toml`

Add `ruff` and `ty` to `[dependency-groups] dev`:

```toml
"ruff>=0.11.0",
"ty>=0.0.1a7",
```

Run `uv sync --group dev`.

### 1b. Add ruff config to `pyproject.toml`

```toml
[tool.ruff]
target-version = "py310"
line-length = 100
src = ["src"]

[tool.ruff.lint]
select = [
    "F",      # pyflakes — unused imports, undefined names
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "I",      # isort — import ordering
    "UP",     # pyupgrade — modernize for 3.10+
    "B",      # flake8-bugbear — common bugs
    "SIM",    # flake8-simplify — simplification
    "C4",     # flake8-comprehensions — comprehension style
    "PT",     # flake8-pytest-style — pytest conventions
    "T20",    # flake8-print — no stray print() in library code
    "RUF",    # ruff-specific rules
]
ignore = [
    "E501",   # line length handled by formatter
]

[tool.ruff.lint.isort]
known-first-party = ["tokentoss"]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["T20"]  # allow print() in tests

[tool.ruff.format]
quote-style = "double"
```

### 1c. Add ty config to `pyproject.toml`

Per `_blueprint/context/ty/06-configuration-reference.md`:

```toml
[tool.ty.environment]
python-version = "3.10"
```

ty is alpha — treat output as advisory, not blocking.

### 1d. Run ruff format and lint, fix issues

```bash
uv run ruff format src/ tests/
uv run ruff check src/ tests/ --fix
uv run ruff check src/ tests/        # verify clean
```

Expected fixes: import reordering, possible duplicate imports, minor style issues.

### 1e. Run ty and evaluate

```bash
uv run ty check src/
```

Expect false positives from traitlets typing and lazy `__getattr__` imports. Don't suppress aggressively.

### 1f. Run tests to confirm nothing broke

```bash
uv run pytest tests/ -v
```

**Files modified:** `pyproject.toml`, plus any source files ruff auto-fixes.

---

## Step 2: Test Migration (unittest.mock → pytest-mock)

### Scope

Only `tests/test_client.py` uses `unittest.mock`. All other test files already use `mocker`.

### Changes

1. **Remove** `from unittest.mock import MagicMock, PropertyMock` (PropertyMock is unused)

2. **Add `mocker` fixture** to all test methods/fixtures that create mocks directly:
   - `_mock_response` helper → add `mocker` param, update all call sites
   - `TestIAPClientInit` methods → add `mocker` param
   - `TestGetIdToken` methods → add `mocker` param where missing
   - `TestRequest._make_client_with_token` → already has `mocker`, just swap calls
   - `TestHTTPMethods.setup_client` → already has `mocker`, just swap calls
   - `TestLifecycle` methods → add `mocker` param

3. **Replace** all `MagicMock(...)` with `mocker.MagicMock(...)`

Per `_blueprint/context/pytest-mock/usage.md`, `mocker.MagicMock` is directly available as a convenience alias.

### Verify

```bash
uv run ruff check tests/test_client.py
uv run pytest tests/test_client.py -v
```

**Files modified:** `tests/test_client.py`

---

## Step 3: ConfigureWidget

### Purpose

A new anywidget that provides password-style input fields for client_id and client_secret, so credentials are entered at runtime and never appear in `.ipynb` source. This keeps secrets out of version control.

### Design

**New file:** `src/tokentoss/configure_widget.py`

**Class:** `ConfigureWidget(anywidget.AnyWidget)`

**Traitlets:**
- `client_id` (Unicode) — synced from JS input
- `client_secret` (Unicode) — synced from JS input
- `status` (Unicode) — display status ("Enter credentials", "Saved!", "Error: ...")
- `configured` (Bool) — set True after successful configure()

**JavaScript UI:**
- Two labeled `<input>` fields: Client ID (type="text") and Client Secret (type="password")
- "Configure" submit button
- Status text display
- Style consistent with existing `GoogleAuthWidget`

**Python behavior:**
- On `client_id` + `client_secret` change (or button press via traitlet), call `tokentoss.configure(client_id=..., client_secret=...)`
- On success: set `status = "Configured! Saved to ~/.config/tokentoss/client_secrets.json"`, set `configured = True`
- On error: set `status = "Error: ..."`, keep `configured = False`

**Flow:**
```
User runs cell: display(ConfigureWidget())
       │
       ▼
Widget renders with two input fields + button
       │
       ▼
User pastes client_id and client_secret, clicks "Configure"
       │
       ▼
JS sends values to Python via traitlets
       │
       ▼
Python calls configure(client_id=..., client_secret=...)
       │
       ├── Success → status = "Configured!", configured = True
       └── Error → status = "Error: ...", configured = False
```

**Trigger mechanism:** Use a `_submit` traitlet (Int, incremented on button click) with `observe()` in Python. This avoids reacting to partial input — only fires when user explicitly clicks Submit.

**Export:** Add to `__init__.py` exports.

### Tests

**New file:** `tests/test_configure_widget.py`

- Test widget instantiation and default traitlet values
- Test successful configure flow (mock `configure()`)
- Test error handling (mock `configure()` raising ValueError)
- Test that `configured` flag updates correctly
- Test that status messages are set properly

### Verify

```bash
uv run ruff check src/tokentoss/configure_widget.py tests/test_configure_widget.py
uv run pytest tests/test_configure_widget.py -v
```

**Files modified/created:**
- `src/tokentoss/configure_widget.py` (new)
- `tests/test_configure_widget.py` (new)
- `src/tokentoss/__init__.py` (add export)

---

## Step 4: README Update

### Changes to `README.md`

1. **Quick Start section** — restructure:
   - Step 1: GCP Console setup (keep as-is)
   - Step 2: **Configure credentials** — show both ConfigureWidget and `tokentoss.configure()` approaches
   - Step 3: Authenticate in Jupyter — `GoogleAuthWidget()` without `client_secrets_path`
   - Step 4: Make requests (keep as-is)

2. **How It Works** — update to mention `configure()` stores credentials to standard location

3. **Development section** — add ruff/ty commands:
   ```bash
   uv run ruff format src/ tests/
   uv run ruff check src/ tests/
   uv run ty check src/
   ```

4. **Remove** `client_secrets_path` from widget examples

**Files modified:** `README.md`

---

## Hypothesis Evaluation

**Skip.** Not a good fit for an OAuth integration library. Testing complexity is in mocking external services, not exploring input spaces.

---

## Verification

After all changes:
```bash
uv run ruff format src/ tests/           # formatting clean
uv run ruff check src/ tests/            # linting clean
uv run ty check src/                     # type check (advisory)
uv run pytest tests/ -v                  # all tests pass
```

Manual verification: open a Jupyter notebook and confirm ConfigureWidget renders with password fields.
