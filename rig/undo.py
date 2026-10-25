"""Undo candidates (Paper draft 4.5, budget B about 55): Tier 1 generic, Tier 2 Calc-specific, Tier 3 proposed
(rig/proposer.py), Tier 4 blind pairs of generic atoms.  A candidate is a list of steps in the small step
language shared with the proposer:

    key:<chord>      pyautogui.hotkey / press        reopen          relaunch or reopen the task file, maximised
    wait:<s>         time.sleep                      menu:alt+e,u    open a menu by Alt accelerator, press the item's mnemonic letters
    confirm          Enter, only if a window (a question) opened since the candidate began (24 Oct)
    click:<label>    press the named button, menu entry or sidebar row through its accessibility action (22 Oct)

Every step is something a user could do at the keyboard with what the applications themselves offer; nothing here
touches snapshots, backups or copies.  No typing (decided with the author 20 Oct 2026): re-entering lost content or
typing commands is not an undo; if the application cannot bring the state back, it is gone.  The type: step and its
20-character cap (19 Oct) were dropped.
K counts actions, not steps: a wait is not an action (action_count).
"""
import itertools
import re
import shlex
from typing import List, Optional

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
    ["key:ctrl+w"],                                              # close a window the action opened (new document, 0181)
    ["key:ctrl+w", "wait:2", "key:alt+n", "reopen"],             # discard the open document and reopen the file (Don't Save
                                                                 # is Alt+N on this image; Alt+D, used until 19 Oct, opens Data)
    ["key:alt+e", "key:enter"],                                  # Edit > Undo (first item of the Edit menu)
    ["key:ctrl+shift+l"],                                        # AutoFilter toggles back
    ["key:ctrl+z", "key:ctrl+s", "wait:4", "confirm", "wait:3"],  # undo in memory, then save the undone state back
    ["key:ctrl+z", "key:ctrl+s", "wait:4", "confirm", "wait:3", "key:ctrl+y"],  # ...then redo the edit: a save after
                                                                 # an unsaved edit undone with the edit back on screen (pilot2: 0126, 0210)
    ["key:ctrl+z", "key:ctrl+s", "wait:4", "confirm", "wait:3", "key:ctrl+y", "key:ctrl+home"],  # redo leaves the redone
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
    ["key:alt+f4"],                        # close the window the action opened (a terminal, a compose window)
    ["key:ctrl+w"],                        # close the tab or editor the action opened
    ["key:ctrl+w", "wait:2", "reopen"],
    ["key:escape", "key:shift+delete", "wait:2", "key:alt+d"],   # a folder the action created, deleted for good (Ctrl+Z
                                                                 # does not undo New Folder, probe; v2-0085, 25 Oct)
]


# VS Code (24 Oct): a save has no dialog, so Calc's "Ctrl+S, Enter" route would type a newline; the undo of a
# saved edit is Ctrl+Z then Ctrl+S; a closed editor comes back with Ctrl+Shift+T; a palette, a find widget or a
# settings tab closes with Escape or Ctrl+W (generic tier).  Unprobed except Ctrl+W (probe-0027).
VSCODE: List[Candidate] = [
    ["key:ctrl+z", "key:ctrl+s", "key:ctrl+y"],                  # a save after an edit: file back, edit back on screen (v2-0044)
    ["key:ctrl+z", "key:ctrl+s"],
    ["key:ctrl+z", "key:ctrl+z", "key:ctrl+s"],
    ["key:ctrl+shift+t"],
    ["key:ctrl+shift+k"],                                        # delete the line the action added
    ["key:ctrl+w", "wait:2", "reopen"],
    ["key:alt+f4"],
]

# Thunderbird (24 Oct): a compose window with content asks "Save message?" on close (Don't Save is Alt+N as in
# LibreOffice's dialog on this image, to be confirmed by the smoke rows); a moved or deleted message comes back
# with Ctrl+Z; a tab (address book, settings) closes with Ctrl+W; a toggled flag toggles back with the same key.
THUNDERBIRD: List[Candidate] = [
    ["key:alt+f4"],
    ["key:alt+f4", "wait:2", "click:Discard changes"],                  # the Save Message question's button is 'Discard changes' (tree of v2-0053 S1, 24 Oct)
    ["key:ctrl+w", "wait:2", "click:Discard changes"],
    ["key:alt+f4", "wait:2", "key:alt+n"],
    ["key:ctrl+w"],
    ["key:ctrl+z"],
    ["key:m"],                                                   # mark read/unread toggles back
    ["key:s"],                                                   # star toggles back
    ["key:ctrl+z", "key:ctrl+z"],
]


