When directed to this folder use the following guidance for finding the information you need more efficiently.

# Orientation

This `_blueprint` folder holds reference content, planning documents, and knowledge for
developing the project. Nothing here is part of the application itself.

# Guidance

## Directory Structure

### `roadmap/` — Status and history

| File | Role |
|---|---|
| `ROADMAP.md` | Slim index — status and links to detailed files, one-liner, spec link |
| `phase-history.md` | Append-only narrative log of completed phases (decisions, detours, full story) |
| `implementation-progress.md` | Deep index of current active features and phase(s) only |
| `decision-log.md` | Working decisions for active/recent phase — flushed to history during cleanup |
| `feature-backlog.md` | Plans for non-active phases + backlog ideas/fixes/enhancements |


### `features/` — Active implementation specs
- Active specs for upcoming or in-progress phases
- Each active spec linked from `roadmap/ROADMAP.md`
- See `features/AGENTS.md` for naming conventions and workflow primitives

### `archive/` — Completed, superseded, and reference work
- Mirrors the blueprint structure (`features/`, `prompts/`, etc.)
- Files prefixed with `[completed]` (shipped), `[discarded]` (superseded/stale), or `[reference]` (durable historical material — audits, snapshots, design references)
- Whole-directory snapshots are NOT prefixed; treat any unprefixed dir as `[reference]` by default
- See `archive/AGENTS.md` for full archiving guidelines

### `context/` — Technical Reference Material
- One subfolder per topic or package (e.g., `pytest/`, `ruff/`, `google-iap/`)
- Contains markdown, text, HTML with reference docs relevant to that topic
- If a topic is missing, ask the user if they want to create a new directory

### `prompts/` — Session prompt templates
- Reusable prompt templates for different session types (planning, implementation, alignment)


# Feature Spec Template

When creating a new feature spec in `features/`, use this structure:

```markdown
# <Feature Name>

> One-line summary of what this feature does.

**Status**: Planned | In Progress | Done
**Priority**: P0 | P1 | P2 | P3
**Phase**: N
**Last updated**: YYYY-MM-DD

---

## Problem

What problem does this solve? Why does it matter?

## Solution

### Overview
High-level description of the approach.

### Implementation Details
Detailed design, code locations, pseudocode, architecture changes.

## Dependencies

- **Requires**: What must be done first (link to other feature specs)
- **Enables**: What this unblocks

## Open Questions

Unresolved design decisions or trade-offs.

## Acceptance Criteria

- [ ] Criterion 1
- [ ] Criterion 2
```

# Workflow

1. **Ideation** happens in `roadmap/feature-backlog.md` — one-to-three lines per item is enough; raw brainstorms and unstructured exploration live here until refined.
2. When an idea is committed to, create a spec in `features/` and link from `roadmap/ROADMAP.md`.
3. When work is complete, move the spec to `archive/features/` with `[completed]` prefix.
4. Superseded or stale docs go to `archive/` with `[discarded]` prefix.
