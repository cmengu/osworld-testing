"""Data for the agent-step review page (29 Oct 2026): one record per agent step that types, deletes, saves, quits or
undoes, with the agent's own before/after screenshots, what changed (from the states recorded during the agent's run,
or the rig's S/S' where its replay was faithful), the rig's result and the draft on-task mark.  Writes
rig/out/review_page/{rows.json,img/*.jpg}; the page is rig/agentrun/review_page.html.

    OSWorld/.venv/bin/python -I rig/agentrun/make_review_page.py
"""
import glob
import json
import pathlib
import re
import subprocess
import sys

BASE = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE))
from rig.snapshot import load_snapshot  # noqa: E402

OUT = BASE / "rig" / "out" / "review_page"
IMG = OUT / "img"
VS = {"___optimize_refactor", "___change_permissions", "___reorganize_rename", "___shell_script_permissions", "___fix_text_search", "___fix_todo_list"}
CHANGING = re.compile(r"typewrite|\.write\(|press\('(delete|enter)'\)|'ctrl', '(z|s|q)'|'ctrl', 'shift', 'k'")
NOISE = ("/home/user/.config/", "/home/user/.cache/", "/home/user/.local/share/", "/home/user/.mozilla/", "/home/user/.thunderbird/",
         "/home/user/.vscode/", "/home/user/snap/", "/home/user/.pki/", "/home/user/.rig_cache/", "/home/user/.bash_history")


def load(pats):
    out = {}
    for pat in pats:
        for f in sorted(glob.glob(str(BASE / pat))):
            for line in open(f):
                r = json.loads(line)
                if r.get("status") != "error":
                    out[r["row_id"]] = r
    return out


def jpg(src, name):
    if not src or not pathlib.Path(src).is_file():
        return None
    dst = IMG / f"{name}.jpg"
    if not dst.exists():
        subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "80", "-Z", "1920", str(src), "--out", str(dst)],
                       capture_output=True)
    return f"img/{dst.name}" if dst.exists() else None


def agent_shot(traj_dir, lines, k):
    """The agent's screenshot after its k-th action (k >= 1), as the agent saw it."""
    if k < 1 or k > len(lines):
        return None
    f = lines[k - 1].get("screenshot_file")
    p = traj_dir / f if f else None
    if p and p.is_file():
        return p
    c = sorted(traj_dir.glob(f"step_{lines[k - 1].get('step_num')}_*.png"))
    return c[0] if c else None


def file_changes(d0, d1):
    a = {p: v for p, v in d0.items() if not p.startswith(NOISE)}
    b = {p: v for p, v in d1.items() if not p.startswith(NOISE)}
    out = []
    for p in sorted(set(a) | set(b)):
        x, y = a.get(p), b.get(p)
        if x == y:
            continue
        if x is None:
            out.append({"path": p, "change": "created"})
        elif y is None:
            out.append({"path": p, "change": "deleted"})
        elif x.get("mode") != y.get("mode") and x.get("h") == y.get("h"):
            out.append({"path": p, "change": f"permissions {oct(x['mode'] & 0o777)[2:]} -> {oct(y['mode'] & 0o777)[2:]}"})
        elif x.get("h") != y.get("h") or x.get("s") != y.get("s"):
            out.append({"path": p, "change": f"contents changed ({x.get('s')} -> {y.get('s')} bytes)"})
        elif x.get("m") != y.get("m"):
            continue                      # timestamp only
    # a deleted file and a created one with the same contents is a move
    gone = {a[c["path"]].get("h"): c for c in out if c["change"] == "deleted" and a[c["path"]].get("h")}
    for c in out:
        if c["change"] == "created" and b[c["path"]].get("h") in gone:
            g = gone.pop(b[c["path"]].get("h"))
            g["change"] = "moved to " + c["path"]
            c["change"] = None
    return [c for c in out if c["change"]][:40]


def windows(w):
    return [l.split(None, 3)[-1] for l in (w or "").splitlines() if l.strip() and not l.startswith("---") and "@!" not in l and len(l.split(None, 3)) == 4]


# Seen first (30 Oct, the author's first sitting): every step the rig called no-undo, all of the run with step snapshots,
# and the two rig-found undos as controls.  Ordered by task and step, so the order says nothing about the rig's answer.
CONTROLS = {"ag-close_delete_spreadsheets-01", "ag-redundant_files-02"}


def plan_line(text):
    """One line for the run's outline, in the agent's own words: what it says it will do next."""
    text = re.sub(r"```.*", "", str(text), flags=re.S)
    text = re.sub(r"^\W*(reflection|plan|next step|thought)s?\W+", "", text.strip(), flags=re.I)
    parts = [x.strip() for x in re.split(r"(?<=[.!?])\s+", text.replace("\n", " ")) if x.strip()]
    pick = [x for x in parts if re.match(r"(I'll|I will|I need to|I'm going to|Let me|Now I|Next)\b", x)]
    line = (pick or parts or ["(no note from the agent)"])[0]
    line = re.sub(r"^(I'll|I will|I'm going to|Let me|Now I'll|Next,? I'll)\s+", "", line)
    line = line[0].upper() + line[1:]
    return line if len(line) <= 130 else line[:127].rsplit(" ", 1)[0] + "..."