def tier2(app: str) -> List[Candidate]:
    """The application-specific tier: Calc's for the LibreOffice applications (Writer and Impress share its
    dialogs and key routes), Files' for Files rows, VS Code's and Thunderbird's for theirs, Files' + Calc's for
    multi_apps rows."""
    if app == "files":
        return FILES
    if app in ("libreoffice-calc", "libreoffice-writer", "libreoffice-impress"):
        return CALC
    if app == "vs_code":
        return VSCODE + [c for c in FILES if c not in VSCODE]
    if app == "thunderbird":
        return THUNDERBIRD + [c for c in FILES if c not in THUNDERBIRD]
    return FILES + [c for c in CALC if c not in FILES]   # multi_apps: the cheap generic window moves first


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
        raise ValueError("type: is not an undo step (dropped 20 Oct 2026); a terminal command is shell:")
    if kind == "shell":
        # since 25 Oct (decided with the author, "execute this then"): a command typed into the terminal and run, the
        # natural undo of a terminal action (cp a copy -> rm it, mv -> mv back, convert-to -> rm the output; v2-0069,
        # 0078, 0079 were NO-UNDO-FOUND by construction without it).  The terminal window is brought to the front first.
        return ("__import__('subprocess').run(['wmctrl', '-a', 'user@user-virtual-machine'], timeout=15); time.sleep(1.5); "
                f"pyautogui.typewrite({_py(arg)}, interval=0.02); pyautogui.press('enter'); time.sleep(3)")
    if kind == "focus":
        # since 25 Oct: bring the newest window to the front, so a window-closing key reaches the window the action
        # opened and not the one that kept the focus (v2-0090: Writer opened from a terminal without the focus;
        # Alt+F4 closed the terminal).  wmctrl lists windows in mapping order, the newest last.
        if arg != "newest":
            raise ValueError(f"unknown focus target {arg!r}")
        return ("__import__('subprocess').run(['sh', '-c', 'w=$(wmctrl -l | grep -v \"@!\" | tail -1 | cut -d\" \" -f1); "
                "[ -n \"$w\" ] && wmctrl -i -a \"$w\"'], timeout=15); time.sleep(1.5)")
    if kind == "click":
        # a named control on screen, pressed through its accessibility action (22 Oct, decided with the author):
        # a button, a menu entry, a sidebar row.  ctx["proc"] names the application to search ("*" = all)
        from rig.dialog_keys import click_code
        return click_code(arg, settle=3, proc=ctx.get("proc") or "*")
    if kind == "wait":
        return f"time.sleep({min(float(arg), 8.0)})"
    if kind == "confirm":
        # Enter for a question the previous step may have opened (Keep Current Format, Save Document?), pressed only
        # when a window appeared since the candidate began: on this image LibreOffice saves .pptx/.docx without the
        # Keep Current Format question, and a blind Enter went into the slide (v2-0015, 24 Oct)
        return f"(pyautogui.press('enter'), time.sleep(3)) if {WINDOW_COUNT} > _n0 else None; time.sleep(0.5)"
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
        # wait for the document's own window, up to 90 s, not a fixed 8 s: on this software-rendered VM loading takes
        # longer, and the window list read while "Load document" was still running said "no window" (probe-0003 c07,
        # 20 Oct, screenshot shows the Start Center's load progress bar)
        name = path.rsplit("/", 1)[-1]
        wait_doc = ("next((1 for _ in range(90) if (time.sleep(1) or " + _py(name) + " in __import__('subprocess').run("
                    "['wmctrl', '-l'], capture_output=True, text=True).stdout)), 0); time.sleep(3)")
        # Open the file as a double-click in the file manager would: `libreoffice --calc <file>` hands it to the
        # running instance (replacing the Start Center) or starts one.  Until 20 Oct a running instance got Ctrl+O
        # and the path typed into GTK's Open dialog, which on this slow VM sometimes left the dialog open beside the
        # document (probe-0005 c00).  The GNOME run dialog (Alt+F2), used before that, never opened anything on this
        # image (pilot2 0141).
        return ("__import__('subprocess').Popen(['libreoffice', '--calc', " + _py(path) + "], start_new_session=True, "
                "stdout=__import__('subprocess').DEVNULL, stderr=__import__('subprocess').DEVNULL); " + wait_doc + "; "
                "pyautogui.hotkey('super', 'up'); time.sleep(3)")
    raise ValueError(f"unknown step {step!r}")


