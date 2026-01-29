# CLAUDE.md

## Testing

Run tests using `uv`:
```bash
uv run pytest tests/ -x -q
```

- Always use `uv run` to execute commands (not `python` or `python3` directly)
- The `-x` flag stops on first failure; `-q` gives concise output
