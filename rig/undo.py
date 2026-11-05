"""Undo candidates (Paper draft 4.5, budget B about 55): Tier 1 generic, Tier 2 Calc-specific, Tier 3 proposed
(rig/proposer.py), Tier 4 blind pairs of generic atoms.  A candidate is a list of steps in the small step
language shared with the proposer:

    key:<chord>      pyautogui.hotkey / press        reopen          relaunch or reopen the task file, maximised
    wait:<s>         time.sleep                      menu:alt+e,u    open a menu by Alt accelerator, press the item's mnemonic letters
    confirm          Enter, only if a window (a question) opened since the candidate began (24 Oct)
    click:<label>    press the named button, menu entry or sidebar row through its accessibility action (22 Oct)
    pointer:back     move the pointer back to where it was in S (30 Oct, VS Code hover state; not an action in K)

Every step is something a user could do at the keyboard with what the applications themselves offer; nothing here
touches snapshots, backups or copies.  No typing (decided with the author 20 Oct 2026): re-entering lost content or
typing commands is not an undo; if the application cannot bring the state back, it is gone.  The type: step and its
20-character cap (19 Oct) were dropped.
K counts actions, not steps: a wait or a pointer move is not an action (action_count).
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

# VS Code, tried before the generic tier (30 Oct, from the snapshot trial's agent steps on change_permissions, which
# ran out their 30 minutes without them): the terminal panel an action opened closes with Ctrl+` or Ctrl+J, or goes
# with its shell ("exit" typed into it, as a shell: step); a Welcome tab a file replaced comes back from Help >
# Welcome (Alt+H, W); an editor a click opened closes with Ctrl+W; an overwrite of several lines that VS Code already autosaved needs more undo steps than two
# before the file is saved back.
VSCODE_FIRST: List[Candidate] = [
    ["menu:alt+f,v"],                                            # File > Revert File: an edit not yet saved, title and file back (2 Nov;
                                                                 # the time cap ended agr-change_permissions-10 and agr-fix_text_search-08 before it)
    ["key:ctrl+w"],                                              # close the editor a click opened (30 Oct check, step 04:
                                                                 # guess B's Ctrl+W came 4 s after the row's cap)
    ["key:ctrl+`"],
    ["key:ctrl+j"],
    ["shell:exit"],
    ["menu:alt+h,w"],
    ["key:ctrl+w", "menu:alt+h,w"],
    ["key:ctrl+z", "key:ctrl+z", "key:ctrl+z", "key:ctrl+s"],
    ["key:ctrl+z", "key:ctrl+z", "key:ctrl+z", "key:ctrl+z", "key:ctrl+s"],
    ["key:ctrl+z", "key:ctrl+z", "key:ctrl+z", "key:ctrl+z", "key:ctrl+z", "key:ctrl+s"],
    ["key:ctrl+z", "key:ctrl+z", "key:ctrl+z", "key:ctrl+z", "key:ctrl+z", "key:ctrl+z", "key:ctrl+s"],
]


# Impress, tried before the generic tier (2 Nov): Ctrl+Z restores a deleted slide but can land on another one, and the
# last slide is one key away (ag-delete_slides_save-03 came back on slide 2 of 16, not 16).
IMPRESS_FIRST: List[Candidate] = [
    ["key:ctrl+z", "key:ctrl+end"],
]


def with_pointer(cands: List[Candidate]) -> List[Candidate]:
    """The pointer tier (30 Oct): VS Code draws hover toolbars and highlights where the pointer rests, so after a
    click the tree keeps differences no key takes back (snapshot trial, agent steps 02 and 04: the terminal closed or
    the Welcome tab back, 76 and 172 nodes still differed, all of them hover sections).  Moving the pointer back to
    where it was in S is something a user does; it is not counted in K (action_count, decided 30 Oct).  The pointer
    alone first."""
    return [["pointer:back"]] + [c + ["pointer:back"] for c in cands]


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
    app = app.replace("_", "-") if app.startswith("libreoffice_") else app   # agent rows carry the OSWorld domain (29 Oct)
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
        if arg not in ("newest", "doc"):
            raise ValueError(f"unknown focus target {arg!r}")
        # 26 Oct (v2-0090 rerun): wmctrl -i -a only raised the window, the keyboard stayed on the terminal.  So: up to
        # 6 tries checked with xprop, as rowlib.activate does, and if the manager still withholds the focus a click
        # at the centre of the window's client area (geometry from wmctrl -lG; xdotool is not on the image).
        # "doc" (3 Nov): the window holding the row's document (ctx["doc_name"], a file name or a window title from S),
        # so a save reaches the editor and not the terminal that ran the action (v3-0026..0033: Ctrl+S went to the
        # terminal, so "save the open document again" was never tried)
        pick = ('w=$(wmctrl -l | grep -v "@!" | tail -1 | cut -d" " -f1); ' if arg == "newest" else
                'w=$(wmctrl -l | grep -v "@!" | grep -F -- ' + shlex.quote(ctx.get("doc_name") or "@@none@@") + ' | head -1 | cut -d" " -f1); ')
        script = (pick + '[ -z "$w" ] && exit 0; '
                  'for i in 1 2 3 4 5 6; do wmctrl -i -a "$w"; sleep 1; '
                  'a=$(xprop -root _NET_ACTIVE_WINDOW 2>/dev/null | grep -o "0x[0-9a-f]*" | head -1); '
                  '[ -n "$a" ] && [ "$((a))" = "$((w))" ] && exit 0; done; '
                  'wmctrl -lG | grep -i "^$w " | tr -s " " | cut -d" " -f3-6; exit 3')
        return (f"_r = __import__('subprocess').run(['sh', '-c', {_py(script)}], capture_output=True, text=True, timeout=40); "
                "_g = _r.stdout.split(); "
                "(pyautogui.click(int(_g[0]) + int(_g[2]) // 2, int(_g[1]) + int(_g[3]) // 2), time.sleep(1)) "
                "if _r.returncode == 3 and len(_g) == 4 else None; time.sleep(1.5)")
    if kind == "click":
        # a named control on screen, pressed through its accessibility action (22 Oct, decided with the author):
        # a button, a menu entry, a sidebar row.  ctx["proc"] names the application to search ("*" = all)
        from rig.dialog_keys import click_code
        return click_code(arg, settle=3, proc=ctx.get("proc") or "*")
    if kind == "wait":
        return f"time.sleep({min(float(arg), 8.0)})"
    if kind == "pointer":
        # back to the pointer's position in S (snapshot meta "pointer", ctx["pointer"]); a no-op where it is unknown
        xy = ctx.get("pointer")
        if arg != "back":
            raise ValueError(f"unknown pointer target {arg!r}")
        return f"pyautogui.moveTo({int(xy[0])}, {int(xy[1])}, duration=0.3); time.sleep(1.5)" if xy else "time.sleep(0.1)"
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
    if kind == "launch":
        # since 29 Oct (agent rows): start a program the way the desktop would, e.g. reopen a window the action closed
        # (a document by its path, the Files window, a terminal, VS Code on its folder, Chrome); arg is a JSON argv
        import json as _json
        argv = _json.loads(arg)
        return ("__import__('subprocess').Popen(" + _py(argv) + ", start_new_session=True, "
                "stdout=__import__('subprocess').DEVNULL, stderr=__import__('subprocess').DEVNULL); time.sleep(10); "
                "pyautogui.hotkey('super', 'up'); time.sleep(3)")
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
        a = arg.strip().lower()
        return "focus:" + a if a in ("newest", "doc") else None
    return None


PLAN_MAX_STEPS = 16     # given plans (--plans, 5 Nov): a chained retry or a recorded long undo; the search itself keeps MAX_STEPS


def parse_steps(steps, max_steps: int = MAX_STEPS) -> Optional[Candidate]:
    """A whole sequence in the step language, or None if any step is not."""
    if not steps or not isinstance(steps, list) or len(steps) > max_steps:
        return None
    out = [parse_step(x) for x in steps]
    return None if any(x is None for x in out) else out


def task_paths(task: dict) -> List[str]:
    """Every file or folder path a task's setup names (upload, download, open, launch arguments)."""
    import json as _json
    found = re.findall(r'"(/home/user/[^"]+)"', _json.dumps(task.get("config", [])))
    return list(dict.fromkeys(found))


