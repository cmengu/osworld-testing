"""Score the FORWARD job (6 Nov 2026): is Model-E's predicted change right?  Offline, against the rig's recorded change
(the FORWARD target: a sample of the tree diff plus every file diff).

Both texts are parsed into EFFECTS, the level a guard and an undo need:
  files    set of (path, created | deleted | modified), LibreOffice lock files (.~lock.*) left out (not state)
  windows  set of (role, name, opened | closed) for application, frame, dialog, alert and window nodes
  content  did a document's content change (any non-node attribute, or a cell, paragraph or text node)?
  none     no change at all (no tree difference, no file change)
Scores: per-effect precision, recall and F1 (micro, over all rows), row-level accuracy for content and none, and
row-level exact match of the whole effect set.

Then the SYMBOLIC DECISION test: a one-line rule over effects, "not reversible if a file is deleted or modified on
disk", is applied to (a) the recorded effects (the rule's ceiling) and (b) the predicted effects, and compared with
the REVERSIBLE label and with the model's own REVERSIBLE head on the same rows.

    OSWorld/.venv/bin/python -I rig/train/score_forward.py   # -> rig/out/forward/forward_score.json
"""
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent / "out" / "forward"
LINE = re.compile(r"^\s+(?P<path>/\S.*?) :: (?P<attr>[^:]+): (?P<old>.*?) -> (?P<new>.*)$")
SEG = re.compile(r"([a-z-]+)\[(.*?)\]#\d+$")
WIN_ROLES = {"application", "frame", "dialog", "alert", "window", "file-chooser"}
CONTENT_ROLES = {"table-cell", "paragraph", "text", "document-text", "heading", "list-item", "entry"}


def parse(text):
    eff = {"files": set(), "windows": set(), "content": False, "tree_n": None, "parsed": False}
    for ln in (text or "").splitlines():
        if ln.startswith("TREE:"):
            m = re.match(r"TREE:\s*(\d+)", ln)
            if m:
                eff["tree_n"] = int(m.group(1)); eff["parsed"] = True
        elif ln.startswith("FILE:"):
            try:
                d = json.loads(ln[5:])
            except json.JSONDecodeError:
                continue
            eff["parsed"] = True
            p = d.get("path", "")
            if "/.~lock." in p:
                continue
            kind = "created" if d.get("before") == "absent" else "deleted" if d.get("after") == "absent" else "modified"
            eff["files"].add((p, kind))
        elif ln.strip() == "no change":
            eff["parsed"] = True; eff["tree_n"] = 0
        else:
            m = LINE.match(ln)
            if not m:
                continue
            last = m.group("path").rsplit("/", 1)[-1]
            sm = SEG.match(last)
            role, name = (sm.group(1), sm.group(2)) if sm else ("", "")
            if m.group("attr") == "__node__":
                if role in WIN_ROLES:
                    eff["windows"].add((role, name, "opened" if m.group("old") == "None" else "closed"))
                elif role in CONTENT_ROLES:
                    eff["content"] = True
            elif m.group("attr") in ("text", "value", "format"):
                eff["content"] = True
    eff["none"] = (eff["tree_n"] == 0) and not eff["files"]
    return eff


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return {"precision": round(p, 3), "recall": round(r, 3), "f1": round(2 * p * r / (p + r), 3) if p + r else 0.0,
            "true": tp + fn, "predicted": tp + fp}


def destroys(eff):
    return any(k in ("deleted", "modified") for _, k in eff["files"])


def main():
    pred = json.loads((OUT / "model_forward_k3_v5w.json").read_text())["rows"]
    res = {"rows": len(pred), "unparsed_predictions": 0, "hit_max_tokens": sum(v.get("hit_max", False) for v in pred.values())}
    cnt = {"files": [0, 0, 0], "windows": [0, 0, 0]}
    acc = {"content": 0, "none": 0, "exact_effects": 0, "exact_text": 0, "files_exact": 0}
    per_row = {}
    for rid, v in pred.items():
        t, p = parse(v["target"]), parse(v["text"])
        if not p["parsed"]:
            res["unparsed_predictions"] += 1
        for k in ("files", "windows"):
            cnt[k][0] += len(t[k] & p[k]); cnt[k][1] += len(p[k] - t[k]); cnt[k][2] += len(t[k] - p[k])
        acc["content"] += t["content"] == p["content"]
        acc["none"] += t["none"] == p["none"]
        acc["files_exact"] += t["files"] == p["files"]
        acc["exact_effects"] += (t["files"] == p["files"] and t["windows"] == p["windows"] and t["content"] == p["content"])
        acc["exact_text"] += v["text"].strip() == v["target"].strip()
        per_row[rid] = {"true": {"files": sorted(map(list, t["files"])), "windows": sorted(map(list, t["windows"])), "content": t["content"], "none": t["none"]},
                        "pred": {"files": sorted(map(list, p["files"])), "windows": sorted(map(list, p["windows"])), "content": p["content"], "none": p["none"]}}
    n = len(pred)
    res["files"] = prf(*cnt["files"])
    res["windows"] = prf(*cnt["windows"])
    res["row_accuracy"] = {k: round(v / n, 3) for k, v in acc.items()}
    res["base_rates"] = {"rows_with_file_change": sum(bool(r["true"]["files"]) for r in per_row.values()),
                         "rows_with_content_change": sum(r["true"]["content"] for r in per_row.values()),
                         "rows_no_change": sum(r["true"]["none"] for r in per_row.values())}

    # symbolic decision test on the rows that also have a REVERSIBLE label
    rev_truth, rev_head = {}, {}
    for f in range(5):
        for l in (HERE / "data_k3_v5" / f"fold{f}_test.jsonl").read_text().splitlines():
            d = json.loads(l)
            if d["task"] == "REVERSIBLE":
                rev_truth[d["row_id"]] = d["target"].startswith("yes")
        m = json.loads((HERE / "runs" / "modal" / "k3_v5w" / f"fold{f}.json").read_text())
        for rid, t, p in m["_curves"]["REVERSIBLE"]:
            rev_head[rid] = p >= 0.5
    rows = [r for r in pred if r in rev_truth and r in rev_head]
    def score(fn):
        tp = sum(1 for r in rows if fn(r) and rev_truth[r]); tn = sum(1 for r in rows if not fn(r) and not rev_truth[r])
        return {"accuracy": round((tp + tn) / len(rows), 3), "right": tp + tn, "n": len(rows)}
    T = {rid: parse(pred[rid]["target"]) for rid in rows}
    P = {rid: parse(pred[rid]["text"]) for rid in rows}
    res["symbolic_decision"] = {
        "rule": "not reversible if a file is deleted or modified on disk",
        "rule_on_recorded_effects (ceiling)": score(lambda r: not destroys(T[r])),
        "rule_on_predicted_effects": score(lambda r: not destroys(P[r])),
        "model_REVERSIBLE_head": score(lambda r: rev_head[r]),
        "rows_where_rule_on_recorded_is_wrong": sorted(r for r in rows if (not destroys(T[r])) != rev_truth[r]),
    }
    (OUT / "forward_score.json").write_text(json.dumps({**res, "per_row": per_row}, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
