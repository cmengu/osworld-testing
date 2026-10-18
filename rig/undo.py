"""Undo candidates (Paper draft 4.5, budget B about 55): Tier 1 generic, Tier 2 Calc-specific, Tier 3 proposed
(rig/proposer.py), Tier 4 blind pairs of generic atoms.  A candidate is a list of steps in the small step
language shared with the proposer:

    key:<chord>      pyautogui.hotkey / press        type:<text>     pyautogui.typewrite
    wait:<s>         time.sleep                      reopen          relaunch or reopen the task file, maximised
    menu:alt+e,u     open a menu by Alt accelerator, press the item's mnemonic letters

Every step is something a user could do at the keyboard; nothing here touches snapshots, backups or copies.
"""
import itertools
import shlex
from typing import List

Candidate = List[str]

GENERIC: List[Candidate] = [
    ["key:ctrl+z"],
    ["key:ctrl+z", "key:ctrl+home"],        # second since 18 Oct: after a real undo the cursor sits on the undone cell
    ["key:ctrl+z", "key:ctrl+z"],
    ["key:ctrl+z", "key:ctrl+z", "key:ctrl+z"],
    ["key:escape"],
    ["key:escape", "key:escape"],
    ["key:ctrl+home"],
    ["reopen"],
    ["key:escape", "key:ctrl+z"],
    ["key:escape", "key:ctrl+home"],
]

# Calc-specific routes.  Probed 17 Oct 2026: a menu opened by its Alt accelerator has its first item focused, so
# Edit > Undo is Alt+E then Enter.  File > Reload sits deep in a menu with state-dependent disabled items and is
# left out; "discard and reopen" covers the same ground.
MNEMONICS = {}
CALC: List[Candidate] = [
    ["key:ctrl+w", "key:alt+d", "reopen"],                       # discard the open document and reopen the file
    ["key:alt+e", "key:enter"],                                  # Edit > Undo (first item of the Edit menu)
    ["key:ctrl+shift+l"],                                        # AutoFilter toggles back
    ["key:ctrl+z", "key:ctrl+s", "wait:4", "key:enter", "wait:3"],  # undo in memory, then save the undone state back
    ["key:ctrl+z", "key:ctrl+s", "wait:4", "key:enter", "wait:3", "key:ctrl+y"],  # ...then redo the edit: a save after
                                                                 # an unsaved edit undone with the edit back on screen (pilot2: 0126, 0210)
    ["key:ctrl+w", "key:alt+d", "reopen", "key:ctrl+home"],       # discard, reopen, cursor home
]

# atoms for the blind pair tier
ATOMS = ["key:ctrl+z", "key:escape", "key:enter", "key:ctrl+home", "key:ctrl+shift+l", "key:alt+c", "reopen"]


def blind_pairs(exclude: List[Candidate], limit: int = 40) -> List[Candidate]:
    seen = {tuple(c) for c in exclude}
    out = []
    for a, b in itertools.product(ATOMS, repeat=2):
        c = [a, b]
        if tuple(c) in seen:
            continue
        seen.add(tuple(c))
        out.append(c)
        if len(out) >= limit:
            break
    return out


def fill_mnemonics(c: Candidate, mnemonics=None) -> Candidate:
    m = dict(MNEMONICS, **(mnemonics or {}))
    out = []
    for s in c:
        for k, v in m.items():
            s = s.replace("{" + k + "}", v)
        out.append(s)
    return out


def describe(c: Candidate) -> str:
    return " ; ".join(c)


# ---------------------------------------------------------------------------------------------------------
# step -> pyautogui code.  `ctx` carries what the reopen macro needs: the document path and whether a
# LibreOffice window exists right now (read from the window list of the state the candidate starts from).
# ---------------------------------------------------------------------------------------------------------
def _py(s: str) -> str:
    return repr(s)


def step_code(step: str, ctx: dict) -> str:
    kind, _, arg = step.partition(":")
    if kind == "key":
        parts = [p.strip().lower() for p in arg.split("+") if p.strip()]
        parts = ["esc" if p == "escape" else p for p in parts]
        if len(parts) == 1:
            return f"pyautogui.press({_py(parts[0])}); time.sleep(0.8)"
        return "pyautogui.hotkey(" + ", ".join(_py(p) for p in parts) + "); time.sleep(0.8)"
    if kind == "type":
        return f"pyautogui.typewrite({_py(arg)}); time.sleep(0.5)"
    if kind == "wait":
        return f"time.sleep({min(float(arg), 8.0)})"
    if kind == "menu":
        chord, _, letters = arg.partition(",")
        parts = [p.strip().lower() for p in chord.split("+")]
        code = "pyautogui.hotkey(" + ", ".join(_py(p) for p in parts) + "); time.sleep(1.5)"
        for ch in letters.strip().lower():
            code += f"; pyautogui.press({_py(ch)}); time.sleep(1.0)"
        return code + "; time.sleep(1.5)"
    if kind == "reopen":
        path = ctx.get("doc_path") or ""
        if ctx.get("office_running"):
            # Start Center or another window: open the file through the Open dialog
            return ("pyautogui.hotkey('ctrl', 'o'); time.sleep(3); pyautogui.typewrite(" + _py(path) + "); time.sleep(1); "
                    "pyautogui.press('enter'); time.sleep(8); pyautogui.hotkey('super', 'up'); time.sleep(3)")
        # no LibreOffice at all: the GNOME run dialog
        return ("pyautogui.hotkey('alt', 'f2'); time.sleep(2); pyautogui.typewrite(" + _py("libreoffice --calc " + shlex.quote(path)) + "); time.sleep(1); "
                "pyautogui.press('enter'); time.sleep(15); pyautogui.hotkey('super', 'up'); time.sleep(3)")
    raise ValueError(f"unknown step {step!r}")


def candidate_code(c: Candidate, ctx: dict) -> str:
    return "; ".join(step_code(s, ctx) for s in c)