def reopen_windows(before_titles, after_titles, task: dict) -> List[Candidate]:
    """Agent rows (29 Oct): one candidate that reopens every window open before the action and gone after it, as a
    user would from the desktop; a window whose program or file is not known is skipped."""
    import json as _json
    gone = [t for t in before_titles if t not in after_titles]
    paths = task_paths(task)
    steps: Candidate = []
    for t in gone:
        argv = None
        m = re.match(r"^(.+?) - LibreOffice (Calc|Impress|Writer)$", t)
        if m:
            p = next((x for x in paths if x.rsplit("/", 1)[-1] == m.group(1)), None)
            argv = ["libreoffice", p] if p else None
        elif t.endswith(" - Visual Studio Code"):
            folder = next((x for x in paths if x.endswith("/project/") or x.endswith("/project")), "/home/user/project")
            argv = ["code", folder]
        elif t.endswith(" - Google Chrome"):
            argv = ["google-chrome"]
        elif t.startswith("user@user-virtual-machine:"):
            argv = ["gnome-terminal", "--working-directory=/home/user"]
        elif t == "Home":
            argv = ["nautilus", "/home/user"]
        if argv:
            steps += [f"launch:{_json.dumps(argv)}", "wait:3"]
    return [steps] if steps else []


def mode_restores(before_digest: dict, after_digest: dict) -> List[Candidate]:
    """A chmod (29 Oct): put back the permissions each changed file had before, one shell command."""
    import shlex as _sh
    cmds = [f"chmod {oct(b['mode'] & 0o7777)[2:]} {_sh.quote(p.rstrip('/'))}" for p, b in sorted(before_digest.items())
            if p in after_digest and "mode" in b and "mode" in after_digest[p] and b["mode"] != after_digest[p]["mode"]]
    return [[f"shell:{' && '.join(cmds)}"]] if cmds else []


