# Working in craft-ds

Short on purpose. These rules apply to the kit and to every project that adopts it; the `craft-ds` rule (`.claude/rules/craft-ds.md` = `.agents/rules/craft-ds.md`) carries the per-file detail and names the probe that checks each one.

## What this repo is

1. **The kit**: `css/craft-ds.css`, `js/craft-ds.js`, `js/tokens-data.js`, `js/icons.js`, `tokens/tokens.json`, `assets/` and the two licences. Generated together from PhotoCraft (`~/git/photocraft`); described in [DESIGN.md](DESIGN.md); shown in `index.html`.
2. **The enforcement**: `bin/craft-ds` + `lib/craftds/` (stdlib Python), `lib/guard.mjs` and `lib/shoot.mjs` (Node, no dependencies), `templates/` rendered into a project's `.claude/` and `.agents/`.

## Rules

1. **The kit files are one artefact.** `tokens.json`, `tokens-data.js`, `craft-ds.css` and `icons.js` must agree (`kit-consistency`). Change them together, bump `version` in `tokens.json`, run `bin/craft-ds pin .`. Consumers never edit their vendored copy (`kit-intact`; the guard hook blocks it).
2. **Tokens, not values.** Colour, radius and type in any UI file come from `--craft-*`. Literals live only in the kit stylesheet's theme blocks, in files listed in `allow_raw`, or on a line marked `craft-allow` / `data-craft-allow` with a reason nearby (`raw-colours`, `raw-values`, `unknown-tokens`).
3. **Themes are tokens; grammars are flags.** New appearance = a theme block + flags in `tokens.json`, never a `[data-craft-theme=…]` rule in component CSS and never a `--craft-*` override downstream (`theme-patches`, `token-overrides`, `theme-ids`, `grammar-flags`). Decision #1.
4. **Kit components, kit icons.** A `craft-*` class or `data-craft-icon` name must exist (`class-names`, `icon-names`); downstream styles never target `.craft-*` (`component-restyle`).
5. **Named, dense, legible.** Icon-only buttons carry `aria-label` or `title` (`named-controls`); every change is checked at the `large` UI font size and in one theme per grammar.
6. **Deviate on purpose.** A difference from PhotoCraft (here) or from the kit (downstream) is a row in the design doc's "Deliberate deviations" table plus a numbered entry in `docs/DECISIONS.md`; a trap goes in `docs/LESSONS.md` (`deviations-logged`).
7. **One body, two frontmatters.** Rules, skills and the reviewer are written once in `templates/` and rendered for both tools; the bodies must stay identical (`check` → mirrors). Decision #8.
8. **A probe fires on a written rule** and reports `path:line — what`; no probe without a test in `tests/test_craftds.py` that breaks that rule in the fixture repo. Probes are evidence (`probe` exits 0); `check` is the gate.
9. **No dependencies.** Python stdlib; Node built-ins; `shoot.mjs` resolves playwright/puppeteer from the *target* repo or defers to `screenshots.command`.

## Definition of done

- `bash scripts/check.sh` prints `CHECK OK` (unit tests, every template renders, the kit's own `check` and `probe` are clean, both hook protocols block what they should).
- For a visual change to the kit or the showcase: `bin/craft-ds shoot . index.html` (or the `--command` fallback) in `proMedium`, `studio`, `classic` and one light theme, PNGs read, and the `craft-design-reviewer` agent run.
- The report says what ran, with counts.

## Commands

- `bin/craft-ds check .` · `bin/craft-ds probe .` · `bin/craft-ds pin .` · `bin/craft-ds shoot . index.html`
- `bin/craft-ds init <repo>` · `apply <repo>` · `update <repo>` · `report <repo>`: adopt the system elsewhere (see the `craft-adopt` skill)
- `bash scripts/check.sh`: the whole gate · `python3 -m http.server 8765`: the showcase
