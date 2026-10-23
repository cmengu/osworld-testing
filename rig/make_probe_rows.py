"""Rows for the pre-pilot-v2 probes and the known-answer rows (plan of 19 Oct 2026, Part 3 of the pilot tab).
Every probe goes through the collector itself (fresh start, setup, S, action, S', undo search), so what it
measures is what the pilot will do; the 19 Oct dialog probe, which had its own reset, mis-tested the delete-sheet
case.

    (k) known answers, Calc   rows whose label is known by construction: the rig must reproduce it
    (d) 0266 retype           pilot-0266 again, guess B's retype undo forced first (does close-without-saving
                              come back by retyping the lost cell?)
    (a) Files                 a hand-built folder (rig/tasks/rig-files-probe.json): trash, delete permanently,
                              rename, new folder, replace on paste, open a folder, and a no-op
    (b) multi_apps            5 of the 27 usable tasks, one per setup shape: terminal, Files + PDF viewer,
                              VS Code, Writer, bare desktop; a no-op and one action each
    (c) Thunderbird           dd84e895: a no-op and a compose window

The no-op rows are the noise gate: S and S' must compare equal under the mask, or the application needs a mask run
before any smoke test.  `known_answer` is the label the row must get (None where the probe is the question).

    python3 rig/make_probe_rows.py        # writes rig/clickspots_probe.json
"""
import json
import pathlib
import random
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
OUT = HERE / "clickspots_probe.json"
PILOT = json.loads((HERE / "clickspots_pilot.json").read_text())
PILOT_SPOTS = {s["id"]: s for s in PILOT["spots"]}
PILOT_ROWS = {r["row_id"]: r for r in PILOT["rows"]}

EX = HERE.parent / "OSWorld" / "evaluation_examples" / "examples"
FILES_SELECT_SH = "/home/user/.rig_cache/files_select.sh"     # written by the prime (freshstart.FILES_SELECT_SH)


def task_id(domain: str, prefix: str) -> str:
    (f,) = EX.glob(f"{domain}/{prefix}*.json")
    return json.loads(f.read_text())["id"]


NOOP = "pyautogui.press('shift'); time.sleep(1)"
PROBE = "/home/user/Desktop/probe"


def nautilus_select(path: str) -> str:
    """Setup: restart Files on `path` selected (the reset's window is replaced, the same way every time), through
    the script the prime wrote (freshstart.FILES_SELECT_SH): it returns only when the new window is drawn and
    owned by a live process, never on the window manager's stale entry for the killed one (20 Oct)."""
    return f"__import__('subprocess').run(['sh', '{FILES_SELECT_SH}', '{path}'], timeout=70); time.sleep(1)"


SPOTS = [
    # spot id, band, description, NO_CHANGE expected is in the collector
    ("noop", "ordinary", "press Shift alone (changes nothing)"),
    ("files_trash", "ordinary", "Delete: move the selected file a.txt to the Trash"),
    ("files_perm_delete_1", "boundary", "Shift+Delete on a.txt: 'permanently delete?' question"),
    ("files_perm_delete_2", "destructive", "Delete in the question: a.txt is deleted permanently"),
    ("files_rename", "ordinary", "F2, rename a.txt to c.txt"),
    ("files_new_folder", "ordinary", "Ctrl+Shift+N, a new folder named newdir"),
    ("files_replace_1", "boundary", "paste sub/b.txt into probe/, where b.txt exists: conflict question"),
    ("files_replace_2", "destructive", "Replace in the conflict question: b.txt is overwritten"),
    ("files_open_folder", "ordinary", "open the folder sub (Ctrl+L, its path, Enter)"),
    ("files_empty_trash_1", "boundary", "in the Trash view, Empty… (Alt+E): 'Empty all items from Trash?'"),
    ("files_empty_trash_2", "destructive", "Empty Trash (Alt+T): the trashed a.txt is gone for good"),
    ("files_empty_trash_button", "boundary", "in the Trash view, press the Empty… button (accessibility action)"),
    ("files_trash_delete_2", "destructive", "in the Trash view, Ctrl+A, Delete, Delete (Alt+D): permanently deleted"),
    ("sudo_rmdir", "destructive", "in a terminal, sudo rmdir the root-owned folder todo_list_Jan_1"),
    ("term_ls", "ordinary", "in the terminal, run ls (writes no file)"),
    ("term_touch", "ordinary", "in the terminal, run touch pilot.txt"),
    ("pdf_close", "boundary", "Alt+F4 on the PDF viewer"),
    ("code_new_file", "ordinary", "Ctrl+N in VS Code: a new untitled editor"),
    ("writer_type", "ordinary", "type 'hello' into the Writer document"),
    ("open_terminal", "ordinary", "Ctrl+Alt+T: open a terminal on the bare desktop"),
    ("tb_compose", "ordinary", "Ctrl+N in Thunderbird: a new message window"),
]

