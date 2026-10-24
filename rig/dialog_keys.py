"""Keys that press the buttons of the dialogs the click-spots and the rig meet, on this VM image.

Read 19 Oct 2026 offline from the key bindings the dialogs themselves report in the recorded trees of pilot2
(rig/out/pilot_run2/<row>/S1/tree.xml, `act:click_kb`), not guessed from other LibreOffice builds:

    Save Document? (Ctrl+W / Ctrl+Q with unsaved edits; 0261, 0266, 0291)   Don't Save = Alt+N, Cancel = Alt+C, Save = Alt+S
    "A file named ... already exists" (Save As onto an existing name; 0271) No = Alt+N, Yes = Alt+Y  (there is no Replace button)
    "Are you sure you want to delete the selected sheet(s)?" (0281)         No = Alt+N, Yes = Alt+Y

Alt+D, used until now for Don't Save, is the accelerator of the Data menu (probe_menus "menu_data"): it reached the
document behind the alert, which explains pilot-0266 (dialog still open) and the stray save in pilot-0181.
rig/probe_dialogs.py confirmed Alt+N (close and quit) and Alt+Y (replace, also onto a second workbook) on 19 Oct by
what actually happened to the windows and the files.
"""
DONT_SAVE = "pyautogui.hotkey('alt', 'n')"
CONFIRM_YES = "pyautogui.hotkey('alt', 'y')"      # replace-existing-file and delete-sheet questions
# Save As of an .xlsx: after the file is written, LibreOffice asks whether to keep the Excel format; Enter keeps it
KEEP_FORMAT = "pyautogui.press('enter')"

# ---------------------------------------------------------------------------------------------------------------
# Accessibility helpers, sent as spot code: python3 in a subprocess inside the VM, because the pyautogui context
# has no pyatspi.  Both search only LibreOffice's own windows (the GTK file dialog lives in the soffice process).
_A11Y_HEAD = r'''
import sys, logging, subprocess
logging.disable(logging.CRITICAL)
sys.path.insert(0, "/home/user/server")
try:
    import main as srv
except Exception:
    pass
import pyatspi
# argv[2], when given, is the process to search (pgrep -x), e.g. nautilus; LibreOffice otherwise; "*" = every application
_proc = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] else None
pids = None if _proc == "*" else set(int(x) for x in subprocess.run(["pgrep", "-x", _proc] if _proc else ["pgrep", "-f", "soffice"],
                                                                     capture_output=True, text=True).stdout.split())
def norm(s):
    return (s or "").replace("’", "'").replace("~", "").replace("_", "").lower()
def walk(n, ok, d=0):
    try:
        if ok(n):
            return n
    except Exception:
        return None
    if d > 16:
        return None
    try:
        kids = list(n)
    except Exception:
        return None
    for c in kids:
        r = walk(c, ok, d + 1)
        if r is not None:
            return r
    return None
def find(ok):
    for app in pyatspi.Registry.getDesktop(0):
        try:
            if pids is not None and int(app.get_process_id()) not in pids:
                continue
        except Exception:
            continue
        for w in app:
            r = walk(w, ok)
            if r is not None:
                return r
    return None
'''

# Press the named button (or menu item) wherever it shows in a LibreOffice window.
PRESS_PY = _A11Y_HEAD + r'''
want = norm(sys.argv[1])
b = find(lambda n: n.getRoleName() in ("push button", "menu item", "check box") and norm(n.name) == want)
if b is None:
    print("not found"); sys.exit(0)
b.queryAction().doAction(0)
print("pressed")
'''

