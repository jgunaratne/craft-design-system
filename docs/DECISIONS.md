# Decisions (craft-ds)

Numbered, append-only. Context / Decision / Consequences. Read before re-deciding anything about the kit; every row of "Deliberate deviations" in [DESIGN.md](../DESIGN.md) points here.

## 1. Themes are tokens; grammars are flags

**Context.** PhotoCraft's 14 themes differ in colour *and* in structure: Pro has pill buttons, checkboxes and colon labels; Studio has rounded cards, switches and round colour chips; Classic has bevels. A plain `[data-theme]` swap cannot express that without per-theme CSS everywhere.

**Decision.** One token set (`--craft-*`) defined per theme block in `css/craft-ds.css`, plus three boolean grammar flags (`data-craft-pro`, `data-craft-bevel`, `data-craft-round-chips`) and `data-craft-dark`, set by `CraftDS.setTheme()` from `tokens.json`. Component CSS may branch on the flags, never on a theme id.

**Consequences.** A project can add a theme by adding a token block and flags, with no component changes. Project CSS containing `[data-craft-theme=…]` is drift (`theme-patches`); hard-coded flags that disagree with `tokens.json` are drift (`grammar-flags`). Several themes can coexist on one page via `.craft-scope`.

## 2. egui points become CSS pixels, scaled by `--craft-font-scale`

**Context.** `theme.rs` sizes text in points (12/12.5/13/15) and `UiFontSize` multiplies them (10/12, 1, 14/12, 16/12).

**Decision.** Use the same numbers as `px` and expose the multiplier as `--craft-font-scale` via `data-craft-font-size`. Every `--craft-fs-*` token is `calc(N px * scale)`.

**Consequences.** A screenshot at `large` is part of the visual check; nothing may wrap inside a 24 px field or a 28/30 px button at 1.333×.

## 3. Classic bevels are inset box-shadows

**Context.** PhotoCraft paints two 1 px strokes per edge. On the web that would need extra elements or borders that change box size.

**Decision.** `[data-craft-bevel="true"]` rules use `inset 1px 1px #fff, inset -1px -1px #404040` (inverted when sunken) with `border-radius: 0`.

**Consequences.** Any `box-shadow` or `border-radius` set directly on a kit class by a project beats the bevel. Hence `component-restyle`: project styles never target `.craft-*`.

## 4. Popup value fields are DOM popovers

**Context.** egui's popup slider is a floating area. **Decision.** `.craft-popup-slider-popover` is absolutely positioned under the field, toggled by `.is-open`, closed on outside click. **Consequences.** Hosts that clip overflow on a toolbar must allow it (or the popover is cut); the showcase's options bar does.

## 5. Unknown icons render `sparkles` and are a probe finding

**Context.** A missing icon in egui is a compile error. A web page must still render.

**Decision.** `getIconSvg()` falls back to `sparkles`; `craft-ds probe` (`icon-names`) flags every `data-craft-icon` that is not one of the 161.

**Consequences.** The showcase itself shipped six wrong names until the probe existed (`sun-moon`, `trash-2`, `history`, `contrast-2`, `flip-horizontal-2`, `align-center-horizontal`). Keep the probe in the gate.

## 6. Every appearance state is a URL

**Context.** Screenshots and bug reports need a reproducible state. **Decision.** `?theme=<id>` and `?font=<size>` win; otherwise whatever is already on `<html>`; otherwise `proMedium`/`small`. No storage. **Consequences.** `craft-ds shoot` selects themes by query and attribute; hosts that persist a choice do it themselves.

## 7. The kit is vendored whole, read-only and hash-pinned

**Context.** A design system that projects patch locally stops being one.

**Decision.** `craft-ds init` copies `css/ js/ tokens/ assets/` and the licences into the project and pins SHA-256 hashes in `craft-ds.json`; `craft-ds update` replaces them whole; a PreToolUse guard (one script for Claude Code and Gemini) blocks edits; `kit-intact` and `check` catch what slipped through.

**Consequences.** Needs the kit lacks are composed in project files and proposed upstream here (`KIT-GAP` in the drift skill). The kit's own showcase is checked with the same manifest (`kit.dir: "."`).

## 8. One body, two frontmatters

**Context.** Claude Code loads `.claude/rules/*.md` by `paths:`; Gemini loads `.agents/rules/*.md` by `trigger:`; skills and agents have slightly different headers.

**Decision.** `templates/` hold one body per rule, skill and agent; `craft-ds apply` renders it twice with the right frontmatter; `craft-ds check` fails if the two bodies differ.

**Consequences.** Edit the template (or one copy, then `apply --force`), never one tool's copy alone.
