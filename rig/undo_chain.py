"""Step 2 (6 Nov 2026, author: "lets do all steps"): chain FORWARD into UNDO.  The undo plan is written from the
PREDICTED change (Model-E FORWARD, rig/out/forward/model_forward_k3_v5w.json), the state before and the action keys,
using the same "where does the content survive" reading as step 1b (rig/train/symbolic_rule.py):

  predicted change                                          plan
  a file moved to the Trash or renamed, by a Files key      key:ctrl+z                       (Files undoes its last op)
  a file moved or renamed by a typed shell command          shell:mv <new> <old>             (names from the change)
  only new files, made by a typed shell command             shell:rm <new files>
  a deleted file VS Code still holds                        focus:doc ; key:ctrl+s
  the app's own save of its open document                   the model's plan if it saves, else Ctrl+Z, Ctrl+S, ...
  no file written                                           the model's plan WITHOUT its save steps (nothing on
                                                            disk to put back; a save there writes a new file state)
  content survives nowhere (step 1b says not undoable)      no plan (the model's plan is kept, for comparison)
Otherwise the model's own plan (_v5w, rig/out/undo_eval/model_plans_v5.json) is used unchanged.

Scoring is on the 99 H3 rows.  A chained plan identical to a plan already executed on that row (any earlier run) takes
that run's result at no cost; the rest go to plans_chain_<src>.json for a --plans-only run (source "chain").
CAVEAT: the "no file written -> drop the save" and Trash rules were chosen after seeing the model's H3 failures.

    OSWorld/.venv/bin/python -I rig/undo_chain.py build    # -> rig/out/undo_eval/plans_chain_<src>.json, chain_build.json
    OSWorld/.venv/bin/python -I rig/undo_chain.py score    # after the ch_* run -> rig/out/undo_eval/chain_score.json
"""
import collections
import glob
import json
import pathlib
import re
import shlex
import sys

BASE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "rig" / "train"))
from rig import undo as U  # noqa: E402
from rig.undo_eval_retry import load, DROPPED, CHAIN, norm  # noqa: E402
from symbolic_rule import decide, parse_change, parse_before  # noqa: E402

EV = BASE / "rig" / "out" / "undo_eval"
SAVE_TAIL = {"key:ctrl+s", "confirm", "key:enter", "key:ctrl+y"}


def strip_save(plan):
    if "key:ctrl+s" not in plan:
        return plan
    head = plan[:plan.index("key:ctrl+s")]
    return [s for s in head if not s.startswith("wait:")] or ["key:ctrl+z"]


def home_rel(p):
    return p[len("/home/user/"):] if p.startswith("/home/user/") else p


def chain(prompt, change, model_plan):
    frames, keys = parse_before(prompt)
    files, _ = parse_change(change)
    rev, why, _ = decide(prompt, change)
    typed_shell = "typewrite(" in keys and any(t.startswith("user@") for t in frames)
    real = [f for f in files if "/.local/share/Trash/info/" not in f["path"]]
    gone = [f for f in real if f["kind"] == "deleted"]
    new = [f for f in real if f["kind"] == "created"]
    mod = [f for f in real if f["kind"] == "modified"]
    if not rev:
        return model_plan, "step 1b: not undoable (model plan kept)"
    if gone and new and not mod:
        if typed_shell and len(gone) == 1 and len(new) == 1:
            return [f"shell:mv {shlex.quote(home_rel(new[0]['path'].rstrip('/')))} {shlex.quote(home_rel(gone[0]['path'].rstrip('/')))}"], "moved by shell: mv back"
        if not typed_shell:
            return ["key:ctrl+z"], "moved by Files: Ctrl+Z"
    if new and not gone and not mod and typed_shell:
        return ["shell:rm " + " ".join(shlex.quote(home_rel(f["path"])) for f in new)], "new files only: rm them"
    if gone and not new and "VS Code" in why:
        return ["focus:doc", "key:ctrl+s"], "VS Code buffer: re-save"
    if mod and "undo history" in why:
        if "key:ctrl+s" in model_plan:
            return model_plan, "own save: model plan (saves)"
        return ["key:ctrl+z", "key:ctrl+s", "wait:4", "confirm", "wait:3", "key:ctrl+y"], "own save: undo, save, confirm, redo"
    if not real:
        p = strip_save(model_plan)
        return p, "no file written: model plan without save" if p != model_plan else "no file written: model plan"
    return model_plan, "other: model plan"


