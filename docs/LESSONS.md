# Lessons (craft-ds)

Symptom → cause → rule.

- **Six toolbar icons rendered as sparkles and nobody noticed.** → `getIconSvg()` falls back silently, and the names (`trash-2`, `history`, `sun-moon`…) *sounded* right. → Names come from `assets/icons/`; `craft-ds probe` (`icon-names`) runs before a visual change is called done.
- **A regex edit produced `craft-icon-btn-smNone` in 5 buttons.** → A Python `re.sub` with an optional group interpolated `None`. → `class-names` catches any `craft-*` class the stylesheet does not define; run the probes after scripted edits too.
- **The scrubby labels wrapped onto two lines in Pro.** → `.craft-scrub-label` was `inline-flex` inside a flex options bar, so the colon pseudo-element broke the line. → Field labels are `display: inline; white-space: nowrap`; shoot the options bar at the narrow width after any label change.
- **`rgba(0,0,0,.55)` was flagged as a raw colour even though neutral alphas are allowed.** → The probe replaced it with the text `rgba()`, which the function matcher then matched. → Placeholders in `_strip_safe` contain no parenthesis; the unit test breaks that rule on purpose.
- **An empty `styles: []` scanned the whole repo.** → `select()` treated "no include globs" as "everything". → No include globs means no files; the manifest says explicitly what is UI.
- **Jetski and Claude Code hooks speak different protocols.** → Claude Code reads `tool_name`/`tool_input` and blocks on exit code 2; Jetski reads `toolCall.name`/`toolCall.args` and blocks on `{"decision":"deny"}`. → One `guard.mjs` detects the payload shape; `tests/test_craftds.py` (`GuardTests`) feeds it both.
