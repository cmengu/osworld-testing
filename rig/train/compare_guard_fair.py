"""Fair guard comparison (5 Nov 2026): Claude guess B gets the on-task flag from the data, so give the model the same flag:
refuse = model REVERSIBLE head says no (p < 0.5) AND off-task.  Same 269 rows as compare_teacher.py --tag _v5w --data _v5.
    OSWorld/.venv/bin/python -I rig/train/compare_guard_fair.py
"""
import json, sys, pathlib
sys.path.insert(0, "rig/train")
import compare_teacher as C
G = C.guesses(); H = pathlib.Path("rig/train")
pairs = {"model GUARD head": [], "model REV head + on-task flag": [], "Claude B + on-task flag": []}
for f in range(5):
    rows = {}
    for l in (H/"data_k3_v5"/f"fold{f}_test.jsonl").read_text().splitlines():
        d = json.loads(l)
        if d["task"] in ("REVERSIBLE", "GUARD"): rows.setdefault(d["row_id"], {})[d["task"]] = d
    m = json.load(open(H/"runs/modal/k3_v5w"/f"fold{f}.json"))
    rev = {rid: p for rid, t, p in m["_curves"]["REVERSIBLE"]}
    for rid, t, p in m["_curves"]["GUARD"]:
        g = G.get(rid, {}).get("B")
        if g is None or rid not in rev: continue
        on = rows[rid]["GUARD"].get("on_task")
        pairs["model GUARD head"].append((bool(t), p >= .5))
        pairs["model REV head + on-task flag"].append((bool(t), rev[rid] < .5 and not on))
        pairs["Claude B + on-task flag"].append((bool(t), (not g) and not on))
for k, v in pairs.items(): print(k, C.prf(v))
a = pairs["model REV head + on-task flag"]; b = pairs["Claude B + on-task flag"]
print("one-sided model vs Claude:", sum(x[1]==x[0]!=y[1] for x,y in zip(a,b)), sum(y[1]==y[0]!=x[1] for x,y in zip(a,b)))
