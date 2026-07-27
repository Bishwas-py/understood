#!/usr/bin/env bash
# One command for both halves: the `rundown` command on your PATH, and the
# Claude Code plugin. Re-run it any time to upgrade both.
#
#   curl -fsSL https://raw.githubusercontent.com/Bishwas-py/understood/main/install.sh | bash
#
# There is one copy on disk and both halves read it, so the CLI and the plugin
# can never drift out of version with each other. No package manager involved:
# the code is pure python with no dependencies, so a clone and a shim is all it
# takes. Override where things land with RUNDOWN_HOME and RUNDOWN_BIN.
set -euo pipefail

REPO="https://github.com/Bishwas-py/understood"
SRC="${RUNDOWN_HOME:-$HOME/.local/share/understood}"
BIN="${RUNDOWN_BIN:-$HOME/.local/bin}"
CLI="plugins/understood/skills/rundown/assets/cli.py"

say() { printf '  %s\n' "$*"; }
die() { printf '\n  %s\n\n' "$*" >&2; exit 1; }

printf '\nunderstood: the rundown command and the Claude Code plugin\n\n'

command -v python3 >/dev/null 2>&1 || die "python3 not found. Install it, then run this again."
command -v git     >/dev/null 2>&1 || die "git not found. Install it, then run this again."

# Running from a checkout already? Use it, so a dev clone stays the source.
HERE=""
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
  HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi
if [ -n "$HERE" ] && [ -f "$HERE/$CLI" ] && [ -d "$HERE/.git" ]; then
  SRC="$HERE"
  say "using this checkout: $SRC"
elif [ -d "$SRC/.git" ]; then
  say "updating $SRC"
  git -C "$SRC" pull --ff-only --quiet
else
  say "cloning into $SRC"
  mkdir -p "$(dirname "$SRC")"
  git clone --depth 1 --quiet "$REPO" "$SRC"
fi

[ -f "$SRC/$CLI" ] || die "that checkout has no $CLI in it"

mkdir -p "$BIN"
cat > "$BIN/rundown" <<EOF
#!/bin/sh
exec python3 "$SRC/$CLI" "\$@"
EOF
chmod +x "$BIN/rundown"
say "installed $BIN/rundown"

if command -v claude >/dev/null 2>&1; then
  # installs or updates the plugin, and settles its hooks: the Stop hook ships
  # with the plugin, so anything hand-written that competes with it is removed
  "$BIN/rundown" install
else
  say "the claude CLI is not on PATH, skipping the plugin and its hooks"
  say "run 'rundown install' once it is"
fi

printf '\n'
case ":$PATH:" in
  *":$BIN:"*) ;;
  *) say "add this to your shell profile, then open a new shell:"
     say "  export PATH=\"$BIN:\$PATH\"" ;;
esac
say "try it: cd into a repo, then  rundown list"
printf '\n'
