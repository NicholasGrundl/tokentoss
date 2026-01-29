# CLAUDE.md

## Testing

Run tests using `uv`:
```bash
uv run pytest tests/ -x -q
```

- Always use `uv run` to execute commands (not `python` or `python3` directly)
- The `-x` flag stops on first failure; `-q` gives concise output
- Always use pytest — do not use unittest directly
- When unittest functionality is needed (e.g. mocking), prefer pytest ecosystem equivalents (e.g. `pytest-mock`, `monkeypatch`) over `unittest.mock`
