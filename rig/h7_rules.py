"""H7 step 1 (6 Nov 2026, author's go: "contniuneuright now"): does a pre-click guard have more to catch on OSWorld 2.0
than on OSWorld 1.0?  Free first pass: rule flags on the published Opus 5 trajectories of both benchmarks (same agent,
same harness: xlangai/ubuntu_osworld_verified_trajs, results_opus5_task221874_osworld1.0 and
results_opus5_task220297_osworld2.0; only traj.jsonl and result.txt are extracted, to rig/out/traj/v1 and v2).
TEST ONLY: these trajectories are never training data.

A step is a COMMIT CANDIDATE if it can change lasting state in a way that may not be undone in a few actions:
  shell   a typed shell command that writes, deletes, moves, installs or sends (rm, mv, sed -i, > file, pip install, ...)
  save    Ctrl+S / Ctrl+Shift+S (writes over a file on disk)
  click   a click or Return whose own narration (or the last one before it) names a committing verb
          (send, submit, delete, pay, book, confirm, publish, discard, overwrite, replace all, ...)
These are candidates, not labels: step 2 labels a sample (reversible within K = 3? off-task?).  Rates are per task
and per 100 acting steps (screenshot, wait, zoom, mouse_move and scroll are not acting steps).

    OSWorld/.venv/bin/python -I rig/h7_rules.py      # -> rig/out/h7/rules.json, rig/out/h7/candidates_<v>.jsonl
"""
import json
import pathlib
import re
import statistics

BASE = pathlib.Path(__file__).resolve().parent.parent
TRAJ = BASE / "rig" / "out" / "traj"
OUT = BASE / "rig" / "out" / "h7"
PASSIVE = {"screenshot", "wait", "zoom", "mouse_move", "scroll", None}
SHELL = re.compile(r"(^|[;&|]\s*|\bsudo\s+)(rm|rmdir|unlink|mv|shred|truncate|dd|chmod|chown|kill|pkill|killall)\b"
                   r"|\bsed\s+-i|\bfind\b.*-delete|\bgit\s+(commit|push|reset|checkout|clean|rebase|merge|rm)\b"
                   r"|\b(pip3?|apt(-get)?|npm|snap)\s+(install|remove|uninstall|purge)\b"
                   r"|\bcurl\b.*(-X\s*(POST|PUT|DELETE|PATCH)|\s-d\s|--data)"
                   r"|(^|[^0-9&>])>{1,2}\s*(?!/dev/null|&)[~/\w.\"']"
                   r"|\btee\b(?!.*/dev/null)|\bcp\b\s", re.M)
VERBS = re.compile(r"\b(send|sent|submit|delet|remov|trash|pay|purchas|book|transfer|publish|post(ing)? (the|it|a)|"
                   r"confirm|discard|don't save|overwrit|replace all|archiv|approv|reject|cancel (the )?(booking|order|"
                   r"reservation|subscription)|merge|empty|uninstall|reset|revoke|withdraw|place (the )?order|checkout|"
                   r"sign (up|out)|log ?out|unsubscrib|accept)", re.I)


def expand(step):
    tc = step.get("tool_call") or {}
    inp = tc.get("input") or {}
    if inp.get("action") == "batched_actions":
        return inp.get("actions") or []
    return [inp] if inp else []


def flags(acts, narr):
    out = set()
    for a in acts:
        kind = a.get("action")
        if kind == "type":
            t = a.get("text", "")
            if SHELL.search(t) and ("\n" in t or t.strip().endswith(";")):   # a command, entered
                out.add("shell")
        elif kind == "key":
            k = (a.get("text") or "").lower().replace(" ", "")
            if k in ("ctrl+s", "ctrl+shift+s"):
                out.add("save")
            if k in ("return", "kp_enter", "enter") and VERBS.search(narr or ""):
                out.add("click")
        elif kind in ("left_click", "double_click") and VERBS.search(narr or ""):
            out.add("click")
    return out


def run(tag):
    rows, per_task = [], []
    for f in sorted((TRAJ / tag).rglob("traj.jsonl")):
        task = str(f.parent.relative_to(TRAJ / tag))
        steps = [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
        last_narr, acting, cand = "", 0, {"shell": 0, "save": 0, "click": 0, "any": 0}
        for s in steps:
            narr = (s.get("response") or "").strip()
            if narr:
                last_narr = narr
            acts = expand(s)
            if not any(a.get("action") not in PASSIVE for a in acts):
                continue
            acting += 1
            fl = flags(acts, narr or last_narr)
            for k in fl:
                cand[k] += 1
            if fl:
                cand["any"] += 1
                rows.append({"bench": tag, "task": task, "step": s.get("step_num"), "flags": sorted(fl),
                             "narration": (narr or last_narr)[:400], "actions": acts, "screenshot": s.get("screenshot_file")})
        score = None
        r = f.parent / "result.txt"
        if r.exists():
            try:
                score = float(r.read_text().strip())
            except ValueError:
                pass
        per_task.append({"task": task, "steps": len(steps), "acting": acting, "score": score, **cand})
    return rows, per_task


def summary(per_task):
    acting = sum(t["acting"] for t in per_task)
    s = {"tasks": len(per_task), "acting_steps": acting, "acting_per_task_median": statistics.median(t["acting"] for t in per_task)}
    for k in ("any", "shell", "save", "click"):
        n = sum(t[k] for t in per_task)
        s[k] = {"total": n, "per_task_mean": round(n / len(per_task), 2),
                "per_task_median": statistics.median(t[k] for t in per_task),
                "tasks_with_any": sum(t[k] > 0 for t in per_task),
                "per_100_acting": round(100 * n / acting, 2)}
    return s


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    res = {}
    for tag in ("v1", "v2"):
        rows, per_task = run(tag)
        (OUT / f"candidates_{tag}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
        res[tag] = {"summary": summary(per_task), "per_task": per_task}
        print(tag, json.dumps(res[tag]["summary"], indent=1))
    (OUT / "rules.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
