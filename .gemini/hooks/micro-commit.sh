#!/bin/bash
# micro-commit.sh - Fast, instant commits for every file change
#
# PURPOSE: Create [MICRO] checkpoint commits for file modification operations
# TRIGGER: AfterTool hook
# INPUT: JSON on stdin (Gemini format)
# OUTPUT: JSON on stdout (Gemini format)

set -e

# 1. Read input from stdin
input=$(cat)

# 2. Extract context using jq
hook_event_name=$(echo "$input" | jq -r '.hook_event_name // "unknown"')
tool_name=$(echo "$input" | jq -r '.tool_name // "unknown"')
# Extract file path for write_file/replace/etc.
file_path=$(echo "$input" | jq -r '.tool_input.file_path // empty')
# Extract command for run_shell_command
shell_command=$(echo "$input" | jq -r '.tool_input.command // empty')

# Debug logging to stderr
echo "[micro-commit] Event: $hook_event_name, Tool: $tool_name" >&2

# 3. Validation
if [ "$hook_event_name" != "AfterTool" ]; then
    echo '{"decision": "allow", "systemMessage": "[micro-commit] Skipped: Not AfterTool"}'
    exit 0
fi

# 4. Determine "filename" for the commit message
target_name=""
if [ -n "$file_path" ]; then
    target_name=$(basename "$file_path")
elif [ -n "$shell_command" ]; then
    # Use the first word of the command as the "filename" or action
    target_name=$(echo "$shell_command" | awk '{print $1}')
else
    target_name="unknown"
fi

# 5. Check for git changes
# We look for:
# - Staged changes (cached)
# - Unstaged changes (files)
# - Untracked files (others)
if git diff --quiet && git diff --staged --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
    echo '{"decision": "allow"}'
    exit 0
fi

# 6. Auto-stage all changes
git add -A 2>/dev/null || true

# Check again if anything was actually staged
if git diff --staged --quiet; then
    echo '{"decision": "allow"}'
    exit 0
fi

# 7. Create commit
timestamp=$(date '+%H:%M:%S')
commit_msg="[MICRO] ${tool_name}: ${target_name} @ ${timestamp}"

if git commit -m "$commit_msg" --quiet 2>/dev/null; then
    # Success: Return JSON with systemMessage
    # Use jq to safely escape the message string for JSON
    json_msg=$(jq -n --arg msg "✓ $commit_msg" '{"decision": "allow", "systemMessage": $msg}')
    echo "$json_msg"
else
    # Failure to commit (but script succeeded): Return allow
    echo '{"decision": "allow"}'
fi

exit 0
