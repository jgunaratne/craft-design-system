# Craft Design System (`craft-ds`)

**Craft DS** is the standalone web design system, token library, component stylesheet, and interactive showcase extracted from **PhotoCraft** (`~/git/photocraft`).

It reproduces PhotoCraft's complete visual language and direct-manipulation widget mechanics:
- **14 Built-in Themes (`ThemeKind::ALL`)**: `Pro (Dark)`, `Pro (Medium Gray)` *(default)*, `Pro (Light Gray)`, `Pro (Light)`, `Studio (Dark)`, `Studio (Light)`, `Classic` *(Windows 2000 3D Bevel)*, `GNOME Adwaita Light/Dark`, `KDE Breeze Light/Dark`, `Solarized Dark`, and `Soft Dark/Light`.
- **3 Structural Layout Grammars**:
  - **Pro Spectrum (`data-craft-pro="true"`)**: Flat charcoal panels, `#378ef0` Spectrum blue accent, `28px` pill buttons (with `1.5px` inside-stroke secondary buttons), `14×14px` checkboxes, 5-icon layer lock strips, colon-suffixed labels (`Opacity:`), full-bleed blue menu hover, monochrome gray input selection, and `18×18px` overlapping square color chips.
  - **Studio Card/Pill (`data-craft-round-chips="true"`)**: Rounded cards, `#8b7cf6` violet accent, near-white primary buttons, `24px` pill tabs, `30×17px` iOS-style toggle switches, single lock icon button, and `30px` stacked round color chips with a curved swap arc.
  - **Classic 3D Bevel (`data-craft-bevel="true"`)**: Warm `#d4d0c8` surfaces, `0px` corners, raised/sunken 2px 3D bevels, and `10×16px` rectangular slider thumbs.
- **Bundled Typography & Icons**:
  - Self-hosted `Inter` (`400`, `500`, `600`) and `JetBrains Mono` (`400`) in `assets/fonts/`.
  - All **161 SVG icons** (`stroke-width: 1.75`) in `assets/icons/` and `js/icons.js`, plus the PhotoCraft Kitsune app icon (`assets/brand/photocraft-icon.png`).

---

## Repository Structure

```text
craft-ds/
├── index.html              # Interactive demo page + live miniature PhotoCraft workspace
├── DESIGN.md               # Complete design system specification & token reference
├── README.md               # Quickstart & usage guide
├── css/
│   └── craft-ds.css        # Standalone CSS tokens, 14 themes, 3 grammars & widget styles
├── js/
│   ├── tokens-data.js      # Exported theme tokens, layer label colors, metrics & tool catalog
│   ├── icons.js            # All 161 normalized SVG icons (window.CRAFT_ICONS)
│   └── craft-ds.js         # Interactive runtime (scrubby labels, math fields, curves, dials)
├── tokens/
│   └── tokens.json         # Machine-readable W3C/JSON design tokens for all 14 themes
├── assets/
│   ├── brand/              # PhotoCraft kitsune app icon
│   ├── fonts/              # Inter (Regular, Medium, SemiBold) & JetBrains Mono + OFL licenses
│   └── icons/              # 161 raw SVG icons (24x24 viewBox, 1.75px stroke)
│
├── bin/craft-ds            # The enforcement CLI (init, apply, check, probe, shoot, update, report)
├── lib/craftds/            # manifest, kit, probes (15), check (the gate), render — stdlib Python
├── lib/guard.mjs           # PreToolUse guard for Claude Code *and* Gemini (one script)
├── lib/shoot.mjs           # Screenshots per theme × width × UI font size, with report.json
├── templates/              # One rule, four skills, the reviewer, hooks, docs, CI — rendered for both tools
├── craft-ds.json           # This repo's own manifest (kit.dir ".")
├── .claude/ · .agents/     # The rendered harness, dogfooded here
├── tests/test_craftds.py   # A fixture project that breaks one rule per test; both hook protocols
├── MAPPING.md              # The manifest, field by field, and every probe
├── AGENTS.md · CLAUDE.md · GEMINI.md · CONVENTIONS.md · docs/DECISIONS.md · docs/LESSONS.md
└── scripts/check.sh        # The whole gate: `CHECK OK`
```

---

## Applying the design system to another project (enforced)

