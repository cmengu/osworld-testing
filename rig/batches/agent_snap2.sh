#!/bin/zsh
# 30 Oct (author: "yep agree", +5 USD): one agent run on change_permissions with a VM snapshot before each step,
# then the same sandbox labelled straight away by the updated rig (warm snapshots, size shortcut, tier V with Ctrl+W
# first, guess B after V, pointer tier not counted in K, QMP reconnect), unchanged steps left out.
# RUN / PREFIX name the result folder and row prefix (first try 13:00 lost its sandbox to a relative --out; rerun as
# RUN=agent_snap3 PREFIX=ags3).  The sandbox's lifetime is 5 h (at most about 3.80 USD; that, not --max-usd, is the real cap); it is ended at the end whatever happens.  TEST ONLY rows (ags2-).
cd /Users/ngchenmeng/ai-research/osworld-testing
base=$PWD
run=${RUN:-agent_snap2}; prefix=${PREFIX:-ags2}
out=rig/out/$run
mkdir -p $out
echo "[orchestrator] agent run starts $(date)"
(cd OSWorld && RIG_RECORD_STATES=1 RIG_SNAPSHOT_STEPS=1 RIG_QEMU_QMP_PORT=7102 CLAUDE_SUB_MODEL=claude-sonnet-5-5 \
  MODAL_SANDBOX_TIMEOUT=18000 caffeinate -i .venv/bin/python -u run.py --provider_name modal --headless --model claude-sub \
  --action_space pyautogui --observation_type screenshot --max_steps 20 --test_config_base_dir $base/rig/agentrun/tasks \
  --test_all_meta_path $base/rig/agentrun/tasks/batch_snap2.json --result_dir $base/$out)
sj=$(find $out -name sandbox.json | head -1)
if [ -z "$sj" ]; then echo "[orchestrator] no sandbox.json: agent run did not keep its sandbox"; exit 1; fi
sid=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['sandbox_id'])" $sj)
echo "[orchestrator] agent run done $(date); sandbox $sid"
OSWorld/.venv/bin/python -I $base/rig/agentrun/make_rows_agent.py $base/$out --prefix $prefix --skip-unchanged --out $base/rig/clickspots_$run.json
rows=$(python3 -c "import json; print(','.join(r['row_id'] for r in json.load(open('$base/rig/clickspots_$run.json'))['rows']))")
echo "[orchestrator] labelling rows: $rows"
if [ -n "$rows" ]; then
  OSWORLD_MODAL_SANDBOX_ID=$sid MODAL_SANDBOX_TIMEOUT=18000 caffeinate -i OSWorld/.venv/bin/python -I -u rig/collect_pilot.py \
    --spots $base/rig/clickspots_$run.json --out $base/rig/out/${run}_label --rows $rows \
    --row-minutes 25 --budget 55 --blind 40 --max-usd 6.5 --yes --vm-snapshots --end-sandbox
fi
echo "[orchestrator] ending sandbox $sid (safety) $(date)"
OSWorld/.venv/bin/python -I -c "import modal,sys; modal.Sandbox.from_id(sys.argv[1]).terminate(); print('terminated')" $sid
echo "[orchestrator] done $(date)"
