When directed to this folder use the following guidance for finding the information you need more efficiently.

## Directory Structure

### `context/` — External Reference Material
- One subfolder per topic or package (e.g., `pytest/`, `ruff/`, `google-iap/`)
- Contains markdown files with reference docs relevant to that topic
- If a topic is missing, ask the user if they want you to create a new directory and populate it with content from the web

### `plan/` — Design Docs & Roadmap
- Properly documented design documents and roadmap items
- Numbered files for ordering (e.g., `01-next-steps.md`, `03-widgets-subpackage.md`)
- Move completed plans to `archive/` once fully implemented

### `implement/` — Actionable Implementation Plans
- Ready-to-execute implementation plans and manual setup checklists
- Plan mode outputs should be saved here
- Includes both code-level implementation plans and browser/hands-on step guides (e.g., GitHub settings, PyPI setup)

### `ideas/` — Unstructured Thinking
- Catch-all for brainstorms, early-stage ideas, LLM design explorations, research dumps, and scratch notes
- No structure requirements
- Refined ideas graduate to `plan/` once properly documented

### `archive/` — Completed Work
- Finished implementation plans and completed design docs move here
- Serves as the historical record of completed work

## Workflow

- **Roadmap and design docs** belong in `plan/`
- **Plan mode outputs** (implementation plans ready for execution) go in `implement/`
- **Completed plans and implementations** move to `archive/`
- **Raw ideas and exploration** go in `ideas/` until refined into a proper plan
