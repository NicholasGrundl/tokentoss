When directed to this folder use the following guidance for finding the information you need more efficiently.

<overview>

If searching for <context> on a specific package, protocol, or other factual topic:
- look in the @_blueprint/context/{topic/package}/ directory.
- folders are named by their topic or package and contain markdown files relevant to that specific package
- if a topic is missing consider asking the user if they want you to create a new directory and populate it with content from the web

If searching for <plan> information such as design docs, implementation plans, etc.:
- look in the @_blueprint/plan/ directory.
- this directory contains markdown files with greater details

If searching for <notes> such as ideas, earlier plans, brainstorming documents, or examples:
- look in the @_blueprint/notes/ directory.
- this directory has a free form structure but should contain largely markdown and other text files

</overview>

<testing>

## Testing

Run tests using `uv`:
```bash
uv run pytest tests/ -x -q
```

- Always use `uv run` to execute commands (not `python` or `python3` directly)
- The `-x` flag stops on first failure; `-q` gives concise output

</testing>