def plan_of(traj_lines):
    return [plan_line(l.get("response", "")) for l in traj_lines]


def changes_picture(name):
    """The after picture with a red box round every part of the screen that differs from before.  The top bar is left
    out: its clock changes on every step."""
    import numpy as np
    from PIL import Image, ImageDraw
    a, b, dst = IMG / f"{name}_b.jpg", IMG / f"{name}_a.jpg", IMG / f"{name}_d.jpg"
    if not a.exists() or not b.exists():
        return None, None
    x, y = Image.open(a).convert("L"), Image.open(b).convert("RGB")
    if x.size != y.size:
        return None, None
    d = np.abs(np.asarray(x, dtype=int) - np.asarray(y.convert("L"), dtype=int)) > 30
    d[:28] = False
    cell = 24
    h, w = d.shape[0] // cell, d.shape[1] // cell
    on = [[d[j * cell:(j + 1) * cell, i * cell:(i + 1) * cell].sum() >= 4 for i in range(w)] for j in range(h)]
    seen, boxes = set(), []
    for j in range(h):
        for i in range(w):
            if on[j][i] and (j, i) not in seen:
                stack, cells = [(j, i)], []
                seen.add((j, i))
                while stack:
                    p, q = stack.pop()
                    cells.append((p, q))
                    for n, m in [(p + s, q + t) for s in (-2, -1, 0, 1, 2) for t in (-2, -1, 0, 1, 2)]:
                        if 0 <= n < h and 0 <= m < w and on[n][m] and (n, m) not in seen:
                            seen.add((n, m))
                            stack.append((n, m))
                boxes.append((min(c[1] for c in cells) * cell, min(c[0] for c in cells) * cell,
                              (max(c[1] for c in cells) + 1) * cell, (max(c[0] for c in cells) + 1) * cell))
    im = y.copy()
    dr = ImageDraw.Draw(im)
    for bx in boxes:
        dr.rectangle(bx, outline=(255, 30, 30), width=4)
    im.save(dst, quality=80)
    return f"img/{dst.name}", len(boxes)


def summarize(r):
    if not r:
        return {"rig": "not labelled", "undo": None, "tried": None, "teacher": None}
    st = r.get("status")
    if st == "replay_diverged":
        rig = "replay diverged (not labelled)"
    else:
        rig = (r.get("executed_label") or st or "?") + (" (nothing changed)" if r.get("no_change") else "")
        unjudged = sum(1 for x in r.get("undo_search") or [] if x.get("error") and not x.get("capped"))
        if unjudged and r.get("executed_label") == "NO-UNDO-FOUND":
            rig += f" ({unjudged} candidates not judged)"
    g = r.get("guessed_label_defined") or {}
    return {"rig": rig, "undo": r.get("shortest_undo"), "tried": r.get("budget_used"),
            "teacher": None if g.get("reversible") is None else ("reversible" if g["reversible"] else "one-way")}


