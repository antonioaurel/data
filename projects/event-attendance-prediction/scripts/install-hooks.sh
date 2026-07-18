#!/usr/bin/env bash
# Install the versioned git hooks into .git/hooks (which git does not track).
# Run once after cloning:  bash projects/event-attendance-prediction/scripts/install-hooks.sh
set -euo pipefail

root="$(git rev-parse --show-toplevel)"
src="$root/projects/event-attendance-prediction/scripts/hooks/pre-commit"
dst="$root/.git/hooks/pre-commit"

chmod +x "$src"
if ln -sf "$src" "$dst" 2>/dev/null; then
  echo "linked  $dst -> $src"
else
  cp "$src" "$dst" && chmod +x "$dst"
  echo "copied  $src -> $dst"
fi
