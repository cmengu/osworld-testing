"""Step 1b (6 Nov 2026, author: "lets do all steps"): decide REVERSIBLE (undo within K = 3) symbolically from
(state before, action keys, change), where the change is either the rig's recorded change (the rule's ceiling) or
Model-E's predicted change (FORWARD).  No learning: the rule asks, for every piece of content the change destroys,
WHERE THAT CONTENT STILL SURVIVES and what the cheapest way back from there costs.

  survives in             evidence                                                   way back           actions
  Trash / a move          a deleted file reappears in Trash/files, or a new file      Undo / mv back     1
                          of the same size appears in the same step
  an editor buffer        a deleted file is open in a VS Code window that stays       focus, Ctrl+S      2
  the app's undo history  the app saved its own open document (Ctrl+S in the window   Ctrl+Z, Ctrl+S,    3 (Calc, Impress,
                          whose title names the file)                                 confirm / Ctrl+Y   VS Code); Writer > 3
  nowhere                 a file deleted or rewritten by anything else; Don't Save    -                  not undoable
                          (Alt+N) on a close question: unsaved content lost with no
                          file change
New files only (cp to a new name, > new file) are undone by removing them (1 action).  Lock files are not state.

The narration of the action is NOT used, only its keys.  CAVEAT: the survival places were found by reading the
60 rows where the plain rule ("a file deleted or modified = not undoable") fails, and those are test rows; the
number here is therefore optimistic.  A fair check needs fresh rows (step 3).

    OSWorld/.venv/bin/python -I rig/train/symbolic_rule.py   # -> rig/out/forward/symbolic_rule.json
"""
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent / "out" / "forward"
LINE = re.compile(r"^\s+(?P<path>/\S.*?) :: (?P<attr>[^:]+): (?P<old>.*?) -> (?P<new>.*)$")
SEG = re.compile(r"([a-z-]+)\[(.*?)\]#\d+$")
SIZE = re.compile(r"(\d+) B")
UNDO_COST = {"Calc": 3, "Impress": 3, "Visual Studio Code": 3, "Writer": 5}   # Ctrl+Z, Ctrl+S, confirm/Ctrl+Y; Writer's save undo needs 5-7


def parse_change(text):
    files, windows = [], []
    for ln in (text or "").splitlines():
        if ln.startswith("FILE:"):
            try:
                d = json.loads(ln[5:])
            except json.JSONDecodeError:
                continue
            p = d.get("path", "")
            if "/.~lock." in p:
                continue
            b, a = str(d.get("before", "")), str(d.get("after", ""))
            kind = "created" if b == "absent" else "deleted" if a == "absent" else "modified"
            sb, sa = SIZE.search(b), SIZE.search(a)
            files.append({"path": p, "kind": kind, "before": int(sb.group(1)) if sb else None,
                          "after": int(sa.group(1)) if sa else None})
        else:
            m = LINE.match(ln)
            if m and m.group("attr") == "__node__":
                sm = SEG.match(m.group("path").rsplit("/", 1)[-1])
                if sm and sm.group(1) in ("frame", "alert", "dialog", "application"):
                    windows.append((sm.group(1), sm.group(2), "opened" if m.group("old") == "None" else "closed"))
    return files, windows


def parse_before(prompt):
    state = prompt.split("STATE BEFORE:", 1)[1].split("\nACTION:", 1)[0]
    frames = re.findall(r"^FRAME: '(.*)'$", state, re.M)
    keys = prompt.split("\nkeys:", 1)[1].split("\nWhat changes?", 1)[0] if "\nkeys:" in prompt else ""
    return frames, keys


def app_of(title):
    for app in UNDO_COST:
        if title.endswith(app) or f"LibreOffice {app}" in title:
            return app
    return None


