# Widgets Subpackage Refactor

## Motivation

Two widgets exist (`GoogleAuthWidget`, `ConfigureWidget`) with more likely to come. The largest file in the package is `widget.py` at ~730 lines. Moving to a `widgets/` subpackage improves organization and gives room to grow.

## Current Structure

```
src/tokentoss/
    widget.py              # GoogleAuthWidget + CallbackServer (~730 lines)
    configure_widget.py    # ConfigureWidget (~180 lines)
```

## Proposed Structure

```
src/tokentoss/
    widgets/
        __init__.py        # re-exports GoogleAuthWidget, ConfigureWidget
        auth.py            # GoogleAuthWidget + CallbackServer (from widget.py)
        configure.py       # ConfigureWidget (from configure_widget.py)
```

## Migration Steps

### 1. Create `src/tokentoss/widgets/` package

```bash
mkdir src/tokentoss/widgets
```

### 2. Move files

```bash
mv src/tokentoss/widget.py src/tokentoss/widgets/auth.py
mv src/tokentoss/configure_widget.py src/tokentoss/widgets/configure.py
```

### 3. Create `widgets/__init__.py`

```python
"""Widget components for tokentoss."""

from .auth import GoogleAuthWidget
from .configure import ConfigureWidget

__all__ = ["GoogleAuthWidget", "ConfigureWidget"]
```

### 4. Update `src/tokentoss/__init__.py` lazy imports

Change:
```python
if name == "GoogleAuthWidget":
    from .widget import GoogleAuthWidget
    return GoogleAuthWidget
# ...
if name == "ConfigureWidget":
    from .configure_widget import ConfigureWidget
    return ConfigureWidget
```

To:
```python
if name == "GoogleAuthWidget":
    from .widgets.auth import GoogleAuthWidget
    return GoogleAuthWidget
# ...
if name == "ConfigureWidget":
    from .widgets.configure import ConfigureWidget
    return ConfigureWidget
```

### 5. Update internal imports

Check if `widget.py` imports from other tokentoss modules (e.g., `from .auth_manager import ...`). After the move to `widgets/auth.py`, these become `from ..auth_manager import ...` (parent package).

Same for `configure_widget.py` → `widgets/configure.py`.

### 6. Update test imports

Tests currently import directly:
```python
from tokentoss.widget import GoogleAuthWidget, CallbackServer
from tokentoss.configure_widget import ConfigureWidget
```

Update to:
```python
from tokentoss.widgets.auth import GoogleAuthWidget, CallbackServer
from tokentoss.widgets.configure import ConfigureWidget
```

Top-level imports (`from tokentoss import GoogleAuthWidget`) continue to work via `__getattr__`.

### 7. Update `pyproject.toml` ty overrides

Current override references `src/tokentoss/widget.py`:
```toml
[[tool.ty.overrides]]
include = ["src/tokentoss/widget.py"]
```

Change to:
```toml
[[tool.ty.overrides]]
include = ["src/tokentoss/widgets/auth.py"]
```

### 8. Verify

```bash
uv run ruff format --check src/ tests/
uv run ruff check src/ tests/
uv run ty check src/
uv run pytest tests/ -v
```

## Future Consideration: Factor Out CallbackServer

`auth.py` (formerly `widget.py`) contains both `GoogleAuthWidget` (~240 lines) and `CallbackServer` + `_CallbackHandler` (~140 lines), plus ~350 lines of JS/CSS/HTML constants. If the file becomes harder to navigate, consider:

```
widgets/
    __init__.py
    auth.py                # GoogleAuthWidget only
    configure.py           # ConfigureWidget
    callback_server.py     # CallbackServer + _CallbackHandler
```

This is optional and can be decided when actually doing the refactor. The current split (just moving files into `widgets/`) is sufficient for now.

## Files Changed

| Action | File |
|--------|------|
| Create | `src/tokentoss/widgets/__init__.py` |
| Move   | `widget.py` → `widgets/auth.py` |
| Move   | `configure_widget.py` → `widgets/configure.py` |
| Modify | `src/tokentoss/__init__.py` (lazy import paths) |
| Modify | `pyproject.toml` (ty override path) |
| Modify | `tests/test_widget.py` (imports) |
| Modify | `tests/test_configure_widget.py` (imports) |
| Delete | `src/tokentoss/widget.py` |
| Delete | `src/tokentoss/configure_widget.py` |
