"""Score the H3 rollback comparison (3 November 2026): for each source (model, claude, ctrlz), how many of the 125
UNDO rows its plan rolled back in the rig, with every failure given a reason.

Failure reasons, per plan:
  no plan            Claude said one-way, or the text is not in the step language (counts as a failure)
  rig's own undo     the plan is the rig's recorded undo, yet it did not match this time: the rig, not the plan
  files differ       a file was left changed: usually the wrong plan
  window differs     files restored, but a window or dialog is left open or closed: plan incomplete, or a dialog
  screen differs     files and windows restored, only the accessibility tree differs: may be the comparison being strict
  unconfirmed        matched once, but the rig could not rebuild the after-state to confirm it: the rig, not the plan
Rows where the 30-minute cap stopped a plan from running are left out too.
Rows the rig could not rebuild (status not ok) are left out for every source alike.  Rows with no Claude guess on
record (all probe rows, v2-0035, v2-0078) are left out of the comparison: an absent guess is not a one-way claim
(fixed 3 November 23:55; the first tables counted them as Claude failures).

    /usr/bin/python3 -I rig/undo_eval_score.py      # -> rig/out/undo_eval/h3_score.json and .md
"""
import collections
import glob
import json
import math
import pathlib

BASE = pathlib.Path(__file__).resolve().parent.parent
EV = BASE / "rig" / "out" / "undo_eval"
SRC = ("model", "claude", "ctrlz")


def reason(p, rig_undo):
    if p.get("result") == "not run":
        return "not run"
    if not p.get("executed"):
        return "no plan"
    if p.get("match"):
        return "ok"
    if [s.strip() for s in (p.get("parsed") or [])] == rig_undo:
        return "rig's own undo"
    r = p.get("result") or ""
    if "not confirmed" in r:
        return "unconfirmed"
    if "files differ" in r:
        return "files differ"
    if "windows differ" in r:
        return "window differs"
    if "state differs" in r:
        return "screen differs"
    return "other: " + r[:60]


def main():
    target = {}
    for l in open(BASE / "rig/train/data_k3_v3/all.jsonl"):
        d = json.loads(l)
        if d["task"] == "UNDO":
            target[d["row_id"]] = [s.strip() for s in d["target"].split(";")]
    rec = {}
    for f in sorted(glob.glob(str(BASE / "rig/out/h3*/results.jsonl"))):
        for l in open(f):
            r = json.loads(l) if l.strip() else {}
            if r.get("row_id") in target and (r.get("status") == "ok" or r["row_id"] not in rec):
                rec[r["row_id"]] = r
    how = {}
    for f in glob.glob(str(EV / "plans_h3_*.json")):
        for rid, ps in json.loads(pathlib.Path(f).read_text()).items():
            how[rid] = next((p.get("how") for p in ps if p["source"] == "claude"), None)
    rows, skipped = {}, {}
    for rid in sorted(target):
        r = rec.get(rid)
        if how.get(rid) == "no guess":
            skipped[rid] = "no Claude guess on record"
            continue
        if not r or r.get("status") != "ok" or not r.get("plans"):
            skipped[rid] = (r or {}).get("status", "not run")
            continue
        v = {p["source"]: reason(p, target[rid]) for p in r["plans"]}
        if "not run" in v.values():
            skipped[rid] = "row time cap reached before every plan ran"
            continue
        rows[rid] = v
    n = len(rows)
    out = {"scored": n, "left_out": skipped, "rows": rows, "by_source": {}}
    md = [f"# H3 rollback comparison ({n} of {len(target)} rows scored)", "",
          "| Source | Rolled back | " + " | ".join(("no plan", "rig's own undo", "unconfirmed", "files differ", "window differs", "screen differs")) + " |",
          "|---|---|---|---|---|---|---|---|"]
    for s in SRC:
        c = collections.Counter(v[s] for v in rows.values())
        out["by_source"][s] = dict(c)
        md.append(f"| {s} | {c['ok']} of {n} ({100 * c['ok'] / max(n, 1):.0f}%) | " +
                  " | ".join(str(c[k]) for k in ("no plan", "rig's own undo", "unconfirmed", "files differ", "window differs", "screen differs")) + " |")
    mo = sum(v["model"] == "ok" and v["claude"] != "ok" for v in rows.values())
    cl = sum(v["claude"] == "ok" and v["model"] != "ok" for v in rows.values())
    m, k = mo + cl, min(mo, cl)
    p = min(1.0, 2 * sum(math.comb(m, i) for i in range(k + 1)) / 2 ** m) if m else 1.0
    none = [r for r, v in rows.items() if all(v[s] != "ok" for s in SRC)]
    out.update(model_only=mo, claude_only=cl, sign_test_p=p, none_of_three=none)
    md += ["", f"Model only {mo}, Claude only {cl}, both {sum(v['model'] == 'ok' and v['claude'] == 'ok' for v in rows.values())}, "
           f"neither {sum(v['model'] != 'ok' and v['claude'] != 'ok' for v in rows.values())}; sign test p = {p:.2f}.",
           f"No source rolled back {len(none)} rows. Left out (rig could not rebuild the after-state, or the row cap stopped a plan; includes rows still running): {len(skipped)} {sorted(skipped)}."]
    comb = sum((v["claude"] if v["claude"] != "no plan" else v["model"]) == "ok" for v in rows.values())
    either = sum(v["claude"] == "ok" or v["model"] == "ok" for v in rows.values())
    out.update(claude_else_model=comb, model_or_claude=either)
    md += [f"Claude's plan when it gives one, else the model's: {comb} of {n} ({100 * comb / max(n, 1):.0f}%). "
           f"Either one works (upper bound of any mix): {either} of {n} ({100 * either / max(n, 1):.0f}%)."]
    by_app = collections.defaultdict(lambda: collections.Counter())
    for rid, v in rows.items():
        a = rec[rid].get("app") or "?"
        by_app[a]["n"] += 1
        for s in SRC:
            by_app[a][s] += v[s] == "ok"
    md += ["", "| App | Rows | Model | Claude | Ctrl+Z |", "|---|---|---|---|---|"]
    md += [f"| {a} | {c['n']} | {c['model']} | {c['claude']} | {c['ctrlz']} |" for a, c in sorted(by_app.items(), key=lambda x: -x[1]["n"])]
    (EV / "h3_score.json").write_text(json.dumps(out, indent=1))
    (EV / "h3_score.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
