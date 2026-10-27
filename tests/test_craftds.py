"""craft-ds tests: a fixture project that adopts the kit, then breaks one rule per test and expects
exactly that probe to fire. Run: python3 -m unittest discover -s tests"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))

from craftds import check as checkmod  # noqa: E402
from craftds import kit as kitmod  # noqa: E402
from craftds import manifest as mf  # noqa: E402
from craftds import probes as probemod  # noqa: E402
from craftds import render  # noqa: E402

CLI = ROOT / "bin" / "craft-ds"

CLEAN_HTML = """<!DOCTYPE html>
<html data-craft-theme="studio" data-craft-pro="false" data-craft-bevel="false" data-craft-round-chips="true" data-craft-dark="true">
<head><link rel="stylesheet" href="../vendor/craft-ds/css/craft-ds.css"><link rel="stylesheet" href="styles/app.css"></head>
<body class="craft-app">
  <div class="craft-panel app-inspector">
    <div class="craft-panel-header"><div class="craft-tab-strip"><button type="button" class="craft-tab is-active">Layers</button></div></div>
    <div class="craft-panel-body">
      <button type="button" class="craft-icon-btn" title="Delete"><span class="craft-icon" data-craft-icon="trash"></span></button>
      <button type="button" class="craft-btn craft-btn-primary">Apply</button>
      <label class="craft-check-row"><span class="craft-toggle is-adaptive is-checked"></span><span>Pressure</span></label>
    </div>
  </div>
  <script src="../vendor/craft-ds/js/tokens-data.js"></script><script src="../vendor/craft-ds/js/icons.js"></script><script src="../vendor/craft-ds/js/craft-ds.js"></script>
  <script>CraftDS.setTheme('studio');</script>
