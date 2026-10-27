"""Model vs zero-shot teacher on identical rows.

The teacher's guesses (guess A = SafePred prompt, guess B = definition-matched) were recorded by the collector at
run time; the probe run and some reruns ran with --no-teacher, so a fold's teacher baseline covers only part of its
rows.  For every row the earliest recorded guess (any results directory) is used, since the guess only sees the
before-state, the task and the action.  Rows without any guess are reported, and the model is scored on the covered
subset as well as on the whole fold, so the two are compared on the same rows.

    OSWorld/.venv/bin/python -I rig/train/compare_teacher.py --folds 0 1 2 3 4 [--k 3] [--tag ""]
"""
import argparse
import json
import pathlib
import statistics

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent / "out"
DIRS = ("pilot_run2 pilot150_a pilot150_b pilot150_c probe_run v2_a v2_b v2_c rv_a rv_b rv_c rx_a gd_a gd_b gd_c cf_a cf_b cf_c cf_f cf_g "
        "s3_a s3_c c3_a c3_b c3_c c3_d c3_e c3_f r3_a r3_b r3_c r3_d r3_e r3_f r4_a r4_b r4_c r4_d r4_e r4_f r5_a r5_b r5_c").split()   # s3_b out (wrong VS Code dialog code)


def prf(pairs):
    tp = sum(1 for t, p in pairs if t and p)
    fp = sum(1 for t, p in pairs if not t and p)
    fn = sum(1 for t, p in pairs if t and not p)
    tn = sum(1 for t, p in pairs if not t and not p)
    n = len(pairs)
    pr = tp / (tp + fp) if tp + fp else 0.0
    rc = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * pr * rc / (pr + rc) if pr + rc else 0.0
    return {"n": n, "positives": tp + fn, "accuracy": round((tp + tn) / n, 3) if n else None,
            "precision": round(pr, 3), "recall": round(rc, 3), "f1": round(f1, 3)}


def guesses():
    """row_id -> {"A": bool|None, "B": bool|None}; the earliest recorded guess wins."""
    out = {}
    for d in DIRS:
        p = OUT / d / "results.jsonl"
        if not p.exists():
            continue
        for line in p.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("status") != "ok":
                continue
            g = out.setdefault(r["row_id"], {"A": None, "B": None})
            for key, field in (("A", "guessed_label_verbatim"), ("B", "guessed_label_defined")):
                v = (r.get(field) or {}).get("reversible")
                if g[key] is None and v is not None:
                    g[key] = bool(v)
    return out


def fold_report(fold, k, tag, G, data=""):
    test = [json.loads(l) for l in (HERE / f"data_k{k}{data}" / f"fold{fold}_test.jsonl").read_text().splitlines() if l.strip()]
    mpath = HERE / "runs" / "modal" / f"k{k}{tag}" / f"fold{fold}.json"
    model = json.load(mpath.open()) if mpath.exists() else None
    rows = {}
    for ln in test:
        if ln["task"] in ("REVERSIBLE", "GUARD"):
            rows.setdefault(ln["row_id"], {})[ln["task"]] = ln
    covered = {rid for rid in rows if G.get(rid, {}).get("B") is not None or G.get(rid, {}).get("A") is not None}
    missing = sorted(set(rows) - covered)
    rep = {"fold": fold, "rows": len(rows), "covered": len(covered), "missing": missing, "teacher": {}, "model": {}}
    for which in ("A", "B"):
        rev, grd = [], []
        for rid in sorted(covered):
            g = G[rid].get(which)
            if g is None:
                continue
            r = rows[rid]
            if "REVERSIBLE" in r:
                rev.append((r["REVERSIBLE"]["target"].startswith("yes"), g))
            if "GUARD" in r:
                grd.append((r["GUARD"]["target"] == "refuse", (not g) and not r["GUARD"].get("on_task")))
        rep["teacher"][which] = {"REVERSIBLE": prf(rev), "GUARD": prf(grd)}
    if model:
        for subset, ids in (("all", set(rows)), ("covered", covered)):
            s = {}
            for task in ("REVERSIBLE", "GUARD"):
                pairs = [(bool(t), p >= 0.5) for rid, t, p in model["_curves"][task] if rid in ids]
                s[task] = prf(pairs)
            rep["model"][subset] = s
        rep["model"]["reported"] = {t: model[t] for t in ("REVERSIBLE", "GUARD", "UNDO")}
    return rep


def fmt(s):
    return f"{s['precision']:.3f}/{s['recall']:.3f}/{s['f1']:.3f} (n={s['n']})" if s else "-"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folds", nargs="+", type=int, default=[0, 1, 2, 3, 4])
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--tag", default="")
    ap.add_argument("--data", default="", help="export suffix: '' for data_k{k}, '_v3' for data_k{k}_v3")
    ap.add_argument("--json", default="")
    args = ap.parse_args()
    G = guesses()
    reps = [fold_report(f, args.k, args.tag, G, args.data) for f in args.folds]
    print("| Fold | Rows | With teacher guess | Model REV P/R/F1 (all) | Model REV (covered) | Teacher A REV | Teacher B REV | Model GUARD (all) | Model GUARD (covered) | Teacher A GUARD | Teacher B GUARD | Model UNDO EM |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in reps:
        m = r["model"]
        print(f"| {r['fold']} | {r['rows']} | {r['covered']} | {fmt(m.get('all', {}).get('REVERSIBLE'))} | {fmt(m.get('covered', {}).get('REVERSIBLE'))} | "
              f"{fmt(r['teacher']['A']['REVERSIBLE'])} | {fmt(r['teacher']['B']['REVERSIBLE'])} | {fmt(m.get('all', {}).get('GUARD'))} | "
              f"{fmt(m.get('covered', {}).get('GUARD'))} | {fmt(r['teacher']['A']['GUARD'])} | {fmt(r['teacher']['B']['GUARD'])} | "
              f"{m['reported']['UNDO']['exact_match']:.2f} (n={m['reported']['UNDO']['n']})" if m else "| - |")
    done = [r for r in reps if r["model"]]
    if len(done) > 1:
        print()
        for task in ("REVERSIBLE", "GUARD"):
            for who, pick in (("model (all rows)", lambda r: r["model"]["all"][task]["f1"]),
                              ("model (covered rows)", lambda r: r["model"]["covered"][task]["f1"]),
                              ("teacher A", lambda r: r["teacher"]["A"][task]["f1"]),
                              ("teacher B", lambda r: r["teacher"]["B"][task]["f1"])):
                xs = [pick(r) for r in done]
                print(f"{task} F1 {who}: mean {statistics.mean(xs):.3f} sd {statistics.pstdev(xs):.3f} over {len(xs)} folds")
        xs = [r["model"]["reported"]["UNDO"]["exact_match"] for r in done]
        print(f"UNDO exact match: mean {statistics.mean(xs):.3f} sd {statistics.pstdev(xs):.3f}")
    for r in reps:
        if r["missing"]:
            print(f"\nfold {r['fold']} rows without a teacher guess ({len(r['missing'])}): {', '.join(r['missing'])}")
    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(reps, indent=1))


if __name__ == "__main__":
    main()
