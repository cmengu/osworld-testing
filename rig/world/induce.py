"""P3 (rig/plan_forward_model.md): rule induction.  The model grows from recorded data and stays symbolic.

Loop, DEV only (the inducer never sees a TEST transition):
  1. Misses: DEV transitions where T (base + accepted rules) says nothing, grouped by family, largest first.
  2. Claude (subscription, rig.teacher._claude) gets the rule API and 3 recorded examples of one group: the state
     excerpt T can read, the action, and the recorded change (which files changed and how, the window change).
     It writes ONE general rule:  def rule(ev, cmd, st, screen) -> Optional[Delta].
  3. The rule runs on every DEV transition where T is silent.  Accepted only if it makes >= 2 transitions exact and
     fires wrongly on none ("break" = it returns a Delta that is not exact).  Accepted rules go to
     rig/world/rules_induced/r_NNN.py and the ledger (rig/world/rules_induced/ledger.jsonl).
  4. After each accepted rule: DEV and TEST coverage and exactness (TEST read only, for the learning curve).

    OSWorld/.venv/bin/python -I rig/world/induce.py --rounds 12
"""
import argparse
import collections
import json
import pathlib
import re
import sys
import textwrap
import time

BASE = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path[:0] = [str(BASE), str(BASE / "rig")]
from rig.snapshot import load_snapshot                                  # noqa: E402
from rig.symbolic import typed_command                                  # noqa: E402
from rig.symbolic_gui import Screen, events                             # noqa: E402
from rig.world import T as TM                                           # noqa: E402
from rig.world.score_forward import corpus, holds, truth                # noqa: E402

RULES_DIR = BASE / "rig" / "world" / "rules_induced"
LEDGER = RULES_DIR / "ledger.jsonl"

API = '''You write ONE transition rule for a symbolic world model of an Ubuntu desktop (GNOME, LibreOffice, VS Code, GNOME Files,
terminal).  The model predicts which files a step changes.  Write a Python function, nothing else:

def rule(ev, cmd, st, screen):
    """Return a Delta when this rule applies to the step, else None."""

Inputs:
  ev      list of input events of the step, in order: ("key", "enter"), ("hotkey", "ctrl+shift+s"), ("type", "text"),
          ("click", x, y, "click"), ("view", "scroll"), ("maybe-enter",).  None when the step is not plain pyautogui.
  cmd     the shell command line when the step types a command into a terminal (lines joined with " ; "), else None.
  st      the state before the step:
            st.files  dict path -> {"s": size, "h": content hash, "mode": int, ...} for every file under /home/user
            st.dirs   set of folder paths (no trailing slash)
            st.titles list of window titles, e.g. "report.docx - LibreOffice Writer", "Desktop" (GNOME Files), "user@host: ~"
            st.system dict (users, groups, crontab, sudoers_d, hosts, ...)
            st.doc_path(basename) -> the one full path with that file name, or None
            st.lock_of(path) -> LibreOffice's lock file path for a document
            st.tree   the accessibility tree XML (a string; elements have name="..." and st:selected="true" etc.)
  screen  screen.question() -> "save-changes" | "delete" | "empty-trash" | "replace" | None (an open question dialog);
          screen.named_file() -> a file name quoted in that dialog, or None; screen.at(x, y) -> (tag, name) under a click

Return Delta(files={path: value, ...}, windows="same"|"opens"|"closes"|"unknown", rules=["<short rule name>"]) where value is
  ("absent",)  ("content", other_path_before)  ("empty",)  ("dir",)  ("sym", "why")  ("sym-or-same", "why")  ("maybe-absent",)
List ONLY the paths the step changes; folders end with "/".  `Delta` and the modules re, posixpath, fnmatch are available.
Make it GENERAL (no file names or paths from the examples hard-coded); return None whenever you are not sure.
'''


def load_dev():
    """Every DEV transition with what T reads and the recorded truth (loaded once)."""
    out = []
    for t in corpus():
        S, S1 = load_snapshot(t["S"]), load_snapshot(t["S1"])
        a, b, changed, sysch, win = truth(S, S1)
        out.append({**t, "st": TM.WState(S), "a": a, "b": b, "changed": changed, "win": win})
    return out


def exact(d, x):
    if d is None:
        return None
    strict = {p for p, v in d.files.items() if v[0] not in ("sym-or-same", "maybe-absent")}
    maybe = {p for p, v in d.files.items() if v[0] in ("sym-or-same", "maybe-absent")}
    return not (strict - x["changed"]) and not (x["changed"] - strict - maybe) and all(holds(p, d.files[p], x["a"], x["b"]) for p in strict)


def load_rules():
    rules = []
    for f in sorted(RULES_DIR.glob("r_*.py")):
        ns = {"Delta": TM.Delta, "re": re, "posixpath": TM.posixpath, "fnmatch": TM.fnmatch}
        exec(compile(f.read_text(), str(f), "exec"), ns)
        rules.append((f.stem, ns["rule"]))
    return rules


def predict(x, rules):
    try:
        d = TM._base(x["code"], x["st"])
    except Exception:  # noqa: BLE001
        d = None
    if d is not None:
        return d, "base"
    ev = events(x["code"])
    cmd = typed_command(x["code"])
    screen = Screen(x["st"].tree, x["st"].windows)
    for name, fn in rules:
        try:
            d = fn(ev, cmd, x["st"], screen)
        except Exception:  # noqa: BLE001  a crashing rule is silent here
            d = None
        if d is not None:
            return d, name
    return None, None


