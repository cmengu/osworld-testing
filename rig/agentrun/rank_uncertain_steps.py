"""Rank the scored agent steps by how likely the model is wrong or unsure (2 Nov 2026, read-only, TEST ONLY rows).

Score per step, higher = more worth a human look:
  unsure      = 1 - 2*|p_yes - 0.5|          (0.5 -> 1, 0 or 1 -> 0)
  split       = max - min across the 5 adapters
  vs_claude   = 1 if the model and Claude's guess disagree
  vs_rig      = 1 if the model and a usable rig label disagree
  vs_human    = 1 if the model and the author's final lenient label disagree (19 steps only)
  new_kind    = 1 if the action is a click, heredoc, chmod or terminal command (kinds training lacks)
"""
import json
import pathlib
import re
import sys

BASE = pathlib.Path("/Users/ngchenmeng/ai-research/osworld-testing")
OUT = BASE / "rig" / "out" / "model_on_agent"
preds = json.load(open(OUT / "predictions.json"))["rows"]
rows = {r["id"]: r for r in json.load(open(BASE / "rig/out/review_page/rows.json"))}
mm = json.load(open(OUT / "replay_mismatch.json"))
excluded, unclear = set(mm["excluded"]), set(mm["unclear"])
replayed = {json.loads(l)["row_id"] for l in open(OUT / "prompts.jsonl") if json.loads(l).get("state_source") == "rig replay"}
final = {x["id"]: x for x in json.load(open(BASE / "rig/agentrun/comparison_final_20261102.json"))["lenient"]}


def kind(code):
    c = code or ""
    if "<<" in c or "EOF" in c:
        return "heredoc"
    if re.search(r"\bchmod\b|\bchown\b", c):
        return "chmod"
    if re.search(r"\b(rm|mv|cp|sudo|useradd|usermod|touch|sed|echo)\b", c) and ("typewrite" in c or "write(" in c):
        return "terminal"
    if "click" in c:
        return "click"
    if "hotkey" in c or "press" in c:
        return "key"
    if "typewrite" in c or "write" in c:
        return "type"
    return "other"


table = []
for rid, p in preds.items():
    r = rows.get(rid, {})
    if rid in excluded and rid in replayed:
        continue  # prediction on a state that is not the agent's
    ys = p["reversible_yes"]
    py, spread = sum(ys) / len(ys), max(ys) - min(ys)
    pr = sum(p["guard_refuse"]) / len(p["guard_refuse"])
    model = py >= 0.5
    claude = None if r.get("teacher") is None else r["teacher"] == "reversible"
    rig_lbl = r.get("rig") or ""
    rig = None if rid in excluded else (True if rig_lbl.startswith("REVERSIBLE") else False if rig_lbl == "NO-UNDO-FOUND" else None)
    h = final.get(rid, {}).get("human")
    k = kind(r.get("code"))
    reasons = []
    unsure = 1 - 2 * abs(py - 0.5)
    if unsure >= 0.6:
        reasons.append(f"p={py:.2f} near 0.5")
    if spread >= 0.4:
        reasons.append(f"adapters split {min(ys):.2f}-{max(ys):.2f}")
    if claude is not None and claude != model:
        reasons.append("vs Claude")
    if rig is not None and rig != model:
        reasons.append("vs rig" + (" (unclear replay)" if rid in unclear else ""))
    if h is not None and h != model:
        reasons.append("vs author")
    if k in ("click", "heredoc", "chmod", "terminal"):
        reasons.append(f"kind: {k}")
    score = unsure + spread + (claude is not None and claude != model) + (rig is not None and rig != model) + 1.5 * (h is not None and h != model) + 0.5 * (k in ("heredoc", "chmod", "terminal", "click"))
    table.append({"id": rid, "score": round(score, 2), "p_yes": round(py, 2), "spread": round(spread, 2), "p_refuse": round(pr, 2),
                  "model": model, "claude": claude, "rig": rig, "author": h, "kind": k, "reviewed": rid in final,
                  "run": r.get("run"), "code": (r.get("code") or "")[:90].replace("\n", " "), "reasons": reasons})

table.sort(key=lambda x: -x["score"])
pathlib.Path(BASE / "rig/agentrun/uncertain_steps_20261102.json").write_text(json.dumps(table, indent=1))
n = len(table)
print(f"{n} agent steps with a usable prediction; {sum(x['reviewed'] for x in table)} already reviewed by the author")
print(f"model unsure (p 0.3-0.7): {sum(0.3 <= x['p_yes'] <= 0.7 for x in table)}; adapters split >= 0.4: {sum(x['spread'] >= 0.4 for x in table)}")
print(f"disagrees with Claude: {sum(x['claude'] is not None and x['claude'] != x['model'] for x in table)} of {sum(x['claude'] is not None for x in table)}")
print(f"disagrees with rig: {sum(x['rig'] is not None and x['rig'] != x['model'] for x in table)} of {sum(x['rig'] is not None for x in table)}")
print(f"kinds: " + ", ".join(f"{k} {sum(x['kind'] == k for x in table)}" for k in ("click", "key", "type", "terminal", "heredoc", "chmod", "other")))
print()
print(f"{'step':34} {'p_yes':>5} {'split':>5} {'model':>6} {'Claude':>6} {'rig':>5} {'author':>6} {'kind':8} why")
for x in table:
    f = lambda v: "-" if v is None else ("undo" if v else "1way")
    print(f"{x['id']:34} {x['p_yes']:5.2f} {x['spread']:5.2f} {f(x['model']):>6} {f(x['claude']):>6} {f(x['rig']):>5} {f(x['author']):>6} {x['kind']:8} {'; '.join(x['reasons'])}")
