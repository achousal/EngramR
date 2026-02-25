#!/usr/bin/env bash
# Arscontexta note validation hook
# Checks that notes written to notes/ have required schema fields
# Runs on PostToolUse (Write) events

set -euo pipefail

# Source shared vault root detection
_LIB="$(git rev-parse --show-toplevel 2>/dev/null || echo "${PROJECT_DIR:-.}")/ops/scripts/lib/vault-env.sh"
[ -f "$_LIB" ] && source "$_LIB"
VAULT_ROOT="$(find_vault_root 2>/dev/null || git rev-parse --show-toplevel 2>/dev/null || echo "${PROJECT_DIR:-.}")"
MARKER="$VAULT_ROOT/.arscontexta"

# Only run if this is an arscontexta vault
[[ -f "$MARKER" ]] || exit 0

# Read the tool input from stdin (JSON with tool_name and tool_input)
INPUT=$(cat)

# Extract file path from tool input
FILE_PATH=$(echo "$INPUT" | grep -o '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"file_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')

# Only validate files in notes/
if [[ "$FILE_PATH" != *"/notes/"* ]]; then
  exit 0
fi

# Skip non-markdown files
if [[ "$FILE_PATH" != *.md ]]; then
  exit 0
fi

# Check if file exists
if [[ ! -f "$FILE_PATH" ]]; then
  exit 0
fi

# Check for description field
if ! grep -q '^description:' "$FILE_PATH" 2>/dev/null; then
  echo "WARN: $FILE_PATH is missing required 'description' field in frontmatter"
fi

# Check for empty description
DESC=$(grep '^description:' "$FILE_PATH" 2>/dev/null | sed 's/^description:[[:space:]]*//' | tr -d '"')
if [[ -z "$DESC" || "$DESC" == '""' ]]; then
  echo "WARN: $FILE_PATH has an empty description field"
fi

# Check for truncated wiki links (e.g. [[some title...]])
if grep -qE '\[\[[^\]]*\.\.\.\]\]' "$FILE_PATH" 2>/dev/null; then
  echo "BLOCK: $FILE_PATH contains truncated wiki links ([[...]]). Write the full title or use backtick code spans for shorthand references."
  exit 1
fi
