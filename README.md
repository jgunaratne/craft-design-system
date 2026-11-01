# Craft DS

A design system for dense, pro-tool interfaces (tokens, 14 themes, 161 icons and direct-manipulation widgets), plus a CLI and agent hooks that keep a project consistent with it.

<!-- ![Showcase page cycling through themes](docs/themes.gif) -->
<!-- TODO: GIF of index.html switching Pro Medium → Studio → Classic, then scrubbing a label -->

## How it works

- **Tokens:** one source (`tokens/tokens.json`, W3C format) generates the CSS custom properties for all 14 themes.
- **Three layout grammars:** *Pro* (flat panels, 28px pills), *Studio* (rounded cards, toggle switches) and *Classic* (3D bevels). Each is switched by a `data-craft-*` attribute, so one markup tree renders all three.
- **Widgets:** `js/craft-ds.js` implements scrubby labels, math-capable number fields, curve editors and dials, all without dependencies.
- **Enforcement:** `bin/craft-ds` vendors a hash-pinned copy of the kit into a project and runs 15 probes (raw colors, off-grid spacing, unknown icons, and more). It screenshots every theme × width × font size. The same rules are rendered as rules, skills and a pre-tool-use hook for coding agents, so generated UI is checked before it is written.

```
tokens.json ─► css/craft-ds.css ─► index.html showcase
                       │
bin/craft-ds init ─► vendored kit + craft-ds.json manifest ─► check (15 probes) ─► shoot (screenshots)
                       └─► .claude/ hooks + skills (guard.mjs)
```

## Stack

CSS custom properties · vanilla JS · SVG · Python (stdlib CLI) · Node (Playwright screenshots) · Inter / JetBrains Mono

## Run it

```bash
python3 -m http.server -d . 8000     # open http://localhost:8000 for the showcase
scripts/check.sh                     # full gate: prints CHECK OK
bin/craft-ds init ~/src/my-app --sources "src/**/*.tsx" --styles "src/**/*.css"
bin/craft-ds check ~/src/my-app
```

See [DESIGN.md](DESIGN.md) for the full spec and [MAPPING.md](MAPPING.md) for every probe.

Full setup, configuration and design notes: [GUIDE.md](GUIDE.md).
