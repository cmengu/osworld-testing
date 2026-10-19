#!/bin/zsh
# Start the pilot collector in a detached tmux session so it survives a closed terminal or a dropped SSH/Claude
# session, and under caffeinate so the Mac does not sleep mid-run.  The cloud side is guarded separately: the
# collector bounds every fetch and restarts the sandbox when a step passes its 15-minute watchdog.
#
#   rig/run_in_tmux.sh pilot2 --rows 1-10 --row-minutes 45 --yes     # start
#   tmux attach -t pilot2                                             # watch (detach: ctrl+b then d)
#   tail -f rig/out/pilot2.log                                        # or just read the log
#   pkill -INT -f rig/collect_pilot.py                                # stop: the sandbox closes in a finally.  Not Ctrl+C in the
#                                                                     # pane or kill-session: they also kill tee, and the finally
#                                                                     # died on the broken pipe (19 Oct, orphan sandbox).  Then
#                                                                     # check `modal container list`.
set -eu
name="${1:?usage: rig/run_in_tmux.sh <session-name> <collector args...>}"
shift
cd "$(dirname "$0")/.."
if tmux has-session -t "$name" 2>/dev/null; then
  echo "tmux session '$name' already exists; attach with: tmux attach -t $name" >&2
  exit 1
fi
log="rig/out/${name}.log"
args=""
for a in "$@"; do args+=" ${(q)a}"; done
cmd="caffeinate -i OSWorld/.venv/bin/python -I -u rig/collect_pilot.py${args} 2>&1 | tee -a ${(q)log}"
tmux new-session -d -s "$name" "$cmd; echo; echo '[collector exited]'; sleep 86400"
echo "started tmux session '$name'; log: $log"
echo "watch: tmux attach -t $name    stop: pkill -INT -f rig/collect_pilot.py, then modal container list"
