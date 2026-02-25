#!/usr/bin/env bash
# Arscontexta auto-commit hook
# Commits vault note changes after writes

set -euo pipefail

# Source shared vault root detection
_LIB="$(git rev-parse --show-toplevel 2>/dev/null || echo "${PROJECT_DIR:-.}")/ops/scripts/lib/vault-env.sh"
[ -f "$_LIB" ] && source "$_LIB"
VAULT_ROOT="$(find_vault_root 2>/dev/null || git rev-parse --show-toplevel 2>/dev/null || echo "${PROJECT_DIR:-.}")"
MARKER="$VAULT_ROOT/.arscontexta"

# Only run if this is an arscontexta vault
[[ -f "$MARKER" ]] || exit 0

# Check if git auto-commit is enabled
if grep -q 'git: false' "$MARKER" 2>/dev/null; then
  exit 0
fi

cd "$VAULT_ROOT"

# Only commit if there are changes
if git diff --quiet HEAD 2>/dev/null && git diff --cached --quiet HEAD 2>/dev/null; then
  # Check for untracked files in key directories
  UNTRACKED=$(git ls-files --others --exclude-standard notes/ inbox/ self/ ops/ _research/ _code/templates/ docs/ 2>/dev/null | head -1)
  if [[ -z "$UNTRACKED" ]]; then
    exit 0
  fi
fi

# Stage vault content directories
git add notes/ inbox/ archive/ self/ ops/ _research/ _code/templates/ _code/styles/ docs/ projects/ 2>/dev/null || true

# Commit if there are staged changes
if ! git diff --cached --quiet HEAD 2>/dev/null; then
  git commit -m "auto: vault update" --no-verify 2>/dev/null || true
fi
