#!/bin/zsh
# One batch of the unguarded agent run, in a detached tmux session, under caffeinate (see README.md).
set -eu
b="${1:?usage: rig/agentrun/run_agent.sh <batch letter>}"
cd "$(dirname "$0")/../.."
base="$PWD"
out="$base/rig/out/agent_$b"; mkdir -p "$out"
cmd="cd $base/OSWorld && CLAUDE_SUB_MODEL=claude-sonnet-5-5 MODAL_SANDBOX_TIMEOUT=10800 caffeinate -i .venv/bin/python -u run.py \
 --provider_name modal --headless --model claude-sub --action_space pyautogui --observation_type screenshot \
 --max_steps 20 --test_config_base_dir $base/rig/agentrun/tasks --test_all_meta_path $base/rig/agentrun/tasks/batch_$b.json \
 --result_dir $out 2>&1 | tee -a $base/rig/out/agent_$b.log"
tmux new-session -d -s "ag$b" "$cmd; echo; echo '[agent run exited]'; sleep 86400"
echo "started tmux session ag$b; log rig/out/agent_$b.log"