def describe(x):
    st = x["st"]
    lines = [f"WINDOW TITLES: {st.titles}"]
    q = Screen(st.tree, st.windows)
    if q.question():
        lines.append(f"QUESTION DIALOG: {q.question()} (names a file: {q.named_file()})")
    sel = sorted(set(re.findall(r'name="([^"]+)"[^>]*st:selected="true"', st.tree)))[:8]
    if sel:
        lines.append(f"SELECTED ELEMENTS: {sel}")
    near = set()
    for p in x["changed"]:
        d = p.rstrip("/").rsplit("/", 1)[0]
        near |= {f for f in st.files if f.startswith(d + "/") and f.count("/") == p.rstrip("/").count("/")}
    lines.append("FILES NEAR THE CHANGE (before): " + ", ".join(f"{f} ({st.files[f].get('s')} B)" for f in sorted(near)[:15]))
    lines.append(f"ACTION CODE: {x['code'][:700]}")
    ch = []
    for p in sorted(x["changed"]):
        bv, av = x["a"].get(p), x["b"].get(p)
        if av is None:
            ch.append(f"{p}: now absent")
        else:
            same = [q for q, v in x["a"].items() if v and (v.get("h") or v.get("c")) and (v.get("h"), v.get("c")) == (av.get("h"), av.get("c"))]
            ch.append(f"{p}: {'new' if bv is None else 'changed'}, {av.get('s')} B" + (f", same content as {same[0]} before" if same else ""))
    lines.append("RECORDED CHANGE: " + ("; ".join(ch) if ch else "no file changed") + f"; windows: {x['win']}")
    return "\n".join(lines)


def ask(cluster):
    from rig.teacher import _claude
    examples = "\n\n".join(f"EXAMPLE {i + 1}\n{describe(x)}" for i, x in enumerate(cluster[:3]))
    user = f"These recorded steps share one behaviour the model does not cover yet ({cluster[0]['family']}).\n\n{examples}\n\nWrite the rule."
    res = _claude(API, user)
    text = res.get("result") or ""
    m = re.search(r"```(?:python)?\n(.*?)```", text, re.S)
    return (m.group(1) if m else text).strip(), res.get("ok")


def score_all(xs, rules):
    out = {}
    for split in ("DEV", "TEST"):
        ys = [x for x in xs if x["split"] == split]
        dec = ex = 0
        for x in ys:
            d, _ = predict(x, rules)
            if d is not None:
                dec += 1
                ex += bool(exact(d, x))
        out[split] = {"n": len(ys), "coverage": round(dec / max(1, len(ys)), 3), "exact": round(ex / max(1, dec), 3)}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=12)
    a = ap.parse_args()
    RULES_DIR.mkdir(parents=True, exist_ok=True)
    xs = load_dev()
    dev = [x for x in xs if x["split"] == "DEV"]
    rules = load_rules()
    print("start:", json.dumps(score_all(xs, rules)), flush=True)
    tried = set()
    for rnd in range(a.rounds):
        misses = [x for x in dev if predict(x, rules)[0] is None]
        groups = collections.defaultdict(list)
        for x in misses:
            groups[x["family"]].append(x)
        cand = [g for f, g in sorted(groups.items(), key=lambda kv: -len(kv[1])) if len(g) >= 2 and f not in tried]
        if not cand:
            print("no more groups", flush=True)
            break
        cluster = cand[0]
        fam = cluster[0]["family"]
        tried.add(fam)
        code, ok = ask(cluster)
        ns = {"Delta": TM.Delta, "re": re, "posixpath": TM.posixpath, "fnmatch": TM.fnmatch}
        try:
            exec(compile(code, "<induced>", "exec"), ns)
            fn = ns["rule"]
        except Exception as exc:  # noqa: BLE001
            rec = {"round": rnd, "family": fam, "accepted": False, "why": f"does not compile: {exc!r}"[:200]}
            print(json.dumps(rec), flush=True)
            LEDGER.open("a").write(json.dumps({**rec, "code": code}) + "\n")
            continue
        fixes = breaks = 0
        for x in misses:
            try:
                d = fn(events(x["code"]), typed_command(x["code"]), x["st"], Screen(x["st"].tree, x["st"].windows))
            except Exception:  # noqa: BLE001
                d = None
            if d is None:
                continue
            if exact(d, x):
                fixes += 1
            else:
                breaks += 1
        accepted = fixes >= 2 and breaks == 0
        rec = {"round": rnd, "family": fam, "group_size": len(cluster), "fixes": fixes, "breaks": breaks, "accepted": accepted,
               "date": time.strftime("%Y-%m-%d %H:%M")}
        if accepted:
            name = f"r_{len(rules) + 1:03d}"
            (RULES_DIR / f"{name}.py").write_text(f'"""Induced {rec["date"]} from DEV family: {fam}\nfixes {fixes}, breaks 0."""\n' + code + "\n")
            rules = load_rules()
            rec["rule"] = name
            rec["after"] = score_all(xs, rules)
        LEDGER.open("a").write(json.dumps({**rec, "code": code}) + "\n")
        print(json.dumps(rec), flush=True)
    print("end:", json.dumps(score_all(xs, rules)), flush=True)


if __name__ == "__main__":
    main()
