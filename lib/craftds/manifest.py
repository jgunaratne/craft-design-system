"""The manifest `craft-ds.json`: how one project maps onto the Craft Design System.

The manifest says where the kit is vendored, which files are the project's own UI sources and
styles, which themes the project must look right in, where its docs live, and which tools get a
harness. `defaults()` is complete; a project's file only needs to override what differs.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

from . import kit as kitmod
from . import util

FILENAME = "craft-ds.json"
PROBE_IDS = [
    "kit-intact",
    "kit-consistency",
    "raw-colours",
    "raw-values",
    "unknown-tokens",
    "token-overrides",
    "theme-patches",
    "theme-ids",
    "grammar-flags",
    "icon-names",
    "class-names",
    "component-restyle",
    "named-controls",
    "deviations-logged",
    "rule-coverage",
]


def defaults() -> dict:
    return {
        "project": "",
        "_doc": "Maps this project onto the Craft Design System. Every path is relative to the repo root. See MAPPING.md in the craft-ds checkout.",
        "kit": {
            "dir": "vendor/craft-ds",
            "source": util.home_relative(kitmod.ROOT),
            "version": "",
            "hashes": {},
        },
        "sources": ["src/**/*.html", "src/**/*.tsx", "src/**/*.jsx", "src/**/*.vue", "src/**/*.svelte", "src/**/*.js", "src/**/*.ts"],
        "styles": ["src/**/*.css"],
        "exclude": ["**/*.test.*", "**/*.spec.*", "**/*.stories.*", "**/node_modules/**", "**/dist/**"],
        "allow_raw": [],
        "enforce": ["colour", "radius", "font"],
        "themes": ["proMedium", "studio", "classic"],
        "font_sizes": ["small", "large"],
        "screenshots": {"widths": [1280, 900], "out": "test-results/craft-shots", "command": None},
        "docs": {
            "design": "docs/DESIGN.md",
            "decisions": "docs/DECISIONS.md",
            "lessons": "docs/LESSONS.md",
            "deviations_heading": "Deliberate deviations",
            "scan": ["AGENTS.md", "CLAUDE.md", "GEMINI.md", "CONVENTIONS.md", "README.md", "docs/**/*.md", ".claude/**/*.md", ".agents/**/*.md"],
        },
        "harness": {"claude": True, "gemini": True, "gemini_rule_trigger": "model_decision", "hooks": True},
        "probes": {"disable": []},
    }


def merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def path(repo: Path) -> Path:
    return Path(repo) / FILENAME


def load(repo: Path) -> dict:
    repo = Path(repo).resolve()
    p = path(repo)
    data = {}
    if p.is_file():
        data = json.loads(util.read(p))
    m = merge(defaults(), data)
    m["_repo"] = str(repo)
    m["_present"] = p.is_file()
    return m


def save(repo: Path, m: dict) -> None:
    out = {k: v for k, v in m.items() if not k.startswith("_") or k == "_doc"}
    path(repo).write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")


def kit_dir(m: dict) -> Path:
    return (Path(m["_repo"]) / m["kit"]["dir"]).resolve()


def validate(m: dict) -> list[str]:
    """Problems with the manifest itself (not the repo): shape, unknown probe ids, theme ids and grammar coverage."""
    problems: list[str] = []
    known = set(defaults().keys())
    for k in m:
        if not k.startswith("_") and k not in known:
            problems.append(f"manifest: unknown top-level key `{k}`")
    if not isinstance(m.get("sources"), list) or not m["sources"]:
        problems.append("manifest: `sources` must list at least one glob of this project's UI files")
    if not isinstance(m.get("themes"), list) or not m["themes"]:
        problems.append("manifest: `themes` must list at least one craft-ds theme id")
    for e in m.get("enforce", []):
        if e not in ("colour", "radius", "font", "shadow"):
            problems.append(f"manifest: `enforce` entry `{e}` is not one of colour, radius, font, shadow")
    for pid in m.get("probes", {}).get("disable", []):
        if pid not in PROBE_IDS:
            problems.append(f"manifest: probes.disable names unknown probe `{pid}` (known: {', '.join(PROBE_IDS)})")
    for fs in m.get("font_sizes", []):
        if fs not in ("tiny", "small", "medium", "large"):
            problems.append(f"manifest: font_sizes entry `{fs}` is not tiny, small, medium or large")
    kd = kit_dir(m)
    if kd.is_dir() and not kitmod.missing(kd):
        k = kitmod.Kit(kd)
        bad = [t for t in m["themes"] if t not in k.themes]
        if bad:
            problems.append(f"manifest: unknown theme id(s) {', '.join(bad)}; the kit defines {', '.join(k.themes)}")
        covered = k.grammars_covered(m["themes"])
        gaps = {"pro", "studio", "classic"} - covered
        if gaps:
            problems.append(
                f"manifest: `themes` must cover every layout grammar; missing {', '.join(sorted(gaps))} "
                "(pick one of: pro/proMedium/proLightGray/proLight · studio/studioLight/adwaita/breeze*/soft*/solarizedDark · classic)"
            )
    return problems