def decide(prompt, change_text):
    """-> (reversible: bool, reason: str, actions: int | None)"""
    frames, keys = parse_before(prompt)
    files, windows = parse_change(change_text)
    if re.search(r"hotkey\('alt', 'n'\)", keys):
        return False, "Don't Save: unsaved content lost, no file keeps it", None
    saved_by_app = "hotkey('ctrl', 's')" in keys
    real = [f for f in files if "/.local/share/Trash/info/" not in f["path"]]
    created = [f for f in real if f["kind"] == "created"]
    cost, reasons = 0, []
    for f in real:
        if f["kind"] == "created":
            continue
        base = f["path"].rstrip("/").rsplit("/", 1)[-1]
        holders = [t for t in frames if base and base in t]
        moved = [c for c in created if (c["path"].startswith("/home/user/.local/share/Trash/files/") and c["path"].endswith("/" + base))
                 or (f["before"] is not None and c["after"] == f["before"]) or (f["path"].endswith("/") and c["path"].endswith("/"))]
        if f["kind"] == "deleted" and moved:
            cost = max(cost, 1); reasons.append(f"{base}: moved (Trash or new name), move it back")
        elif f["kind"] == "deleted" and any(app_of(t) == "Visual Studio Code" for t in holders):
            cost = max(cost, 2); reasons.append(f"{base}: VS Code still holds it in a buffer, re-save")
        elif f["kind"] == "modified" and saved_by_app and holders and app_of(holders[0]):
            c = UNDO_COST[app_of(holders[0])]
            cost = max(cost, c); reasons.append(f"{base}: saved by {app_of(holders[0])}, old content in its undo history ({c} actions)")
        else:
            return False, f"{base}: {f['kind']}, old content survives nowhere", None
    if created and not cost:
        cost = 1; reasons.append("new files only: remove them")
    if cost > 3:
        return False, "; ".join(reasons) + " -> more than 3 actions", cost
    return True, "; ".join(reasons) or "no file content lost", cost


def main():
    pred = json.loads((OUT / "model_forward_k3_v5w.json").read_text())["rows"]
    rows, truth, head = {}, {}, {}
    for f in range(5):
        for l in (HERE / "data_k3_v5" / f"fold{f}_test.jsonl").read_text().splitlines():
            d = json.loads(l)
            if d["task"] == "FORWARD":
                rows[d["row_id"]] = d
            elif d["task"] == "REVERSIBLE":
                truth[d["row_id"]] = d["target"].startswith("yes")
        m = json.loads((HERE / "runs" / "modal" / "k3_v5w" / f"fold{f}.json").read_text())
        for rid, t, p in m["_curves"]["REVERSIBLE"]:
            head[rid] = p >= 0.5
    ids = sorted(r for r in pred if r in truth and r in head)
    res, per = {"n": len(ids)}, {}
    for name, src in (("recorded", "target"), ("predicted", "text")):
        right, wrong = 0, []
        for r in ids:
            rev, why, _ = decide(rows[r]["prompt"], pred[r][src])
            per.setdefault(r, {"truth": truth[r], "head": head[r]})[name] = [rev, why]
            if rev == truth[r]:
                right += 1
            else:
                wrong.append(r)
        res[f"rule_on_{name}"] = {"accuracy": round(right / len(ids), 3), "right": right, "wrong": wrong}
    res["learned_head"] = {"accuracy": round(sum(head[r] == truth[r] for r in ids) / len(ids), 3)}
    hr = [r for r in ids if per[r]["predicted"][0] == truth[r] and head[r] != truth[r]]
    rh = [r for r in ids if per[r]["predicted"][0] != truth[r] and head[r] == truth[r]]
    res["predicted_rule_vs_head"] = {"rule_only_right": len(hr), "head_only_right": len(rh), "rule_only": hr, "head_only": rh}
    from math import comb
    n, k = len(hr) + len(rh), min(len(hr), len(rh))
    res["predicted_rule_vs_head"]["sign_p"] = round(min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n), 3) if n else 1.0
    (OUT / "symbolic_rule.json").write_text(json.dumps({**res, "per_row": per}, indent=1))
    print(json.dumps({k: ({kk: vv for kk, vv in v.items() if kk != "wrong"} if isinstance(v, dict) else v) for k, v in res.items()}, indent=1))


if __name__ == "__main__":
    main()
