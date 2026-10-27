"""Small stdlib helpers shared by the craft-ds CLI: paths, globs, hashing, CSS and frontmatter parsing."""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path


def read(p: Path) -> str:
    return Path(p).read_text(encoding="utf-8", errors="replace")


def rel(repo: Path, p: Path) -> str:
    try:
        return Path(p).resolve().relative_to(Path(repo).resolve()).as_posix()
    except ValueError:
        return Path(p).as_posix()


def glob_to_regex(pattern: str) -> re.Pattern:
    """`**` matches across directories, `*` within one, `?` one char. Anchored to the whole path."""
    out = ""
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if c == "*":
            if pattern[i : i + 3] == "**/":
                out += "(?:.*/)?"
                i += 3
                continue
            if pattern[i : i + 2] == "**":
                out += ".*"
                i += 2
                continue
            out += "[^/]*"
        elif c == "?":
            out += "[^/]"
        elif c in ".+^$()[]{}|\\":
            out += "\\" + c
        else:
            out += c
        i += 1
    return re.compile("^" + out + "$")


def matches(relpath: str, patterns: list[str]) -> bool:
    return any(glob_to_regex(p).match(relpath) for p in patterns or [])


SKIP_DIRS = {"node_modules", ".git", "dist", "build", "out", ".next", ".turbo", "test-results", "storybook-static", "__pycache__", ".venv", "coverage"}


def walk(repo: Path, skip_dirs: list[str] | None = None) -> list[Path]:
    """Every file under `repo`, skipping generated and vendored folders and dot-folders other than the harness ones."""
    out: list[Path] = []
    skip = SKIP_DIRS | set(skip_dirs or [])
    keep_dot = {".claude", ".agents", ".github"}
    for dp, dns, fns in os.walk(repo):
        dns[:] = sorted(d for d in dns if d not in skip and not (d.startswith(".") and d not in keep_dot))
        for f in sorted(fns):
            out.append(Path(dp) / f)
    return out


def select(files: list[Path], repo: Path, include: list[str], exclude: list[str] | None = None) -> list[Path]:
    """Files matching any `include` glob and no `exclude` glob. No include globs → no files."""
    if not include:
        return []
    inc = [glob_to_regex(p) for p in include]
    exc = [glob_to_regex(p) for p in exclude or []]
    picked: list[Path] = []
    for f in files:
        r = rel(repo, f)
        if not any(x.match(r) for x in inc):
            continue
        if any(x.match(r) for x in exc):
            continue
        picked.append(f)
    return picked


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def strip_css_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), css, flags=re.S)


def css_blocks(css: str) -> list[tuple[str, str, int]]:
    """Top-level `selector { body }` blocks as (selector, body, line). Nested at-rules are flattened
    with the at-rule prefixed to the selector."""
    css = strip_css_comments(css)
    out: list[tuple[str, str, int]] = []

    def parse(text: str, prefix: str, base_line: int) -> None:
        i = 0
        n = len(text)
        while i < n:
            j = text.find("{", i)
            if j < 0:
                break
            selector = text[i:j].strip().split(";")[-1].strip()
            depth = 1
            k = j + 1
            while k < n and depth:
                if text[k] == "{":
                    depth += 1
                elif text[k] == "}":
                    depth -= 1
                k += 1
            body = text[j + 1 : k - 1]
            line = base_line + text[:j].count("\n")
            full = (prefix + " " + selector).strip()
            if "{" in body and selector.startswith("@"):
                parse(body, full, line)
            else:
                out.append((full, body, line))
            i = k

    parse(css, "", 1)
    return out


def custom_props(body: str) -> list[str]:
    return re.findall(r"(?m)^\s*(--[A-Za-z0-9_-]+)\s*:", body)


def frontmatter(text: str) -> tuple[dict, str]:
    """A flat YAML-ish frontmatter (key: value, and `key:` followed by `- item` lists)."""
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?(.*)$", text, flags=re.S)
    if not m:
        return {}, text
    data: dict = {}
    key = None
    for raw in m.group(1).splitlines():
        if not raw.strip():
            continue
        lm = re.match(r"^\s+-\s+(.*)$", raw)
        if lm and key is not None:
            data.setdefault(key, [])
            if isinstance(data[key], list):
                data[key].append(lm.group(1).strip().strip("\"'"))
            continue
        km = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", raw)
        if km:
            key, val = km.group(1), km.group(2).strip()
            if val == "":
                data[key] = []
            elif val.startswith("[") and val.endswith("]"):
                data[key] = [x.strip().strip("\"'") for x in val[1:-1].split(",") if x.strip()]
            else:
                data[key] = val.strip("\"'")
    return data, m.group(2)


def lines_matching(path: Path, repo: Path, pattern: re.Pattern, ok=None, limit: int = 110) -> list[str]:
    """`path:line — text` for each line matching `pattern`, unless `ok(line)` says it is fine."""
    out = []
    for i, line in enumerate(read(path).splitlines(), 1):
        if pattern.search(line) and not (ok and ok(line)):
            out.append(f"{rel(repo, path)}:{i} — {line.strip()[:limit]}")
    return out


def home_relative(p: str | Path) -> str:
    s = str(Path(p).resolve())
    home = str(Path.home())
    return "~" + s[len(home) :] if s.startswith(home + "/") else s
