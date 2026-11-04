"""Score a retrained model's undo plans on the H3 rows (4 November 2026, author's go: "go ahead with all three").

The H3 run of 3-4 Nov executed three plans per row (old model, Claude, Ctrl+Z).  A new plan identical to one of those
is scored from that execution, at no cost.  The rest are written to plans_h3new_<src>.json for a --plans-only run
(source "model_v5"), and scored from that run's records once it exists (rig/out/n5_*).

    /usr/bin/python3 -I rig/undo_eval_new.py rig/out/undo_eval/model_plans_v5.json
"""
import collections
import glob
import json
import pathlib
import sys

BASE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from rig import undo as U  # noqa: E402

EV = BASE / "rig" / "out" / "undo_eval"


def norm(steps):
    return [s.strip() for s in steps if s.strip()]


def main(plans_path):
    new = json.loads(pathlib.Path(plans_path).read_text())["rows"]
    score = json.loads((EV / "h3_score.json").read_text())["rows"]           # the 107 rows scored in the H3 run
    rec = {}
    for f in glob.glob(str(BASE / "rig/out/h3*/results.jsonl")):
        if "/n5_" in f:
            continue
        for l in open(f):
            r = json.loads(l)
            if r.get("status") == "ok" and r.get("plans"):
                rec[r["row_id"]] = r
    reruns = {}
    for f in glob.glob(str(BASE / "rig/out/n5_*/results.jsonl")):
        for l in open(f):
            r = json.loads(l)
            if r.get("status") == "ok" and r.get("plans"):
                reruns[r["row_id"]] = next(p for p in r["plans"] if p["source"] == "model_v5")
    res, todo = {}, collections.defaultdict(dict)
    for rid in score:
        steps = norm(new[rid]["text"].split(";")) if rid in new else None
        if not steps:
            res[rid] = "no plan"
            continue
        if not U.parse_steps(steps):
            res[rid] = "no plan"
            continue
        known = {tuple(norm(p.get("parsed") or [])): p.get("match") for p in rec[rid]["plans"] if p.get("executed")}
        if tuple(steps) in known:
            res[rid] = "ok" if known[tuple(steps)] else "fail (same plan as before)"
        elif rid in reruns:
            res[rid] = "ok" if reruns[rid].get("match") else "fail: " + (reruns[rid].get("result") or "")[:40]
        else:
            res[rid] = "needs a run"
            todo[rid.split("-")[0]][rid] = [{"source": "model_v5", "steps": steps}]
    for src, d in todo.items():
        (EV / f"plans_h3new_{src}.json").write_text(json.dumps(d, indent=1))
    n = len(score)
    old = sum(v["model"] == "ok" for v in score.values())
    cl = sum(v["claude"] == "ok" for v in score.values())
    c = collections.Counter("ok" if v == "ok" else "needs a run" if v == "needs a run" else "fail" for v in res.values())
    print(f"{n} H3 rows: old model {old}, Claude {cl}; new model ok {c['ok']}, fail {c['fail']}, still to run {c['needs a run']}")
    print("rows to run per source:", {k: len(v) for k, v in todo.items()})
    out = {"rows": res, "old_model_ok": old, "claude_ok": cl, "new_ok": c["ok"], "new_fail": c["fail"], "to_run": c["needs a run"]}
    (EV / "h3_new_score.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
