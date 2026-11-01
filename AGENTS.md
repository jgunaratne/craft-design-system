# Craft Design System (craft-ds)

The PhotoCraft look as a design system you can hand to any project, with the tooling that keeps the project on it. This file is loaded by every tool (Claude Code reads it as `CLAUDE.md` via `@AGENTS.md`; Gemini reads it directly) and says what matters most.

## When goals conflict, in this order
1. **The kit is one truth.** `tokens.json`, `tokens-data.js`, `craft-ds.css`, `icons.js` and `assets/` agree with each other and with PhotoCraft (`~/git/photocraft`). Never patch one of them alone; never let a consumer patch its copy.
2. **Downstream projects stay enforceable.** Every rule here can be checked by `bin/craft-ds` and is written identically for Claude Code and Gemini. A rule that cannot be checked is written so that it could be.
3. **Fidelity to PhotoCraft.** Pro Spectrum, Studio and Classic grammars behave as in `~/git/photocraft/crates/ui-egui`; deviations are recorded, not discovered.
4. **A good showcase.** `index.html` demonstrates every token, theme, grammar and widget, and is itself checked by the same probes.

## Map
- Kit: `css/craft-ds.css` (tokens + components), `js/craft-ds.js` (runtime), `js/tokens-data.js` + `tokens/tokens.json` (14 themes, metrics, tools), `js/icons.js` + `assets/icons/` (161 icons), `assets/fonts/`, `assets/brand/`. Spec: [DESIGN.md](DESIGN.md) (read §6 "Deliberate deviations" before changing anything).
- Enforcement: `bin/craft-ds` → `lib/craftds/{manifest,kit,probes,check,render,cli}.py`; `lib/guard.mjs` (PreToolUse guard for both tools); `lib/shoot.mjs` (themed screenshots); `templates/` (rule, 4 skills, reviewer, hooks, docs, CI); `craft-ds.json` (this repo's own manifest, `kit.dir: "."`). How a project maps onto it: [MAPPING.md](MAPPING.md).
- Context: [CONVENTIONS.md](CONVENTIONS.md) (the rules), [docs/DECISIONS.md](docs/DECISIONS.md) (before re-deciding), [docs/LESSONS.md](docs/LESSONS.md) (before debugging a probe or a hook).

## Skills and reviewer
`.claude/skills/` = `.agents/skills/`: **craft-adopt** (apply this design system to another project), **craft-new-component**, **craft-visual-check**, **craft-drift-and-align**, **craft-upgrade**. `.claude/agents/` = `.agents/agents/`: **craft-design-reviewer** (read-only). Use them; they encode how this repo checks its own work.

## Definition of done
1. `bash scripts/check.sh` prints `CHECK OK`.
2. A visual change: screenshots in `proMedium`, `studio`, `classic` and one light theme, looked at, not assumed; `craft-design-reviewer` run.
3. Report honestly what ran, with counts; never claim green without the output.

## Autonomy
- The kit files are protected by `.claude/hooks/craft-guard.mjs` / `.agents/hooks/craft-guard.mjs` (one script). Editing them means editing the generator or asking the user; then `bin/craft-ds pin .`.
- Commit only when asked. Never push.
- No new dependencies.

## The rules
@CONVENTIONS.md
