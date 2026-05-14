# Features Directory Standards

This directory is the primary workspace for planning, auditing, and implementing tokentoss's features. It follows a strict topology and naming convention to ensure scannability and context retention for both humans and LLMs.

## Topology

- **Root (`_blueprint/features/`)**: Contains active LLM rule files (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`) and all files related to the **current** active feature(s) being implemented.
- **Planning**: Features in the planning or ideation stage carry the `[planning]` distinguisher. Use this for draft plans, specs that emerged from another work thread but are not yet active, and anything not currently being implemented.

## Filename Convention

Filenames must be semantic and descriptive. Use the following structure:
`[<distinguisher>]<descriptive-name>-<suffix>.md`

0. **Distinguisher** (Optional): Used to differentiate state and/or version (e.g., `planning`, `draft`, `deprecated`, `completed`).
1. **Descriptive Name**: A concise, dash-separated name for the feature (e.g., `daisyui-migration`).
2. **Suffix** (optional): Used to link related files together (multi-stage plans → `stage1`, `stage2`; revisions → `revision1`).

**Example**: `[planning]daisyui-migration-v1.md`

## Header Convention (Markdown)

Every spec in this folder MUST start with a markdown header block. LLMs should read this section first to determine the document's status and history without reading the entire file. The canonical template lives in `_blueprint/AGENTS.md` under "Feature Spec Template" — it uses these top-level fields:

```markdown
# <Feature Name>

> One-line summary of what this feature does.

**Status**: Planned | In Progress | Done
**Priority**: P0 | P1 | P2 | P3
**Phase**: N
**Last updated**: YYYY-MM-DD
```

YAML frontmatter is NOT required. The markdown-header convention won during the v2 cleanup; it survives copy/paste into chat windows and matches the rest of the roadmap files.

---

**Instruction for LLMs**: When entering this directory, scan the filenames and read the markdown header (Status / Priority / Phase / Last updated) of relevant files to synchronize with each feature's trajectory before suggesting changes.
