#!/bin/bash
# Reconcile Claude desktop session titles to the v2 PR/module convention.
#
# USAGE: fully quit the Claude app (Cmd+Q) FIRST, then run this — double-click it
# in Finder, or `bash rename_sessions.command` — then reopen the app.
#
# It refuses to run while the app is open, because running sessions keep their
# in-memory (old) title and the app only re-reads these files at startup.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Reconciling session titles to the PR/module convention…"
echo
# --require-closed makes the script abort (writing nothing) if the app is still
# open, so a partial/invisible apply can't happen.
python3 "$DIR/rename_sessions_by_pr.py" --require-closed "$@"
echo
echo "✅ Done. Reopen the Claude app to see the new titles."
