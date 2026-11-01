"""Render the harness for one project from `templates/`: the same rule, skills and reviewer written
for Claude (`.claude/…`, `paths:` frontmatter, settings.json hooks) and for Gemini
(`.agents/…`, `trigger:` frontmatter, hooks.json). `{{name}}` placeholders only. Existing files are
never overwritten unless `force` is set."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from . import kit as kitmod
from . import manifest as mf
from . import util

ROOT = kitmod.ROOT
TEMPLATES = ROOT / "templates"
GUARD = ROOT / "lib" / "guard.mjs"


def variables(m: dict) -> dict[str, str]:
    kd = mf.kit_dir(m)
    k = kitmod.Kit(kd) if kd.is_dir() else kitmod.source_kit()
    cli = util.home_relative(ROOT / "bin" / "craft-ds")
    themes = [t for t in m["themes"]]
    labels = []
    for t in themes:
        th = k.themes.get(t)
        labels.append(f"`{t}` ({th['label']}, {kitmod.grammar_of(th)} grammar)" if th else f"`{t}`")
    shots = m["screenshots"]
    widths = ",".join(str(w) for w in shots["widths"])
    shoot_cmd = shots.get("command") or f"{cli} shoot . <url-or-file> --widths {widths}"
    kit_rel = m["kit"]["dir"].rstrip("/") or "."
    srcs = m["sources"]
    styles = m["styles"]
    grammar_rows = "\n".join(
        f"| `{tid}` | {th['label']} | {kitmod.grammar_of(th)} | pro={str(bool(th['pro'])).lower()} bevel={str(bool(th['bevel'])).lower()} round_chips={str(bool(th['round_chips'])).lower()} dark={str(bool(th['dark'])).lower()} |"
        for tid, th in k.themes.items()
    )
    return {
        "project": m["project"] or Path(m["_repo"]).name,
        "cli": cli,
        "source_checkout": util.home_relative(ROOT),
        "kit_dir": kit_rel,
        "kit_css": f"{kit_rel}/css/craft-ds.css",
        "kit_js": f"{kit_rel}/js/craft-ds.js",
        "kit_tokens": f"{kit_rel}/tokens/tokens.json",
        "kit_design": f"{kit_rel}/DESIGN.md",
        "kit_showcase": f"{kit_rel}/index.html",
        "kit_version": k.version,
        "default_theme": k.default_theme,
        "theme_list": ", ".join(labels),
        "theme_ids_csv": ",".join(themes),
        "theme_count": str(len(k.themes)),
        "grammar_rows": grammar_rows,
        "font_sizes": ", ".join(f"`{s}`" for s in m["font_sizes"]),
        "font_sizes_csv": ",".join(m["font_sizes"]),
        "widths": widths.replace(",", ", "),
        "widths_csv": widths,
        "shoot_command": shoot_cmd,
        "shots_out": shots["out"],
        "sources": ", ".join(f"`{s}`" for s in srcs),
        "styles": ", ".join(f"`{s}`" for s in styles) or "(no project stylesheet yet: add one to `styles` in the manifest when you write CSS)",
        "paths_yaml": "\n".join(f'  - "{s}"' for s in srcs + styles),
        "allow_raw": ", ".join(f"`{a}`" for a in m["allow_raw"]) or "none",
        "enforce_list": ", ".join(m["enforce"]),
        "design_doc": m["docs"]["design"],
        "decisions_doc": m["docs"]["decisions"],
        "lessons_doc": m["docs"]["lessons"],
        "deviations_heading": m["docs"]["deviations_heading"],
        "gemini_rule_trigger": m["harness"]["gemini_rule_trigger"],
        "manifest": mf.FILENAME,
    }


def render_text(template: str, vars: dict[str, str]) -> str:
    def sub(mm: re.Match) -> str:
        key = mm.group(1)
        if key not in vars:
            raise KeyError(f"template placeholder {{{{{key}}}}} has no value")
        return vars[key]

    return re.sub(r"\{\{(\w+)\}\}", sub, template)


def _frontmatter(kind: str, tool: str, vars: dict[str, str], meta: dict[str, str]) -> str:
    if kind == "rule":
        if tool == "claude":
            return f"---\npaths:\n{vars['paths_yaml']}\n---\n"
        if vars["gemini_rule_trigger"] == "always_on":
            return "---\ntrigger: always_on\n---\n"
        return f"---\ntrigger: model_decision\ndescription: \"{meta.get('description', 'Craft Design System rules')}\"\n---\n"
    if kind == "skill":
        return f"---\nname: {meta['name']}\ndescription: \"{meta['description']}\"\n---\n"
    if tool == "claude":
        return f"---\nname: {meta['name']}\ndescription: \"{meta['description']}\"\ntools: Read, Grep, Glob, Bash\nmodel: inherit\n---\n"
    return (
        f"---\nname: {meta['name']}\ndescription: \"{meta['description']}\"\n"
        "tools: [view_file, list_dir, grep_search, find_by_name, run_command, send_message]\nsubagent: true\nmainAgent: false\n---\n"
    )


def _template(rel: str, vars: dict[str, str]) -> tuple[dict[str, str], str]:
    fm, body = util.frontmatter(util.read(TEMPLATES / rel))
    meta = {k: render_text(str(v), vars) for k, v in fm.items()}
    return meta, render_text(body, vars)


def plan(m: dict, only: set[str] | None = None) -> list[tuple[str, str]]:
    """(relative path, content) for everything `apply` would write."""
    vars = variables(m)
    out: list[tuple[str, str]] = []
    tools = [t for t, on in (("claude", m["harness"]["claude"]), ("agents", m["harness"]["gemini"])) if on]
    want = lambda k: only is None or k in only  # noqa: E731

    if want("docs"):
        for name, dest in (("DESIGN.md", m["docs"]["design"]), ("DECISIONS.md", m["docs"]["decisions"]), ("LESSONS.md", m["docs"]["lessons"])):
            out.append((dest, render_text(util.read(TEMPLATES / "docs" / name), vars)))
    if want("rules"):
        meta, body = _template("rules/craft-ds.md", vars)
        for tool in tools:
            out.append((f".{tool}/rules/craft-ds.md", _frontmatter("rule", tool, vars, meta) + body))
    if want("skills"):
        for skill in sorted(p.name for p in (TEMPLATES / "skills").iterdir() if p.is_dir()):
            meta, body = _template(f"skills/{skill}/SKILL.md", vars)
            for tool in tools:
                out.append((f".{tool}/skills/{skill}/SKILL.md", _frontmatter("skill", tool, vars, meta) + body))
    if want("agents"):
        for agent in sorted(p.name for p in (TEMPLATES / "agents").glob("*.md")):
            meta, body = _template(f"agents/{agent}", vars)
            for tool in tools:
                out.append((f".{tool}/agents/{agent}", _frontmatter("agent", tool, vars, meta) + body))
    if want("hooks") and m["harness"].get("hooks"):
        guard = util.read(GUARD)
        for tool in tools:
            out.append((f".{tool}/hooks/craft-guard.mjs", guard))
        if "claude" in tools:
            out.append((".claude/settings.json", util.read(TEMPLATES / "hooks" / "claude-settings.json")))
        if "agents" in tools:
            out.append((".agents/hooks.json", util.read(TEMPLATES / "hooks" / "gemini-hooks.json")))
    if want("ci"):
        out.append((".github/workflows/craft-ds.yml", render_text(util.read(TEMPLATES / "ci" / "github.yml"), vars)))
    if want("docs"):
        # A start-here file for every tool. Written only when the project has none (apply never overwrites).
        out.append(("AGENTS.md", f"# {vars['project']}: agents start here\n\nThis file is read by every tool (Gemini reads it directly; for Claude Code, make CLAUDE.md contain `@AGENTS.md`).\n\n" + agents_snippet(m)))
    return out


def apply(m: dict, only: set[str] | None = None, force: bool = False, dry_run: bool = False) -> tuple[list[str], list[str]]:
    repo = Path(m["_repo"])
    written: list[str] = []
    skipped: list[str] = []
    for rel, content in plan(m, only):
        dest = repo / rel
        if dest.exists() and not force:
            # settings.json / hooks.json belong to the project: never clobber, even with --force, if they already mention the guard.
            skipped.append(rel)
            continue
        if dest.name in ("settings.json", "hooks.json") and dest.exists() and "craft-guard.mjs" in util.read(dest):
            skipped.append(rel)
            continue
        if not dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
            if dest.suffix == ".mjs":
                dest.chmod(0o755)
        written.append(rel)
    return written, skipped


def agents_snippet(m: dict) -> str:
    v = variables(m)
    return (
        "## Craft Design System\n"
        f"- This project's look is the Craft Design System (`{v['kit_dir']}`, v{v['kit_version']}, vendored read-only from `{v['source_checkout']}`). "
        "Use its tokens (`var(--craft-*)`), classes (`.craft-*`), icons (`data-craft-icon`) and themes (`data-craft-theme`); never hand-edit the kit (upgrade with `craft-ds update .`).\n"
        f"- Themes are tokens, grammars are flags: no colour, radius or font literals, no `[data-craft-theme=…]` patches, no `.craft-*` restyling. Deviations go under \"{v['deviations_heading']}\" in `{v['design_doc']}` and as a numbered entry in `{v['decisions_doc']}`.\n"
        f"- Read `{v['design_doc']}` and the `craft-ds` rule before touching {v['sources']}.\n"
        f"- Before saying a UI change is done: `{v['cli']} check .` and `{v['cli']} probe .` are clean (or explained), screenshots in {v['theme_list']} at {v['widths']} px wide were looked at, and the `craft-design-reviewer` agent ran.\n"
    )


def hooks_merge_hint(m: dict) -> str:
    claude = json.loads(util.read(TEMPLATES / "hooks" / "claude-settings.json"))
    gemini = json.loads(util.read(TEMPLATES / "hooks" / "gemini-hooks.json"))
    return (
        "The project already has hook files; merge these entries by hand:\n"
        "  .claude/settings.json → hooks.PreToolUse += " + json.dumps(claude["hooks"]["PreToolUse"][0]) + "\n"
        "  .agents/hooks.json   → " + json.dumps({"craft-ds-guard": gemini["craft-ds-guard"]}) + "\n"
    )


def copy_guard(dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(GUARD, dest)
