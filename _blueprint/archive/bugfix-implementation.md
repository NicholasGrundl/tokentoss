# Plan: Fix OAuth Callback Bug + Package Logging System

Two deliverables: (A) a proper logging module for the package, then (B) the callback bug fix instrumented with that logging.

---

## Part A: Package Logging Module

### Design

Create `src/tokentoss/_logging.py` with a Jupyter-friendly logging setup.

**Key decisions:**
- Use stdlib `logging` only (no external deps)
- Follow Python library convention: attach `NullHandler` to the package logger by default (silent unless user opts in)
- Provide `tokentoss.enable_debug()` convenience function for users
- Jupyter-friendly: route to `sys.stdout` (not stderr) to avoid red output in notebooks
- Deduplicate handlers: check before adding to prevent double-output on repeated `enable_debug()` calls
- Telemetry stub: define a `_telemetry.py` with a no-op interface (emit functions that do nothing), ready for future OpenTelemetry or similar integration

### `_logging.py` contents

```python
"""Logging configuration for tokentoss."""

import logging
import sys

# Package-level logger
_package_logger = logging.getLogger("tokentoss")
_package_logger.addHandler(logging.NullHandler())  # Library convention

# Sentinel for our handler
_HANDLER_NAME = "_tokentoss_stream"


def enable_debug(level: int = logging.DEBUG) -> None:
    """Enable debug logging for tokentoss.

    Jupyter-friendly: outputs to stdout (not stderr) to avoid
    red-colored output in notebook cells.

    Can be called multiple times safely (won't duplicate handlers).
    """
    _package_logger.setLevel(level)

    # Don't add duplicate handlers
    for h in _package_logger.handlers:
        if getattr(h, "name", None) == _HANDLER_NAME:
            h.setLevel(level)
            return

    handler = logging.StreamHandler(sys.stdout)
    handler.name = _HANDLER_NAME
    handler.setLevel(level)
    handler.setFormatter(
        logging.Formatter(
            "[%(name)s %(levelname)s] %(message)s"
        )
    )
    _package_logger.addHandler(handler)


def disable_debug() -> None:
    """Disable debug logging and remove the tokentoss handler."""
    _package_logger.setLevel(logging.WARNING)
    _package_logger.handlers = [
        h for h in _package_logger.handlers
        if getattr(h, "name", None) != _HANDLER_NAME
    ]
```

### `_telemetry.py` stub (no-op)

```python
"""Telemetry stubs for future instrumentation.

All functions are no-ops. When a telemetry backend is added (e.g.
OpenTelemetry), these will be wired up without changing call sites.
"""


def trace_event(name: str, **attributes) -> None:
    """Record a trace event (no-op)."""


def increment_counter(name: str, value: int = 1, **tags) -> None:
    """Increment a metric counter (no-op)."""
```

### Expose in `__init__.py`

Add `enable_debug` and `disable_debug` to public API:
```python
from ._logging import enable_debug, disable_debug
```

### Usage pattern in each module

Each module gets its own child logger:
```python
import logging
logger = logging.getLogger(__name__)  # e.g. "tokentoss.widget"
```

Then `logger.debug(...)`, `logger.warning(...)`, etc.

---

## Part B: Fix OAuth Callback Bug

### Bug Summary

Three interacting bugs prevent the callback server from capturing the auth code:

1. **`_try_start_server()` orphans old servers** — creates new `CallbackServer` without stopping the previous one. Old server keeps running, receives the OAuth redirect, but widget checks the new (empty) server.
2. **`_check_callback()` restarts server after every callback** (lines 649-650) — assigns new port, breaking subsequent flows.
3. **JS `popup.closed` race** — browser may briefly report popup as closed during redirect, triggering premature check.

### Fix 1: `_try_start_server()` — stop old server first

**File:** `src/tokentoss/widget.py:572-575`

```python
def _try_start_server(self) -> None:
    """Try to start the callback server."""
    if self._callback_server:
        self._callback_server.stop()
        logger.debug("Stopped old callback server on port %s", self._callback_server.port)
    self._callback_server = CallbackServer()
    self._server_available = self._callback_server.start()
    if self._server_available:
        logger.debug("Started callback server on port %s", self._callback_server.port)
    else:
        logger.warning("Failed to start callback server")
```

### Fix 2: `_check_callback()` — don't restart server, just reset state

**File:** `src/tokentoss/widget.py:620-654`

Replace lines 648-650 (`stop()` + `_try_start_server()`) with `self._callback_server.reset()`. The server stays alive on the same port.

```python
def _check_callback(self) -> None:
    if not self._callback_server:
        return

    logger.debug(
        "Checking callback: port=%s, received=%s",
        self._callback_server.port,
        self._callback_server.callback_received,
    )

    if self._callback_server.check_callback():
        if self._callback_server.error:
            self.error = f"Authentication error: {self._callback_server.error}"
            self.status = "Authentication failed"
            self._code_verifier = None
        elif self._callback_server.auth_code:
            if self._callback_server.state and self._callback_server.state != self.state:
                self.error = "Invalid state - possible CSRF attack"
                self.status = "Authentication failed"
                self._code_verifier = None
                return
            self._exchange_code(
                self._callback_server.auth_code,
                self._callback_server.redirect_uri,
            )
        else:
            self.status = "Click to sign in"
            self._code_verifier = None

        # Reset state but keep server alive on same port
        self._callback_server.reset()
    else:
        self.show_manual_input = True
        self.status = "Paste the redirect URL below"
```

### Fix 3: JS polling — debounce `popup.closed` detection

**File:** `src/tokentoss/widget.py` (JS in `_ESM` string, ~line 338)

Require 2 consecutive `popup.closed` checks (1 second total) before firing `check_callback`:

```javascript
function startPolling() {
    stopPolling();
    let closedCount = 0;
    pollInterval = setInterval(() => {
        if (popup && popup.closed) {
            closedCount++;
            if (closedCount >= 2) {
                stopPolling();
                popup = null;
                model.send({ type: 'check_callback' });
            }
        } else {
            closedCount = 0;
        }
    }, 500);
}
```

### Fix 4: Add logging to `CallbackServer` and handler

Add `logger.debug()` calls to:
- `CallbackServer.start()` — port bound
- `CallbackServer.stop()` — shutting down
- `_CallbackHandler.do_GET()` — callback received (code present/absent)
- `prepare_auth()` — redirect_uri, auth URL generated
- `_handle_message()` — message type received

---

## Files Modified

| File | Change |
|------|--------|
| `src/tokentoss/_logging.py` | **New** — package logging config |
| `src/tokentoss/_telemetry.py` | **New** — no-op telemetry stubs |
| `src/tokentoss/__init__.py` | Add `enable_debug`, `disable_debug` to public API |
| `src/tokentoss/widget.py` | Bug fixes + logging instrumentation |

## Verification

1. `pytest tests/` — run existing tests to check nothing breaks
2. In a Jupyter notebook:
   ```python
   import tokentoss
   tokentoss.enable_debug()
   widget = tokentoss.GoogleAuthWidget(client_secrets_path="./client_secrets.json")
   display(widget)
   ```
3. Click "Sign in", complete OAuth flow
4. Check logs show consistent port throughout: `prepare_auth` → `do_GET` → `_check_callback` → `_exchange_code`
5. Verify widget updates to "Signed in as ..."
6. Sign out, sign in again — verify second flow also works
7. `tokentoss.disable_debug()` — verify logging stops
