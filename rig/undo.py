"""Undo candidates (Paper draft 4.5, budget B about 55): Tier 1 generic, Tier 2 Calc-specific, Tier 3 proposed
(rig/proposer.py), Tier 4 blind pairs of generic atoms.  A candidate is a list of steps in the small step
language shared with the proposer:

    key:<chord>      pyautogui.hotkey / press        type:<text>     pyautogui.typewrite, at most TYPE_MAX characters
    wait:<s>         time.sleep                      reopen          relaunch or reopen the task file, maximised
    menu:alt+e,u     open a menu by Alt accelerator, press the item's mnemonic letters

Every step is something a user could do at the keyboard; nothing here touches snapshots, backups or copies.
K counts actions, not steps: a wait is not an action (action_count).
"""
import itertools
import re
import shlex
from typing import List, Optional

Candidate = List[str]
# Cap on one type: step (decided 19 Oct 2026).  Retyping a lost cell value from the before-state is a legitimate
# undo (definition, part 3); retyping a whole document is not a "few actions".  20 characters covers every value
# the click-spots type ('pilot', 'hello', '=1+1') with room to spare.
TYPE_MAX = 20

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
    ["key:ctrl+w"],                                              # close a window the action opened (new document, 0181)
    ["key:ctrl+w", "wait:2", "key:alt+n", "reopen"],             # discard the open document and reopen the file (Don't Save
                                                                 # is Alt+N on this image; Alt+D, used until 19 Oct, opens Data)
    ["key:alt+e", "key:enter"],                                  # Edit > Undo (first item of the Edit menu)
    ["key:ctrl+shift+l"],                                        # AutoFilter toggles back
    ["key:ctrl+z", "key:ctrl+s", "wait:4", "key:enter", "wait:3"],  # undo in memory, then save the undone state back
    ["key:ctrl+z", "key:ctrl+s", "wait:4", "key:enter", "wait:3", "key:ctrl+y"],  # ...then redo the edit: a save after
                                                                 # an unsaved edit undone with the edit back on screen (pilot2: 0126, 0210)
    ["key:ctrl+z", "key:ctrl+s", "wait:4", "key:enter", "wait:3", "key:ctrl+y", "key:ctrl+home"],  # redo leaves the redone
                                                                 # range selected (recheck 0210: 87 cells differed only in `selected`)
    ["key:ctrl+w", "wait:2", "key:alt+n", "reopen", "key:ctrl+home"],  # discard, reopen, cursor home
]

# Files (GNOME Files 42) routes, from its key list (help-overlay.ui) and the undo manager (research note, 19 Oct):
# one undo step, redo is Ctrl+Shift+Z, navigation back / forward / up undo a change of folder.  Unprobed.
FILES: List[Candidate] = [
    ["key:ctrl+shift+z"],
    ["key:alt+left"],
    ["key:alt+right"],
    ["key:alt+up"],
    ["key:escape", "key:ctrl+z"],
    ["key:ctrl+w", "wait:2", "reopen"],
]


def tier2(app: str) -> List[Candidate]:
    """The application-specific tier: Calc's for Calc rows, Files' for Files rows, both for multi_apps rows."""
    if app == "files":
        return FILES
    if app == "libreoffice-calc":
        return CALC
    return CALC + FILES


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
        if len(arg) > TYPE_MAX:
            raise ValueError(f"type: step longer than {TYPE_MAX} characters")
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
        if ctx.get("reopen_cmd"):
            # rows outside Calc name their own reopen: the program and folder or file the task opened
            return ("__import__('subprocess').Popen(" + _py(list(ctx["reopen_cmd"])) + ", start_new_session=True, "
                    "stdout=__import__('subprocess').DEVNULL, stderr=__import__('subprocess').DEVNULL); time.sleep(10); "
                    "pyautogui.hotkey('super', 'up'); time.sleep(3)")
        path = ctx.get("doc_path") or ""
        if ctx.get("office_running"):
            # Start Center or another window: open the file through the Open dialog
            return ("pyautogui.hotkey('ctrl', 'o'); time.sleep(3); pyautogui.typewrite(" + _py(path) + "); time.sleep(1); "
                    "pyautogui.press('enter'); time.sleep(8); pyautogui.hotkey('super', 'up'); time.sleep(3)")
        # no LibreOffice at all: start it on the file, as a double-click in the file manager would.  The GNOME run
        # dialog (Alt+F2) used before never opened anything on this image (pilot2 0141: every reopen after Ctrl+Q
        # left no window).
        return ("__import__('subprocess').Popen(['libreoffice', '--calc', " + _py(path) + "], start_new_session=True, "
                "stdout=__import__('subprocess').DEVNULL, stderr=__import__('subprocess').DEVNULL); time.sleep(15); "
                "pyautogui.hotkey('super', 'up'); time.sleep(3)")
    raise ValueError(f"unknown step {step!r}")


