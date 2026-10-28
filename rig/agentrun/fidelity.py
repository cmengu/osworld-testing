"""Replay fidelity for agent rows (28 Oct 2026): run OSWorld/.venv/bin/python -I rig/agentrun/fidelity.py
"""
# For each labelled agent row: does the rig's replayed before-state S look like the screen the agent saw before
# that step?  Mean absolute grayscale difference (0-255) at 192x108 between rig S/screenshot.png and the agent's
# screenshot after its previous step.
import json, glob, pathlib, sys
from PIL import Image
BASE = pathlib.Path('/Users/ngchenmeng/ai-research/osworld-testing')
rows = {r['row_id']: r for r in json.load(open(BASE / 'rig/clickspots_agent.json'))['rows']}
def small(p):
    return Image.open(p).convert('L').resize((192, 108))
def mad(a, b):
    pa, pb = a.getdata(), b.getdata()
    return sum(abs(x - y) for x, y in zip(pa, pb)) / len(pa)
out = []
for d in sorted(glob.glob(str(BASE / (sys.argv[1] if len(sys.argv) > 1 else 'rig/out/agent_label_*') / 'ag-*'))):
    rid = pathlib.Path(d).name
    s = pathlib.Path(d) / 'S' / 'screenshot.png'
    if not s.exists():
        continue
    r = rows[rid]
    traj = BASE / r['source_traj']
    lines = [json.loads(l) for l in traj.read_text().splitlines() if l.strip()]
    lines = [l for l in lines if 'action' in l]
    i = r['step'] - 1                      # index of this step in the trajectory
    if i == 0:
        continue                           # before step 1 is the task's start screen
    prev = lines[i - 1]
    shot = traj.parent / prev.get('screenshot_file', '')
    if not shot.is_file():
        cands = sorted(traj.parent.glob(f"step_{prev.get('step_num')}_*.png"))
        if not cands:
            continue
        shot = cands[0]
    out.append((mad(small(s), small(shot)), rid))
for v, rid in sorted(out, reverse=True):
    print(f"{v:6.1f}  {rid}")
