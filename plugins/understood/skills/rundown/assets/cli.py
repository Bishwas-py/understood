#!/usr/bin/env python3
"""rundown: build, serve, and keep the rundowns that live in this repo.

    rundown list                     every rundown here, with its question count
    rundown serve                    all of them on one origin, index at /
    rundown serve ask-loop --open    the same server, opened at that one
    rundown build ask-loop --fix     validate, resync drifted refs, render
    rundown save  ask-loop spec.json snapshot the old spec, write the new, build
    rundown verify ask-loop          validate only, nothing written
    rundown path  ask-loop           print its folder
    rundown rm    ask-loop --force   delete it and its conversation
    rundown install                  install or update the Claude Code plugin
    rundown upgrade                  pull the latest source, update the plugin
    rundown uninstall                remove the command and the plugin
    rundown doctor                   versions, store location, what is missing

Runs the same either way: as loose scripts inside the plugin, or as the
installed `rundown` command. The modules sit next to this file, so put that
directory on the path before importing them.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import serve as serve_mod  # noqa: E402
import store  # noqa: E402
import validate as validate_mod  # noqa: E402
from spec import load  # noqa: E402

REPO = "Bishwas-py/understood"
PLUGIN = "understood@understood"


# assets -> rundown -> skills -> understood -> plugins -> the checkout
SOURCE = HERE.parents[4]
MANIFEST = HERE.parents[2] / ".claude-plugin" / "plugin.json"


def version() -> str:
    if MANIFEST.is_file():
        try:
            return json.loads(MANIFEST.read_text(encoding="utf-8")).get("version", "unknown")
        except ValueError:
            pass
    return "unknown"


def marketplace_source() -> str:
    """Prefer the checkout this file lives in, so both halves read one copy."""
    return str(SOURCE) if (SOURCE / ".git").is_dir() else REPO


def cmd_list(args) -> int:
    homes = list(store.each())
    if not homes:
        print(f"no rundowns in {store.store_dir()}")
        return 0
    for home in homes:
        spec = load(home.spec)
        built = "built" if home.page.is_file() else "not built"
        print(
            f"{home.slug:<28} {spec.get('title', '')[:40]:<42} "
            f"{store.count_lines(home.questions)} asked, "
            f"{store.count_lines(home.answers)} answered, {built}"
        )
    return 0


def cmd_build(args) -> int:
    return store.build(store.Home(args.slug), fix=args.fix)


def cmd_save(args) -> int:
    home = store.Home(args.slug)
    shot = store.save_spec(home, load(Path(args.file)))
    print(f"saved {home.spec}" + (f", previous kept at {shot.name}" if shot else ""))
    return store.build(home, fix=args.fix)


def cmd_verify(args) -> int:
    home = store.Home(args.slug)
    if not home.exists():
        print(f"no rundown named {args.slug}", file=sys.stderr)
        return 1
    rep = validate_mod.validate(load(home.spec))
    print(f"validating {args.slug}")
    rep.print()
    return 1 if rep.errors else 0


def cmd_path(args) -> int:
    print(store.Home(args.slug).dir if args.slug else store.store_dir())
    return 0


def cmd_rm(args) -> int:
    home = store.Home(args.slug)
    if not home.dir.is_dir():
        print(f"no rundown named {args.slug}", file=sys.stderr)
        return 1
    shots = len(list(home.history.glob("*.json"))) if home.history.is_dir() else 0
    print(
        f"{home.dir}: {store.count_lines(home.questions)} questions, "
        f"{store.count_lines(home.answers)} answers, {shots} snapshots"
    )
    if not args.force:
        print("nothing removed, pass --force to delete it")
        return 1
    shutil.rmtree(home.dir)
    print(f"removed {home.dir}")
    return 0


def cmd_serve(args) -> int:
    return serve_mod.run(args.slug, args.port, args.open)


def claude_cli() -> str | None:
    return shutil.which("claude")


def run_claude(claude: str, *argv: str) -> tuple[int, str]:
    out = subprocess.run([claude, *argv], capture_output=True, text=True)
    return out.returncode, (out.stdout + out.stderr).strip()


def cmd_install(args) -> int:
    """Install or update the Claude Code plugin, through Claude's own commands.

    Never writes into ~/.claude directly: Claude Code owns its configuration,
    and a tool that edits another tool's config behind its back is a tool
    nobody can trust.
    """
    claude = claude_cli()
    if not claude:
        print("the `claude` CLI is not on PATH. Run these two lines yourself:\n")
        print(f"    claude plugin marketplace add {REPO}")
        print(f"    claude plugin install {PLUGIN}")
        return 1

    source = marketplace_source()
    code, out = run_claude(claude, "plugin", "marketplace", "add", source)
    if code == 0:
        print(f"marketplace added: {source}")
    else:
        code, out = run_claude(claude, "plugin", "marketplace", "update", "understood")
        print("marketplace updated" if code == 0 else f"marketplace: {out.splitlines()[-1] if out else 'failed'}")

    code, out = run_claude(claude, "plugin", "install", PLUGIN)
    if code == 0:
        print(f"plugin installed: {PLUGIN}")
    else:
        code, out = run_claude(claude, "plugin", "update", PLUGIN)
        if code == 0:
            print(f"plugin updated: {PLUGIN}")
        else:
            print(f"plugin: {out.splitlines()[-1] if out else 'failed'}", file=sys.stderr)
            return 1

    print(f"\nrundown {version()} is installed. Restart Claude Code, skills do not hot-reload.")
    return 0


def cmd_upgrade(args) -> int:
    """One clone, both halves, so pulling it updates the command and the plugin."""
    if not (SOURCE / ".git").is_dir():
        print(f"{SOURCE} is not a git checkout, nothing to pull", file=sys.stderr)
        return 1
    out = subprocess.run(["git", "-C", str(SOURCE), "pull", "--ff-only"], capture_output=True, text=True)
    print((out.stdout + out.stderr).strip())
    if out.returncode != 0:
        return 1
    return cmd_install(args)


def cmd_uninstall(args) -> int:
    claude = claude_cli()
    shim = Path(os.environ.get("RUNDOWN_BIN", Path.home() / ".local" / "bin")) / "rundown"
    if claude:
        code, out = run_claude(claude, "plugin", "uninstall", PLUGIN)
        print("plugin removed" if code == 0 else f"plugin: {out.splitlines()[-1] if out else 'not installed'}")
    if shim.is_file():
        shim.unlink()
        print(f"removed {shim}")
    print(f"the source is still at {SOURCE}")
    if not args.force:
        print("pass --force to delete it too")
        return 0
    if (SOURCE / ".git").is_dir():
        shutil.rmtree(SOURCE)
        print(f"removed {SOURCE}")
    return 0


def cmd_doctor(args) -> int:
    claude = claude_cli()
    root = store.store_dir()
    print(f"rundown      {version()}")
    print(f"source       {SOURCE}")
    print(f"python       {sys.version.split()[0]} ({sys.executable})")
    print(f"store        {root}" + ("" if root.is_dir() else "  (not created yet)"))
    print(f"rundowns     {len(list(store.each()))}")
    print(f"claude cli   {claude or 'not on PATH'}")
    if claude:
        code, out = run_claude(claude, "plugin", "list")
        line = next((l for l in out.splitlines() if "understood" in l), None)
        print(f"plugin       {line.strip() if line else 'not installed, run: rundown install'}")
    editor = shutil.which("cursor") or shutil.which("code")
    print(f"editor       {editor or 'no cursor or code on PATH, links still work if the app is installed'}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="rundown", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--version", action="version", version=f"rundown {version()}")
    subs = ap.add_subparsers(dest="cmd", required=True)

    subs.add_parser("list", help="every rundown in this repo").set_defaults(fn=cmd_list)

    p = subs.add_parser("serve", help="serve them all on one origin")
    p.add_argument("slug", nargs="?", help="open at this one; omit for the index")
    p.add_argument("--port", type=int, default=None)
    p.add_argument("--open", action="store_true")
    p.set_defaults(fn=cmd_serve)

    p = subs.add_parser("build", help="validate and render into the folder")
    p.add_argument("slug")
    p.add_argument("--fix", action="store_true", help="code moved: put every ref back on the line its pattern finds")
    p.set_defaults(fn=cmd_build)

    p = subs.add_parser("save", help="snapshot the old spec, write a new one, build")
    p.add_argument("slug")
    p.add_argument("file")
    p.add_argument("--fix", action="store_true")
    p.set_defaults(fn=cmd_save)

    p = subs.add_parser("verify", help="validate only, write nothing")
    p.add_argument("slug")
    p.set_defaults(fn=cmd_verify)

    p = subs.add_parser("path", help="print a rundown's folder, or the store")
    p.add_argument("slug", nargs="?")
    p.set_defaults(fn=cmd_path)

    p = subs.add_parser("rm", help="delete a rundown and its conversation")
    p.add_argument("slug")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_rm)

    subs.add_parser("install", help="install or update the Claude Code plugin").set_defaults(fn=cmd_install)
    subs.add_parser("upgrade", help="pull the latest source, update the plugin").set_defaults(fn=cmd_upgrade)

    p = subs.add_parser("uninstall", help="remove the command and the plugin")
    p.add_argument("--force", action="store_true", help="delete the source checkout too")
    p.set_defaults(fn=cmd_uninstall)
    subs.add_parser("doctor", help="versions, store location, what is missing").set_defaults(fn=cmd_doctor)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
