"""Re-ask guess B on rows already collected, with the current prompt (19 Oct 2026: the step-language answer format).

Same inputs the collector gave it (task instruction, the recorded before-state text, the trajectory, the action), so
the only change is the prompt.  For each row: the old and new answer, whether the new undo parses in the step
language, and whether it equals the undo the checker executed.  No VM: whether a new undo actually works is
measured by the collector's zero-shot field on the next run.

    OSWorld/.venv/bin/python -I rig/reask_guess_b.py --runs rig/out/pilot_run2 rig/out/pilot_rerun --out rig/out/reask_b
"""
import argparse
import json
import pathlib
import sys
from concurrent.futures import ThreadPoolExecutor

HERE = pathlib.Path(__file__).resolve().parent
BASE = HERE.parent
sys.path.insert(0, str(BASE))

from rig import teacher, undo as U   # noqa: E402

TASK_DIR = BASE / "OSWorld" / "evaluation_examples" / "examples" / "libreoffice_calc"


def load(runs):
    rows = {}
    for run in runs:
        for line in (pathlib.Path(run) / "results.jsonl").read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                if r.get("status") == "ok":
                    rows[r["row_id"]] = r
    return [rows[k] for k in sorted(rows)]


def ask(r, spots):
    task = json.loads((TASK_DIR / f"{r['task_id']}.json").read_text())
    setup = (r.get("action") or {}).get("setup") or ""
    trajectory = ["Ctrl+Home (cursor to A1)"] + ([f"setup keys: {setup}"] if setup else [])
    desc = spots[r["spot_id"]]["desc"]
    new = teacher.guess_b(task["instruction"], r["state_before_compact"], trajectory, desc, r["action"]["code"])
    old = r.get("guessed_label_defined") or {}
    cand, how = U.guess_parse(new.get("shortest_undo"))
    executed = r.get("shortest_undo")
    return {"row_id": r["row_id"], "spot_id": r["spot_id"], "executed_label": r.get("executed_label"),
            "executed_undo": executed, "old": {k: old.get(k) for k in ("reversible", "shortest_undo", "length")},
            "old_parse": U.guess_parse(old.get("shortest_undo"))[1],
            "new": {k: new.get(k) for k in ("reversible", "shortest_undo", "length", "confidence", "reason", "model", "prompt_sha256")},
            "new_parse": how, "new_candidate": cand,
            "same_as_executed": bool(cand is not None and executed is not None and cand == executed),
            "call": new.get("call")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--out", default=str(HERE / "out" / "reask_b"))
    ap.add_argument("--spots", default=str(HERE / "clickspots_pilot.json"))
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()
    spots = {s["id"]: s for s in json.load(open(args.spots))["spots"]}
    rows = load(args.runs)
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    done = set()
    res_path = out / "results.jsonl"
    if res_path.exists():
        done = {json.loads(l)["row_id"] for l in res_path.read_text().splitlines() if l.strip()}
    todo = [r for r in rows if r["row_id"] not in done]
    print(f"{len(todo)} rows to ask ({len(done)} done)", flush=True)
    with ThreadPoolExecutor(args.workers) as ex, res_path.open("a") as fh:
        for rec in ex.map(lambda r: ask(r, spots), todo):
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()
            print(rec["row_id"], rec["executed_label"], "new:", rec["new"]["reversible"], rec["new_parse"], rec["new_candidate"], flush=True)
    recs = [json.loads(l) for l in res_path.read_text().splitlines() if l.strip()]
    from collections import Counter
    print("old parse:", dict(Counter(r["old_parse"] for r in recs)))
    print("new parse:", dict(Counter(r["new_parse"] for r in recs)))
    print("new label agrees with executed:", sum(1 for r in recs if (r["new"]["reversible"] is True) == (r["executed_label"] == "REVERSIBLE")), "/", len(recs))
    print("new undo identical to executed undo:", sum(r["same_as_executed"] for r in recs))


if __name__ == "__main__":
    main()
