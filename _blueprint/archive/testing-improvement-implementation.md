# Plan: Testing Strategy + pytest-mock Migration

## Part A: pytest-mock Migration

### Current State

All three test files use `unittest.mock`:

| File | Patterns Used |
|------|--------------|
| `test_auth_manager.py` | `@patch("module.path")` decorator, `Mock()` |
| `test_widget.py` | `patch.object(Cls, "method")` context manager + decorator, `Mock()` |
| `test_storage.py` | No mocking (uses real filesystem via `tmp_path`) |

### Migration Plan

1. Add `pytest-mock` to dev dependencies in `pyproject.toml`
2. Replace all `unittest.mock` usage with `mocker` fixture:

**Before:**
```python
from unittest.mock import Mock, patch

@patch("tokentoss.auth_manager.requests.post")
def test_exchange(self, mock_post, auth_manager):
    mock_response = Mock()
    ...
```

**After:**
```python
def test_exchange(self, auth_manager, mocker):
    mock_post = mocker.patch("tokentoss.auth_manager.requests.post")
    mock_response = mocker.Mock()
    ...
```

Key changes:
- Remove `from unittest.mock import Mock, patch` from all test files
- Add `mocker` as fixture parameter to tests that need mocking
- `@patch("x")` → `mocker.patch("x")` (inline, not decorator)
- `patch.object(Cls, "m")` → `mocker.patch.object(Cls, "m")`
- `Mock()` → `mocker.Mock()`
- No more context managers for patching; mocker auto-cleans up

### Files to Change

- `pyproject.toml` - add `pytest-mock>=3.12.0` to dev dependencies
- `tests/test_auth_manager.py` - migrate 6 tests using `@patch`
- `tests/test_widget.py` - migrate ~10 tests using `patch.object` / `Mock`
- `tests/test_storage.py` - no changes needed (no mocking)

---

## Part B: Widget & System Testing Strategy

### Testing Layers

#### Layer 1: Python Unit Tests (already have, improve with mocker)
- Test traitlet state transitions
- Test method logic with mocked dependencies
- Test error handling paths
- **No Jupyter needed**, runs in plain pytest

#### Layer 2: Flow Simulation Tests (NEW)
- Simulate the full auth flow by manipulating traitlets as JS would
- Test the `prepare_auth` → `auth_code change` → `exchange_code` → authenticated pipeline
- Test the `check_callback` flow (server receives code → exchange)
- Test sign-out → re-auth cycle
- **No Jupyter needed**, tests the Python-JS contract without a browser

Example:
```python
def test_full_auth_flow(widget, mocker):
    """Simulate complete auth flow as JS would drive it."""
    mock_exchange = mocker.patch.object(widget._auth_manager, "exchange_code")
    mock_exchange.return_value = TokenData(...)

    # JS sends prepare_auth message
    widget._handle_message(widget, {"type": "prepare_auth"}, [])
    assert widget.auth_url != ""
    assert widget.status == "Waiting for authentication..."

    # JS sets auth_code (simulating manual paste)
    widget.auth_code = "real-auth-code"

    assert widget.is_authenticated is True
    assert "Signed in as" in widget.status
```

#### Layer 3: CallbackServer Integration Tests (already have, improve)
- Real HTTP requests to the callback server
- Test code extraction from OAuth-like redirect URLs
- Test error handling (error parameter, missing code)
- **Already marked with `@pytest.mark.integration`**

#### Layer 4: End-to-End Notebook Tests (future, not this PR)
- Would use Playwright + Galata (JupyterLab testing framework)
- Requires running Jupyter server, browser automation
- Can't automate Google's OAuth consent screen (would need to mock at network level)
- **Recommend deferring** - high setup cost, fragile, limited value over Layer 2

### Why Layer 2 is the key addition

The widget's Python side is fully testable without Jupyter because:
- `anywidget.AnyWidget` traitlets work in plain Python
- The `observe()` callback fires when traitlets change, even outside a notebook
- Custom messages can be simulated via `_handle_message()`
- The only thing we can't test is the JS rendering and popup behavior

This means we can test the entire auth pipeline (prepare → callback → exchange → authenticated) with just pytest, giving us confidence to refactor safely.

### New Test Cases to Add

**Flow simulation tests (`test_widget.py`):**
1. Full auth flow via manual paste (prepare → set auth_code → authenticated)
2. Full auth flow via callback server (prepare → check_callback → authenticated)
3. Sign out and re-authenticate cycle
4. Auth flow with exchange failure then retry
5. Popup closed without completing auth (check_callback with no code)

**Edge case tests:**
6. Multiple prepare_auth calls (verify PKCE regenerated)
7. Auth code set without calling prepare_auth first
8. Widget init with already-expired credentials (should still show authenticated)

---

## Implementation Order

1. Add `pytest-mock` to `pyproject.toml` dev dependencies
2. Migrate `test_auth_manager.py` to use `mocker` fixture
3. Migrate `test_widget.py` to use `mocker` fixture
4. Add Layer 2 flow simulation tests to `test_widget.py`
5. Run full test suite to verify
