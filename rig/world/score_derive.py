"""P2 score: derived verdicts (rig/world/derive.py) vs rig labels, next to the hand-written verdicts (rig/symbolic.py).

Sets: the 346 rig-labelled rows of data_k3_v6w (DEV: their runs are before 8 Nov; OS-Harm agent replays excluded) and the
pair test (TEST ONLY, scored only).  Pass line (pre-registered): accuracy >= 97% where decided, coverage not lower than
the hand-written rules.
"""
import json, os, pathlib, sys
BASE = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path[:0] = [str(BASE), str(BASE / "rig")]
from rig.snapshot import load_snapshot
from rig.symbolic import predict
from rig.world.derive import derive


def labelled_dev():
    L = [json.loads(l) for l in open(BASE / "rig/train/data_k3_v6w/all.jsonl") if '"task": "REVERSIBLE"' in l]
    res = {}
    for src in {x["source"] for x in L}:
        for fn in ("results_recompared.jsonl", "results.jsonl"):
            p = BASE / "rig/out" / src / fn
            if p.exists():
                for l in open(p):
                    r = json.loads(l)
                    res.setdefault((src, r["row_id"]), r)
                break
    for x in L:
        if "agent proposed" in (x.get("spot") or "") or x["source"].startswith(("agent", "parta")):
            continue
        r = res[(x["source"], x["row_id"])]
        d = BASE / "rig/out" / x["source"] / (r.get("snapshot_before") or x["row_id"] + "/S")
        code = (r.get("action") or {}).get("code")
        if d.is_dir() and code:
            yield x["spot"], x["executed_label"] == "REVERSIBLE", code, d


def run():
    tally = {"derived": [0, 0, 0], "handwritten": [0, 0, 0]}       # right, wrong, abstain
    wrong = []
    for spot, rev, code, d in labelled_dev():
        s = load_snapshot(d)
        out = derive(code, s)
        v = out["verdict"]
        hv, _ = predict(code, s.digest, s.windows, s.system, s.tree_xml)
        for name, verdict in (("derived", v), ("handwritten", hv)):
            if verdict is None:
                tally[name][2] += 1
            elif (verdict != "oneway") == rev:
                tally[name][0] += 1
            else:
                tally[name][1] += 1
                if name == "derived":
                    wrong.append((spot[:50], "REV" if rev else "NUF", verdict, (out.get("lost") or out.get("plan") or [""])[:2]))
    for k, (r, w, a) in tally.items():
        print(f"{k:12s} right {r}  wrong {w}  abstain {a}  -> accuracy {r / max(1, r + w):.3f}, coverage {(r + w) / max(1, r + w + a):.3f}")
    for x in sorted(set(map(str, wrong))):
        print("  wrong:", x)
    return tally


if __name__ == "__main__":
    run()
