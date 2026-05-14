# AGENTS.md

Project-level guidance for any LLM working in this repo. `CLAUDE.md` and `GEMINI.md` are symlinks to this file.

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
just start-release 0.2.0   # bump version, commit, tag, and push
```

## Blueprint Directory

The `_blueprint/` directory contains all planning, design, and reference documentation. See `_blueprint/AGENTS.md` for detailed guidance. Summary:

- **`roadmap/`** — Phase index (`ROADMAP.md`), narrative history (`phase-history.md`), live progress (`implementation-progress.md`), working decisions (`decision-log.md`), and unscheduled work (`feature-backlog.md`).
- **`features/`** — Active implementation specs. Each follows the `[<distinguisher>]<name>-<suffix>.md` convention; see `_blueprint/features/AGENTS.md`.
- **`context/`** — External reference material, one subfolder per topic/package.
- **`prompts/`** — Reusable session prompt templates (planning, implementation, alignment).
- **`archive/`** — Completed, superseded, or durable-reference work. Prefix conventions in `_blueprint/archive/AGENTS.md`.

### Workflow Rules

- Plan-mode outputs and roadmap-committed work go to `_blueprint/features/` as `[planning]<name>-v1.md` specs, linked from `roadmap/ROADMAP.md`.
- Raw ideas and unscheduled work live in `roadmap/feature-backlog.md` until they graduate to a feature spec.
- Completed specs move to `_blueprint/archive/features/` with `[completed]` prefix; superseded ones with `[discarded]`.

## Exploring with `tree`

Use the `tree` command for rapid assessment of directory structure. This is useful for progressive disclosure — start broad, then drill into specific areas.

### Basic usage

```bash
# Full tree of a directory
tree _blueprint/

# Full tree of src package
tree src/
```

### Directories only

```bash
# Show only folder structure (no files)
tree -d _blueprint/
tree -d src/
```

### Limit depth

```bash
# Top-level folders only
tree -L 1 _blueprint/

# Two levels deep (folders + immediate contents)
tree -L 2 _blueprint/context/

# Quick overview of entire project
tree -L 1 .
```

### Exclude directories

```bash
# Exclude __pycache__ and .git
tree -I "__pycache__|.git" src/

# Exclude multiple patterns
tree -I "__pycache__|.git|node_modules|*.pyc" .
```

### Common patterns

```bash
# Blueprint context topics at a glance
tree -d -L 1 _blueprint/context/

# Then drill into a specific topic
tree _blueprint/context/pytest/

# Source module structure without cache dirs
tree -I "__pycache__" src/

# Project overview: dirs only, 2 levels, skip noise
tree -d -L 2 -I "__pycache__|.git|*.egg-info" .
```
