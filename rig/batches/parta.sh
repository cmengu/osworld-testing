#!/bin/zsh
# 2 Nov part A: five agent steps replayed under the new rules (looser comparison, Revert File and Ctrl+End candidates,
# settling wait).  Test only.  Two sandboxes; at most 2.5 sandbox-hours, about 1.9 USD, plus at most one retry per row.
cd /Users/ngchenmeng/ai-research/osworld-testing
export MODAL_SANDBOX_TIMEOUT=7200
C="caffeinate -i OSWorld/.venv/bin/python -I -u rig/collect_pilot.py --row-minutes 30 --budget 55 --blind 40 --no-teacher --no-proposer --yes --vm-snapshots"
${=C} --max-usd 2 --spots rig/clickspots_agent_rec.json --out rig/out/parta_rec --rows agr-change_permissions-10,agr-fix_text_search-08 > rig/out/parta_rec.log 2>&1 &
${=C} --max-usd 2 --spots rig/clickspots_agent.json --out rig/out/parta_ag --rows ag-delete_slides_save-01,ag-delete_slides_save-02,ag-delete_slides_save-03 > rig/out/parta_ag.log 2>&1 &
# stop cleanly if the Mac is about to die on battery
while pgrep -f "rig/collect_pilot.py --row-minutes" >/dev/null; do
  b=$(pmset -g batt | grep -o '[0-9]*%' | tr -d %); s=$(pmset -g batt | grep -c discharging)
  if [ "$s" -gt 0 ] && [ "$b" -le 10 ]; then pkill -INT -f "rig/collect_pilot.py --row-minutes"; echo "stopped at ${b}%"; break; fi
  sleep 60
done
wait
echo "part A over"; OSWorld/.venv/bin/modal container list 2>/dev/null | wc -l