</body></html>
"""
CLEAN_CSS = """/* app */
:root { --app-inspector-w: 290px; --app-brand: var(--craft-accent); }
.app-inspector { width: var(--app-inspector-w); background: var(--craft-card); border-radius: var(--craft-radius-lg); box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4); }
[data-craft-pro="true"] .app-inspector { border-radius: 0; }
.app-inspector h2 { font-family: var(--craft-font-sans); font-size: var(--craft-fs-heading); color: var(--craft-text); }
"""


class Fixture:
    def __init__(self):
        self.dir = Path(tempfile.mkdtemp(prefix="craftds-"))
        (self.dir / "src/styles").mkdir(parents=True)
        (self.dir / "src/index.html").write_text(CLEAN_HTML)
        (self.dir / "src/styles/app.css").write_text(CLEAN_CSS)
        r = subprocess.run([sys.executable, str(CLI), "init", str(self.dir), "--sources", "src/**/*.html", "--styles", "src/**/*.css", "--themes", "proMedium,studio,classic"], capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        r = subprocess.run([sys.executable, str(CLI), "apply", str(self.dir)], capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        (self.dir / "AGENTS.md").write_text("# app\n\n" + render.agents_snippet(mf.load(self.dir)))

    def write(self, rel: str, text: str) -> None:
        p = self.dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def append(self, rel: str, text: str) -> None:
        p = self.dir / rel
        p.write_text(p.read_text() + text)

    def probe(self, pid: str) -> list[str]:
        for p in probemod.run(mf.load(self.dir)):
            if p.id == pid:
                return p.findings
        raise KeyError(pid)

    def all_clean(self) -> dict[str, list[str]]:
        return {p.id: p.findings for p in probemod.run(mf.load(self.dir)) if p.findings}

    def check(self) -> list[str]:
        return checkmod.run(mf.load(self.dir))

    def cleanup(self) -> None:
        shutil.rmtree(self.dir, ignore_errors=True)


class ProbeTests(unittest.TestCase):
    def setUp(self):
        self.fx = Fixture()

    def tearDown(self):
        self.fx.cleanup()

    def test_clean_fixture_has_no_findings_and_passes_check(self):
        self.assertEqual(self.fx.all_clean(), {})
        self.assertEqual(self.fx.check(), [])

    def test_raw_colour_in_markup_and_css(self):
        self.fx.append("src/styles/app.css", ".x { color: #378ef0; }\n.y { background: rgb(10, 20, 30); }\n")
        self.fx.append("src/index.html", '<div style="background:#ff0000"></div>\n')
        f = self.fx.probe("raw-colours")
        self.assertEqual(len(f), 3, f)
        self.assertTrue(any("app.css:6" in x for x in f))

    def test_raw_colour_exceptions(self):
        self.fx.append("src/styles/app.css", ".a { color: var(--craft-accent, #378ef0); }\n.b { box-shadow: 0 1px 2px rgba(0,0,0,.5); }\n.c { color: #123456; } /* craft-allow: brand */\n")
        self.fx.append("src/index.html", '<p>The accent is <code>#378ef0</code>.</p>\n<div data-craft-allow style="background:#00ff00"></div>\n')
        self.assertEqual(self.fx.probe("raw-colours"), [])

    def test_allow_raw_glob(self):
        self.fx.write("src/brand/logo.html", '<div style="background:#ff00ff"></div>')
        self.assertEqual(len(self.fx.probe("raw-colours")), 1)
        m = json.loads((self.fx.dir / "craft-ds.json").read_text())
        m["allow_raw"] = ["src/brand/**"]
        (self.fx.dir / "craft-ds.json").write_text(json.dumps(m))
        self.assertEqual(self.fx.probe("raw-colours"), [])

    def test_raw_values(self):
        self.fx.append("src/styles/app.css", ".r { border-radius: 6px; }\n.f { font-family: Arial, sans-serif; }\n.ok { border-radius: 50%; font-family: inherit; }\n")
        f = self.fx.probe("raw-values")
        self.assertEqual(len(f), 2, f)

    def test_unknown_token(self):
        self.fx.append("src/styles/app.css", ".u { color: var(--craft-accent-colour); }\n")
        f = self.fx.probe("unknown-tokens")
        self.assertEqual(len(f), 1)
        self.assertIn("--craft-accent-colour", f[0])

    def test_token_override(self):
        self.fx.append("src/styles/app.css", ":root { --craft-accent: hotpink; }\n")
        self.assertEqual(len(self.fx.probe("token-overrides")), 1)

    def test_theme_patch_but_grammar_flag_is_fine(self):
        self.fx.append("src/styles/app.css", '[data-craft-theme="studio"] .app-inspector { padding: 2px; }\n[data-craft-bevel="true"] .app-inspector { padding: 0; }\n')
        f = self.fx.probe("theme-patches")
        self.assertEqual(len(f), 1, f)

    def test_theme_ids(self):
        self.fx.append("src/index.html", "<script>CraftDS.setTheme('studioDrak');</script>\n<a href=\"?theme=neon\">x</a>\n")
        f = self.fx.probe("theme-ids")
        self.assertEqual(len(f), 2, f)

    def test_grammar_flags(self):
        self.fx.append("src/index.html", '<div class="craft-scope" data-craft-theme="classic" data-craft-bevel="false" data-craft-pro="false"></div>\n')
        f = self.fx.probe("grammar-flags")
        self.assertEqual(len(f), 1, f)
        self.assertIn("bevel=true", f[0])

    def test_icon_and_class_names(self):
        self.fx.append("src/index.html", '<button type="button" class="craft-icon-btn craft-button" title="x"><span class="craft-icon" data-craft-icon="trash-2"></span></button>\n')
        self.assertEqual(len(self.fx.probe("icon-names")), 1)
        self.assertEqual(len(self.fx.probe("class-names")), 1)

    def test_component_restyle(self):
        self.fx.append("src/styles/app.css", ".craft-btn { height: 40px; }\n.app-x .craft-icon { width: 20px; }\n")
        self.assertEqual(len(self.fx.probe("component-restyle")), 2)

    def test_named_controls(self):
        self.fx.append("src/index.html", '<button type="button" class="craft-icon-btn"><span class="craft-icon" data-craft-icon="trash"></span></button>\n')
        self.assertEqual(len(self.fx.probe("named-controls")), 1)

    def test_kit_intact_catches_a_hand_edit(self):
        css = self.fx.dir / "vendor/craft-ds/css/craft-ds.css"
        css.write_text(css.read_text() + "\n.craft-btn { height: 99px; }\n")
        f = self.fx.probe("kit-intact")
        self.assertEqual(len(f), 1)
        self.assertIn("changed since it was pinned", f[0])
        self.assertTrue(any("craft-ds.css" in p for p in self.fx.check()))

    def test_kit_consistency_catches_a_missing_theme_block(self):
        tj = self.fx.dir / "vendor/craft-ds/tokens/tokens.json"
        spec = json.loads(tj.read_text())
        spec["themes"].append({**spec["themes"][0], "id": "neon", "label": "Neon"})
        tj.write_text(json.dumps(spec))
        f = self.fx.probe("kit-consistency")
        self.assertTrue(any("neon" in x for x in f), f)

    def test_deviations_logged(self):
        (self.fx.dir / "docs/DESIGN.md").write_text("# design\n")
        f = self.fx.probe("deviations-logged")
        self.assertEqual(len(f), 1)
        self.assertIn("Deliberate deviations", f[0])

    def test_rule_coverage(self):
        self.fx.write("src/pages/other.html", "<p>hi</p>")
        m = json.loads((self.fx.dir / "craft-ds.json").read_text())
        m["sources"] = ["src/**/*.html", "lib/**/*.html"]
        (self.fx.dir / "craft-ds.json").write_text(json.dumps(m))
        self.fx.write("lib/widget.html", "<p>x</p>")
        f = self.fx.probe("rule-coverage")
        self.assertEqual(len(f), 1, f)
        self.assertIn("lib/", f[0])

    def test_disable_probe(self):
        self.fx.append("src/styles/app.css", ".craft-btn { height: 40px; }\n")
        m = json.loads((self.fx.dir / "craft-ds.json").read_text())
        m["probes"]["disable"] = ["component-restyle"]
        (self.fx.dir / "craft-ds.json").write_text(json.dumps(m))
        self.assertEqual(self.fx.probe("component-restyle"), [])


class CheckTests(unittest.TestCase):
    def setUp(self):
        self.fx = Fixture()

    def tearDown(self):
        self.fx.cleanup()

    def test_mirrors_must_match(self):
        p = self.fx.dir / ".agents/rules/craft-ds.md"
        p.write_text(p.read_text() + "\n- extra gemini-only rule\n")
        self.assertTrue(any("body differs" in x for x in self.fx.check()))

    def test_claude_rule_needs_paths_and_gemini_needs_trigger(self):
        c = self.fx.dir / ".claude/rules/craft-ds.md"
        c.write_text("---\nfoo: bar\n---\nbody\n")
        g = self.fx.dir / ".agents/rules/craft-ds.md"
        g.write_text("---\nfoo: bar\n---\nbody\n")
        probs = self.fx.check()
        self.assertTrue(any("paths:" in x for x in probs))
        self.assertTrue(any("trigger:" in x for x in probs))

    def test_dead_link_and_unknown_command(self):
        (self.fx.dir / "AGENTS.md").write_text("see [x](docs/NOPE.md) and `src/missing.css`; run `craft-ds frobnicate .`\n")
        probs = self.fx.check()
        self.assertTrue(any("NOPE.md" in x for x in probs))
        self.assertTrue(any("src/missing.css" in x for x in probs))
        self.assertTrue(any("frobnicate" in x for x in probs))

    def test_themes_must_cover_all_grammars(self):
        m = json.loads((self.fx.dir / "craft-ds.json").read_text())
        m["themes"] = ["proMedium", "pro"]
        (self.fx.dir / "craft-ds.json").write_text(json.dumps(m))
        self.assertTrue(any("missing classic, studio" in x for x in self.fx.check()))

    def test_hooks_wired(self):
        (self.fx.dir / ".agents/hooks.json").write_text("{}")
        self.assertTrue(any("hooks.json" in x and "craft-guard" in x for x in self.fx.check()))

    def test_skill_name_must_match_folder(self):
        p = self.fx.dir / ".claude/skills/craft-upgrade/SKILL.md"
        p.write_text(p.read_text().replace("name: craft-upgrade", "name: upgrade"))
        self.assertTrue(any("must equal the folder name" in x for x in self.fx.check()))


class CliTests(unittest.TestCase):
    def setUp(self):
        self.fx = Fixture()

    def tearDown(self):
        self.fx.cleanup()

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(CLI), *args], capture_output=True, text=True, cwd=self.fx.dir)

    def test_baseline_ratchet(self):
        r = self.run_cli("probe", ".", "--update-baseline")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self.run_cli("probe", ".", "--baseline", ".craft-ds-baseline.json")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.fx.append("src/styles/app.css", ".x { color: #ff0000; }\n")
        r = self.run_cli("probe", ".", "--baseline", ".craft-ds-baseline.json")
        self.assertEqual(r.returncode, 1)
        self.assertIn("raw-colours: 0 → 1", r.stderr)

    def test_strict(self):
        self.fx.append("src/styles/app.css", ".x { color: #ff0000; }\n")
        self.assertEqual(self.run_cli("probe", ".", "--strict").returncode, 1)
        self.assertEqual(self.run_cli("probe", ".").returncode, 0)

    def test_update_restores_a_hand_edited_kit(self):
        css = self.fx.dir / "vendor/craft-ds/css/craft-ds.css"
        css.write_text("broken")
        r = self.run_cli("update", ".")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(css.read_text(), (ROOT / "css/craft-ds.css").read_text())
        self.assertEqual(self.fx.probe("kit-intact"), [])

    def test_apply_never_overwrites_without_force(self):
        p = self.fx.dir / ".claude/rules/craft-ds.md"
        p.write_text("mine")
        self.run_cli("apply", ".")
        self.assertEqual(p.read_text(), "mine")
        self.run_cli("apply", ".", "--force", "--only", "rules")
        self.assertNotEqual(p.read_text(), "mine")

    def test_templates_render_without_leftover_placeholders(self):
        for rel, content in render.plan(mf.load(self.fx.dir)):
            self.assertNotIn("{{", content, rel)

    def test_report(self):
        out = self.fx.dir / "report.md"
        r = self.run_cli("report", ".", "--out", str(out))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("# craft-ds report", out.read_text())


class GuardTests(unittest.TestCase):
    """The hook blocks kit edits under both protocols and lets everything else through."""

    def setUp(self):
        self.fx = Fixture()
        self.guard = self.fx.dir / ".claude/hooks/craft-guard.mjs"

    def tearDown(self):
        self.fx.cleanup()

    def run_guard(self, payload: dict, env_root=True):
        env = dict(os.environ)
        if env_root:
            env["CLAUDE_PROJECT_DIR"] = str(self.fx.dir)
        else:
            env.pop("CLAUDE_PROJECT_DIR", None)
        return subprocess.run(["node", str(self.guard)], input=json.dumps(payload), capture_output=True, text=True, cwd=self.fx.dir, env=env)

    def test_claude_blocks_kit_edit_and_allows_project_edit(self):
        r = self.run_guard({"tool_name": "Edit", "tool_input": {"file_path": "vendor/craft-ds/css/craft-ds.css"}})
        self.assertEqual(r.returncode, 2)
        self.assertIn("read-only", r.stderr)
        r = self.run_guard({"tool_name": "Edit", "tool_input": {"file_path": "src/styles/app.css"}})
        self.assertEqual(r.returncode, 0)

    def test_claude_blocks_shell_writes_into_kit_but_not_reads_or_prose(self):
        blocked = self.run_guard({"tool_name": "Bash", "tool_input": {"command": "sed -i 's/a/b/' vendor/craft-ds/js/craft-ds.js"}})
        self.assertEqual(blocked.returncode, 2)
        blocked = self.run_guard({"tool_name": "Bash", "tool_input": {"command": "echo x > vendor/craft-ds/css/craft-ds.css"}})
        self.assertEqual(blocked.returncode, 2)
        ok = self.run_guard({"tool_name": "Bash", "tool_input": {"command": "cat vendor/craft-ds/tokens/tokens.json | head"}})
        self.assertEqual(ok.returncode, 0)
        ok = self.run_guard({"tool_name": "Bash", "tool_input": {"command": "git diff vendor/craft-ds && echo 'never sed -i vendor/craft-ds'"}})
        self.assertEqual(ok.returncode, 0, ok.stderr)

    def test_jetski_protocol(self):
        payload = {"toolCall": {"name": "edit_file", "args": {"Path": str(self.fx.dir / "vendor/craft-ds/js/icons.js")}}, "workspacePaths": [str(self.fx.dir)]}
        r = self.run_guard(payload, env_root=False)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(json.loads(r.stdout)["decision"], "deny")
        payload = {"toolCall": {"name": "write_file", "args": {"Path": str(self.fx.dir / "src/new.html")}}, "workspacePaths": [str(self.fx.dir)]}
        r = self.run_guard(payload, env_root=False)
        self.assertEqual(json.loads(r.stdout)["decision"], "allow")
        payload = {"toolCall": {"name": "run_command", "args": {"CommandLine": "cp /tmp/x.css vendor/craft-ds/css/craft-ds.css"}}, "workspacePaths": [str(self.fx.dir)]}
        r = self.run_guard(payload, env_root=False)
        self.assertEqual(json.loads(r.stdout)["decision"], "deny")

    def test_baseline_is_not_hand_edited(self):
        r = self.run_guard({"tool_name": "Write", "tool_input": {"file_path": ".craft-ds-baseline.json"}})
        self.assertEqual(r.returncode, 2)

    def test_self_mode_protects_kit_files_by_name(self):
        env = dict(os.environ)
        env["CLAUDE_PROJECT_DIR"] = str(ROOT)
        r = subprocess.run(["node", str(ROOT / "lib/guard.mjs")], input=json.dumps({"tool_name": "Edit", "tool_input": {"file_path": "css/craft-ds.css"}}), capture_output=True, text=True, cwd=ROOT, env=env)
        self.assertEqual(r.returncode, 2)
        r = subprocess.run(["node", str(ROOT / "lib/guard.mjs")], input=json.dumps({"tool_name": "Edit", "tool_input": {"file_path": "index.html"}}), capture_output=True, text=True, cwd=ROOT, env=env)
        self.assertEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