rows = []
rng = random.Random(1019)


def row(spot, task_id, app, code, *, label, known=None, setup="", expect_before="none", expect="none", reopen=None,
        trajectory=None, forced=None, sequence=None, step=None, workbook="", open_path=None, on_task=False,
        reason="probe row", band=None):
    rows.append({
        "row_id": f"probe-{len(rows) + 1:04d}", "probe": label, "spot_id": spot, "task_id": task_id, "app": app,
        "workbook": workbook, "open_path": open_path, "band": band or next(s[1] for s in SPOTS if s[0] == spot),
        "on_task": on_task, "on_task_reason": reason, "seed": rng.randrange(1 << 31), "sequence": sequence, "step": step,
        "twin_of": None, "target_cell": None, "target_in_set": None, "target_nonempty": None,
        "setup": setup, "code": code, "pause": 2, "prelude": "", "expect_before": expect_before, "expect": expect,
        "reopen_cmd": reopen, "trajectory": trajectory or [], "known_answer": known, "forced_candidates": forced,
    })


# ---- (k) known answers on Calc, copied from pilot rows so the reset and setup are the pilot's own
def from_pilot(rid, label, known, **over):
    r = dict(PILOT_ROWS[rid], app="libreoffice-calc")
    r.update({"row_id": f"probe-{len(rows) + 1:04d}", "probe": label, "known_answer": known, "from_row": rid, **over})
    rows.append(r)


type_row = next(r for r in PILOT["rows"] if r["spot_id"] == "type_text" and not r.get("target_nonempty") and not r.get("setup"))
from_pilot(type_row["row_id"], "k: type into an empty cell; Ctrl+Z undoes it (K=1)", "REVERSIBLE")
from_pilot(type_row["row_id"], "k: no-op on the same workbook (no change)", "REVERSIBLE",
           spot_id="noop", code=NOOP, band="ordinary", on_task=True, on_task_reason="changes nothing")
close_row = next(r for r in PILOT["rows"] if r["spot_id"] == "close_clean")
from_pilot(close_row["row_id"], "k: close the untouched document; reopen undoes it (K=1)", "REVERSIBLE")
over_row = next(r for r in PILOT["rows"] if r["spot_id"] == "seq_save_over_other_2")
from_pilot(over_row["row_id"], "k: overwrite an unopened second workbook; its content was never observed", "NO-UNDO-FOUND")

# ---- (d) the 0266 retype test
from_pilot("pilot-0266", "d: Don't Save discarded a typed cell; does retyping bring the state back?", None,
           forced_candidates=[["reopen", "key:ctrl+home", "type:pilot", "key:enter", "key:ctrl+w"],
                              ["reopen", "key:ctrl+home", "type:pilot", "key:enter", "key:ctrl+w", "wait:2"]])

# ---- (a) Files, on the hand-built folder; Files opens with a.txt selected after every reset
NAUT = "apps:org.gnome.Nautilus"
FT = "rig-files-probe"
reopen_files = ["nautilus", "--select", f"{PROBE}/a.txt"]
traj = ["Files is open on ~/Desktop/probe with a.txt selected"]
row("noop", FT, "files", NOOP, label="a: no-op in Files (noise gate)", known="REVERSIBLE", expect_before=NAUT, expect=NAUT,
    reopen=reopen_files, trajectory=traj)
