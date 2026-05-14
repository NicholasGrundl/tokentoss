# Archive Standards

This directory holds completed, superseded, or durable-reference work — material that no longer drives active development but is worth preserving for historical context.

## Purpose

The archive is the answer to "where did this go?" When work ships, gets superseded, or lives on as a reference, it lands here. Nothing in `archive/` should drive current decisions; if you need to act on something here, lift it back into `features/` or `roadmap/feature-backlog.md` first.

## Prefix Vocabulary

Every file at the top level of an archive subdirectory should carry one of these prefixes in its filename:

| Prefix | Meaning | Example |
|---|---|---|
| `[completed]` | Shipped work. Delivered as designed and merged. | `[completed]daisyui-migration-v1.md` |
| `[discarded]` | Superseded, stale, or rejected. Kept for audit, not for use. | `[discarded]review-prompt-1-hero.md` |
| `[reference]` | Durable historical material — audits, snapshots, design references. Not work product, not stale. | `[reference]repo-audit-2026-01-29.md` |

Choose the prefix that reflects the file's status when it entered the archive, not when it was created.

## Unprefixed Directories

Whole-directory snapshots (e.g., `archive/plan/animation/`, `archive/plan/daisyui_migration/`, `archive/plan/logo_references/`) are NOT prefixed at the directory level. **Treat any unprefixed directory in `archive/` as `[reference]` by default.**

This avoids bulk-renaming dozens of files inside a coherent reference snapshot, while still letting individual files inside such a directory carry their own prefix if needed.

## Current Layout

The current archive layout reflects the v1 blueprint structure preserved as a snapshot:

```
archive/
├── claude-agents/        # Superseded .claude/ subagents (v1 docs-updater)
├── claude-commands/      # Superseded .claude/ slash commands (v1 design/tasks/work/commit-* set)
├── ideas/                # Raw brainstorms and exploration from v1 blueprint
├── implement/            # v1 implementation plans (now empty — all 4 graduated to features/)
├── plan/                 # v1 design docs and reference assets (animation/, daisyui_migration/, logo_references/, style_references/, wireframes/)
├── features/             # Future archive entries for completed/discarded specs
└── prompts/              # Future archive entries for retired prompt templates
```

Going forward, new archive entries follow the same layout as the v2 blueprint — mirror the source directory structure (e.g., a completed `features/[planning]<name>-v1.md` graduates here as `archive/features/[completed]<name>-v1.md`).

## Lifting Content Back

When work in the archive becomes active again:

1. **From `[reference]`**: copy or extract the relevant material into `_blueprint/context/<topic>/` if it's durable reference, or into a new `[planning]<name>-v1.md` spec if it's becoming work.
2. **From `[discarded]`**: re-evaluate first — usually `[discarded]` means the file's premises don't hold anymore. If the underlying problem is back, write a fresh spec rather than reviving the old one.
3. **From `[completed]`**: copy the relevant decisions/rationale into the new spec's Problem section. Don't move the original — it documents what shipped.
