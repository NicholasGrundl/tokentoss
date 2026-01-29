# Contributing to tokentoss

Thanks for your interest in contributing! This guide covers the basics.

## Development Setup

```bash
git clone https://github.com/NicholasGrundl/tokentoss.git
cd tokentoss
uv sync --group dev
```

This installs all runtime and development dependencies (ruff, ty, pytest, jupyter, etc.).

## Running Checks

**Format** (auto-fixes style):
```bash
uv run ruff format src/ tests/
```

**Lint** (auto-fixes safe issues):
```bash
uv run ruff check src/ tests/ --fix
```

**Type check** (advisory — ty is alpha):
```bash
uv run ty check src/
```

**Tests:**
```bash
uv run pytest tests/ -x -q
```

Run all four before submitting a PR. CI will check them automatically.

## Submitting Changes

1. Fork the repository
2. Create a feature branch (`git checkout -b my-feature`)
3. Make your changes
4. Run all checks (format, lint, typecheck, test)
5. Commit with a clear message
6. Push and open a Pull Request

CI must pass before merging.

## Code Style

- Enforced by [ruff](https://docs.astral.sh/ruff/) — run `uv run ruff format src/ tests/` before committing
- Target Python version: 3.10+
- Line length: 100 characters
- Double quotes for strings

## Testing

- All new features and bug fixes should include tests
- Use `pytest` with `pytest-mock` for mocking (not `unittest.mock`)
- Integration tests use the `@pytest.mark.integration` marker
- Run integration tests separately: `uv run pytest -m integration`

## Questions?

Open an [issue](https://github.com/NicholasGrundl/tokentoss/issues) — we're happy to help.
