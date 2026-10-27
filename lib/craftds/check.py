"""`craft-ds check`: the gate. The manifest is valid, the kit is complete and pinned, every path the
harness names exists, every skill/agent/rule has the frontmatter its tool needs, the Claude and
Gemini trees carry the same words, and the hooks are wired. Exit 1 on any problem."""

from __future__ import annotations

import json
import re
from pathlib import Path

from . import kit as kitmod
from . import manifest as mf
from . import util

COMMANDS = ("init", "update", "pin", "check", "probe", "apply", "shoot", "report", "snippet", "show", "self-check")
PLACEHOLDER = re.compile(r"[<>*{}…$|]|\.\.\.|\s")


def _harness_md(repo: Path, m: dict) -> list[Path]:
    files = util.walk(repo)
    return [f for f in util.select(files, repo, m["docs"]["scan"]) if f.suffix == ".md"]


def _top_level(repo: Path) -> set[str]:
    return {p.name for p in repo.iterdir() if not p.name.startswith(".") or p.name in (".claude", ".agents", ".github")}


def run(m: dict) -> list[str]:
    repo = Path(m["_repo"])
    problems: list[str] = []
    fail = lambda where, msg: problems.append(f"{where}: {msg}")  # noqa: E731

    # 1. the manifest
    if not m["_present"]:
        fail(mf.FILENAME, "missing: run `craft-ds init .`")
    problems.extend(mf.validate(m))

    # 2. the kit
    kd = mf.kit_dir(m)
    kit_rel = util.rel(repo, kd)
    if not kd.is_dir():
        fail(kit_rel, "kit folder missing: run `craft-ds init .` or `craft-ds update .`")
    else:
        for g in kitmod.missing(kd):
            fail(f"{kit_rel}/{g}", "kit file missing: run `craft-ds update .`")
        pinned = m["kit"].get("hashes") or {}
        if kit_rel == ".":
            pass  # the repo is the kit: nothing to compare a pin against
        elif not pinned:
            fail(mf.FILENAME, "kit.hashes is empty: run `craft-ds pin .`")
        else:
            now = kitmod.hashes(kd)
            for f, h in sorted(pinned.items()):
                if now.get(f) != h:
                    fail(f"{kit_rel}/{f}", "differs from its pinned hash (hand-edited kit? `craft-ds update .`, or `craft-ds pin .` if deliberate)")
            for f in sorted(set(now) - set(pinned)):
                fail(f"{kit_rel}/{f}", "not pinned: run `craft-ds pin .`")
        k = kitmod.Kit(kd)
        if m["kit"].get("version") and k.version != m["kit"]["version"]:
            fail(mf.FILENAME, f"kit.version is {m['kit']['version']} but the vendored kit says {k.version} (run `craft-ds pin .`)")

    # 3. docs point at real things
    top = _top_level(repo)
    known_files = {"AGENTS.md", "CLAUDE.md", "GEMINI.md", "CONVENTIONS.md", "README.md", "DESIGN.md", "MAPPING.md", mf.FILENAME, "package.json"}
    for md in _harness_md(repo, m):
        text = util.read(md)
        r = util.rel(repo, md)
        for lm in re.finditer(r"\[[^\]]*\]\(([^)\s]+)\)", text):
            target = lm.group(1).split("#")[0]
            if not target or target.startswith(("http://", "https://", "mailto:", "file://")):
                continue
            if not (md.parent / target).exists() and not (repo / target).exists():
                fail(r, f"link to `{target}` points at nothing")
        for im in re.finditer(r"(?m)^@([\w./-]+\.md)\s*$", text):
            if not (md.parent / im.group(1)).exists() and not (repo / im.group(1)).exists():
                fail(r, f"@import `{im.group(1)}` points at nothing")
        for cm in re.finditer(r"`([^`\n]+)`", text):
            s = cm.group(1).strip()
            if PLACEHOLDER.search(s) or len(s) > 120:
                continue
            head = s.split("/")[0]
            looks_like_path = ("/" in s and head in top) or s in known_files or (head in top and s.endswith((".md", ".json", ".css", ".js", ".mjs", ".py", ".sh", ".yml")))
            if looks_like_path and not (repo / s).exists() and not (md.parent / s).exists():
                fail(r, f"`{s}` names a path that does not exist")
        # `craft-ds <cmd>` inside code (backtick spans and fenced blocks), not prose like "craft-ds has".
        code_text = " | ".join(re.findall(r"`([^`\n]+)`", text) + re.findall(r"(?ms)^```.*?^```", text))
        for cmd in re.finditer(r"(?<![\w.-])craft-ds[ \t]+([a-z][a-z-]*)\b", code_text):
            if cmd.group(1) not in COMMANDS:
                fail(r, f"`craft-ds {cmd.group(1)}` is not a CLI command (known: {', '.join(COMMANDS)})")

    # 4. the harness per tool
    tools = [("claude", ".claude"), ("gemini", ".agents")]
    for tool, dot in tools:
        if not m["harness"][tool]:
            continue
        rule = repo / dot / "rules/craft-ds.md"
        if not rule.is_file():
            fail(f"{dot}/rules/craft-ds.md", "missing: run `craft-ds apply .`")
        else:
            fm, _ = util.frontmatter(util.read(rule))
            if tool == "claude":
                paths = fm.get("paths")
                if not isinstance(paths, list) or not paths:
                    fail(f"{dot}/rules/craft-ds.md", "needs a `paths:` list so Claude loads it when UI files are edited")
                else:
                    files = [util.rel(repo, f) for f in util.walk(repo)]
                    for g in paths:
                        if not any(util.glob_to_regex(g).match(f) for f in files):
                            fail(f"{dot}/rules/craft-ds.md", f"`paths:` glob `{g}` matches no file")
            else:
                trig = fm.get("trigger")
                if trig not in ("always_on", "model_decision", "glob", "manual"):
                    fail(f"{dot}/rules/craft-ds.md", "needs `trigger:` (always_on or model_decision) so Jetski/Gemini loads it")
                if trig == "model_decision" and not fm.get("description"):
                    fail(f"{dot}/rules/craft-ds.md", "trigger: model_decision needs a `description:`")
        skills = repo / dot / "skills"
        if skills.is_dir():
            for d in sorted(p for p in skills.iterdir() if p.is_dir()):
                sk = d / "SKILL.md"
                if not sk.is_file():
                    fail(util.rel(repo, d), "skill folder without SKILL.md")
                    continue
                fm, _ = util.frontmatter(util.read(sk))
                if fm.get("name") != d.name:
                    fail(util.rel(repo, sk), f"frontmatter name `{fm.get('name')}` must equal the folder name `{d.name}`")
                if not fm.get("description"):
                    fail(util.rel(repo, sk), "frontmatter needs a description")
        agents = repo / dot / "agents"
        if agents.is_dir():
            for a in sorted(agents.glob("*.md")):
                fm, _ = util.frontmatter(util.read(a))
                if fm.get("name") != a.stem:
                    fail(util.rel(repo, a), f"frontmatter name `{fm.get('name')}` must equal the file name `{a.stem}`")
                if not fm.get("description"):
                    fail(util.rel(repo, a), "frontmatter needs a description")

    # 5. mirrors: the same words for both tools
    if m["harness"]["claude"] and m["harness"]["gemini"]:
        for sub in ("rules", "skills", "agents"):
            c_dir, g_dir = repo / ".claude" / sub, repo / ".agents" / sub
            c_files = {util.rel(c_dir, f): f for f in c_dir.rglob("*.md")} if c_dir.is_dir() else {}
            g_files = {util.rel(g_dir, f): f for f in g_dir.rglob("*.md")} if g_dir.is_dir() else {}
            for name in sorted(set(c_files) | set(g_files)):
                if name not in c_files:
                    fail(f".agents/{sub}/{name}", "has no .claude counterpart (run `craft-ds apply . --force` or mirror it by hand)")
                elif name not in g_files:
                    fail(f".claude/{sub}/{name}", "has no .agents counterpart (run `craft-ds apply . --force` or mirror it by hand)")
                else:
                    _, cb = util.frontmatter(util.read(c_files[name]))
                    _, gb = util.frontmatter(util.read(g_files[name]))
                    if cb.strip() != gb.strip():
                        fail(f".claude/{sub}/{name}", f"body differs from .agents/{sub}/{name}: both tools must read the same rule")

    # 6. hooks
    if m["harness"].get("hooks"):
        if m["harness"]["claude"]:
            s = repo / ".claude/settings.json"
            if not s.is_file():
                fail(".claude/settings.json", "missing: `craft-ds apply .` writes one with the guard hook")
            else:
                try:
                    text = util.read(s)
                    json.loads(text)
                    if "craft-guard.mjs" not in text:
                        fail(".claude/settings.json", "does not run .claude/hooks/craft-guard.mjs on PreToolUse")
                except json.JSONDecodeError as e:
                    fail(".claude/settings.json", f"invalid JSON: {e}")
            if not (repo / ".claude/hooks/craft-guard.mjs").is_file():
                fail(".claude/hooks/craft-guard.mjs", "missing")
        if m["harness"]["gemini"]:
            h = repo / ".agents/hooks.json"
            if not h.is_file():
                fail(".agents/hooks.json", "missing: `craft-ds apply .` writes one with the guard hook")
            else:
                try:
                    text = util.read(h)
                    json.loads(text)
                    if "craft-guard.mjs" not in text:
                        fail(".agents/hooks.json", "does not run .agents/hooks/craft-guard.mjs on PreToolUse")
                except json.JSONDecodeError as e:
                    fail(".agents/hooks.json", f"invalid JSON: {e}")
            if not (repo / ".agents/hooks/craft-guard.mjs").is_file():
                fail(".agents/hooks/craft-guard.mjs", "missing")

    # 7. the baseline, if any
    b = repo / ".craft-ds-baseline.json"
    if b.is_file():
        try:
            json.loads(util.read(b))
        except json.JSONDecodeError as e:
            fail(".craft-ds-baseline.json", f"invalid JSON: {e}")

    return problems