def main():
    IMG.mkdir(parents=True, exist_ok=True)
    tasks = {pathlib.Path(f).stem: json.load(open(f)) for f in glob.glob(str(BASE / "rig/agentrun/tasks/examples/*/*.json"))}
    ag_res = load(["rig/out/agent_label_?/results.jsonl", "rig/out/agent_label2_?/results.jsonl", "rig/out/agent_label3_?/results.jsonl", "rig/out/agent_nuf_?/results.jsonl"])
    agr_res = load(["rig/out/agent_rec_?/results.jsonl"])
    snap_res = load(["rig/out/agent_snap3_label/results.jsonl"])
    marks = json.load(open(BASE / "rig/agentrun/on_task_draft.json"))
    out = []
    for rows_file, res, kind in (("rig/clickspots_agent_rec.json", agr_res, "recorded"), ("rig/clickspots_agent.json", ag_res, "first run"),
                                 ("rig/clickspots_agent_snap3.json", snap_res, "snapshot")):
        for r in json.load(open(BASE / rows_file))["rows"]:
            if kind != "snapshot" and not CHANGING.search(r["code"]):
                continue
            if kind == "first run" and r["task_id"] in VS:
                continue                  # superseded by the recorded VS Code run
            traj = BASE / r["source_traj"]
            lines = [json.loads(l) for l in traj.read_text().splitlines() if l.strip()]
            lines = [l for l in lines if "action" in l]
            i = int(r["step"])
            rec = res.get(r["row_id"])
            changes, win_before, win_after, source, before_replayed = None, None, None, None, False
            if r.get("recorded_before") and r.get("recorded_after"):
                s0, s1 = load_snapshot(BASE / r["recorded_before"]), load_snapshot(BASE / r["recorded_after"])
                changes, win_before, win_after = file_changes(s0.digest, s1.digest), windows(s0.windows), windows(s1.windows)
                before = jpg(BASE / r["recorded_before"] / "screenshot.png", f"{r['row_id']}_b")
                after = jpg(BASE / r["recorded_after"] / "screenshot.png", f"{r['row_id']}_a")
                source = "recorded during the agent's run"
            else:
                before = jpg(agent_shot(traj.parent, lines, i - 1), f"{r['row_id']}_b")
                after = jpg(agent_shot(traj.parent, lines, i), f"{r['row_id']}_a")
                if rec and rec.get("status") != "replay_diverged":
                    od = next(iter(glob.glob(str(BASE / f"rig/out/agent_*/{r['row_id']}/S"))), None)
                    if od and (pathlib.Path(od).parent / "S1" / "digest.json").exists():
                        s0, s1 = load_snapshot(pathlib.Path(od)), load_snapshot(pathlib.Path(od).parent / "S1")
                        changes, win_before, win_after = file_changes(s0.digest, s1.digest), windows(s0.windows), windows(s1.windows)
                        source = "the rig's replay (matched the agent's screen)"
                        if not before:    # the agent's first step has no screenshot before it
                            before = jpg(pathlib.Path(od) / "screenshot.png", f"{r['row_id']}_b")
                            before_replayed = True
            m = marks.get(r["row_id"]) if kind == "first run" else None
            s = summarize(rec)
            prio = 0 if "NO-UNDO-FOUND" in s["rig"] else (1 if changes else (2 if "diverged" in s["rig"] or s["rig"] == "not labelled" else 3))
            out.append({"id": r["row_id"], "run": kind, "task": r["task_id"].strip("_"), "instruction": tasks[r["task_id"]]["instruction"],
                        "step": i, "of": len(lines), "code": re.sub(r"\n?time\.sleep\([\d.]+\)", "", r["code"].replace("import pyautogui, time\n", "").replace("import pyautogui\n", "")).strip(),
                        "reasoning": re.sub(r"```.*", "", str(lines[i - 1].get("response", "")), flags=re.S).strip()[:600],
                        "before": before, "before_replayed": before_replayed, "after": after, "changes": changes, "windows_before": win_before, "windows_after": win_after,
                        "changes_source": source, "on_task_draft": None if m is None else m["on_task"],
                        "on_task_reason": None if m is None else m["reason"], **s, "first20": prio == 0 or kind == "snapshot" or r["row_id"] in CONTROLS,
                        "plan": plan_of(lines), "changed_picture": changes_picture(r["row_id"])})
    # the steps of the snapshot run left out as unchanged, so that run can be read whole from start to end
    have = {x["step"] for x in out if x["run"] == "snapshot"}
    snap = next(x for x in json.load(open(BASE / "rig/clickspots_agent_snap3.json"))["rows"])
    traj = BASE / snap["source_traj"]
    lines = [json.loads(l) for l in traj.read_text().splitlines() if l.strip()]
    lines = [l for l in lines if "action" in l]
    for i in range(1, len(lines) + 1):
        if i in have:
            continue
        rid, st = f"ags3-change_permissions-{i:02d}", traj.parent / "states"
        s0, s1 = load_snapshot(st / f"s{i - 1:02d}"), load_snapshot(st / f"s{i:02d}")
        out.append({"id": rid, "run": "snapshot", "task": snap["task_id"].strip("_"), "instruction": tasks[snap["task_id"]]["instruction"],
                    "step": i, "of": len(lines), "code": str(lines[i - 1]["action"]).replace("import pyautogui\nimport time\n", ""),
                    "reasoning": re.sub(r"```.*", "", str(lines[i - 1].get("response", "")), flags=re.S).strip()[:600],
                    "before": jpg(st / f"s{i - 1:02d}" / "screenshot.png", f"{rid}_b"), "before_replayed": False,
                    "after": jpg(st / f"s{i:02d}" / "screenshot.png", f"{rid}_a"), "changes": file_changes(s0.digest, s1.digest),
                    "windows_before": windows(s0.windows), "windows_after": windows(s1.windows), "changes_source": "recorded during the agent's run",
                    "on_task_draft": None, "on_task_reason": None, "rig": "left out: the rig's recorded states were equal", "undo": None, "tried": None,
                    "teacher": None, "first20": False, "plan": plan_of(lines), "changed_picture": changes_picture(rid)})
    order = {"snapshot": 0, "recorded": 1, "first run": 2}
    out.sort(key=lambda x: (not x["first20"], x["task"], order[x["run"]], x["step"]))
    (OUT / "rows.json").write_text(json.dumps(out, indent=1))
    print(len(out), "rows;", sum(1 for x in out if x["before"]), "with before shots;", sum(1 for x in out if x["changes"] is not None), "with file changes")
    print("first sitting:", sum(1 for x in out if x["first20"]))


if __name__ == "__main__":
    main()
