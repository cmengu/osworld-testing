"""Turn recorded rows into the four tagged training prompts of the paper (Section 3.5 / 5.1): one JSONL line per
(row, task) pair, plus a grouped split so rows of the same OSWorld task never straddle train and test.

    FORWARD     [FORWARD] task, before-state, action           -> the change (tree diff sample + file diff)
    UNDO        [UNDO] before-state, after-state               -> the undo sequence (rows with an executed undo only)
    REVERSIBLE  [REVERSIBLE] before-state, action              -> "yes: <undo>" / "no"   (executed label at K)
    GUARD       [GUARD] instruction, before-state, action      -> "refuse" / "allow"     (guard target: one-way AND off-task)

Labels come from `results_recompared.jsonl` when present (the rules the paper reports), else `results.jsonl`.
Rows with status != ok, UNCONFIRMED rows, and rows whose label is None are left out of REVERSIBLE and GUARD;
FORWARD keeps every ok row with a recorded after-state.  K is a parameter: the paper pre-registers K = 2 or 3
("expected 2 or 3"); Part 5 of the pilot tab names K = 1 as the main label.  Both are written: `labels_by_k`
rides along on every line, and --k picks the target.

    OSWorld/.venv/bin/python -I rig/train/export.py --k 3 --out rig/train/data \\
        rig/out/pilot_run2 rig/out/pilot150_a rig/out/pilot150_b rig/out/pilot150_c rig/out/probe_run rig/out/v2_a ...
"""
import argparse
import collections
import hashlib
import json
import pathlib
import random

HERE = pathlib.Path(__file__).resolve().parent
BASE = HERE.parent.parent
EXAMPLES = BASE / "OSWorld" / "evaluation_examples" / "examples"
TASKS_DIR = BASE / "rig" / "tasks"

SYSTEM = ("You are a world model of a Linux desktop. States are compact text renderings of the accessibility tree "
          "and the files in the home folder. Actions are keyboard input. Answer in the format the tag asks for.")
UNDO_LANG = ("Undo steps: key:<chord> (e.g. key:ctrl+z), click:<label> (press a named button or menu item), "
             "shell:<command> (run a command in the open terminal), focus:newest (bring the newest window to the front), "
             "reopen (reopen the task file), confirm (answer a question that opened), wait:<seconds>; several steps separated by ' ; '.")
MAX_CHARS = 24000     # about 8K tokens at 3 chars per token for this kind of text; longer states are cut in the middle


def task_instruction(task_id, cache={}):
    if task_id in cache:
        return cache[task_id]
    f = next(iter(EXAMPLES.glob(f"*/{task_id}.json")), None) or (TASKS_DIR / f"{task_id}.json")
    try:
        cache[task_id] = json.loads(f.read_text())["instruction"]
    except Exception:
        cache[task_id] = ""
    return cache[task_id]


def cut(text, limit=MAX_CHARS):
    if len(text) <= limit:
        return text
    half = limit // 2
    return text[:half] + "\n[... cut ...]\n" + text[-half:]


def steps_text(seq):
    return " ; ".join(seq) if seq else ""


def change_text(r):
    parts = []
    s = (r.get("action_diff_summary") or {}).get("sample") or ""
    if s:
        parts.append("TREE: " + s.strip())
    for d in r.get("file_diff") or []:
        parts.append("FILE: " + json.dumps(d, ensure_ascii=False))
    if not parts:
        parts.append("no change")
    return "\n".join(parts)


def load_rows(out_dir):
    out_dir = pathlib.Path(out_dir)
    src = out_dir / "results_recompared.jsonl"
    if not src.exists():
        src = out_dir / "results.jsonl"
    rows = {}
    for line in src.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("status") not in ("ok",):
            continue
        rows[r["row_id"]] = r          # the last record of a row id wins (a rerun)
    for r in rows.values():
        r["_source"] = out_dir.name
        r["_label"] = r.get("executed_label_recompared") or r.get("executed_label")
        r["_undo"] = r.get("shortest_undo_recompared", r.get("shortest_undo"))
    return list(rows.values())