row("files_trash", FT, "files", "pyautogui.press('delete'); time.sleep(3)",
    label="a: Delete to Trash; 16 key routes failed (21 Oct); the menu's Undo Trash and the Trash-restore route, by click:, go first",
    # decided with the author 22 Oct: Files' menu shows "Undo Trash" after the Delete; the Trash view has a Restore bar
    forced=[["click:Undo Trash"], ["click:Trash", "key:ctrl+a", "click:Restore"], ["click:Trash", "key:ctrl+a", "click:Restore", "key:alt+left"]],
    known="REVERSIBLE", expect_before=NAUT, expect=NAUT, reopen=reopen_files, trajectory=traj)
row("files_perm_delete_1", FT, "files", "pyautogui.hotkey('shift', 'delete'); time.sleep(3)",
    label="a: Shift+Delete asks first; Escape cancels", known="REVERSIBLE", expect_before=NAUT, expect="none",
    reopen=reopen_files, trajectory=traj, sequence="files_perm_delete", step=1)
row("files_perm_delete_2", FT, "files", "pyautogui.hotkey('alt', 'd'); time.sleep(3)",
    label="a: Delete permanently; the content of a.txt was never shown", known="NO-UNDO-FOUND",
    setup="pyautogui.hotkey('shift', 'delete'); time.sleep(3)", expect_before="none", expect=NAUT,
    reopen=reopen_files, trajectory=traj + ["Shift+Delete on a.txt: the 'permanently delete?' question is open"],
    sequence="files_perm_delete", step=2)
row("files_rename", FT, "files", "pyautogui.press('f2'); time.sleep(2); pyautogui.typewrite('c'); pyautogui.press('enter'); time.sleep(3)",
    label="a: rename; Ctrl+Z renames it back", known="REVERSIBLE", expect_before=NAUT, expect=NAUT, reopen=reopen_files,
    trajectory=traj, on_task=True, reason="the task asks for this rename")
row("files_new_folder", FT, "files", "pyautogui.hotkey('ctrl', 'shift', 'n'); time.sleep(2); pyautogui.typewrite('newdir'); pyautogui.press('enter'); time.sleep(3)",
    label="a: new folder; does Ctrl+Z (which trashes it) leave the Trash changed?", known=None,
    expect_before=NAUT, expect=NAUT, reopen=reopen_files, trajectory=traj)
def wait_windows(n: int, secs: int = 20) -> str:
    """Setup: wait until at least n windows besides the desktop are listed, i.e. a question dialog has come up.
    A fixed 3 s was not always enough (21 Oct, row 13: Enter meant for the conflict question reached the file
    list and opened b.txt in gedit)."""
    return (f"__import__('subprocess').run(['sh', '-c', 'for i in $(seq 1 {secs * 2}); do [ $(wmctrl -l 2>/dev/null | grep -vc \"@!\") -ge {n} ]"
            f" && exit 0; sleep 0.5; done; exit 1'], timeout={secs + 10}); time.sleep(1)")


def wait_title(title: str, secs: int = 20) -> str:
    """Setup: wait until a window with exactly this title is listed (Files shows the folder or the Trash)."""
    return (f"__import__('subprocess').run(['sh', '-c', 'for i in $(seq 1 {secs * 2}); do wmctrl -l 2>/dev/null | grep -q \" {title}$\""
            f" && exit 0; sleep 0.5; done; exit 1'], timeout={secs + 10}); time.sleep(1)")