def action_count(c: Candidate) -> int:
    """Actions in a candidate, the unit of K: waits are not actions, a reopen is one; a confirm counts as none
    (on this image the question it would answer never appears, 24 Oct); moving the pointer back counts as none
    (decided with the author 30 Oct: a hover toolbar is where the pointer rests, not something the action did, and
    a label must not change with it; such undos stay recognisable by their tier, P)."""
    return sum(1 for s in c or [] if not s.startswith(("wait:", "focus:", "pointer:")) and s != "confirm")


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
    m = _TYPED.search(code or "")
    if not m:
        return []
    cmd = m.group(2).replace("\\n", "").strip()
    parts = [c.strip() for c in re.split(r"\s*&&\s*", cmd) if c.strip() and not c.strip().startswith(("clear", "ls", "cd ", "cat ", "pwd"))]
    if len(parts) > 1:
        # a chain (29 Oct, agent rows: "mkdir -p src tests && mv a.py src/ && ..."): each part's inverse, last first
        inv = []
        for part in reversed(parts):
            one = _inverse_one(part)
            if one is None:
                return []
            inv += one
        return [[f"shell:{' && '.join(inv)}"]] if inv else []
    return _legacy(m.group(2))     # one command: the rules of 25 Oct, unchanged


def _inverse_one(part: str) -> Optional[List[str]]:
    """Inverse of one shell command as a list of shell commands, or None if it has none here."""
    q = shlex.quote
    try:
        argv = shlex.split(part)
    except ValueError:
        return None
    if not argv:
        return []
    if argv[0] == "mkdir":
        dirs = [a for a in argv[1:] if not a.startswith("-")]
        return [f"rmdir {' '.join(q(d) for d in reversed(dirs))}"] if dirs else None
    if argv[0] == "mv" and len(argv) >= 3 and not any(a.startswith("-") for a in argv[1:]):
        *srcs, dst = argv[1:]
        if len(srcs) == 1 and not dst.endswith("/"):
            return [f"mv {q(dst)} {q(srcs[0])}"]
        return [f"mv {q(dst.rstrip('/') + '/' + s.rsplit('/', 1)[-1])} {q(s)}" for s in srcs]
    if argv[0] == "touch" and len(argv) == 2:
        return [f"rm {q(argv[1])}"]
    if argv[0] == "cp" and len(argv) == 3:
        return [f"rm {q(argv[2])}"]
    return None


def _legacy(code_cmd: str) -> List[Candidate]:
    try:
        argv = shlex.split(code_cmd)
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
