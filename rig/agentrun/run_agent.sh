#!/bin/zsh
# One batch of the unguarded agent run, in a detached tmux session, under caffeinate (see README.md).
# RIG_RECORD_STATES=1 rig/agentrun/run_agent.sh vs1   records the rig state at every step (OSWorld/lib_run_single.py, 29 Oct).
# RIG_RECORD_STATES=1 RIG_SNAPSHOT_STEPS=1 rig/agentrun/run_agent.sh x   also a QEMU snapshot before each step, and each
#   task's sandbox left running for the rig to label from (rig/vmsnap.py; end it with collect_pilot.py --end-sandbox).
set -eu
b="${1:?usage: rig/agentrun/run_agent.sh <batch letter>}"
cd "$(dirname "$0")/../.."
base="$PWD"
out="$base/rig/out/agent_$b"; mkdir -p "$out"
qmp=""; [ "${RIG_SNAPSHOT_STEPS:-0}" = 1 ] && qmp="RIG_QEMU_QMP_PORT=7102"
cmd="cd $base/OSWorld && RIG_GUARD=${RIG_GUARD:-} RIG_GUARD_BACKUP=${RIG_GUARD_BACKUP:-0} RIG_RECORD_STATES=${RIG_RECORD_STATES:-0} RIG_SNAPSHOT_STEPS=${RIG_SNAPSHOT_STEPS:-0} \
 $qmp CLAUDE_SUB_MODEL=${CLAUDE_SUB_MODEL:-claude-sonnet-5-5} MODAL_SANDBOX_TIMEOUT=${MODAL_SANDBOX_TIMEOUT:-10800} caffeinate -i .venv/bin/python -u run.py \
 --provider_name modal --headless --model claude-sub --action_space pyautogui --observation_type screenshot \
 --max_steps 20 --test_config_base_dir $base/rig/agentrun/tasks --test_all_meta_path $base/rig/agentrun/tasks/batch_$b.json \
 --result_dir $out 2>&1 | tee -a $base/rig/out/agent_$b.log"
tmux new-session -d -s "ag$b" "$cmd; echo; echo '[agent run exited]'; sleep 86400"
echo "started tmux session ag$b; log rig/out/agent_$b.log"
