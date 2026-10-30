#!/bin/zsh
# 30 Oct VS Code check: agent steps 02, 04, 05 of change_permissions replayed from a fresh start (test only), with the
# faster tree reads (warm-up read reused, VS Code VM snapshots saved warm) and the V and P tiers.  One sandbox, at
# most 100 minutes (about 1.27 USD).
cd /Users/ngchenmeng/ai-research/osworld-testing
export MODAL_SANDBOX_TIMEOUT=6000
caffeinate -i OSWorld/.venv/bin/python -I -u rig/collect_pilot.py --spots rig/clickspots_vscode_check.json \
  --out rig/out/vscode_check --rows ags-vscheck-02,ags-vscheck-04,ags-vscheck-05 \
  --row-minutes 25 --budget 55 --blind 40 --max-usd 1.3 --yes --vm-snapshots