Craft DS is not only a stylesheet: it ships the harness that keeps a project on it, for **Claude Code** (`.claude/`) and **Gemini** (`.agents/`), rendered from one set of templates so both tools read the same words. The method is the one distilled in `~/git/ui-consistency` from `~/git/tally-ho`; here it is bound to one concrete design system.

```sh
CDS=~/git/craft-ds/bin/craft-ds

# 1. Vendor the kit (read-only, hash-pinned) and write the manifest
$CDS init ~/src/my-app --sources "src/**/*.html,src/**/*.tsx" --styles "src/**/*.css" --themes proMedium,studio,classic

# 2. Render the harness: rule (paths: / trigger:), 4 skills, the read-only reviewer, guard hooks, doc skeletons, CI
$CDS apply ~/src/my-app          # never overwrites; prints the AGENTS.md section to paste

# 3. The gate and the evidence
$CDS check ~/src/my-app          # manifest, kit pins, dead paths, frontmatter, .claude == .agents, hooks
$CDS probe ~/src/my-app          # 15 drift probes with file:line, each naming the rule it checks
$CDS probe ~/src/my-app --update-baseline   # commit .craft-ds-baseline.json; CI fails only if drift grows

# 4. Look at the pixels
$CDS shoot ~/src/my-app http://localhost:3000/ --font-sizes small,large   # per theme × width; report.json

# 5. Later
$CDS update ~/src/my-app         # replace the kit whole, re-pin, re-probe
```

What the project gets:

| Piece | Claude Code | Gemini |
|---|---|---|
| The rule (loads when UI files are touched) | `.claude/rules/craft-ds.md` with `paths:` | `.agents/rules/craft-ds.md` with `trigger: model_decision` |
| Skills: `craft-new-component`, `craft-visual-check`, `craft-drift-and-align`, `craft-upgrade` | `.claude/skills/*/SKILL.md` | `.agents/skills/*/SKILL.md` |
| Read-only reviewer `craft-design-reviewer` | `.claude/agents/` | `.agents/agents/` |
| Guard: the vendored kit and the baseline cannot be edited by an agent | `.claude/settings.json` → `.claude/hooks/craft-guard.mjs` (exit 2) | `.agents/hooks.json` → `.agents/hooks/craft-guard.mjs` (`{"decision":"deny"}`) |
| Docs skeletons | the project's design doc (with a "Deliberate deviations" table), decisions log, lessons log, and an `AGENTS.md` start-here if it has none | same |
| CI | `.github/workflows/craft-ds.yml`: `check` + `probe --baseline` | same |

The rules the probes enforce, in one line each: the kit is read-only (`kit-intact`); colour, radius and type are `--craft-*` tokens (`raw-colours`, `raw-values`, `unknown-tokens`); themes are tokens and grammars are flags (`theme-patches`, `token-overrides`, `theme-ids`, `grammar-flags`); kit classes and icons exist and are never restyled (`class-names`, `icon-names`, `component-restyle`); icon-only buttons are named (`named-controls`); deviations are written down (`deviations-logged`); the rule covers every UI file (`rule-coverage`); the kit agrees with itself (`kit-consistency`). Full table: [MAPPING.md](MAPPING.md). This repo runs the same gate on its own showcase (`bash scripts/check.sh`).

In this repo, the `craft-adopt` skill (`.claude/skills/craft-adopt`, `.agents/skills/craft-adopt`) walks an agent through the whole adoption, migration and proof.

---

## Running the Demo Page Locally

Because `index.html` loads `js/tokens-data.js`, `js/icons.js`, and `js/craft-ds.js` via standard `<script>` tags and relative `@font-face` paths, you can open `index.html` directly or serve the directory over HTTP:

```bash
cd ~/git/craft-ds
python3 -m http.server 8765
```

---

## Using `craft-ds` in Your Project

```html
<link rel="stylesheet" href="css/craft-ds.css" />
<script src="js/tokens-data.js"></script>
<script src="js/icons.js"></script>
<script src="js/craft-ds.js"></script>

<!-- Switch themes dynamically -->
<script>
  CraftDS.setTheme('proMedium'); // or 'pro', 'studio', 'studioLight', 'classic', etc.
  CraftDS.setFontSize('small');  // 'tiny' | 'small' | 'medium' | 'large'
</script>
```

## License

Dual-licensed under `Apache-2.0 OR MIT` (matching PhotoCraft), with bundled fonts under the SIL Open Font License 1.1 and icons derived from Lucide (`ISC`).
