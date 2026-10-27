---
name: craft-adopt
description: "Apply the Craft Design System (the PhotoCraft look, from ~/git/craft-ds) to another project end to end: vendor and pin the kit, load it in the app shell, write the manifest, render the rule, skills, reviewer and guard hooks for Claude Code and Gemini, migrate existing UI onto kit tokens and components, bring check and probe to clean, baseline, screenshot every grammar, and report. Use when asked to use, adopt, apply or migrate a project to craft-ds or the PhotoCraft design system."
---

# Adopt Craft DS in a project

`CLI=~/git/craft-ds/bin/craft-ds` throughout. Read `~/git/craft-ds/DESIGN.md` and `~/git/craft-ds/MAPPING.md` once; the showcase `~/git/craft-ds/index.html` is the visual reference for everything you build.

## 1. Look before you vendor (read-only)

- `git status --short` in the target: don't adopt on top of someone's uncommitted work without saying so.
- Find the UI: markup/components, stylesheets, theme mechanism, icon set, fonts. Note what will *conflict* (a second token system, Tailwind palettes, another icon font, a `data-theme` attribute) and what is **brand art** (logos, illustrations) that may keep literals.
- Decide the mapping: `sources`, `styles`, `allow_raw`, and the `themes` to verify (one per grammar: e.g. `proMedium`, `studio`, `classic`; add a light one if the product ships light).

## 2. Vendor, manifest, harness

```sh
$CLI init <repo> --kit-dir vendor/craft-ds --sources "src/**/*.html,src/**/*.tsx" --styles "src/styles/**/*.css" --themes proMedium,studio,classic
$CLI apply <repo>            # .claude/ + .agents/: rule, 4 skills, reviewer, guard hooks, docs skeletons, CI
$CLI check <repo>
```
- Paste the printed "Craft Design System" section into the project's `AGENTS.md` (create it if absent) and make `CLAUDE.md` / `GEMINI.md` `@AGENTS.md` (or paste it there too). The words must be the same for both tools.
- If the project already had `.claude/settings.json` or `.agents/hooks.json`, `apply` keeps them and prints the hook entries to merge; merge them.
- Fill the project's `<repo>/docs/DESIGN.md` (which themes ship, project tokens, screens → kit components, copy voice) and keep its "Deliberate deviations" table honest. Decision #1 in `<repo>/docs/DECISIONS.md` is pre-written: adjust it.

## 3. Load the kit in the shell

```html
<link rel="stylesheet" href="vendor/craft-ds/css/craft-ds.css">
<body class="craft-app">…</body>
<script src="vendor/craft-ds/js/tokens-data.js"></script>
<script src="vendor/craft-ds/js/icons.js"></script>
<script src="vendor/craft-ds/js/craft-ds.js"></script>
```
`craft-ds.js` reads `?theme=`/`?font=` or the attributes already on `<html>`, hydrates `[data-craft-icon]`, and wires `data-craft-numeric` fields, sliders, dials, tabs, popovers and dialogs. In a bundler, import the three scripts in that order (they set `window.CRAFT_DS_SPEC`, `window.CRAFT_ICONS`, `window.CraftDS`). For a framework, render the same class names; keep the kit's markup contracts (see the `craft-new-component` skill table).

## 4. Migrate the existing UI (the real work)

Work screen by screen, kit component first, one project class beside it:
1. **Colours → tokens.** Replace literals with the semantic token that means the same thing (surfaces → `--craft-card/-chrome/-dock/-field`; text → `--craft-text/-text-dim/-text-faint`; brand accent → `--craft-accent`; CTAs → `--craft-primary-bg/-primary-text`; danger/warning likewise). A project token derives from a kit token (`--app-brand: var(--craft-accent)`), never redefines one.
2. **Controls → kit components.** Buttons, fields, dropdowns, checkboxes/switches (`.craft-toggle.is-adaptive`), sliders, tabs, menus, dialogs, panels, toolbars, status bars.
3. **Icons → kit icons** (`data-craft-icon`); remove the old icon font if nothing else needs it.
4. **Theme mechanism → `data-craft-theme`.** Delete `[data-theme=…]` overrides; what differed per theme is now a token. If the product needs a look the 14 themes don't give, that is a *new theme block* proposed upstream, not a patch.
5. **Radii and type → tokens.** `--craft-radius-sm/-radius/-radius-lg`, `--craft-font-sans/-mono`, `--craft-fs-*`.
After each screen: `$CLI probe <repo>` and fix until that screen's findings are gone or marked `craft-allow` with a reason.

## 5. Prove it

```sh
$CLI check <repo>                         # must be clean
$CLI probe <repo>                         # clean, or every remaining finding explained in the project's design doc
$CLI probe <repo> --update-baseline       # commit .craft-ds-baseline.json
$CLI shoot <repo> http://localhost:<port>/ --font-sizes small,large
```
Read every PNG with the `craft-visual-check` checklist (Pro: pills, checkboxes, colons; Studio: cards, switches; Classic: bevels). Then run the `craft-design-reviewer` agent on the diff. If the project has no node/playwright, set `screenshots.command` in `craft-ds.json` to its screenshot tool.

## 6. Hand off

Commit the kit folder, `craft-ds.json`, the baseline, `.claude/`, `.agents/`, `.github/workflows/craft-ds.yml` and the docs together (only if asked to commit). Don't push.

## Report

```
Craft DS adoption: <project>
- kit: vendor/craft-ds, version <version>, pinned (<n> files)
- manifest: sources <globs>, styles <globs>, themes <ids>, allow_raw <globs>
- harness: .claude/ + .agents/ (rule, 4 skills, reviewer, guard) · AGENTS.md section added · hooks merged: <yes/printed>
- migrated: <screens/components> → <kit components>; project tokens: <list>
- check: OK · probe: <code n / harness n> (baseline committed) · remaining findings explained: <where>
- shots read: <n> (<themes> × <widths> × <fonts>); fixed: …
- reviewer: <BLOCKER/SHOULD/NIT counts>
- not done / needs you: <conflicts, a theme the kit lacks, brand decisions>
```
