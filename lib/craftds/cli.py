"""The `craft-ds` command line."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import check as checkmod
from . import kit as kitmod
from . import manifest as mf
from . import probes as probemod
from . import render
from . import util

BASELINE = ".craft-ds-baseline.json"


def _repo(arg: str) -> Path:
    p = Path(arg or ".").resolve()
    if not p.is_dir():
        sys.exit(f"craft-ds: {p} is not a directory")
    return p


def cmd_init(a) -> int:
    repo = _repo(a.repo)
    m = mf.load(repo)
    if m["_present"] and not a.force:
        print(f"{mf.FILENAME} already exists in {repo}; edit it, or pass --force to rewrite it")
        return 1
    m["project"] = a.project or repo.name
    m["kit"]["dir"] = a.kit_dir
    if a.sources:
        m["sources"] = a.sources.split(",")
    if a.styles:
        m["styles"] = a.styles.split(",")
    if a.themes:
        m["themes"] = a.themes.split(",")
    kd = mf.kit_dir(m)
    if a.kit_dir != "." and not a.no_vendor:
        written = kitmod.copy_kit(kd)
        print(f"vendored the kit into {util.rel(repo, kd)}/ ({len(written)} files)")
    m["kit"]["hashes"] = kitmod.hashes(kd) if kd.is_dir() else {}
    m["kit"]["version"] = kitmod.Kit(kd).version if kd.is_dir() else kitmod.source_kit().version
    m["kit"]["source"] = util.home_relative(kitmod.ROOT)
    mf.save(repo, m)
    print(f"wrote {mf.FILENAME} (edit `sources`, `styles`, `themes`; then `craft-ds apply .` and `craft-ds check .`)")
    for p in mf.validate(m):
        print("  note:", p)
    return 0


def cmd_update(a) -> int:
    repo = _repo(a.repo)
    m = mf.load(repo)
    kd = mf.kit_dir(m)
    if kd.resolve() == kitmod.ROOT.resolve():
        print("this repo is the kit itself; nothing to update")
        return 0
    before = kitmod.Kit(kd).version if kd.is_dir() else "none"
    written = kitmod.copy_kit(kd)
    m["kit"]["hashes"] = kitmod.hashes(kd)
    m["kit"]["version"] = kitmod.Kit(kd).version
    m["kit"]["source"] = util.home_relative(kitmod.ROOT)
    mf.save(repo, m)
    print(f"kit {before} → {m['kit']['version']}: {len(written)} files refreshed in {util.rel(repo, kd)}/, hashes pinned")
    print("next: `craft-ds probe .` (new tokens or classes may change findings) and reshoot the themes")
    return 0


def cmd_pin(a) -> int:
    repo = _repo(a.repo)
    m = mf.load(repo)
    kd = mf.kit_dir(m)
    if not kd.is_dir():
        sys.exit(f"craft-ds: kit folder {util.rel(repo, kd)} does not exist")
    m["kit"]["hashes"] = kitmod.hashes(kd)
    m["kit"]["version"] = kitmod.Kit(kd).version
    mf.save(repo, m)
    print(f"pinned {len(m['kit']['hashes'])} kit files (v{m['kit']['version']}) in {mf.FILENAME}")
    return 0


def cmd_show(a) -> int:
    repo = _repo(a.repo)
    m = mf.load(repo)
    out = {k: v for k, v in m.items() if not k.startswith("_")}
    out["kit"] = {**out["kit"], "hashes": f"<{len(out['kit'].get('hashes') or {})} pinned>"}
    print(json.dumps(out, indent=2))
    k = kitmod.Kit(mf.kit_dir(m))
    print(f"\nkit v{k.version}: {len(k.themes)} themes, {len(k.tokens)} tokens, {len(k.classes)} classes, {len(k.icons)} icons")
    return 0


def cmd_check(a) -> int:
    repo = _repo(a.repo)
    m = mf.load(repo)
    problems = checkmod.run(m)
    if problems:
        print(f"craft-ds check: {len(problems)} problem{'s' if len(problems) != 1 else ''} in {repo}")
        for p in problems:
            print("  -", p)
        return 1
    print(f"craft-ds check: OK ({repo})")
    return 0


def cmd_probe(a) -> int:
    repo = _repo(a.repo)
    m = mf.load(repo)
    only = set(a.only.split(",")) if a.only else None
    probes = probemod.run(m, only)
    counts = {p.id: len(p.findings) for p in probes}
    if a.json:
        print(json.dumps([p.as_dict() for p in probes], indent=2))
    else:
        print(probemod.markdown(probes, str(repo)))
    bpath = repo / BASELINE
    if a.update_baseline:
        bpath.write_text(json.dumps(counts, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"baseline written to {BASELINE}", file=sys.stderr)
        return 0
    code, harness = probemod.summary(probes)
    if a.baseline or (a.strict is False and bpath.is_file() and a.use_baseline):
        bfile = Path(a.baseline) if a.baseline else bpath
        if not bfile.is_absolute():
            bfile = repo / bfile
        if not bfile.is_file():
            print(f"craft-ds probe: baseline {bfile} not found (run with --update-baseline first)", file=sys.stderr)
            return 1
        base = json.loads(util.read(bfile))
        grew = [(pid, base.get(pid, 0), n) for pid, n in counts.items() if n > base.get(pid, 0)]
        if grew:
            print("craft-ds probe: drift grew past the baseline:", file=sys.stderr)
            for pid, was, now in grew:
                print(f"  - {pid}: {was} → {now}", file=sys.stderr)
            return 1
        print(f"craft-ds probe: within baseline ({code} code, {harness} harness)", file=sys.stderr)
        return 0
    if a.strict and (code or harness):
        return 1
    return 0


def cmd_apply(a) -> int:
    repo = _repo(a.repo)
    m = mf.load(repo)
    if not m["_present"]:
        print(f"no {mf.FILENAME} in {repo}: run `craft-ds init .` first")
        return 1
    only = set(a.only.split(",")) if a.only else None
    written, skipped = render.apply(m, only, force=a.force, dry_run=a.dry_run)
    verb = "would write" if a.dry_run else "wrote"
    for w in written:
        print(f"  {verb} {w}")
    for s in skipped:
        print(f"  kept    {s} (exists; --force to overwrite)")
    hook_kept = [s for s in skipped if s.endswith(("settings.json", "hooks.json"))]
    if hook_kept:
        print()
        print(render.hooks_merge_hint(m))
    print("\nAdd this to AGENTS.md (and CLAUDE.md / GEMINI.md if they don't @import it):\n")
    print(render.agents_snippet(m))
    return 0


def cmd_snippet(a) -> int:
    repo = _repo(a.repo)
    print(render.agents_snippet(mf.load(repo)))
    return 0


def cmd_report(a) -> int:
    repo = _repo(a.repo)
    m = mf.load(repo)
    problems = checkmod.run(m)
    probes = probemod.run(m)
    code, harness = probemod.summary(probes)
    lines = [f"# craft-ds report: {m['project'] or repo.name}", "", f"- repo: `{repo}`", f"- kit: `{m['kit']['dir']}` v{kitmod.Kit(mf.kit_dir(m)).version}", f"- check: {'OK' if not problems else str(len(problems)) + ' problems'}", f"- probes: {code} code drift, {harness} harness drift", ""]
    if problems:
        lines += ["## check", ""] + [f"- {p}" for p in problems] + [""]
    lines.append(probemod.markdown(probes, str(repo)).split("\n", 1)[1])
    text = "\n".join(lines)
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
        print(f"wrote {a.out}")
    else:
        print(text)
    return 0 if not problems else 1


def cmd_shoot(a) -> int:
    repo = _repo(a.repo)
    m = mf.load(repo)
    shots = m["screenshots"]
    themes = (a.themes or ",".join(m["themes"])).split(",")
    widths = (a.widths or ",".join(str(w) for w in shots["widths"])).split(",")
    out = Path(a.out or shots["out"])
    if not out.is_absolute():
        out = repo / out
    out.mkdir(parents=True, exist_ok=True)
    if not a.targets:
        sys.exit("craft-ds shoot: name a URL or an HTML file")
    cmd_tpl = a.command or shots.get("command") or os.environ.get("CRAFT_SHOOT")
    if cmd_tpl:
        # A project-provided screenshot command: {url} {out} {width} {height} {theme} are filled in.
        n = 0
        for target in a.targets:
            base = target if target.startswith(("http://", "https://")) else Path(target).resolve().as_uri()
            ident = Path(target.split("?")[0]).stem or "page"
            for theme in themes:
                for w in widths:
                    sep = "&" if "?" in base else "?"
                    url = f"{base}{sep}theme={theme}"
                    png = out / f"{ident}-{theme}-{w}.png"
                    cmd = cmd_tpl.format(url=url, out=png, width=w, height=a.height, theme=theme)
                    print("  $", cmd)
                    rc = subprocess.call(cmd, shell=True, cwd=repo)
                    if rc:
                        print(f"  failed ({rc})")
                    else:
                        n += 1
        print(f"{n} screenshots in {util.rel(repo, out)}/ — now read every PNG")
        return 0
    node = shutil.which("node")
    if not node:
        sys.exit("craft-ds shoot: node not found (or set screenshots.command / $CRAFT_SHOOT to your own screenshot command)")
    env = dict(os.environ)
    nm = repo / "node_modules"
    env["NODE_PATH"] = os.pathsep.join([str(nm)] + ([env["NODE_PATH"]] if env.get("NODE_PATH") else []))
    args = [node, str(kitmod.ROOT / "lib" / "shoot.mjs"), "--out", str(out), "--widths", ",".join(widths), "--themes", ",".join(themes), "--height", str(a.height)]
    if a.full_page:
        args.append("--full-page")
    if a.font_sizes:
        args += ["--font-sizes", a.font_sizes]
    args += ["--", *a.targets]
    return subprocess.call(args, env=env, cwd=repo)


def cmd_self_check(a) -> int:
    script = kitmod.ROOT / "scripts" / "check.sh"
    return subprocess.call(["bash", str(script)])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="craft-ds", description="Adopt, check and enforce the Craft Design System in a project (Claude Code and Gemini).")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="write craft-ds.json and vendor the kit into a project")
    p.add_argument("repo", nargs="?", default=".")
    p.add_argument("--kit-dir", default="vendor/craft-ds", help="where to vendor the kit (default vendor/craft-ds)")
    p.add_argument("--project", default="")
    p.add_argument("--sources", default="", help="comma-separated globs of the project's UI sources")
    p.add_argument("--styles", default="", help="comma-separated globs of the project's stylesheets")
    p.add_argument("--themes", default="", help="comma-separated theme ids to verify (one per grammar at least)")
    p.add_argument("--no-vendor", action="store_true", help="write the manifest only")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_init)

    p = sub.add_parser("update", help="re-vendor the kit from this checkout and re-pin")
    p.add_argument("repo", nargs="?", default=".")
    p.set_defaults(fn=cmd_update)

    p = sub.add_parser("pin", help="record the kit file hashes in craft-ds.json")
    p.add_argument("repo", nargs="?", default=".")
    p.set_defaults(fn=cmd_pin)

    p = sub.add_parser("show", help="print the effective manifest and kit facts")
    p.add_argument("repo", nargs="?", default=".")
    p.set_defaults(fn=cmd_show)

    p = sub.add_parser("check", help="the gate: manifest, kit pins, docs, harness frontmatter, mirrors, hooks")
    p.add_argument("repo", nargs="?", default=".")
    p.set_defaults(fn=cmd_check)

    p = sub.add_parser("probe", help="drift probes (evidence; exit 1 only with --strict or a baseline)")
    p.add_argument("repo", nargs="?", default=".")
    p.add_argument("--json", action="store_true")
    p.add_argument("--only", default="", help="comma-separated probe ids")
    p.add_argument("--strict", action="store_true", help="exit 1 on any finding")
    p.add_argument("--baseline", default="", help="fail only if a probe has more findings than this file records")
    p.add_argument("--use-baseline", action="store_true", help=f"use {BASELINE} in the repo if present")
    p.add_argument("--update-baseline", action="store_true", help=f"write current counts to {BASELINE}")
    p.set_defaults(fn=cmd_probe)

    p = sub.add_parser("apply", help="render the harness (rule, skills, reviewer, hooks, docs, CI) for Claude and Gemini")
    p.add_argument("repo", nargs="?", default=".")
    p.add_argument("--only", default="", help="comma-separated: docs,rules,skills,agents,hooks,ci")
    p.add_argument("--force", action="store_true", help="overwrite existing rendered files")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=cmd_apply)

    p = sub.add_parser("snippet", help="print the AGENTS.md / CLAUDE.md section")
    p.add_argument("repo", nargs="?", default=".")
    p.set_defaults(fn=cmd_snippet)

    p = sub.add_parser("report", help="check + probes as one markdown report")
    p.add_argument("repo", nargs="?", default=".")
    p.add_argument("--out", default="")
    p.set_defaults(fn=cmd_report)

    p = sub.add_parser("shoot", help="screenshot a page per theme × width (?theme= is honoured by craft-ds.js)")
    p.add_argument("repo", nargs="?", default=".")
    p.add_argument("targets", nargs="*", help="URLs or HTML files")
    p.add_argument("--themes", default="")
    p.add_argument("--widths", default="")
    p.add_argument("--height", default="900")
    p.add_argument("--font-sizes", default="", help="also shoot these UI font sizes (tiny,small,medium,large)")
    p.add_argument("--out", default="")
    p.add_argument("--full-page", action="store_true")
    p.add_argument("--command", default="", help="shell template with {url} {out} {width} {height} {theme}")
    p.set_defaults(fn=cmd_shoot)

    p = sub.add_parser("self-check", help="run the kit's own test suite (scripts/check.sh)")
    p.set_defaults(fn=cmd_self_check)

    a = ap.parse_args(argv)
    return a.fn(a)
