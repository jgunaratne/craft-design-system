"""Drift probes: mechanical, read-only checks that turn the Craft DS rules into facts about a repo.

Each probe names the rule it checks (CONVENTIONS.md / the `craft-ds` rule) and reports findings as
`path:line — what`, marked as *code* drift (fix the code) or *harness* drift (fix the docs, the
manifest or the kit). Probes are evidence, not a gate: `craft-ds probe` exits 0 unless `--strict`
or a baseline says otherwise. `craft-ds check` is the gate.

A deliberate one-off exception carries `craft-allow` on the line (a comment, or a
`data-craft-allow` attribute in markup); whole files or folders go in `allow_raw`.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from . import kit as kitmod
from . import manifest as mf
from . import util

ALLOW = "craft-allow"
COMMENT = re.compile(r"^\s*(//|\*|/\*|<!--|#\s)")
HEX = re.compile(r"(?<![\w&])#[0-9a-fA-F]{3,8}\b(?![\w-])")
FUNC = re.compile(r"\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch)\(")
NEUTRAL = re.compile(r"\brgba?\(\s*(?:0|255)\s*[, ]\s*(?:0|255)\s*[, ]\s*(?:0|255)\s*(?:[,/]\s*[\d.]+%?)?\s*\)")
VAR_CALL = re.compile(r"var\((--[A-Za-z0-9_-]+)(?:\s*,[^)]*)?\)")


class Probe:
    def __init__(self, id: str, rule: str, kind: str):
        self.id = id
        self.rule = rule
        self.kind = kind  # "code" | "harness"
        self.findings: list[str] = []
        self.skipped: str | None = None

    def add(self, *items: str) -> None:
        self.findings.extend(items)

    def as_dict(self) -> dict:
        return {"id": self.id, "rule": self.rule, "kind": self.kind, "findings": self.findings, "skipped": self.skipped}


class Repo:
    """Everything the probes read, computed once."""

    def __init__(self, m: dict):
        self.m = m
        self.root = Path(m["_repo"])
        self.kit_dir = mf.kit_dir(m)
        self.kit = kitmod.Kit(self.kit_dir)
        self.kit_rel = util.rel(self.root, self.kit_dir)
        files = util.walk(self.root)
        in_kit = lambda p: self.kit_rel != "." and util.rel(self.root, p).startswith(self.kit_rel + "/")  # noqa: E731
        kit_paths = {util.rel(self.root, p) for p in kitmod.kit_files(self.kit_dir)}
        self_mode = self.kit_rel == "."
        own = [f for f in files if not in_kit(f) and (self_mode or util.rel(self.root, f) not in kit_paths)]
        excl = list(m["exclude"]) + [".claude/**", ".agents/**", ".github/**"]
        self.sources = util.select(own, self.root, m["sources"], excl)
        self.styles = util.select(own, self.root, m["styles"], excl)
        self.scanned = sorted(set(self.sources) | set(self.styles), key=lambda p: util.rel(self.root, p))
        self.text = {f: util.read(f) for f in self.scanned}
        self.allow_raw = list(m["allow_raw"])

    def rel(self, p: Path) -> str:
        return util.rel(self.root, p)

    def is_allowed_raw(self, p: Path) -> bool:
        return util.matches(self.rel(p), self.allow_raw)

    def lines(self, p: Path):
        for i, line in enumerate(self.text[p].splitlines(), 1):
            yield i, line

    def finding(self, p: Path, n: int, line: str, what: str = "") -> str:
        text = line.strip()[:110]
        return f"{self.rel(p)}:{n} — {what + ': ' if what else ''}{text}"


def _strip_safe(line: str) -> str:
    """Remove the parts of a line that may legitimately hold a colour literal: token fallbacks,
    neutral alphas, urls, and documentation of a value (`<code>#378ef0</code>`, `` `#378ef0` ``)."""
    s = VAR_CALL.sub("var", line)
    s = NEUTRAL.sub("neutral", s)
    s = re.sub(r"url\([^)]*\)", "url()", s)
    s = re.sub(r"<code[^>]*>.*?</code>", "<code/>", s)
    s = re.sub(r"`[^`]*`", "``", s)
    return s


# ── the probes ──────────────────────────────────────────────────────────────────


def p_kit_intact(r: Repo) -> Probe:
    p = Probe("kit-intact", "The vendored kit is read-only and hash-pinned; upgrade with `craft-ds update`, never hand-edit (CONVENTIONS 1)", "harness")
    gone = kitmod.missing(r.kit_dir)
    for g in gone:
        p.add(f"{r.kit_rel}/{g} — missing from the kit (run `craft-ds update .`)")
    if r.kit_rel == ".":
        p.skipped = "this repo is the kit itself (kit.dir is '.'): its files are the source, not a vendored copy"
        return p
    pinned = r.m["kit"].get("hashes") or {}
    if not pinned:
        p.add(f"{mf.FILENAME} — kit.hashes is empty: run `craft-ds pin .` so edits to the kit are caught")
        return p
    now = kitmod.hashes(r.kit_dir)
    for f, h in sorted(pinned.items()):
        if f not in now:
            p.add(f"{r.kit_rel}/{f} — pinned but missing")
        elif now[f] != h:
            p.add(f"{r.kit_rel}/{f} — changed since it was pinned (hand-edited? run `craft-ds update .` or `craft-ds pin .` if the change is deliberate)")
    for f in sorted(set(now) - set(pinned)):
        p.add(f"{r.kit_rel}/{f} — in the kit folder but not pinned")
    return p


def p_kit_consistency(r: Repo) -> Probe:
    p = Probe("kit-consistency", "tokens.json, tokens-data.js, craft-ds.css and icons.js describe the same system (CONVENTIONS 1)", "harness")
    k = r.kit
    if not k.css or not k.themes:
        p.skipped = "kit css or tokens.json missing"
        return p
    skip = {"id", "kind", "label", "family", "description", *kitmod.GRAMMAR_FLAGS}
    css_rel = f"{r.kit_rel}/css/craft-ds.css"
    for tid, t in k.themes.items():
        body = k.theme_css_block(tid)
        if body is None:
            p.add(f"{css_rel} — no `[data-craft-theme=\"{tid}\"]` block for theme `{tid}` in tokens.json")
            continue
        defined = set(util.custom_props(body))
        for key in sorted(t):
            if key in skip:
                continue
            name = "--craft-" + key.replace("_", "-")
            if name not in defined:
                p.add(f"{css_rel} — theme `{tid}` block lacks `{name}` (tokens.json key `{key}`)")
    data_js = r.kit_dir / "js/tokens-data.js"
    if data_js.is_file():
        m = re.search(r"window\.CRAFT_DS_SPEC\s*=\s*(\{.*\});?\s*$", util.read(data_js), flags=re.S)
        try:
            same = m and json.loads(m.group(1)) == k.spec
        except json.JSONDecodeError:
            same = False
        if not same:
            p.add(f"{r.kit_rel}/js/tokens-data.js — does not equal tokens/tokens.json (regenerate both from the same source)")
    icon_dir = r.kit_dir / "assets/icons"
    if icon_dir.is_dir():
        svgs = {x.stem for x in icon_dir.glob("*.svg")}
        for n in sorted(svgs - k.icons):
            p.add(f"{r.kit_rel}/assets/icons/{n}.svg — not in js/icons.js")
        for n in sorted(k.icons - svgs):
            p.add(f"{r.kit_rel}/js/icons.js — icon `{n}` has no assets/icons/{n}.svg")
    for font in ("Inter-Regular.ttf", "Inter-Medium.ttf", "Inter-SemiBold.ttf", "JetBrainsMono-Regular.ttf"):
        if not (r.kit_dir / "assets/fonts" / font).is_file():
            p.add(f"{r.kit_rel}/assets/fonts/{font} — bundled font missing")
    return p


def p_raw_colours(r: Repo) -> Probe:
    p = Probe("raw-colours", "Colour comes from `--craft-*` tokens, never a literal; brand art listed in allow_raw is the exception (CONVENTIONS 2)", "code")
    if "colour" not in r.m["enforce"]:
        p.skipped = "enforce does not include colour"
        return p
    for f in r.scanned:
        if r.is_allowed_raw(f):
            continue
        for n, line in r.lines(f):
            if ALLOW in line or COMMENT.match(line):
                continue
            s = _strip_safe(line)
            if HEX.search(s) or FUNC.search(s):
                p.add(r.finding(f, n, line))
    return p


RADIUS = re.compile(r"border(?:-(?:top|bottom)-(?:left|right))?-radius\s*:\s*([^;\"'}]+)")
FONT_FAMILY = re.compile(r"font-family\s*:\s*([^;\"'}]+)")
SHADOW = re.compile(r"box-shadow\s*:\s*([^;\"'}]+)")


def p_raw_values(r: Repo) -> Probe:
    p = Probe("raw-values", "Radii come from `--craft-radius-*`, type from `--craft-font-*`/`--craft-fs-*`, shadows from `--craft-*-shadow` (CONVENTIONS 2)", "code")
    want = set(r.m["enforce"]) & {"radius", "font", "shadow"}
    if not want:
        p.skipped = "enforce includes none of radius, font, shadow"
        return p
    for f in r.scanned:
        if r.is_allowed_raw(f):
            continue
        for n, line in r.lines(f):
            if ALLOW in line or COMMENT.match(line):
                continue
            if "radius" in want:
                for m in RADIUS.finditer(line):
                    v = m.group(1).strip()
                    if "var(" in v or v in ("0", "50%", "inherit", "9999px", "999px", "100%"):
                        continue
                    if re.search(r"\d(\.\d+)?(px|rem|em)", v):
                        p.add(r.finding(f, n, line, "raw radius"))
                        break
            if "font" in want:
                for m in FONT_FAMILY.finditer(line):
                    v = m.group(1).strip()
                    if "var(--craft-font" in v or v == "inherit":
                        continue
                    p.add(r.finding(f, n, line, "raw font stack"))
                    break
            if "shadow" in want:
                for m in SHADOW.finditer(line):
                    v = m.group(1).strip()
                    if "var(--craft-" in v or v in ("none", "inherit"):
                        continue
                    p.add(r.finding(f, n, line, "hand-made shadow"))
                    break
    return p


def p_unknown_tokens(r: Repo) -> Probe:
    p = Probe("unknown-tokens", "Every `var(--craft-…)` names a token the kit defines (CONVENTIONS 2)", "code")
    if not r.kit.tokens:
        p.skipped = "kit css missing"
        return p
    for f in r.scanned:
        for n, line in r.lines(f):
            for m in re.finditer(r"var\((--craft-[A-Za-z0-9_-]+)", line):
                if m.group(1) not in r.kit.tokens:
                    p.add(r.finding(f, n, line, f"`{m.group(1)}` is not a kit token"))
    return p


def p_token_overrides(r: Repo) -> Probe:
    p = Probe("token-overrides", "Projects never redefine `--craft-*`; project tokens get their own prefix and derive from kit tokens (CONVENTIONS 3)", "code")
    for f in r.scanned:
        for n, line in r.lines(f):
            if ALLOW in line or COMMENT.match(line):
                continue
            if re.search(r"(?<![\w-])--craft-[A-Za-z0-9_-]+\s*:", line) and "var(" not in line.split(":")[0]:
                p.add(r.finding(f, n, line))
    return p


def p_theme_patches(r: Repo) -> Probe:
    p = Probe("theme-patches", "Themes are tokens, grammars are flags: no `[data-craft-theme=…]` selectors in project styles (CONVENTIONS 3)", "code")
    for f in r.styles:
        for sel, _body, line in util.css_blocks(r.text[f]):
            if "[data-craft-theme" in sel:
                src = r.text[f].splitlines()[line - 1] if line - 1 < len(r.text[f].splitlines()) else sel
                if ALLOW in src:
                    continue
                p.add(f"{r.rel(f)}:{line} — {sel[:100]}")
    return p


THEME_REFS = [
    re.compile(r"data-craft-theme\s*=\s*[\"']([^\"'{$]+)[\"']"),
    re.compile(r"setTheme\(\s*[\"']([^\"']+)[\"']"),
    re.compile(r"[?&]theme=([A-Za-z][A-Za-z0-9]*)"),
]


def p_theme_ids(r: Repo) -> Probe:
    p = Probe("theme-ids", "A theme id is one of the kit's ThemeKind ids (CONVENTIONS 3)", "code")
    if not r.kit.themes:
        p.skipped = "kit tokens.json missing"
        return p
    for f in r.scanned:
        for n, line in r.lines(f):
            if ALLOW in line:
                continue
            for rx in THEME_REFS:
                for m in rx.finditer(line):
                    tid = m.group(1).strip()
                    if tid and tid not in r.kit.themes:
                        p.add(r.finding(f, n, line, f"unknown theme `{tid}`"))
    return p


TAG = re.compile(r"<[a-zA-Z][^<>]*>", flags=re.S)


def p_grammar_flags(r: Repo) -> Probe:
    p = Probe("grammar-flags", "Hard-coded grammar flags next to a theme id match tokens.json for that theme (CONVENTIONS 3)", "code")
    if not r.kit.themes:
        p.skipped = "kit tokens.json missing"
        return p
    for f in r.sources:
        text = r.text[f]
        for tm in TAG.finditer(text):
            tag = tm.group(0)
            th = re.search(r"data-craft-theme\s*=\s*[\"']([A-Za-z0-9]+)[\"']", tag)
            if not th or th.group(1) not in r.kit.themes:
                continue
            theme = r.kit.themes[th.group(1)]
            line = text[: tm.start()].count("\n") + 1
            for key, attr in kitmod.THEME_ATTRS.items():
                am = re.search(attr + r"\s*=\s*[\"'](true|false)[\"']", tag)
                if am and am.group(1) != str(bool(theme.get(key))).lower():
                    p.add(f"{r.rel(f)}:{line} — {attr}=\"{am.group(1)}\" but theme `{theme['id']}` has {key}={str(bool(theme.get(key))).lower()}")
    return p


def p_icon_names(r: Repo) -> Probe:
    p = Probe("icon-names", "`data-craft-icon` names one of the kit's icons (CONVENTIONS 4)", "code")
    if not r.kit.icons:
        p.skipped = "kit icons.js missing"
        return p
    for f in r.scanned:
        for n, line in r.lines(f):
            for m in re.finditer(r"data-craft-icon\s*=\s*[\"']([a-z0-9-]+)[\"']", line):
                if m.group(1) not in r.kit.icons:
                    p.add(r.finding(f, n, line, f"no icon `{m.group(1)}`"))
    return p


def p_class_names(r: Repo) -> Probe:
    p = Probe("class-names", "Every `craft-*` class in markup exists in the kit stylesheet (CONVENTIONS 4)", "code")
    if not r.kit.classes:
        p.skipped = "kit css missing"
        return p
    for f in r.sources:
        for n, line in r.lines(f):
            for m in re.finditer(r"class(?:Name)?\s*=\s*[\"']([^\"']*)[\"']", line):
                if "${" in m.group(1) or "{{" in m.group(1):
                    continue
                for c in m.group(1).split():
                    if c.startswith("craft-") and c not in r.kit.classes:
                        p.add(r.finding(f, n, line, f"`.{c}` is not a kit class"))
    return p


def p_component_restyle(r: Repo) -> Probe:
    p = Probe("component-restyle", "Project styles never target `.craft-*` classes; compose or add project classes instead (CONVENTIONS 4)", "code")
    for f in r.styles:
        src_lines = r.text[f].splitlines()
        for sel, _body, line in util.css_blocks(r.text[f]):
            if re.search(r"\.craft-[A-Za-z0-9_-]+", sel):
                if line - 1 < len(src_lines) and ALLOW in src_lines[line - 1]:
                    continue
                p.add(f"{r.rel(f)}:{line} — {sel[:100]}")
    return p


BUTTON = re.compile(r"<button\b([^>]*)>(.*?)</button>", flags=re.S | re.I)


def p_named_controls(r: Repo) -> Probe:
    p = Probe("named-controls", "Every icon-only button has an accessible name (`aria-label` or `title`) (CONVENTIONS 5)", "code")
    for f in r.sources:
        text = r.text[f]
        for m in BUTTON.finditer(text):
            attrs, inner = m.group(1), m.group(2)
            visible = re.sub(r"<[^>]+>", "", inner).strip()
            if visible:
                continue
            if not re.search(r"data-craft-icon|<svg|class=\"[^\"]*craft-icon", inner) and not re.search(r"data-craft-(pro-swap|studio-swap|default-chip-icon)", attrs):
                continue
            if re.search(r"\b(aria-label|aria-labelledby|title)\s*=", attrs) or ALLOW in attrs:
                continue
            line = text[: m.start()].count("\n") + 1
            p.add(f"{r.rel(f)}:{line} — icon-only <button> without aria-label or title")
    return p


def p_deviations_logged(r: Repo) -> Probe:
    p = Probe("deviations-logged", "Differences from the kit are listed under the deviations heading in the design doc and numbered in the decisions log (CONVENTIONS 6)", "harness")
    d = r.m["docs"]
    design = r.root / d["design"]
    if not design.is_file():
        p.add(f"{d['design']} — design doc missing (`craft-ds apply .` writes a skeleton)")
    elif d["deviations_heading"].lower() not in util.read(design).lower():
        p.add(f"{d['design']} — no \"{d['deviations_heading']}\" section")
    dec = r.root / d["decisions"]
    if not dec.is_file():
        p.add(f"{d['decisions']} — decisions log missing")
    elif not re.search(r"(?m)^#{2,3}\s*\d+\.", util.read(dec)):
        p.add(f"{d['decisions']} — no numbered decision yet (`## 1. …` with Context / Decision / Consequences)")
    if not (r.root / d["lessons"]).is_file():
        p.add(f"{d['lessons']} — lessons log missing")
    return p


def p_rule_coverage(r: Repo) -> Probe:
    p = Probe("rule-coverage", "The Claude rule's `paths:` cover every UI source and style the manifest names (CONVENTIONS 7)", "harness")
    if not r.m["harness"]["claude"]:
        p.skipped = "harness.claude is off"
        return p
    rule = r.root / ".claude/rules/craft-ds.md"
    if not rule.is_file():
        p.add(".claude/rules/craft-ds.md — rule missing (`craft-ds apply .`)")
        return p
    fm, _ = util.frontmatter(util.read(rule))
    paths = fm.get("paths") or []
    if not isinstance(paths, list) or not paths:
        p.add(".claude/rules/craft-ds.md — frontmatter has no `paths:` list")
        return p
    uncovered = sorted({str(Path(r.rel(f)).parent) for f in r.scanned if not util.matches(r.rel(f), paths)})
    for d in uncovered:
        p.add(f"{d}/ — UI files here match the manifest but no `paths:` glob in the rule")
    return p


ALL = [
    p_kit_intact,
    p_kit_consistency,
    p_raw_colours,
    p_raw_values,
    p_unknown_tokens,
    p_token_overrides,
    p_theme_patches,
    p_theme_ids,
    p_grammar_flags,
    p_icon_names,
    p_class_names,
    p_component_restyle,
    p_named_controls,
    p_deviations_logged,
    p_rule_coverage,
]


def run(m: dict, only: set[str] | None = None) -> list[Probe]:
    r = Repo(m)
    disabled = set(m["probes"].get("disable", []))
    out: list[Probe] = []
    for fn in ALL:
        pr = fn(r)
        if only and pr.id not in only:
            continue
        if pr.id in disabled:
            pr.findings = []
            pr.skipped = "disabled in manifest"
        out.append(pr)
    return out


def summary(probes: list[Probe]) -> tuple[int, int]:
    code = sum(len(p.findings) for p in probes if p.kind == "code")
    harness = sum(len(p.findings) for p in probes if p.kind == "harness")
    return code, harness


def markdown(probes: list[Probe], repo: str) -> str:
    code, harness = summary(probes)
    lines = [f"# craft-ds probes: {repo}", "", f"**{code} code drift · {harness} harness drift** across {len(probes)} probes", ""]
    for p in probes:
        tag = "skipped" if p.skipped else f"{len(p.findings)} finding{'s' if len(p.findings) != 1 else ''}"
        lines.append(f"## `{p.id}` ({p.kind}) — {tag}")
        lines.append(f"_{p.rule}_")
        if p.skipped:
            lines.append(f"- skipped: {p.skipped}")
        for f in p.findings[:60]:
            lines.append(f"- {f}")
        if len(p.findings) > 60:
            lines.append(f"- … {len(p.findings) - 60} more")
        lines.append("")
    return "\n".join(lines)
