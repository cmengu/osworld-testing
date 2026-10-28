"""Turn recorded agent trajectories into rig rows (28 Oct 2026; see README.md beside this file).

Step n of a trajectory becomes one row: the setup replays the agent's steps 1..n-1 from the task's fresh start, one
VM call per step with a pause between them, and the action is step n.  The collector then records S and S', runs the
usual undo search and labels the step.  A replay that does not reproduce the agent's screen shows up in the
collector's own reset check ("after-state not reproduced"), so a nondeterministic step is flagged, not mislabelled.

Only steps that can change something become rows: typing, key presses and clicks.  Pure waits, scrolls, mouse
moves, screenshots and DONE/FAIL are replayed in the setup but not labelled.  on_task is left None: it is the
author's judgement per step (the paper's rule: set from the task, released for audit) and is filled in at review.

These rows are TEST ONLY (OS-Harm canary).  The export must never see them in a training directory.

    OSWorld/.venv/bin/python -I rig/agentrun/make_rows_agent.py rig/out/agent_a rig/out/agent_b ... \
        --out rig/clickspots_agent.json [--max-per-task 10]
"""
import argparse
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
BASE = HERE.parent.parent
TASKS = HERE / "tasks" / "examples"

# a step "can change something" if it types, presses or clicks; moves, scrolls and waits cannot change files or
# confirm a dialog on their own
CHANGING = re.compile(r"pyautogui\.(typewrite|write|press|hotkey|keyDown|click|doubleClick|tripleClick|rightClick|mouseDown|dragTo)\b")
NON_CODE = {"WAIT", "DONE", "FAIL"}


def load_traj(d: pathlib.Path):
    steps = []
    for line in (d / "traj.jsonl").read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if "action" not in r:
            continue
        steps.append(r)
    return steps


def code_of(action) -> str:
    if isinstance(action, dict):
        action = action.get("command") or action.get("action") or ""
    return str(action or "").strip()


def replay(codes):
    """The agent's earlier steps as a list, one VM call each (the collector pauses 3 s between them).  A WAIT becomes
    a 3 s sleep; DONE and FAIL are dropped."""
    out = []
    for c in codes:
        if c == "WAIT":
            out.append("import time; time.sleep(3)")
        elif c not in NON_CODE:
            out.append(c)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("result_dirs", nargs="+", help="rig/out/agent_<x> directories written by run_agent.sh")
    ap.add_argument("--out", default=str(BASE / "rig" / "clickspots_agent.json"))
    ap.add_argument("--max-per-task", type=int, default=0, help="label at most this many changing steps per task (0: all)")
    a = ap.parse_args()
    rows, seen = [], set()
    for rd in a.result_dirs:
        for traj in sorted(pathlib.Path(rd).resolve().glob("*/*/*/*/*/traj.jsonl")):
            d = traj.parent
            domain, task_id = d.parent.name, d.name
            task = json.loads((TASKS / domain / f"{task_id}.json").read_text())
            steps = load_traj(d)
            codes = [code_of(s["action"]) for s in steps]
            picked = [i for i, c in enumerate(codes) if c not in NON_CODE and CHANGING.search(c)]
            if a.max_per_task:
                picked = picked[:a.max_per_task]
            for i in picked:
                rid = f"ag-{task_id.strip('_')}-{i + 1:02d}"
                if rid in seen:
                    continue
                seen.add(rid)
                rows.append({
                    "row_id": rid, "probe": f"agent step {i + 1} of {len(steps)} on {task_id}",
                    "spot_id": "agent_step", "task_id": task_id, "app": domain, "workbook": "", "open_path": None,
                    "band": "agent", "on_task": None, "on_task_reason": "to be set by the author at review",
                    "seed": 0, "sequence": f"agent_{task_id}", "step": i + 1, "twin_of": None,
                    "target_cell": None, "target_in_set": None, "target_nonempty": None,
                    "setup": replay(codes[:i]), "code": codes[i], "pause": 2, "prelude": "",
                    "expect_before": "none", "expect": "none", "reopen_cmd": None,
                    "trajectory": [task["instruction"]] + [f"step {j + 1}: {codes[j][:160]}" for j in range(i)],
                    "known_answer": None, "forced_candidates": None, "expect_change": None,
                    "source_traj": str(traj.relative_to(BASE)), "test_only": "OS-Harm canary: never train on this row",
                })
    spots = [{"id": "agent_step", "band": "agent", "desc": "a step a Claude agent proposed on an OS-Harm misbehavior task",
              "setup": "", "code": "", "pause": None, "expect": None, "fp": [], "target": None, "sequence": None,
              "step": None, "twin": None, "shares": None}]
    out = {"meta": {"generated_by": "rig/agentrun/make_rows_agent.py", "test_only": True,
                    "source": "OS-Harm misbehavior tasks (tml-epfl/os-harm @ c0fa95e7), unguarded agent runs"},
           "spots": spots, "rows": rows}
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1, ensure_ascii=False))
    per = {}
    for r in rows:
        per[r["task_id"]] = per.get(r["task_id"], 0) + 1
    print(f"{len(rows)} rows from {len(per)} tasks -> {a.out}")
    for t, n in sorted(per.items()):
        print(f"  {t}: {n}")


if __name__ == "__main__":
    main()
