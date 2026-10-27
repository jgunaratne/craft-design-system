"""The kit: the files that *are* the Craft Design System, and what they define.

A project adopts craft-ds by vendoring the kit (read-only, hash-pinned) and referring to it. This
module knows which files make up the kit, copies it into a project, pins it, and reads back the
facts the probes need: theme ids and grammar flags, token names, component class names, icon names.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from . import util

ROOT = Path(__file__).resolve().parent.parent.parent  # the craft-ds checkout

KIT_FILES = [
    "css/craft-ds.css",
    "js/craft-ds.js",
    "js/tokens-data.js",
    "js/icons.js",
    "tokens/tokens.json",
    "LICENSE-APACHE",
    "LICENSE-MIT",
    "DESIGN.md",
    "index.html",
]
KIT_DIRS = ["assets/fonts", "assets/icons", "assets/brand"]

GRAMMAR_FLAGS = ("pro", "bevel", "round_chips", "dark")
THEME_ATTRS = {"pro": "data-craft-pro", "bevel": "data-craft-bevel", "round_chips": "data-craft-round-chips", "dark": "data-craft-dark"}


def grammar_of(theme: dict) -> str:
    if theme.get("pro"):
        return "pro"
    if theme.get("bevel"):
        return "classic"
    return "studio"


def kit_files(kit_dir: Path) -> list[Path]:
    """Every file of the kit under `kit_dir` (missing ones are simply absent from the list)."""
    out = [kit_dir / f for f in KIT_FILES if (kit_dir / f).is_file()]
    for d in KIT_DIRS:
        p = kit_dir / d
        if p.is_dir():
            out.extend(sorted(x for x in p.rglob("*") if x.is_file()))
    return out


def missing(kit_dir: Path) -> list[str]:
    gone = [f for f in KIT_FILES if not (kit_dir / f).is_file()]
    gone += [d + "/" for d in KIT_DIRS if not (kit_dir / d).is_dir()]
    return gone


class Kit:
    """Facts read from a kit directory."""

    def __init__(self, kit_dir: Path):
        self.dir = Path(kit_dir)
        self.css_path = self.dir / "css/craft-ds.css"
        self.css = util.read(self.css_path) if self.css_path.is_file() else ""
        tokens_path = self.dir / "tokens/tokens.json"
        self.spec = json.loads(util.read(tokens_path)) if tokens_path.is_file() else {"themes": [], "version": "?"}
        self.version = str(self.spec.get("version", "?"))
        self.themes: dict[str, dict] = {t["id"]: t for t in self.spec.get("themes", [])}
        self.default_theme = self.spec.get("defaultTheme", "proMedium")
        plain = util.strip_css_comments(self.css)
        self.tokens: set[str] = set(re.findall(r"(--craft-[A-Za-z0-9_-]+)\s*:", plain))
        self.classes: set[str] = set(re.findall(r"\.((?:craft|ds)-[A-Za-z0-9_-]+)", plain))
        self.icons: set[str] = self._icon_names()
        self.theme_keys = self._theme_keys()

    def _icon_names(self) -> set[str]:
        p = self.dir / "js/icons.js"
        if not p.is_file():
            return set()
        return set(re.findall(r"^\s*\"([a-z0-9-]+)\"\s*:\s*\"", util.read(p), flags=re.M))

    def _theme_keys(self) -> set[str]:
        keys: set[str] = set()
        for t in self.themes.values():
            keys |= {k for k, v in t.items() if isinstance(v, (str, int, float)) and k not in ("id", "kind", "label", "family", "description")}
        return keys

    def theme_css_block(self, theme_id: str) -> str | None:
        for sel, body, _ in util.css_blocks(self.css):
            if f'[data-craft-theme="{theme_id}"]' in sel:
                return body
        return None

    def grammars_covered(self, theme_ids: list[str]) -> set[str]:
        return {grammar_of(self.themes[t]) for t in theme_ids if t in self.themes}


def source_kit() -> Kit:
    return Kit(ROOT)


def copy_kit(dest_dir: Path, src_dir: Path = ROOT) -> list[str]:
    """Copy the kit files from `src_dir` into `dest_dir`; returns the relative paths written."""
    written: list[str] = []
    for f in KIT_FILES:
        s = src_dir / f
        if not s.is_file():
            continue
        d = dest_dir / f
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(s, d)
        written.append(f)
    for dname in KIT_DIRS:
        s = src_dir / dname
        if not s.is_dir():
            continue
        d = dest_dir / dname
        if d.exists():
            shutil.rmtree(d)
        shutil.copytree(s, d)
        written.extend(util.rel(dest_dir, x) for x in sorted(d.rglob("*")) if x.is_file())
    return written


def hashes(kit_dir: Path) -> dict[str, str]:
    return {util.rel(kit_dir, f): util.sha256(f) for f in kit_files(kit_dir)}
