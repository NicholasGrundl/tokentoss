The 4 planning specs are independent enough to each warrant their own branch + PR. Suggested naming (matches the spec filename, kebab-case, no feat/ prefix since the existing log doesn't use one):

┌─────────────────────────────┬─────────────────────────────────────────────────┐
│           Branch            │                   Tracks spec                   │
├─────────────────────────────┼─────────────────────────────────────────────────┤
│ workspace-api-integrations  │ [planning]workspace-api-integrations-v1.md (P0) │
├─────────────────────────────┼─────────────────────────────────────────────────┤
│ docs-and-tutorials          │ [planning]docs-and-tutorials-v1.md (P0)         │
├─────────────────────────────┼─────────────────────────────────────────────────┤
│ widgets-subpackage-refactor │ [planning]widgets-subpackage-v1.md (P1)         │
├─────────────────────────────┼─────────────────────────────────────────────────┤
│ architectural-improvements  │ [planning]architectural-improvements-v1.md (P2) │
└─────────────────────────────┴─────────────────────────────────────────────────┘

Suggested first branch: workspace-api-integrations. It's the most direct path to client value, the spec is concrete, and ~80% of the work is docs + example notebooks — manageable for a first post-merge cycle. The scope-mismatch fix is the only code change in the critical path.

One small process tweak worth considering as you start the feature branches: as each spec moves from Planned → In Progress, update its Status field in the spec file and the Status column in ROADMAP.md, and add a note to decision-log.md if you make any spec-shape decisions during implementation. That keeps the roadmap an honest live document instead of a snapshot.