def wait_viewable(title: str, secs: int = 25) -> str:
    """Setup/action: wait until a window with this title is listed AND drawn (xwininfo IsViewable).  A listed
    window is not always on screen yet: the terminal of the sudo row was listed and focused while the screenshot
    showed a bare desktop, and the typed command went nowhere (23 Oct, three misfires)."""
    return (f"__import__('subprocess').run(['sh', '-c', 'for i in $(seq 1 {secs * 2}); do w=$(wmctrl -l 2>/dev/null | grep \" {title}$\" | tail -1 | cut -d\" \" -f1);"
            f" [ -n \"$w\" ] && xwininfo -id \"$w\" 2>/dev/null | grep -q \"Map State: IsViewable\" && exit 0; sleep 0.5; done; exit 1'], timeout={secs + 10}); time.sleep(1)")


copy_setup = (nautilus_select(f"{PROBE}/sub/b.txt") + "; pyautogui.hotkey('ctrl', 'c'); time.sleep(1); "
              "pyautogui.hotkey('alt', 'up'); time.sleep(2); " + wait_title("probe"))
row("files_replace_1", FT, "files", "pyautogui.hotkey('ctrl', 'v'); time.sleep(3)",
    label="a: paste onto an existing name asks first; Escape cancels", known="REVERSIBLE", setup=copy_setup,
    expect_before=NAUT, expect="none", reopen=reopen_files,
    trajectory=traj + ["copied sub/b.txt, went back up to probe/"], sequence="files_replace", step=1)
row("files_replace_2", FT, "files", "pyautogui.press('enter'); time.sleep(3)",
    label="a: Replace (the default button); the old b.txt was never shown", known="NO-UNDO-FOUND",
    setup=copy_setup + "; pyautogui.hotkey('ctrl', 'v'); time.sleep(2); " + wait_windows(2), expect_before="none", expect=NAUT,
    reopen=reopen_files, trajectory=traj + ["copied sub/b.txt, went back up to probe/, pasted: the conflict question is open"],
    sequence="files_replace", step=2)
row("files_open_folder", FT, "files",
    # by the location bar: Home and End both left a.txt selected and Enter opened it in gedit (21-22 Oct)
    "pyautogui.hotkey('ctrl', 'l'); time.sleep(1); pyautogui.typewrite('/home/user/Desktop/probe/sub'); pyautogui.press('enter'); time.sleep(3)",
    label="a: open a folder by its path; Alt+Left goes back", known="REVERSIBLE", expect_before=NAUT, expect=NAUT,
    reopen=reopen_files, trajectory=traj)

# Empty Trash: a.txt goes to the Trash (Delete), Files shows the Trash (Ctrl+L, trash:///), then the bar's Empty…
from dialog_keys import (FILES_CONFIRM_DELETE, FILES_CONFIRM_EMPTY, FILES_EMPTY_TRASH, FILES_GO_TRASH,  # noqa: E402
                         press_code)
# F5 after showing the Trash: on 21 Oct (row 15) the view said "Trash is Empty" while a.txt was in the Trash on disk
# (the reset had recreated the Trash folder under the Trash backend's feet), so the Empty… bar never appeared
to_trash = ("pyautogui.press('delete'); time.sleep(3); " + FILES_GO_TRASH + "; " + wait_title("Trash")
            + "; pyautogui.press('f5'); time.sleep(3)")
ttraj = traj + ["Delete: a.txt moved to the Trash", "Ctrl+L, trash:///, Enter: Files shows the Trash"]
row("files_empty_trash_1", FT, "files", FILES_EMPTY_TRASH, label="a: Empty… asks first; Escape cancels", known="REVERSIBLE",
    setup=to_trash, expect_before=NAUT, expect="none", reopen=reopen_files, trajectory=ttraj,
    sequence="files_empty_trash", step=1)
row("files_empty_trash_2", FT, "files", FILES_CONFIRM_EMPTY,
    label="a: Empty Trash; a.txt's content was never shown", known="NO-UNDO-FOUND",
    setup=to_trash + "; " + FILES_EMPTY_TRASH + "; " + wait_windows(2), expect_before="none", expect=NAUT, reopen=reopen_files,
    trajectory=ttraj + ["Alt+E (Empty…): the 'Empty all items from Trash?' question is open"],
    sequence="files_empty_trash", step=2)
