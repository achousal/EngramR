#!/usr/bin/env bash
# Arscontexta session capture hook
# Saves session metadata to ops/sessions/ on session end

set -euo pipefail

# Source shared vault root detection
_LIB="$(git rev-parse --show-toplevel 2>/dev/null || echo "${PROJECT_DIR:-.}")/ops/scripts/lib/vault-env.sh"
[ -f "$_LIB" ] && source "$_LIB"
VAULT_ROOT="$(find_vault_root 2>/dev/null || git rev-parse --show-toplevel 2>/dev/null || echo "${PROJECT_DIR:-.}")"
MARKER="$VAULT_ROOT/.arscontexta"

# Only run if this is an arscontexta vault
[[ -f "$MARKER" ]] || exit 0

# Check if session capture is enabled
if grep -q 'session_capture: false' "$MARKER" 2>/dev/null; then
  exit 0
fi

SESSIONS_DIR="$VAULT_ROOT/ops/sessions"
mkdir -p "$SESSIONS_DIR"

SESSION_ID="${CLAUDE_CONVERSATION_ID:-$(date +%Y%m%d-%H%M%S)}"
SESSION_FILE="$SESSIONS_DIR/$SESSION_ID.json"

# Only create if it does not already exist
if [[ ! -f "$SESSION_FILE" ]]; then
  cat > "$SESSION_FILE" << EOF
{
  "id": "$SESSION_ID",
  "ended": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "status": "completed"
}
EOF
fi
