#!/usr/bin/env bash
# Undo install.sh: remove the `rundown` command and the Claude Code plugin.
#
#   curl -fsSL https://raw.githubusercontent.com/Bishwas-py/understood/main/uninstall.sh | bash
#   ./uninstall.sh --all      also delete the managed clone
#
# Your rundowns are never touched. They live in .rundown/ inside each repo
# they are about, and deleting the tool has no business deleting your work.
set -euo pipefail

SRC="${RUNDOWN_HOME:-$HOME/.local/share/understood}"
BIN="${RUNDOWN_BIN:-$HOME/.local/bin}"
ALL=0
[ "${1:-}" = "--all" ] && ALL=1

say() { printf '  %s\n' "$*"; }

printf '\nunderstood: removing the rundown command and the plugin\n\n'

if command -v claude >/dev/null 2>&1; then
  if claude plugin uninstall understood@understood >/dev/null 2>&1; then
    say "plugin removed"
  else
    say "plugin was not installed"
  fi
  claude plugin marketplace remove understood >/dev/null 2>&1 && say "marketplace removed" || true
else
  say "the claude CLI is not on PATH, skipping the plugin"
fi

if [ -f "$BIN/rundown" ]; then
  rm -f "$BIN/rundown"
  say "removed $BIN/rundown"
else
  say "no command at $BIN/rundown"
fi

# Only ever delete the clone install.sh manages. A checkout you work in is
# yours, and no uninstaller should reach into it.
HERE=""
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
  HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi
if [ "$ALL" = "1" ] && [ -d "$SRC/.git" ] && [ "$SRC" != "$HERE" ]; then
  rm -rf "$SRC"
  say "removed $SRC"
elif [ -d "$SRC" ] && [ "$SRC" != "$HERE" ]; then
  say "source still at $SRC, pass --all to delete it"
fi

printf '\n'
say "your rundowns are untouched, they live in .rundown/ in each repo"
say "restart Claude Code to drop the skill from the session"
printf '\n'
