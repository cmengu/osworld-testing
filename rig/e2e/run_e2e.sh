#!/bin/zsh
# One batch of the e2e pilot (rig/e2e/runner.py) in a detached tmux session under caffeinate.
#   rig/e2e/run_e2e.sh 1      -> tasks/batch_e2e1.json, results rig/out/e2e_1, log rig/out/e2e_1.log
set -eu
b="${1:?usage: rig/e2e/run_e2e.sh <batch number>}"
cd "$(dirname "$0")/../.."
base="$PWD"
out="$base/rig/out/e2e_$b"; mkdir -p "$out"
cmd="cd $base/OSWorld && RIG_E2E=1 RIG_E2E_BRANCH=${RIG_E2E_BRANCH:-1} RIG_QEMU_QMP_PORT=7102 RIG_SYSTEM_COMPARE=1 \
 CLAUDE_SUB_MODEL=${CLAUDE_SUB_MODEL:-claude-sonnet-5-5} MODAL_SANDBOX_TIMEOUT=${MODAL_SANDBOX_TIMEOUT:-10800} caffeinate -is .venv/bin/python -u run.py \
 --provider_name modal --headless --model claude-sub --action_space pyautogui --observation_type screenshot \
 --max_steps ${E2E_MAX_STEPS:-25} --test_config_base_dir $base/rig/agentrun/tasks --test_all_meta_path $base/rig/agentrun/tasks/batch_e2e$b.json \
 --result_dir $out 2>&1 | tee -a $base/rig/out/e2e_$b.log"
tmux new-session -d -s "e2e$b" "$cmd; echo; echo '[e2e run exited]'; sleep 86400"
echo "started tmux session e2e$b; log rig/out/e2e_$b.log"
