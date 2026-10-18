"""Keys that press the buttons of the dialogs the click-spots and the rig meet, on this VM image.

Read 19 Oct 2026 offline from the key bindings the dialogs themselves report in the recorded trees of pilot2
(rig/out/pilot_run2/<row>/S1/tree.xml, `act:click_kb`), not guessed from other LibreOffice builds:

    Save Document? (Ctrl+W / Ctrl+Q with unsaved edits; 0261, 0266, 0291)   Don't Save = Alt+N, Cancel = Alt+C, Save = Alt+S
    "A file named ... already exists" (Save As onto an existing name; 0271) No = Alt+N, Yes = Alt+Y  (there is no Replace button)
    "Are you sure you want to delete the selected sheet(s)?" (0281)         No = Alt+N, Yes = Alt+Y

Alt+D, used until now for Don't Save, is the accelerator of the Data menu (probe_menus "menu_data"): it reached the
document behind the alert, which explains pilot-0266 (dialog still open) and the stray save in pilot-0181.
rig/probe_dialogs.py confirms these by what actually happens (windows, file) on the next sandbox run; if a key does
not work there, the probe's working route replaces it here and in nothing else.
"""
DONT_SAVE = "pyautogui.hotkey('alt', 'n')"
CONFIRM_YES = "pyautogui.hotkey('alt', 'y')"      # replace-existing-file and delete-sheet questions
# Save As of an .xlsx: after the file is written, LibreOffice asks whether to keep the Excel format; Enter keeps it
KEEP_FORMAT = "pyautogui.press('enter')"
# GTK's "permanently delete?" question of the file dialog: buttons _Cancel and _Delete.  Unverified until the probe.
CONFIRM_DELETE_FILE = "pyautogui.hotkey('alt', 'd')"

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
pids = set(int(x) for x in subprocess.run(["pgrep", "-f", "soffice"], capture_output=True, text=True).stdout.split())
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
            if int(app.get_process_id()) not in pids:
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


def press_code(label: str, settle: float = 3) -> str:
    return ("__import__('subprocess').run(['python3', '-c', " + repr(PRESS_PY) + ", " + repr(label) + "], timeout=30); "
            f"time.sleep({settle})")


def select_file_code(name: str, settle: float = 1) -> str:
    return ("__import__('subprocess').run(['python3', '-c', " + repr(SELECT_FILE_PY) + ", " + repr(name) + "], timeout=30); "
            f"time.sleep({settle})")


# Delete the selected file from GTK's file dialog: the Delete key, then the "permanently delete?" question.
# Unverified: GTK 3 offers Delete in the list's context menu (Shift+F10) in a Save dialog; whether the bare Delete
# key is bound is what probe_dialogs case E finds out, along with the working route.
DELETE_SELECTED_FILE = "pyautogui.press('delete'); time.sleep(2)"
