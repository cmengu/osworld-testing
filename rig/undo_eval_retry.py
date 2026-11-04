"""Second try for the H3 rows where every source failed for what looks like a rig reason (5 November 2026, author's go:
"yep go ahead with step 1").

On 20 of the 26 rows no source rolled back, the failing plan was the rig's own recorded undo, or only the accessibility
tree differed, or a match did not confirm.  Each distinct plan any source gave on those rows (old model, Claude, Ctrl+Z,
retrained model, and the rig's own undo as a control) runs once more in --plans-only mode, after a 3 s wait so a dialog
that is still coming is up before the first key (waits are not actions).  A source counts as rolling back a row if its
plan matched on either try.

    /usr/bin/python3 -I rig/undo_eval_retry.py build      # -> rig/out/undo_eval/plans_retry_<src>.json
    /usr/bin/python3 -I rig/undo_eval_retry.py score      # after the rt_* run -> rig/out/undo_eval/h3_retry_score.json
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
RIG_SIDE = ("rig's own undo", "unconfirmed", "screen differs")


def load():
    s = json.loads((EV / "h3_score.json").read_text())["rows"]
    n = json.loads((EV / "h3_new_score.json").read_text())["rows"]
    new = json.loads((EV / "model_plans_v5.json").read_text())["rows"]
    tgt = {}
    for l in open(BASE / "rig/train/data_k3_v3/all.jsonl"):
        d = json.loads(l)
        if d["task"] == "UNDO":
            tgt[d["row_id"]] = [x.strip() for x in d["target"].split(";")]
    rec = {}
    for f in glob.glob(str(BASE / "rig/out/h3*/results.jsonl")):
        for l in open(f):
            r = json.loads(l)
            if r.get("status") == "ok" and r.get("plans"):
                rec[r["row_id"]] = r
    return s, n, new, tgt, rec


def norm(x):
    return tuple(t.strip() for t in x if t.strip())


def build():
    s, n, new, tgt, rec = load()
    rows = [r for r in s if r in n and n[r] != "needs a run" and all(x != "ok" for x in (s[r]["model"], s[r]["claude"], n[r]))
            and ({s[r]["model"], s[r]["claude"]} & set(RIG_SIDE))]
    out = collections.defaultdict(dict)
    for rid in rows:
        by_plan = collections.defaultdict(list)
        for p in rec[rid]["plans"]:
            if p.get("executed"):
                by_plan[norm(p["parsed"])].append(p["source"])
        ns = norm(new[rid]["text"].split(";"))
        if U.parse_steps(list(ns)):
            by_plan[ns].append("model_v5")
        by_plan[norm(tgt[rid])].append("rig")
        out[rid.split("-")[0]][rid] = [{"source": "+".join(srcs), "steps": ["wait:3"] + list(plan)} for plan, srcs in by_plan.items()]
    for src, d in out.items():
        (EV / f"plans_retry_{src}.json").write_text(json.dumps(d, indent=1))
    print(len(rows), "rows;", {k: len(v) for k, v in out.items()}, "plans:", sum(len(p) for d in out.values() for p in d.values()))


def score():
    s, n, new, tgt, rec = load()
    retry = {}
    for f in glob.glob(str(BASE / "rig/out/rt_*/results.jsonl")):
        for l in open(f):
            r = json.loads(l)
            if r.get("status") == "ok" and r.get("plans"):
                retry[r["row_id"]] = r["plans"]
    rows = [r for r in s if r in n and n[r] != "needs a run"]
    second = collections.defaultdict(dict)        # row -> source -> matched on the second try
    for rid, plans in retry.items():
        for p in plans:
            for src in p["source"].split("+"):
                second[rid][src] = second[rid].get(src, False) or bool(p.get("match"))
    first = {"old": lambda r: s[r]["model"] == "ok", "claude": lambda r: s[r]["claude"] == "ok",
             "ctrlz": lambda r: s[r]["ctrlz"] == "ok", "new": lambda r: n[r] == "ok"}
    key = {"old": "model", "claude": "claude", "ctrlz": "ctrlz", "new": "model_v5"}
    res = {}
    for src in first:
        res[src] = sum(first[src](r) or second.get(r, {}).get(key[src], False) for r in rows)
    res["any of old, new, claude"] = sum(any(first[k](r) or second.get(r, {}).get(key[k], False) for k in ("old", "new", "claude")) for r in rows)
    res["rig's own undo, second try"] = f"{sum(v.get('rig', False) for v in second.values())} of {len(second)}"
    before = {k: sum(first[k](r) for r in rows) for k in first}
    out = {"rows": len(rows), "first_try": before, "best_of_two": res, "retried_rows": len(retry)}
    (EV / "h3_retry_score.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    {"build": build, "score": score}[sys.argv[1]]()
