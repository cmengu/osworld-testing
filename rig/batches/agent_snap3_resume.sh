#!/bin/zsh
# 30 Oct 14:3x: resume labelling of agent_snap3 in its kept sandbox after the collector turned snapshots off on one
# slow save (rig/vmsnap.py now waits as long as a job may take; one failed save no longer ends snapshots).  Then again at 16:3x for step 05 (a DNS outage errored it) and the rest; rows 05, 07-09, was 02 and
# 05-09; the sandbox is ended at the end whatever happens.
cd /Users/ngchenmeng/ai-research/osworld-testing
base=$PWD; sid=sb-k5PZr2neFzQ8yhZvcjRntF
OSWORLD_MODAL_SANDBOX_ID=$sid MODAL_SANDBOX_TIMEOUT=18000 caffeinate -i OSWorld/.venv/bin/python -I -u rig/collect_pilot.py \
  --spots $base/rig/clickspots_agent_snap3.json --out $base/rig/out/agent_snap3_label \
  --rows ags3-change_permissions-05,ags3-change_permissions-07,ags3-change_permissions-08,ags3-change_permissions-09 \
  --row-minutes 25 --budget 55 --blind 40 --max-usd 6.5 --yes --vm-snapshots --end-sandbox
echo "[orchestrator] ending sandbox $sid (safety) $(date)"
OSWorld/.venv/bin/python -I -c "import modal,sys; modal.Sandbox.from_id(sys.argv[1]).terminate(); print('terminated')" $sid
echo "[orchestrator] done $(date)"