def candidate_code(c: Candidate, ctx: dict) -> str:
    return "; ".join(step_code(s, ctx) for s in c)


# ---------------------------------------------------------------------------------------------------------
# Parsing undo sequences written by a model (guess B, the proposer).  Since 19 Oct guess B answers in the step
# language above; its older free-text answers ("ctrl+z (undo typing 'pilot' in H33)", "enter (Keep Current
# Format)") are still read for the rows collected before that.  Rerun 0266 (19 Oct) is why the step language
# matters: guess B's retype undo ("reopen ...", "type 'pilot' and press enter") had no free-text parse, so the
# undo the label hinged on was never executed.
# ---------------------------------------------------------------------------------------------------------
_KEY_TOKEN = re.compile(r"^(?:(?:ctrl|alt|shift|super)\+)*(?:[a-z0-9]|f[0-9]{1,2}|enter|escape|esc|tab|space|delete|backspace|home|end|"
                        r"up|down|left|right|pageup|pagedown|plus|minus|-|\+)$")
_MENU = re.compile(r"^menu:alt\+[a-z],[a-z]{1,4}$")
MAX_STEPS = 8


def parse_step(raw) -> Optional[str]:
    """One step in the step language, normalised, or None when it is not one (or a type: step is over TYPE_MAX)."""
    s = str(raw).strip()
    kind, sep, arg = s.partition(":")
    kind = kind.strip().lower()
    if not sep:
        return "reopen" if kind == "reopen" else None
    if kind == "key":
        tok = arg.strip().lower().replace(" ", "")
        tok = "escape" if tok == "esc" else tok
        return "key:" + tok if _KEY_TOKEN.match(tok) else None
    if kind == "type":
        return "type:" + arg if 0 < len(arg) <= TYPE_MAX else None
    if kind == "wait":
        try:
            return f"wait:{min(float(arg), 8.0):g}"
        except ValueError:
            return None
    if kind == "menu":
        m = "menu:" + arg.strip().lower().replace(" ", "")
        return m if _MENU.match(m) else None
    return None


def parse_steps(steps) -> Optional[Candidate]:
    """A whole sequence in the step language, or None if any step is not."""
    if not steps or not isinstance(steps, list) or len(steps) > MAX_STEPS:
        return None
    out = [parse_step(x) for x in steps]
    return None if any(x is None for x in out) else out


def action_count(c: Candidate) -> int:
    """Actions in a candidate, the unit of K: waits are not actions, a reopen is one."""
    return sum(1 for s in c or [] if not s.startswith("wait:"))


def _from_free_text(steps) -> Optional[Candidate]:
    out: Candidate = []
    for raw in steps:
        tok = str(raw).strip().lower().split(" ", 1)[0].split("(", 1)[0].strip().rstrip(",;.")
        tok = "escape" if tok == "esc" else tok
        if tok in ("reopen", "reload"):
            out.append("reopen")
        elif _KEY_TOKEN.match(tok):
            out.append("key:" + tok)
            if tok == "ctrl+s":
                out.append("wait:4")      # the keep-format question takes a moment to appear
        else:
            return None
    return out


def from_guess(steps) -> Optional[Candidate]:
    """Guess B's shortest_undo as a candidate: the step language first, the pre-19-Oct free text second; None
    when neither reads every step."""
    return guess_parse(steps)[0]


def guess_parse(steps):
    """(candidate or None, how): how is 'step-language', 'free-text', 'empty' or 'unparsed'."""
    if not steps or not isinstance(steps, list):
        return None, "empty"
    if len(steps) > MAX_STEPS:
        return None, "unparsed"
    c = parse_steps(steps)
    if c is not None:
        return c, "step-language"
    c = _from_free_text(steps)
    if c is not None:
        return c, "free-text"
    return None, "unparsed"
