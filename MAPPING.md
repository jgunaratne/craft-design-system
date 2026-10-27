# Mapping a project: `craft-ds.json`

The manifest says where the Craft Design System lives in one project and which of that project's files must follow it. `craft-ds init` writes it; every other command reads it. Paths are relative to the repo root.

```json
{
  "project": "my-app",
  "kit":        { "dir": "vendor/craft-ds", "source": "~/git/craft-ds", "version": "0.16.0", "hashes": { "css/craft-ds.css": "sha256:…" } },
  "sources":    ["src/**/*.html", "src/**/*.tsx"],
  "styles":     ["src/styles/app.css"],
  "exclude":    ["**/*.test.*", "**/*.stories.*"],
  "allow_raw":  ["src/brand/**"],
  "enforce":    ["colour", "radius", "font"],
  "themes":     ["proMedium", "studio", "classic"],
  "font_sizes": ["small", "large"],
  "screenshots": { "widths": [1280, 900], "out": "test-results/craft-shots", "command": null },
  "docs":       { "design": "docs/DESIGN.md", "decisions": "docs/DECISIONS.md", "lessons": "docs/LESSONS.md", "deviations_heading": "Deliberate deviations" },
  "harness":    { "claude": true, "gemini": true, "gemini_rule_trigger": "model_decision", "hooks": true },
  "probes":     { "disable": [] }
}
```

## Fields

| Field | Meaning | Used by |
|---|---|---|
| `kit.dir` | Where the kit is vendored (`"."` when the repo *is* the kit) | everything; the guard hook protects it |
| `kit.source` | The craft-ds checkout the kit came from (`craft-ds update` copies from the checkout running the command) | docs, `update` |
| `kit.version`, `kit.hashes` | Pinned by `craft-ds pin` / `init` / `update` | `kit-intact`, `check` |
| `sources` | Globs of the project's own UI files: markup, components, scripts that build markup | code probes, the Claude rule's `paths:` |
| `styles` | The project's stylesheets | `raw-*`, `theme-patches`, `component-restyle`, `token-overrides` |
| `exclude` | Globs left out (tests, stories, generated) | all |
| `allow_raw` | Globs that may hold colour/radius/font literals (brand art, vendored CSS) | `raw-colours`, `raw-values` |
| `enforce` | Which literal kinds are findings: `colour`, `radius`, `font`, `shadow` | `raw-colours`, `raw-values` |
| `themes` | Theme ids the project verifies in screenshots; **must cover all three grammars** (one of `pro*`, one Studio-grammar theme, `classic`) | `shoot`, templates, `check` |
| `font_sizes` | UI font sizes to verify (`tiny` `small` `medium` `large`) | `shoot --font-sizes`, templates |
| `screenshots.widths` | Viewport widths to shoot (desktop tool: 1280 and 900 are good defaults) | `shoot`, templates |
| `screenshots.out` | Where PNGs and `report.json` land | `shoot` |
| `screenshots.command` | A project screenshot command with `{url} {out} {width} {height} {theme}` placeholders, used when node + playwright/puppeteer are not available | `shoot` |
| `docs.*` | The project's design doc, decisions log, lessons log, deviations heading, and which markdown files `check` scans for dead paths | `deviations-logged`, `check`, templates |
| `harness.claude` / `harness.gemini` | Which trees `apply` writes (`.claude/`, `.agents/`) | `apply`, `check` |
| `harness.gemini_rule_trigger` | `model_decision` (loaded when relevant, needs a description) or `always_on` | `apply` |
| `harness.hooks` | Install the guard hook (`.claude/settings.json`, `.agents/hooks.json`) | `apply`, `check` |
| `probes.disable` | Probe ids to skip, with a reason in the design doc | `probe` |

## The probes

| Probe | Drift | Fires when |
|---|---|---|
| `kit-intact` | harness | A kit file is missing, unpinned, or differs from its pinned hash |
| `kit-consistency` | harness | tokens.json, tokens-data.js, craft-ds.css theme blocks, icons.js and assets/ disagree |
| `raw-colours` | code | A colour literal in sources or styles outside `allow_raw`, not `craft-allow`, not a neutral alpha, not documentation in `<code>`/backticks |
| `raw-values` | code | A pixel radius, font stack or hand-made shadow not from a `--craft-*` token (per `enforce`) |
| `unknown-tokens` | code | `var(--craft-…)` names a token the kit does not define |
| `token-overrides` | code | A project file defines a `--craft-*` custom property |
| `theme-patches` | code | `[data-craft-theme=…]` in a project selector (themes are tokens; grammar flags are allowed) |
| `theme-ids` | code | `data-craft-theme="x"`, `setTheme('x')` or `?theme=x` with an unknown id |
| `grammar-flags` | code | A hard-coded `data-craft-pro/bevel/round-chips/dark` disagrees with tokens.json for the theme on the same element |
| `icon-names` | code | `data-craft-icon` names an icon the kit lacks |
| `class-names` | code | A `craft-*` class in markup that the kit stylesheet does not define |
| `component-restyle` | code | A project selector targets `.craft-*` |
| `named-controls` | code | An icon-only `<button>` without `aria-label` or `title` |
| `deviations-logged` | harness | No deviations section in the design doc; no numbered decision; no lessons log |
| `rule-coverage` | harness | UI files the manifest names that the Claude rule's `paths:` do not cover |

Findings read `path:line — what`. Mark a deliberate exception with `craft-allow` on the line (`data-craft-allow` in markup); list a whole file or folder in `allow_raw`.

## What `check` gates

Manifest shape and theme/grammar coverage · kit complete, pinned and unchanged · every link, `@import` and path-like code span in the scanned docs exists · every `craft-ds <cmd>` in code is real · Claude rule has `paths:` that match files, Gemini rule has `trigger:` (+ description) · skills and agents have `name` = folder/file and a `description` · `.claude/` and `.agents/` bodies are identical · hook files present and wired · baseline file is valid JSON.

## Adopting, in order

1. `craft-ds init <repo>` (vendors the kit into `vendor/craft-ds/`, writes the manifest, pins). Edit `sources`, `styles`, `themes`.
2. Load the kit in the app shell: `<link rel="stylesheet" href="vendor/craft-ds/css/craft-ds.css">` and the three scripts (`tokens-data.js`, `icons.js`, `craft-ds.js`); put `class="craft-app"` on `<body>`; call `CraftDS.setTheme(id)`.
3. `craft-ds apply <repo>`: rule, skills, reviewer, hooks, docs skeletons, CI; paste the printed section into `AGENTS.md` (and `CLAUDE.md`/`GEMINI.md` if they don't `@AGENTS.md`).
4. `craft-ds check <repo>` until clean; `craft-ds probe <repo>`, fix or explain; `craft-ds probe <repo> --update-baseline`.
5. `craft-ds shoot <repo> <url>` and read the PNGs; keep `check` + `probe --baseline` in CI.
