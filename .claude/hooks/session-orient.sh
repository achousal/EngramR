#!/usr/bin/env bash
# Arscontexta session orientation hook
# Surfaces vault state at session start: goals, maintenance conditions, reminders

set -euo pipefail

# Source shared vault root detection
_LIB="$(git rev-parse --show-toplevel 2>/dev/null || echo "${PROJECT_DIR:-.}")/ops/scripts/lib/vault-env.sh"
[ -f "$_LIB" ] && source "$_LIB"
VAULT_ROOT="$(find_vault_root 2>/dev/null || git rev-parse --show-toplevel 2>/dev/null || echo "${PROJECT_DIR:-.}")"
MARKER="$VAULT_ROOT/.arscontexta"

# Only run if this is an arscontexta vault
[[ -f "$MARKER" ]] || exit 0

echo "## Vault Orientation"
echo ""

# Show goals
if [[ -f "$VAULT_ROOT/self/goals.md" ]]; then
  echo "### Active Threads"
  grep -E '^\s*-' "$VAULT_ROOT/self/goals.md" 2>/dev/null | head -10 || true
  echo ""
fi

# Show reminders
if [[ -f "$VAULT_ROOT/ops/reminders.md" ]]; then
  OVERDUE=$(grep -E '^\s*- \[ \]' "$VAULT_ROOT/ops/reminders.md" 2>/dev/null | head -5 || true)
  if [[ -n "$OVERDUE" ]]; then
    echo "### Reminders"
    echo "$OVERDUE"
    echo ""
  fi
fi

# Count notes
CLAIM_COUNT=$(find "$VAULT_ROOT/notes" -name '*.md' -not -name '.*' 2>/dev/null | wc -l | tr -d ' ')
INBOX_COUNT=$(find "$VAULT_ROOT/inbox" -name '*.md' -not -name '.*' 2>/dev/null | wc -l | tr -d ' ')
OBS_COUNT=$(find "$VAULT_ROOT/ops/observations" -name '*.md' -not -name '.*' 2>/dev/null | wc -l | tr -d ' ')
TENSION_COUNT=$(find "$VAULT_ROOT/ops/tensions" -name '*.md' -not -name '.*' -not -name '.gitkeep' 2>/dev/null | wc -l | tr -d ' ')

echo "### Vault State"
echo "  Claims: $CLAIM_COUNT | Inbox: $INBOX_COUNT | Observations: $OBS_COUNT | Tensions: $TENSION_COUNT"

# Maintenance signals
if [[ "$INBOX_COUNT" -gt 0 ]]; then
  echo "  -> Inbox has unprocessed items"
fi
if [[ "$OBS_COUNT" -ge 10 ]]; then
  echo "  -> 10+ observations pending -- consider running /rethink"
fi
if [[ "$TENSION_COUNT" -ge 5 ]]; then
  echo "  -> 5+ tensions pending -- consider running /rethink"
fi

echo ""
