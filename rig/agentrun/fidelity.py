"""Replay fidelity for agent rows (28 Oct 2026).

Does the rig's replayed before-state S look like the screen the agent saw before that step?  The score is the mean
absolute grayscale difference (0-255) at 192x108 between the rig's S/screenshot.png and the agent's own screenshot
after its previous step.  On the first 22 rows (28 Oct) faithful replays scored at most 13 and diverged ones at least
42; the collector skips a row above DIVERGED (status "replay_diverged") instead of labelling a screen the agent never
saw.  Step 1 has no earlier agent screenshot and is not checked.

    OSWorld/.venv/bin/python -I rig/agentrun/fidelity.py [rig/out/agent_label_*]     # score rows on disk
"""
import glob
import json
import pathlib
import sys

from PIL import Image

BASE = pathlib.Path(__file__).resolve().parent.parent.parent
DIVERGED = 25.0


def agent_before_shot(row):
    """The agent's screenshot before this row's step, or None (step 1, or no file)."""
    traj = BASE / row["source_traj"]
    lines = [json.loads(l) for l in traj.read_text().splitlines() if l.strip()]
    lines = [l for l in lines if "action" in l]
    i = row["step"] - 1
    if i <= 0:
        return None
    prev = lines[i - 1]
    shot = traj.parent / (prev.get("screenshot_file") or "")
    if shot.is_file():
        return shot
    cands = sorted(traj.parent.glob(f"step_{prev.get('step_num')}_*.png"))
    return cands[0] if cands else None


def screen_diff(a, b) -> float:
    pa = Image.open(a).convert("L").resize((192, 108)).getdata()
    pb = Image.open(b).convert("L").resize((192, 108)).getdata()
    return sum(abs(x - y) for x, y in zip(pa, pb)) / len(pa)


def main():
    rows = {r["row_id"]: r for r in json.load(open(BASE / "rig/clickspots_agent.json"))["rows"]}
    where = sys.argv[1] if len(sys.argv) > 1 else "rig/out/agent_label_*"
    out = []
    for d in sorted(glob.glob(str(BASE / where / "ag-*"))):
        rid = pathlib.Path(d).name
        s = pathlib.Path(d) / "S" / "screenshot.png"
        shot = agent_before_shot(rows[rid]) if s.exists() else None
        if shot:
            out.append((screen_diff(s, shot), rid))
    for v, rid in sorted(out, reverse=True):
        print(f"{v:6.1f}  {rid}{'  DIVERGED' if v > DIVERGED else ''}")


if __name__ == "__main__":
    main()