WINDOW_COUNT = "int(__import__('subprocess').run(['sh', '-c', 'wmctrl -l 2>/dev/null | grep -vc \"@!\"'], capture_output=True, text=True).stdout.strip() or 0)"


def candidate_code(c: Candidate, ctx: dict) -> str:
    # _n0: the window count when the candidate begins, for the confirm step
    return f"_n0 = {WINDOW_COUNT}; " + "; ".join(step_code(s, ctx) for s in c)


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
    """One step in the step language, normalised, or None when it is not one (type: included: not an undo step)."""
    s = str(raw).strip()
    kind, sep, arg = s.partition(":")
    kind = kind.strip().lower()
    if not sep:
        return kind if kind in ("reopen", "confirm") else None
    if kind == "key":
        tok = arg.strip().lower().replace(" ", "")
        tok = "escape" if tok == "esc" else tok
        return "key:" + tok if _KEY_TOKEN.match(tok) else None
    if kind == "wait":
        try:
            return f"wait:{min(float(arg), 8.0):g}"
        except ValueError:
            return None
    if kind == "menu":
        m = "menu:" + arg.strip().lower().replace(" ", "")
        return m if _MENU.match(m) else None
    if kind == "click":
        label = " ".join(arg.split())              # the control's name as shown, case kept
        return "click:" + label if 0 < len(label) <= 60 else None
    if kind == "shell":
        cmd = arg.strip()
        return "shell:" + cmd if 0 < len(cmd) <= 200 and "\n" not in cmd else None
    if kind == "focus":
        return "focus:newest" if arg.strip().lower() == "newest" else None
    return None


def parse_steps(steps) -> Optional[Candidate]:
    """A whole sequence in the step language, or None if any step is not."""
    if not steps or not isinstance(steps, list) or len(steps) > MAX_STEPS:
        return None
    out = [parse_step(x) for x in steps]
    return None if any(x is None for x in out) else out


def action_count(c: Candidate) -> int:
    """Actions in a candidate, the unit of K: waits are not actions, a reopen is one; a confirm counts as none
    (on this image the question it would answer never appears, 24 Oct)."""
    return sum(1 for s in c or [] if not s.startswith(("wait:", "focus:")) and s != "confirm")


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


# ---------------------------------------------------------------------------------------------------------
# Terminal rows (25 Oct): the inverse of the command the action typed, as shell: candidates.  Only the forms the
# rows use; rm, mv over and cp over have no inverse (the overwritten or removed content is gone).
# ---------------------------------------------------------------------------------------------------------
_TYPED = re.compile(r"pyautogui\.typewrite\((['\"])(.*?)\1")


def shell_inverses(code: str) -> List[Candidate]:
    import shlex
    m = _TYPED.search(code or "")
    if not m:
        return []
    try:
        argv = shlex.split(m.group(2))
    except ValueError:
        return []
    if not argv:
        return []
    out: List[Candidate] = []
    q = shlex.quote
    if argv[0] == "cp" and len(argv) == 3:
        out.append([f"shell:rm {q(argv[2])}"])                          # a new copy; over an existing file it fails, as it should
    elif argv[0] == "mv" and len(argv) == 3:
        out.append([f"shell:mv {q(argv[2])} {q(argv[1])}"])             # a rename back; over an existing file the old one is gone
    elif argv[0] == "libreoffice" and "--convert-to" in argv:
        fmt = argv[argv.index("--convert-to") + 1].split(":")[0]
        src = next((a for a in argv[1:] if not a.startswith("-") and a not in (fmt,) and "." in a.rsplit("/", 1)[-1]), None)
        outdir = argv[argv.index("--outdir") + 1] if "--outdir" in argv else "."
        if src:
            stem = src.rsplit("/", 1)[-1].rsplit(".", 1)[0]
            out.append([f"shell:rm {q(outdir.rstrip('/') + '/' + stem + '.' + fmt)}"])
    elif argv[0] == "touch" and len(argv) == 2:
        out.append([f"shell:rm {q(argv[1])}"])
    elif argv[0] == "mkdir" and len(argv) == 2:
        out.append([f"shell:rmdir {q(argv[1])}"])
    return out
