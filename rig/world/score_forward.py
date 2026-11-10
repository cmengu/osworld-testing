"""Score the forward model T against every recorded transition (P1 of rig/plan_forward_model.md, 9 Nov 2026).

Corpus: every rig/out/<run>/<row>/ with a before-state S and an after-state S1, and the row's action code from the run's
results.  Split fixed before scoring: TEST = the pair runs (pr_, prr_, prx_, pq_; TEST ONLY), DEV = everything else.

Truth: the files that changed between S and S1 under the rig's own masked comparison (rig/mask.py: apply_file_mask,
_fsig), the system keys that changed (system.json), and the change in the set of window titles.

Metrics (where T decides): file-delta EXACT (the predicted changed paths equal the recorded ones and every predicted value
holds), CONTENT-exact (the same, ignoring permission bits), path precision/recall, system exact, window class.  Baseline:
"nothing changes".

    OSWorld/.venv/bin/python -I rig/world/score_forward.py            # -> rig/out/world/forward_score.json
"""
import collections
import glob
import json
import os
import pathlib
import sys

BASE = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path[:0] = [str(BASE), str(BASE / "rig")]
from rig.mask import _fsig, apply_file_mask                       # noqa: E402
from rig.snapshot import SYSTEM_COMPARED, load_snapshot          # noqa: E402
from rig.world.T import T, WState                                 # noqa: E402

OUT = BASE / "rig" / "out" / "world"
MASK = json.load(open(BASE / "rig" / "out" / "mask_run" / "mask.json"))
TEST_PREFIX = ("pr_", "prr_", "prx_", "pq_", "p5")              # 10 Nov: P5 runs (p5a_, p5b_) are TEST too


def corpus():
    codes = {}
    for f in glob.glob(str(BASE / "rig/out/*/results*.jsonl")):
        run = pathlib.Path(f).parent.name
        for l in open(f):
            try:
                r = json.loads(l)
            except json.JSONDecodeError:
                continue
            code = (r.get("action") or {}).get("code")
            if code:
                codes.setdefault((run, r["row_id"]), (code, (r.get("action") or {}).get("desc") or r.get("spot_id")))
    for s1 in sorted(glob.glob(str(BASE / "rig/out/*/*/S1"))):
        row = pathlib.Path(s1).parent
        run = row.parent.name
        if (run, row.name) not in codes or not (row / "S").is_dir():
            continue
        code, family = codes[(run, row.name)]
        # OS-Harm agent steps (replays of a Claude agent's actions) are TEST ONLY like every OS-Harm row (canary
        # osharm:d9a0): never used to write or induce rules
        osharm = run.startswith(("agent", "agr")) or "agent proposed" in (family or "") or row.name.startswith(("agent", "agr"))
        yield {"run": run, "row": row.name, "S": str(row / "S"), "S1": s1, "code": code, "family": family,
               "split": "TEST" if run.startswith(TEST_PREFIX) or osharm else "DEV"}


def content_sig(v):
    s = _fsig("x", v)
    return s[:2] if isinstance(s, tuple) and len(s) >= 2 and s[0] not in ("dir", "link", "doc", "cells") else s[:2] if s else s


def truth(S, S1):
    a, b = apply_file_mask(S.digest, MASK), apply_file_mask(S1.digest, MASK)
    a = {p: v for p, v in a.items() if not p.startswith("/@")}
    b = {p: v for p, v in b.items() if not p.startswith("/@")}
    changed = {p for p in set(a) | set(b) if _fsig(p, a.get(p)) != _fsig(p, b.get(p))}
    sysch = {k for k in SYSTEM_COMPARED if (S.system or {}).get(k) != (S1.system or {}).get(k)} if S.system and S1.system else set()
    ta = {l.split(None, 3)[3] for l in (S.windows or "").splitlines() if len(l.split(None, 3)) == 4 and "@!" not in l}
    tb = {l.split(None, 3)[3] for l in (S1.windows or "").splitlines() if len(l.split(None, 3)) == 4 and "@!" not in l}
    win = "same" if ta == tb else "closes" if tb < ta else "opens" if tb > ta else "other"
    return a, b, changed, sysch, win


