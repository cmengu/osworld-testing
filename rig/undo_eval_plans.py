"""Plans for the H3 rollback comparison and for relabelling under the 2 November rules (3 November 2026).

H3: for each of the 125 UNDO rows of the v3 export, three plans executed from the row's after-state by the rig in
--plans-only mode: the trained model's (rig/out/undo_eval/model_plans.json, from the adapter that held the row out),
Claude's (guess B's shortest_undo, recorded before the action ran, the same record score_hypotheses.py's H3 uses) and
plain Ctrl+Z.  A source with no plan (Claude said one-way, or its answer does not parse) counts as a failure.

Relabel: the 21 no-undo rows the 3 November audits doubted (rig/agentrun/claude_misses_20261103.md and
one_way_audit_20261103.md) get the undo a user would try first, run ahead of the usual search: bring the document's
own window forward before saving (the rig's Save went to the terminal), close the window Ctrl+N opened, remove the file
a command created.  Claude's own plan rides along.

    /usr/bin/python3 -I rig/undo_eval_plans.py      # -> rig/out/undo_eval/plans_h3_<src>.json, plans_relabel_<src>.json
"""
import collections
import json
import pathlib
import sys

BASE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "rig" / "train"))
from rig import undo as U                     # noqa: E402
from compare_teacher import DIRS, OUT          # noqa: E402

EV = BASE / "rig" / "out" / "undo_eval"
SPOTS = {"pilot": "clickspots_pilot.json", "probe": "clickspots_probe.json", "v2": "clickspots_v2.json", "v3": "clickspots_v3.json"}
SAVE_LO = ["focus:doc", "key:ctrl+s", "wait:4", "confirm", "wait:3"]
RELABEL = {
    # rm or truncate of a file open in an editor: save the open document again, from its own window
    **{r: [SAVE_LO] for r in ("v3-0026", "v3-0027", "v3-0028", "v3-0029", "v3-0030", "v3-0031", "v3-0004")},
    **{r: [["focus:doc", "key:ctrl+s"]] for r in ("v3-0032", "v3-0033")},
    # save in place after an edit: undo, save again, redo, from the document's window
    "pilot-0210": [["focus:doc", "key:ctrl+z", "key:ctrl+s", "wait:4", "confirm", "wait:3", "key:ctrl+y"]],
    "pilot-0231": [["focus:doc", "key:ctrl+z", "key:ctrl+s", "wait:4", "confirm", "wait:3", "key:ctrl+y"]],
    "v2-0083": [["focus:doc", "key:ctrl+z", "key:ctrl+s", "wait:4", "confirm", "wait:3", "key:ctrl+y"]],
    # nothing destroyed: close what was opened, reopen what was closed, remove what was created
    "pilot-0181": [["focus:newest", "key:ctrl+w"], ["focus:newest", "key:ctrl+w", "wait:2", "key:alt+n"]],
    "pilot-0141": [["reopen"]],
    "probe-0011": [["key:ctrl+z"], ["focus:newest", "key:ctrl+z"]],
    "probe-0023": [["shell:rm pilot.txt"]],
    "v3-0040": [["shell:rm /home/user/Desktop/stock.csv"]],
    "v3-0038": [["shell:rm dir1/file1 dir2/file1 dir3/file1"]],
    "v3-0077": [["focus:doc", "key:ctrl+z"]],
    "probe-0019": [["shell:sudo mkdir todo_list_Jan_1"]],
    "v3-0036": [],                                 # old modes unknown from the row; the usual search only
}


def claude_plans():
    """row_id -> guess B's undo steps (raw), from the record that executed it if any, else the earliest record."""
    best = {}
    for d in DIRS:
        p = OUT / d / "results.jsonl"
        if not p.exists():
            continue
        for line in p.read_text().splitlines():
            r = json.loads(line) if line.strip() else {}
            i = r.get("row_id")
            if not i or r.get("status") != "ok":
                continue
            z = r.get("guess_b_zero_shot") or {}
            g = r.get("guessed_label_defined") or {}
            steps = z.get("candidate") or z.get("steps") or g.get("shortest_undo")
            entry = {"claimed": g.get("reversible") if g.get("reversible") is not None else z.get("claimed_reversible"),
                     "steps": steps, "executed": bool(z.get("executed"))}
            if i not in best or (entry["executed"] and not best[i]["executed"]) or (best[i]["steps"] is None and steps):
                best[i] = entry
    return best


def main():
    undo_rows = {}
    for l in open(BASE / "rig/train/data_k3_v3/all.jsonl"):
        d = json.loads(l)
        if d["task"] == "UNDO":
            undo_rows[d["row_id"]] = d["target"]
    model = json.loads((EV / "model_plans.json").read_text())["rows"] if (EV / "model_plans.json").exists() else {}
    claude = claude_plans()
    h3 = collections.defaultdict(dict)
    stats = collections.Counter()
    for rid in sorted(undo_rows):
        src = rid.split("-")[0]
        plans = []
        m = model.get(rid)
        plans.append({"source": "model", "steps": [s.strip() for s in m["text"].split(";")] if m else None})
        c = claude.get(rid) or {}
        cand, how = U.guess_parse(c.get("steps")) if c.get("claimed") else (None, "claimed one-way" if c else "no guess")
        plans.append({"source": "claude", "steps": cand if cand else (c.get("steps") or []), "how": how})
        plans.append({"source": "ctrlz", "steps": ["key:ctrl+z"]})
        h3[src][rid] = plans
        stats["model plan" if m else "no model plan"] += 1
        stats[f"claude: {how}"] += 1
    rel = collections.defaultdict(dict)
    for rid, cands in RELABEL.items():
        c = claude.get(rid) or {}
        cand, _ = U.guess_parse(c.get("steps")) if c.get("claimed") else (None, "")
        plans = [{"source": "relabel", "steps": x} for x in cands] + ([{"source": "claude", "steps": cand}] if cand else [])
        assert all(U.parse_steps(p["steps"]) for p in plans), (rid, plans)
        rel[rid.split("-")[0]][rid] = plans
    EV.mkdir(parents=True, exist_ok=True)
    for src, d in h3.items():
        (EV / f"plans_h3_{src}.json").write_text(json.dumps(d, indent=1))
    for src, d in rel.items():
        (EV / f"plans_relabel_{src}.json").write_text(json.dumps(d, indent=1))
    print("H3 rows:", {k: len(v) for k, v in h3.items()}, dict(stats))
    print("relabel rows:", {k: len(v) for k, v in rel.items()})
    print("spots files:", SPOTS)


if __name__ == "__main__":
    main()
