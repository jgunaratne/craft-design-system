#!/bin/bash
# craft-ds's own done oracle: the tooling compiles and is tested, every template renders for the kit's
# own manifest and for a fresh consumer, the kit passes its own gate and probes, and both hook
# protocols block what they should. Prints CHECK OK or fails.
set -euo pipefail
cd "$(dirname "$0")/.."

python3 -m py_compile lib/craftds/*.py bin/craft-ds
node --check lib/guard.mjs
node --check lib/shoot.mjs
python3 -c "import json; json.load(open('tokens/tokens.json')); json.load(open('craft-ds.json'))"

# Unit tests: one fixture project, one broken rule per test, both hook protocols.
python3 -m unittest discover -s tests 2>&1 | tail -n 3

# The kit itself: gate green, no drift, baseline honoured.
bin/craft-ds check .
bin/craft-ds probe . --baseline .craft-ds-baseline.json >/dev/null

# The rendered harness in this repo equals the templates (nobody edited one tool's copy alone).
tmp=$(mktemp -d)
python3 - "$tmp" <<'EOF'
import sys, pathlib
sys.path.insert(0, "lib")
from craftds import manifest as mf, render
repo = pathlib.Path(".")
m = mf.load(repo)
stale = []
for rel, content in render.plan(m, {"rules", "skills", "agents"}):
    here = (repo / rel)
    if not here.is_file() or here.read_text() != content:
        stale.append(rel)
if stale:
    print("rendered harness differs from templates (run bin/craft-ds apply . --force --only rules,skills,agents):")
    for s in stale: print("  -", s)
    sys.exit(1)
print("templates: rendered harness is current for", len(list(render.plan(m, {"rules","skills","agents"}))), "files")
EOF
rm -rf "$tmp"

echo "CHECK OK"