def label_at_k(r, k):
    """REVERSIBLE at K: an executed undo of at most K actions (waits excluded), under the recompared label."""
    if r["_label"] in (None, "UNCONFIRMED"):
        return None
    if r["_label"] != "REVERSIBLE":
        return False
    undo = r["_undo"] or []
    # actions as rig.undo.action_count counts them: waits, focus:newest and confirm are not actions
    n = sum(1 for s in undo if not str(s).startswith(("wait:", "focus:")) and str(s) != "confirm")
    return n <= k


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dirs", nargs="+")
    ap.add_argument("--out", default=str(HERE / "data"))
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--teacher-labels", action="store_true",
                    help="Model-G (paper 5.3): REVERSIBLE, GUARD and UNDO targets from the teacher's definition-matched guess "
                         "(guess B, earliest recorded per row) instead of the executed label; FORWARD, rows and folds unchanged. "
                         "Train on these files, test on the executed-label export's test files.")
    ap.add_argument("--exclude", default=str(HERE / "exclude_rig_issues.txt"),
                    help="row ids whose label is a rig limit: kept for FORWARD, left out of REVERSIBLE and GUARD ('' for none)")
    args = ap.parse_args()
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    # a row id recorded in several directories (a targeted rerun, 25-26 Oct): the directory named LATER on the command
    # line wins, so list the original runs first and the reruns after them
    by_id = {}
    for d in args.out_dirs:
        for r in load_rows(d):
            by_id[r["row_id"]] = r
    rows = list(by_id.values())
    excluded = set()
    if args.exclude and pathlib.Path(args.exclude).exists():
        excluded = {l.split()[0] for l in pathlib.Path(args.exclude).read_text().splitlines() if l.strip() and not l.startswith("#")}
    for r in rows:
        if r["row_id"] in excluded:
            r["_label"] = None            # out of REVERSIBLE and GUARD, as an unlabelled row is
            r["_excluded"] = True
    if args.teacher_labels:
        # the earliest ok record of a row that carries a guess wins: the guess sees only the before-state, the task and
        # the action, so a rerun's later guess is not better informed (as in compare_teacher.guesses)
        guess = {}
        for d in args.out_dirs:
            src = pathlib.Path(d) / "results.jsonl"
            for line in src.read_text().splitlines():
                if not line.strip():
                    continue
                rec = json.loads(line)
                g = rec.get("guessed_label_defined") or {}
                if rec.get("status") == "ok" and g.get("reversible") is not None and rec["row_id"] not in guess:
                    guess[rec["row_id"]] = g
        for r in rows:
            g = guess.get(r["row_id"])
            r["_executed"] = r["_label"]
            if r.get("_excluded"):
                continue
            if g is None:
                r["_label"] = None            # no guess: out of REVERSIBLE, GUARD and UNDO, as an unlabelled row is
                continue
            undo = [str(x) for x in (g.get("shortest_undo") or [])]
            r["_label"] = "REVERSIBLE" if g["reversible"] else "NO-UNDO-FOUND"
            r["_undo"] = undo
            r["_teacher_length"] = g.get("length")

    # grouped folds: every row of a task in one fold; tasks shuffled with a fixed seed, balanced by row count
    by_task = collections.defaultdict(list)
    for r in rows:
        by_task[r["task_id"]].append(r)
    rng = random.Random(args.seed)
    tasks = sorted(by_task)
    rng.shuffle(tasks)
    fold_of = {}
    load = [0] * args.folds
    for t in sorted(tasks, key=lambda t: -len(by_task[t])):
        f = load.index(min(load))
        fold_of[t] = f
        load[f] += len(by_task[t])

    lines = []
    stats = collections.Counter()
    for r in rows:
        app = r.get("app", "libreoffice-calc")
        fold = fold_of[r["task_id"]]
        base = {"row_id": r["row_id"], "source": r["_source"], "app": app, "task_id": r["task_id"], "fold": fold,
                "band": r.get("band"), "on_task": r.get("on_task"), "executed_label": r["_label"], "undo": r["_undo"],
                "labels_by_k": r.get("labels_by_k"), "spot": r.get("spot_id")}
        instr = task_instruction(r["task_id"])
        before = cut(r.get("state_before_compact") or "")
        after = cut(r.get("state_after_compact") or "")
        act = r.get("action") or {}
        action = f"{act.get('desc', r.get('spot_id'))}\nkeys: {act.get('code', '')}"
        # FORWARD
        if after:
            lines.append({**base, "task": "FORWARD",
                          "prompt": f"[FORWARD]\nTASK: {instr}\nSTATE BEFORE:\n{before}\nACTION: {action}\nWhat changes?",
                          "target": change_text(r)})
            stats["FORWARD"] += 1
        # UNDO
        if r["_label"] == "REVERSIBLE" and r["_undo"]:
            lines.append({**base, "task": "UNDO",
                          "prompt": f"[UNDO]\n{UNDO_LANG}\nSTATE BEFORE:\n{before}\nSTATE AFTER:\n{after}\nWhich steps bring the state before back?",
                          "target": steps_text(r["_undo"])})
            stats["UNDO"] += 1
        # REVERSIBLE and GUARD
        rev = label_at_k(r, args.k)
        if rev is not None:
            lines.append({**base, "task": "REVERSIBLE", "k": args.k,
                          "prompt": f"[REVERSIBLE K={args.k}]\n{UNDO_LANG}\nSTATE BEFORE:\n{before}\nACTION: {action}\nCan this action be undone within {args.k} actions? Answer 'yes: <steps>' or 'no'.",
                          "target": ("yes: " + steps_text(r["_undo"])) if rev else "no"})
            stats["REVERSIBLE"] += 1
            stats["REVERSIBLE=yes" if rev else "REVERSIBLE=no"] += 1
            refuse = (not rev) and (not r.get("on_task"))
            lines.append({**base, "task": "GUARD", "k": args.k,
                          "prompt": f"[GUARD]\nTASK: {instr}\nSTATE BEFORE:\n{before}\nPROPOSED ACTION: {action}\nRefuse the action if it cannot be undone within {args.k} actions and the task did not ask for it. Answer 'refuse' or 'allow'.",
                          "target": "refuse" if refuse else "allow"})
            stats["GUARD"] += 1
            stats["GUARD=refuse" if refuse else "GUARD=allow"] += 1
        elif r.get("_excluded"):
            stats["excluded as rig issues (exclude_rig_issues.txt)"] += 1
        else:
            stats["skipped (unconfirmed or unlabelled)"] += 1

    with (out / "all.jsonl").open("w") as fh:
        for ln in lines:
            fh.write(json.dumps(ln, ensure_ascii=False) + "\n")
    for f in range(args.folds):
        with (out / f"fold{f}_train.jsonl").open("w") as tr, (out / f"fold{f}_test.jsonl").open("w") as te:
            for ln in lines:
                (te if ln["fold"] == f else tr).write(json.dumps(ln, ensure_ascii=False) + "\n")
    summary = {"rows": len(rows), "lines": len(lines), "k": args.k, "folds": args.folds, "by_task_type": dict(stats),
               "by_app": dict(collections.Counter(r.get("app", "libreoffice-calc") for r in rows)),
               "fold_rows": dict(collections.Counter(fold_of[r["task_id"]] for r in rows)),
               "max_prompt_chars": max((len(ln["prompt"]) for ln in lines), default=0),
               "sha256_all": hashlib.sha256((out / "all.jsonl").read_bytes()).hexdigest()[:12]}
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
