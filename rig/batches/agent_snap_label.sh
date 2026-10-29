#!/bin/zsh
# 29 Oct snapshot trial, part B: label the agent's change_permissions steps from the sandbox its run left running
# (sb-YrqKPyZ2q3GyBYGs0sew4J, lifetime to about 03:08), one collector at a time, steps that changed files first.
cd /Users/ngchenmeng/ai-research/osworld-testing
export OSWORLD_MODAL_SANDBOX_ID=sb-YrqKPyZ2q3GyBYGs0sew4J MODAL_SANDBOX_TIMEOUT=14400
C="caffeinate -i OSWorld/.venv/bin/python -I -u rig/collect_pilot.py --spots rig/clickspots_agent_snap.json --out rig/out/agent_snap_label --row-minutes 30 --budget 55 --blind 40 --max-usd 5 --yes --vm-snapshots"
${=C} --rows ags-change_permissions-05,ags-change_permissions-10,ags-change_permissions-11,ags-change_permissions-04
${=C} --rows ags-change_permissions-13,ags-change_permissions-14,ags-change_permissions-15,ags-change_permissions-16,ags-change_permissions-01,ags-change_permissions-02,ags-change_permissions-03
${=C} --rows ags-change_permissions-06,ags-change_permissions-07,ags-change_permissions-08,ags-change_permissions-09,ags-change_permissions-12,ags-change_permissions-17,ags-change_permissions-18,ags-change_permissions-19,ags-change_permissions-20 --end-sandbox
