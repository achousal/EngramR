#!/usr/bin/env bash
# pipeline-bridge.sh -- PostToolUse hook for Write
# Detects new files in _research/literature/ or _research/hypotheses/ and suggests /reduce.
# Non-blocking, informational only. Never modifies files.

set -euo pipefail

# Source shared vault root detection
_LIB="$(cd "$(dirname "$0")/../.." && pwd)/ops/scripts/lib/vault-env.sh"
[ -f "$_LIB" ] && source "$_LIB"
VAULT_ROOT="$(find_vault_root 2>/dev/null || (cd "$(dirname "$0")/../.." && pwd))"
QUEUE_FILE="${VAULT_ROOT}/ops/queue/queue.json"

# Read tool input from stdin (JSON with file_path)
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))" 2>/dev/null || echo "")

# Exit silently if no file path detected
if [[ -z "$FILE_PATH" ]]; then
  exit 0
fi

# Normalize to vault-relative path
REL_PATH="${FILE_PATH#${VAULT_ROOT}/}"

# Only trigger for _research/literature/ or _research/hypotheses/ (exclude _index.md and _templates)
case "$REL_PATH" in
  _research/literature/_index.md|_research/hypotheses/_index.md|_code/templates/*)
    exit 0
    ;;
  _research/literature/*.md)
    NOTE_TYPE="literature note"
    ;;
  _research/hypotheses/*.md)
    NOTE_TYPE="hypothesis"
    ;;
  *)
    exit 0
    ;;
esac

BASENAME=$(basename "$REL_PATH")

# Check if a reduce task already exists in queue for this file
if [[ -f "$QUEUE_FILE" ]]; then
  ALREADY_QUEUED=$(python3 -c "
import json, sys
try:
    with open('${QUEUE_FILE}') as f:
        q = json.load(f)
    tasks = q.get('tasks', [])
    for t in tasks:
        src = t.get('source', '')
        if '${REL_PATH}' in src and t.get('status') != 'done':
            print('yes')
            sys.exit(0)
    print('no')
except Exception:
    print('no')
" 2>/dev/null || echo "no")

  if [[ "$ALREADY_QUEUED" == "yes" ]]; then
    exit 0
  fi
fi

echo "[Pipeline Bridge] New ${NOTE_TYPE}: ${BASENAME}. Consider: /reduce ${REL_PATH}"
