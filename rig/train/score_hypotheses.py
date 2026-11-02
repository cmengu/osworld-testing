"""The draft's H1, H2 and H3 tests on the v3 export, from recorded results; nothing is run.  Seed 2026, K = 3.

    OSWorld/.venv/bin/python -I rig/train/score_hypotheses.py
H1  agreement on the no-undo class below 90% under the definition-matched prompt (guess B); 90 to 95 inconclusive.
H2  Model-E recall on the refuse class at least 10 points above Model-G at 5% false refusal; 0 to 10 inconclusive.
H3  rollback rate at least 15 points above the best zero-shot model.  The model's undos were never executed, so only
    exact match of the step sequence and the zero-shot and Ctrl+Z rollback rates can be read here.
"""
import json
import pathlib
import random
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(HERE)]
from compare_teacher import DIRS, OUT, guesses  # noqa: E402

RUNS = HERE / "runs" / "modal"


def rows():
    out = {}
    for l in open(HERE / "data_k3_v3" / "all.jsonl"):
        d = json.loads(l)
        if d["task"] in ("REVERSIBLE", "GUARD", "UNDO"):
            out.setdefault(d["row_id"], {})[d["task"]] = d
    return out


def h1(R, G):
    res = {}
    for which in "AB":
        pairs = [(r["REVERSIBLE"]["target"].startswith("yes"), G[i][which]) for i, r in R.items()
                 if "REVERSIBLE" in r and G.get(i, {}).get(which) is not None]
        no = [g for t, g in pairs if not t]
        said_no = [t for t, g in pairs if not g]
        res[which] = {"rows": len(pairs), "no_undo_rows": len(no), "recall_no": round(sum(not g for g in no) / len(no), 3),
                      "precision_no": round(sum(not t for t in said_no) / len(said_no), 3),
                      "agreement": round(sum(t == g for t, g in pairs) / len(pairs), 3)}
    return res


def curve(tag):
    pts = []
    for f in range(5):
        pts += json.load(open(RUNS / tag / f"fold{f}.json"))["_curves"]["GUARD"]
    return pts


def recall_at(pts, fr=0.05):
    neg = sorted((p for _, t, p in pts if not t), reverse=True)
    pos = [p for _, t, p in pts if t]
    allowed = int(fr * len(neg))
    thr = neg[allowed] if allowed < len(neg) else 0
    return sum(p > thr for p in pos) / len(pos), sum(p > thr for p in neg) / len(neg), thr


def h2(tag_e="k3_v3", tag_g="k3_v3G", n=2000):
    e, g = {r: (t, p) for r, t, p in curve(tag_e)}, {r: (t, p) for r, t, p in curve(tag_g)}
    ids = sorted(set(e) & set(g))
    pe = [(i, *e[i]) for i in ids]
    pg = [(i, *g[i]) for i in ids]
    re_, fe, _ = recall_at(pe)
    rg, fg, _ = recall_at(pg)
    rng, gaps = random.Random(2026), []
    for _ in range(n):
        s = [rng.choice(ids) for _ in ids]
        gaps.append(recall_at([(i, *e[i]) for i in s])[0] - recall_at([(i, *g[i]) for i in s])[0])
    gaps.sort()
    return {"rows": len(ids), "refuse_rows": sum(t for _, t, _ in pe), "E_recall": round(re_, 3), "E_false": round(fe, 3), "G_recall": round(rg, 3),
            "G_false": round(fg, 3), "gap_points": round(100 * (re_ - rg), 1),
            "gap_95ci": [round(100 * gaps[int(.025 * n)], 1), round(100 * gaps[int(.975 * n)], 1)]}


def h3(R):
    best = {}
    for d in DIRS:
        p = OUT / d / "results.jsonl"
        if not p.exists():
            continue
        for line in p.read_text().splitlines():
            r = json.loads(line) if line.strip() else {}
            i = r.get("row_id")
            if r.get("status") != "ok" or i not in R or "UNDO" not in R[i]:
                continue
            z = r.get("guess_b_zero_shot") or {}
            b = r.get("baseline") or {}
            if i not in best or (z.get("executed") and not best[i]["executed"]):
                best[i] = {"executed": bool(z.get("executed")), "matched": bool(z.get("matched")), "claimed": z.get("claimed_reversible"),
                           "ctrl_z": bool(b.get("ctrl+z")) if "ctrl+z" in b else None}
    n = len(best)
    em = [json.load(open(RUNS / "k3_v3" / f"fold{f}.json"))["UNDO"] for f in range(5)]
    total = sum(x["n"] for x in em)
    return {"reversible_rows_with_an_undo": n, "zero_shot_executed": sum(v["executed"] for v in best.values()),
            "zero_shot_rollback_rate": round(sum(v["matched"] for v in best.values()) / n, 3),
            "ctrl_z_recorded": sum(v["ctrl_z"] is not None for v in best.values()),
            "ctrl_z_rollback_rate": round(sum(bool(v["ctrl_z"]) for v in best.values()) / n, 3),
            "model_exact_match_not_rollback": round(sum(x["exact_match"] * x["n"] for x in em) / total, 3), "model_undo_rows": total}


if __name__ == "__main__":
    R, G = rows(), guesses()
    res = {"H1": h1(R, G), "H2": h2(), "H3": h3(R)}
    print(json.dumps(res, indent=1))
    (HERE.parent / "agentrun" / "hypotheses_20261102.json").write_text(json.dumps(res, indent=1))
