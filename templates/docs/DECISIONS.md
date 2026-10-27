# Decisions ({{project}})

Numbered, append-only. Context / Decision / Consequences. Read before re-deciding anything about the UI; link each "{{deviations_heading}}" row in `{{design_doc}}` to an entry here.

## 1. Build on the Craft Design System

**Context.** {{project}} needs a dense, themeable desktop-tool UI and should look like one product family with PhotoCraft and its siblings.

**Decision.** Vendor the Craft DS kit (`{{kit_dir}}/`, v{{kit_version}}) read-only and hash-pinned; use its tokens, classes, icons and themes; verify {{theme_list}}; run `craft-ds check` and `craft-ds probe` as the gate and the ratchet.

**Consequences.** No colour, radius or font literal outside brand art; no `[data-craft-theme=…]` patches or `--craft-*` overrides; the kit is upgraded whole with `craft-ds update`. Things the kit lacks are composed locally and proposed upstream.