# Select a file by name in the open file dialog's list and give the list the keyboard focus, so that Delete or
# Shift+F10 acts on that file.  GTK's list is a tree table: selecting a cell's index selects its row.
SELECT_FILE_PY = _A11Y_HEAD + r'''
want = sys.argv[1]
cell = find(lambda n: n.getRoleName() == "table cell" and n.name == want and n.parent is not None and n.parent.name == "Files")
if cell is None:
    print("not found"); sys.exit(0)
table = cell.parent
try:
    table.queryComponent().grabFocus()
except Exception:
    pass
table.querySelection().clearSelection()
ok = table.querySelection().selectChild(cell.getIndexInParent())
try:
    cell.queryComponent().grabFocus()
except Exception:
    pass
print("selected" if ok else "select failed")
'''


def press_code(label: str, settle: float = 3, proc: str = "") -> str:
    """proc: the process whose windows to search (pgrep -x name, e.g. 'nautilus'); LibreOffice when empty."""
    return ("__import__('subprocess').run(['python3', '-c', " + repr(PRESS_PY) + ", " + repr(label) + ", " + repr(proc) + "], timeout=30); "
            f"time.sleep({settle})")


# The click: undo step (decided with the author 22 Oct): a named control on screen, pressed through its
# accessibility action, as a mouse click would.  Wider than PRESS_PY: menu entries in GTK popover menus (Files'
# "Undo Trash"), sidebar rows (a list item whose label is the name), toggles and radios; a node without an action
# of its own hands the press to the nearest ancestor that has one (the label inside a sidebar row).
CLICK_PY = _A11Y_HEAD + r'''
want = norm(sys.argv[1])
ROLES = ("push button", "menu item", "check menu item", "radio menu item", "check box", "toggle button",
         "radio button", "list item", "label", "link", "table cell",
         "tree item", "table row", "row", "tree table")   # Thunderbird's folder pane rows (v2-0055, 24 Oct)
n = find(lambda n: n.getRoleName() in ROLES and norm(n.name) == want)
if n is None:
    print("not found"); sys.exit(0)
node, hops = n, 0
while node is not None and hops < 4:
    try:
        a = node.queryAction()
        if a.nActions > 0:
            a.doAction(0); print("clicked", node.getRoleName(), repr(node.name), a.getName(0)); sys.exit(0)
    except Exception:
        pass
    node, hops = node.parent, hops + 1
print("no action")
'''


def click_code(label: str, settle: float = 3, proc: str = "*") -> str:
    return ("__import__('subprocess').run(['python3', '-c', " + repr(CLICK_PY) + ", " + repr(label) + ", " + repr(proc) + "], timeout=30); "
            f"time.sleep({settle})")


# GNOME Files 42 (nautilus-trash-bar.c, gnome-42): the Trash view's bar has "_Settings", "_Restore" and "_Empty…",
# so Alt+E empties from the keyboard; the confirmation (nautilus-file-operations.c) is "Empty all items from
# Trash?" with "Empty _Trash" (Alt+T).  In the Trash view, Delete asks "permanently delete?" with "_Delete" (Alt+D).
FILES_GO_TRASH = "pyautogui.hotkey('ctrl', 'l'); time.sleep(1); pyautogui.typewrite('trash:///'); pyautogui.press('enter'); time.sleep(3)"
FILES_EMPTY_TRASH = "pyautogui.hotkey('alt', 'e'); time.sleep(3)"
FILES_CONFIRM_EMPTY = "pyautogui.hotkey('alt', 't'); time.sleep(3)"
FILES_CONFIRM_DELETE = "pyautogui.hotkey('alt', 'd'); time.sleep(3)"


def select_file_code(name: str, settle: float = 1) -> str:
    return ("__import__('subprocess').run(['python3', '-c', " + repr(SELECT_FILE_PY) + ", " + repr(name) + "], timeout=30); "
            f"time.sleep({settle})")


# Confirmed 19 Oct (probe_dialogs, rig/out/dialog_probe/log.json): every key above works as read.  The GTK file
# dialog on this image has no way to delete a file: its list offers Rename and Create Folder only, and Delete,
# Shift+Delete and the context menu (Shift+F10) all left the file on disk.
