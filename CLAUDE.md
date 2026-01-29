# CLAUDE.md

## Running Commands

Always use `uv run` to execute commands (not `python` or `python3` directly).

## Testing

```bash
uv run pytest tests/ -x -q
```

- The `-x` flag stops on first failure; `-q` gives concise output
- Always use pytest — do not use unittest directly
- When unittest functionality is needed (e.g. mocking), prefer pytest ecosystem equivalents (e.g. `pytest-mock`, `monkeypatch`) over `unittest.mock`
- Integration tests are marked with `@pytest.mark.integration`; run them with `uv run pytest -m integration`

## Formatting

```bash
uv run ruff format src/ tests/
```

## Linting

```bash
uv run ruff check src/ tests/ --fix
```

- The `--fix` flag auto-fixes safe issues
- To see issues without fixing: `uv run ruff check src/ tests/`

## Type Checking

```bash
uv run ty check src/
```