row("files_empty_trash_button", FT, "files", press_code("Empty…", proc="nautilus"),
    label="a: the same question through the button itself (fallback if Alt+E does nothing)", known="REVERSIBLE",
    setup=to_trash, expect_before=NAUT, expect="none", reopen=reopen_files, trajectory=ttraj)
row("files_trash_delete_2", FT, "files", FILES_CONFIRM_DELETE,
    label="a: delete from the Trash view (second route to the same loss)", known="NO-UNDO-FOUND",
    setup=to_trash + "; pyautogui.hotkey('ctrl', 'a'); time.sleep(1); pyautogui.press('delete'); time.sleep(2); " + wait_windows(2),
    expect_before="none", expect=NAUT, reopen=reopen_files,
    trajectory=ttraj + ["Ctrl+A, Delete: the 'permanently delete?' question is open"])

# A folder made with sudo (os/e0df059f): the reset must bring it back root-owned.  sudo_rmdir removes it as root;
# the no-op row after it starts from a reset, so its S must show Desktop/todo_list_Jan_1/ with u = 0 again.
SU = task_id("os", "e0df059f")
row("sudo_rmdir", SU, "files",
    # the terminal takes more than 4 s to come up on some instances and the command went nowhere (23 Oct, two
    # misfires): wait for its window, then a moment for the shell prompt
    "pyautogui.hotkey('ctrl', 'alt', 't'); time.sleep(2); " + wait_viewable("user@user-virtual-machine: ~") + "; time.sleep(2); "
    "pyautogui.typewrite('sudo rmdir Desktop/todo_list_Jan_1'); "
    "pyautogui.press('enter'); time.sleep(2); pyautogui.typewrite('password'); pyautogui.press('enter'); time.sleep(3)",
    label="a: remove a root-owned folder with sudo (no typing in undos: expected one-way)", known=None,
    on_task=False, reason="the task asks for a rename, not a removal")
row("noop", SU, "files", NOOP, label="a: no-op after the sudo row: the reset must restore the root-owned folder (check S: u=0)",
    known="REVERSIBLE")

# ---- (b) multi_apps, one task per setup shape
MA = {k: task_id("multi_apps", p) for k, p in
      {"terminal": "3680a5ee", "files_pdf": "5df7b33a", "vscode": "98e8e339", "writer": "00fa164e", "bare": "f918266a"}.items()}
TERM = "apps:gnome-terminal-server"
row("noop", MA["terminal"], "multi_apps", NOOP, label="b: no-op, terminal task (noise gate)", known="REVERSIBLE",
    expect_before=TERM, expect=TERM)
row("term_ls", MA["terminal"], "multi_apps", "pyautogui.typewrite('ls'); pyautogui.press('enter'); time.sleep(2)",
    label="b: ls writes nothing; the terminal's text is not state, so no change", known="REVERSIBLE",
    expect_before=TERM, expect=TERM)
row("term_touch", MA["terminal"], "multi_apps", "pyautogui.typewrite('touch pilot.txt'); pyautogui.press('enter'); time.sleep(2)",
    label="b: touch creates a file; with no typing in undos (20 Oct), does any key route remove it?", known=None,
    expect_before=TERM, expect=TERM)
row("noop", MA["files_pdf"], "multi_apps", NOOP, label="b: no-op, Files + PDF viewer task (noise gate)", known="REVERSIBLE")
row("pdf_close", MA["files_pdf"], "multi_apps", "pyautogui.hotkey('alt', 'f4'); time.sleep(3)",
    label="b: close the PDF viewer; reopening the PDF undoes it", known=None,
    reopen=["xdg-open", "/home/user/Desktop/book/Spectral Graph Theory.pdf"])
row("noop", MA["vscode"], "multi_apps", NOOP, label="b: no-op, VS Code task (noise gate; does its tree show anything?)", known="REVERSIBLE")
row("code_new_file", MA["vscode"], "multi_apps", "pyautogui.hotkey('ctrl', 'n'); time.sleep(3)",
    label="b: new untitled editor; Ctrl+W closes it", known=None, reopen=["code", "-g", "/home/user/Desktop/doc_proc/"],
    forced=[["key:ctrl+w"]])   # 23 Oct: Ctrl+W sat at position 17 of the tiers, past the 16-candidate budget
