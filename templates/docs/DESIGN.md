# {{project}} — design

{{project}} is built on the **Craft Design System** (the PhotoCraft look), vendored read-only at `{{kit_dir}}/` (v{{kit_version}}). This file says how *this project* uses it; the system itself is described in the kit's own spec `{{kit_design}}` and shown in `{{kit_showcase}}`.

## Themes this project ships

| Theme id | Grammar | Where it is used |
|---|---|---|
| `{{default_theme}}` | (fill in) | default |

The project verifies {{theme_list}} at {{widths}} px (see `{{manifest}}`). All {{theme_count}} kit themes must keep working, because every value is a token.

<details><summary>All kit themes and their grammar flags</summary>

| id | label | grammar | flags |
|---|---|---|---|
{{grammar_rows}}

</details>

## Project tokens

Project-specific values get their own prefix and derive from kit tokens. List them here with their purpose:

| Token | Value | Purpose |
|---|---|---|
| `--app-example` | `var(--craft-accent)` | (example) brand accent for marketing surfaces |

## Screens and components

For each screen or composite component: which kit components it is built from, which project classes wrap them, and where the markup lives.

| Screen / component | Built from | Project class | File |
|---|---|---|---|

## Copy and voice

Where user-facing strings live, and the voice they follow (PhotoCraft: short, imperative, tool-maker's vocabulary: "Layer Style…", "Export As…", labels end with a colon in Pro only via `.craft-pro-colon`).

## {{deviations_heading}}

Every intentional difference from the kit showcase or from PhotoCraft, with the decision that records why. A difference not in this table is drift.

| What differs | From | Why | Decision |
|---|---|---|---|
| (none yet) | | | |
