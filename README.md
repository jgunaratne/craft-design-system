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
└── assets/
    ├── brand/              # PhotoCraft kitsune app icon
    ├── fonts/              # Inter (Regular, Medium, SemiBold) & JetBrains Mono + OFL licenses
    └── icons/              # 161 raw SVG icons (24x24 viewBox, 1.75px stroke)
```

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