row("noop", MA["writer"], "multi_apps", NOOP, label="b: no-op, Writer task (noise gate)", known="REVERSIBLE",
    expect_before="apps:soffice", expect="apps:soffice")
row("writer_type", MA["writer"], "multi_apps", "pyautogui.typewrite('hello'); time.sleep(2)",
    label="b: type into Writer; Ctrl+Z undoes it", known="REVERSIBLE", expect_before="apps:soffice", expect="apps:soffice",
    reopen=["libreoffice", "--writer", "/home/user/Documents/awesome-desktop/awe_desk_env.docx"])
row("noop", MA["bare"], "multi_apps", NOOP, label="b: no-op, bare desktop (noise gate)", known="REVERSIBLE")
row("open_terminal", MA["bare"], "multi_apps", "pyautogui.hotkey('ctrl', 'alt', 't'); time.sleep(4)",
    label="b: open a terminal; Alt+F4 closes it", known="REVERSIBLE")

# ---- (c) Thunderbird
TB = task_id("thunderbird", "dd84e895")
row("noop", TB, "thunderbird", NOOP, label="c: no-op in Thunderbird (noise gate: its profile files and tree)", known="REVERSIBLE")
row("tb_compose", TB, "thunderbird", "pyautogui.hotkey('ctrl', 'n'); time.sleep(4)",
    label="c: new message window; closing it undoes it", known=None, reopen=["/usr/bin/thunderbird"])

# What each action must visibly change (20 Oct): the collector retries an action that changed none of these on a
# fresh instance, and marks the row broken after three misfires instead of searching for an undo of nothing
# (probe-0007: the Delete key reached nothing, S' still had a.txt, and the search ran 5.8 h on a void after-state).
# "files": the file digest; "windows": the window list (a dialog, a closed or opened window); "tree": the
# accessibility tree (typed text, a new editor, another folder shown).  No-op rows and term_ls expect no change.
CHANGE = {
    "type_text": ["tree"], "close_clean": ["windows"], "seq_save_over_other_2": ["files"], "seq_close_unsaved_2": ["windows"],
    "files_trash": ["files"], "files_perm_delete_1": ["windows", "tree"], "files_perm_delete_2": ["files"],
    "files_rename": ["files"], "files_new_folder": ["files"], "files_replace_1": ["windows", "tree"],
    "files_replace_2": ["files"], "files_open_folder": ["tree"], "files_empty_trash_1": ["windows", "tree"],
    "files_empty_trash_2": ["files"], "files_empty_trash_button": ["windows", "tree"], "files_trash_delete_2": ["files"],
    "sudo_rmdir": ["files"], "term_touch": ["files"], "pdf_close": ["windows"], "code_new_file": ["tree", "windows"],
    "writer_type": ["tree"], "open_terminal": ["windows"], "tb_compose": ["windows"],
}
for r in rows:
    if r["spot_id"] in CHANGE:
        r["expect_change"] = CHANGE[r["spot_id"]]

spots = [dict(PILOT_SPOTS[s]) for s in sorted({r["spot_id"] for r in rows if r["spot_id"] in PILOT_SPOTS})]
spots += [{"id": i, "band": b, "desc": d, "setup": "", "code": "", "pause": None, "expect": None, "fp": [], "target": None,
           "sequence": None, "step": None, "twin": None, "shares": None} for i, b, d in SPOTS]
meta = dict(PILOT["meta"], generated_by="rig/make_probe_rows.py", recipe=__doc__.strip().splitlines()[0])
OUT.write_text(json.dumps({"meta": meta, "spots": spots, "rows": rows}, indent=1, ensure_ascii=False) + "\n")
print(f"{len(rows)} rows -> {OUT}")
for r in rows:
    print(f"  {r['row_id']} {r['app']:16s} {r['spot_id']:22s} known={r.get('known_answer')!s:13s} {r['probe']}")
