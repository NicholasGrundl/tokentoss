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

## Security

```bash
uv run pip-audit
uv run bandit -r src/ -c pyproject.toml
```

- `pip-audit` checks dependencies for known CVEs
- `bandit` scans source code for common security issues
- Both run in CI on every PR and weekly via `.github/workflows/security.yml`

## Just Commands

A `justfile` provides shortcuts for common tasks. Run `just --list` to see all recipes.

```bash
just ci              # run all CI checks locally (lint + typecheck + test)
just fix             # auto-fix formatting and lint issues
just security        # run all security checks
just release 0.2.0   # bump version, commit, and tag
```

## Blueprint Directory

The `_blueprint/` directory contains all planning, design, and reference documentation. See `_blueprint/CLAUDE.md` for detailed guidance. Summary:

- **`context/`** — External reference material, one subfolder per topic/package
- **`plan/`** — Design docs and roadmap items (numbered for ordering). Move to `archive/` when done.
- **`implement/`** — Actionable implementation plans and setup checklists. Plan mode outputs go here.
- **`ideas/`** — Catch-all for brainstorms, rough notes, and early-stage thinking. No structure required.
- **`archive/`** — Completed work only. Historical record of finished plans and implementations.

### Workflow Rules

- When plan mode produces an implementation plan, save it to `_blueprint/implement/`
- Roadmap and design documents belong in `_blueprint/plan/`
- Once a plan or implementation is complete, move it to `_blueprint/archive/`
- Raw ideas and exploration go in `_blueprint/ideas/` until refined into a proper plan
