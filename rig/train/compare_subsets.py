"""Pooled scores of a Modal run, split by row subset (27 Oct 2026).

The v3 export (data_k3_v3) adds one-way rows, and its task-grouped folds differ from data_k3's, so a pooled number on
the new test sets is not the same test as before.  This script pools the per-row curves of every fold of a run and
reports F1 at 0.5 on (a) all rows, (b) the rows that were already in an older export (like for like with that run),
(c) the rows new to this export.

    OSWorld/.venv/bin/python -I rig/train/compare_subsets.py --run k3_v3pre --old-data rig/train/data_k3
"""
import argparse, glob, json, pathlib

HERE = pathlib.Path(__file__).parent


def f1(pairs, thr=0.5):
    tp = sum(1 for y, p in pairs if y and p >= thr)
    fp = sum(1 for y, p in pairs if not y and p >= thr)
    fn = sum(1 for y, p in pairs if y and p < thr)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    return {"n": len(pairs), "positives": tp + fn, "precision": round(prec, 3), "recall": round(rec, 3),
            "f1": round(2 * prec * rec / (prec + rec), 3) if prec + rec else 0.0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, help="directory under rig/train/runs/modal, e.g. k3_v3pre")
    ap.add_argument("--old-data", default=str(HERE / "data_k3"), help="an older export; its row ids form the 'old' subset")
    ap.add_argument("--json", default="")
    a = ap.parse_args()
    old_ids = {json.loads(l)["row_id"] for l in (pathlib.Path(a.old_data) / "all.jsonl").read_text().splitlines() if l.strip()}
    curves = {"REVERSIBLE": [], "GUARD": []}
    folds = sorted(glob.glob(str(HERE / "runs" / "modal" / a.run / "fold*.json")))
    for f in folds:
        r = json.load(open(f))
        for task in curves:
            curves[task] += [(rid, bool(y), float(p)) for rid, y, p in r["_curves"][task]]
    out = {"run": a.run, "folds": len(folds), "old_data": a.old_data}
    for task, c in curves.items():
        out[task] = {"all": f1([(y, p) for _, y, p in c]),
                     "old rows": f1([(y, p) for rid, y, p in c if rid in old_ids]),
                     "new rows": f1([(y, p) for rid, y, p in c if rid not in old_ids])}
    for task in curves:
        print(f"{task}:")
        for k, v in out[task].items():
            print(f"  {k:9s} n={v['n']:3d} pos={v['positives']:3d}  P={v['precision']:.3f} R={v['recall']:.3f} F1={v['f1']:.3f}")
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