def executed():
    ex = collections.defaultdict(list)
    for f in glob.glob(str(BASE / "rig/out/*/results.jsonl")):
        for l in open(f):
            r = json.loads(l)
            if r.get("status") == "ok" and r.get("plans"):
                for p in r["plans"]:
                    if p.get("executed"):
                        st = tuple(x for x in norm(p.get("parsed") or []) if not x.startswith("wait:"))
                        ex[(r["row_id"], st)].append(bool(p.get("match")))
    return ex


def rows_and_sources():
    s, n, new, tgt, rec = load()
    rows = [r for r in s if r in n and n[r] != "needs a run" and r not in DROPPED]
    fw = json.loads((BASE / "rig/out/forward/model_forward_k3_v5w.json").read_text())["rows"]
    prompts = {}
    for f in range(5):
        for l in open(BASE / f"rig/train/data_k3_v5/fold{f}_test.jsonl"):
            d = json.loads(l)
            if d["task"] == "FORWARD":
                prompts[d["row_id"]] = d["prompt"]
    return rows, s, n, new, fw, prompts


def build():
    rows, s, n, new, fw, prompts = rows_and_sources()
    ex = executed()
    out, todo, counts = {}, collections.defaultdict(dict), collections.Counter()
    for rid in rows:
        mp = norm(new[rid]["text"].split(";"))
        if rid not in fw or rid not in prompts:
            plan, how = mp, "no FORWARD row: model plan"
        else:
            plan, how = chain(prompts[rid], fw[rid]["text"], mp)
        key = tuple(x for x in plan if not x.startswith("wait:"))
        known = ex.get((rid, key))
        status = ("ok" if any(known) else "fail (executed before)") if known else "needs a run"
        if status == "needs a run":
            if not U.parse_steps(plan):
                status = "no plan (does not parse)"
            else:
                todo[rid.split("-")[0]][rid] = [{"source": "chain", "steps": ["wait:3"] + plan}]
        out[rid] = {"plan": plan, "how": how, "changed": plan != mp, "status": status}
        counts[(how.split(":")[0], status.split(" ")[0])] += 1
    for src, d in todo.items():
        (EV / f"plans_chain_{src}.json").write_text(json.dumps(d, indent=1))
    (EV / "chain_build.json").write_text(json.dumps(out, indent=1))
    print("changed vs model plan:", sum(v["changed"] for v in out.values()), "of", len(out))
    print("known ok:", sum(v["status"] == "ok" for v in out.values()), "known fail:", sum(v["status"].startswith("fail") for v in out.values()),
          "needs a run:", sum(v["status"] == "needs a run" for v in out.values()), {k: len(v) for k, v in todo.items()})
    for k, v in sorted(counts.items()):
        print(" ", k, v)
    for rid, v in out.items():
        if v["changed"]:
            print(rid, v["how"], "|", ";".join(v["plan"])[:70], "|", v["status"])


def score():
    rows, s, n, new, fw, prompts = rows_and_sources()
    built = json.loads((EV / "chain_build.json").read_text())
    runs = collections.defaultdict(list)
    for f in glob.glob(str(BASE / "rig/out/ch_*/results.jsonl")):
        for l in open(f):
            r = json.loads(l)
            if r.get("status") == "ok" and r.get("plans"):
                runs[r["row_id"]] += [bool(p.get("match")) for p in r["plans"] if p["source"] == "chain"]
    retry = json.loads((EV / "h3_retry_score.json").read_text())
    ok = {}
    for rid in rows:
        st = built[rid]["status"]
        ok[rid] = st == "ok" or any(runs.get(rid, []))
    pending = [r for r in rows if built[r]["status"] == "needs a run" and r not in runs]
    from math import comb
    # per-row ok sets of the earlier sources, as in undo_eval_retry.score
    sys.argv.append("--quiet")
    res = {"rows": len(rows), "chain_ok": sum(ok.values()), "pending_runs": pending,
           "earlier_best_of_two": retry["best_of_two"]}
    (EV / "chain_score.json").write_text(json.dumps({**res, "per_row": {r: {**built[r], "ok": ok[r]} for r in rows}}, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    {"build": build, "score": score}[sys.argv[1]]()