def holds(p, value, a, b):
    kind = value[0]
    v = b.get(p)
    if kind == "absent":
        return v is None
    if v is None:
        return False
    if kind == "content":
        src = a.get(value[1])
        return src is not None and (v.get("c") or v.get("h")) == (src.get("c") or src.get("h")) and v.get("s") == src.get("s")
    if kind == "bytes":
        return v.get("h") == value[1] and v.get("s") == value[2]
    if kind == "empty":
        return v.get("s") == 0
    if kind == "dir":
        return bool(v.get("d"))
    if kind == "link":
        return "l" in v
    if kind == "mode":
        return v.get("mode") == value[1]
    return True                                                     # sym, sym-or-same: exists


def score():
    rows = []
    for t in corpus():
        S, S1 = load_snapshot(t["S"]), load_snapshot(t["S1"])
        a, b, changed, sysch, win = truth(S, S1)
        try:
            d = T(t["code"], WState(S))
        except Exception as exc:  # noqa: BLE001  a crash counts as not decided, and is listed
            d, t["crash"] = None, repr(exc)[:120]
        rec = {**{k: t[k] for k in ("run", "row", "family", "split")}, "changed": sorted(changed), "sys_changed": sorted(sysch),
               "win": win, "decided": d is not None, "crash": t.get("crash")}
        if d is not None:
            strict = {p for p, v in d.files.items() if v[0] not in ("sym-or-same", "maybe-absent")}
            maybe = {p for p, v in d.files.items() if v[0] in ("sym-or-same", "maybe-absent")}
            fp = strict - changed
            fn = changed - strict - maybe
            vals = all(holds(p, d.files[p], a, b) for p in strict)
            rec.update({"pred": {p: list(v) for p, v in d.files.items()}, "fp": sorted(fp), "fn": sorted(fn),
                        "file_exact": not fp and not fn and vals,
                        "content_exact": not fn and not (fp - {p for p in fp if b.get(p) and a.get(p) and content_sig(a[p]) == content_sig(b[p])}) and vals,
                        "sys_exact": (d.system == sysch) if S.system and S1.system else None,
                        "win_pred": d.windows, "win_ok": d.windows in ("unknown", win), "rules": d.rules})
        rec["baseline_exact"] = not changed
        rows.append(rec)
    OUT.mkdir(parents=True, exist_ok=True)
    out = {}
    for split in ("DEV", "TEST"):
        rs = [r for r in rows if r["split"] == split]
        dec = [r for r in rs if r["decided"]]
        out[split] = {"transitions": len(rs), "decided": len(dec), "coverage": round(len(dec) / max(1, len(rs)), 3),
                      "file_exact": round(sum(r["file_exact"] for r in dec) / max(1, len(dec)), 3),
                      "content_exact": round(sum(r["content_exact"] for r in dec) / max(1, len(dec)), 3),
                      "baseline_nothing_changes_on_decided": round(sum(r["baseline_exact"] for r in dec) / max(1, len(dec)), 3),
                      "baseline_nothing_changes_all": round(sum(r["baseline_exact"] for r in rs) / max(1, len(rs)), 3),
                      "system_exact": f"{sum(r['sys_exact'] is True for r in dec)}/{sum(r['sys_exact'] is not None for r in dec)}",
                      "windows_ok": round(sum(r["win_ok"] for r in dec) / max(1, len(dec)), 3),
                      "crashes": sum(bool(r["crash"]) for r in rs)}
    fam = collections.defaultdict(lambda: collections.Counter())
    for r in rows:
        if r["split"] == "DEV":
            fam[r["family"]]["n"] += 1
            fam[r["family"]]["decided"] += r["decided"]
            fam[r["family"]]["exact"] += bool(r.get("file_exact"))
    out["dev_families_worst"] = sorted(([f, dict(c)] for f, c in fam.items() if c["decided"] > c["exact"]),
                                       key=lambda x: -(x[1]["decided"] - x[1]["exact"]))[:25]
    out["dev_undecided"] = sorted(([f, dict(c)] for f, c in fam.items() if c["n"] > c["decided"]), key=lambda x: -(x[1]["n"] - x[1]["decided"]))[:25]
    (OUT / "forward_score.json").write_text(json.dumps(out, indent=1))
    (OUT / "forward_rows.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    print(json.dumps({k: out[k] for k in ("DEV", "TEST")}, indent=1))
    return out


if __name__ == "__main__":
    score()
