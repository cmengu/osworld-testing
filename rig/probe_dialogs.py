"""Probe of 19 Oct 2026, about 25 min of sandbox: which keys press the buttons of Calc's dialogs on this image.

pilot2 showed that Alt+D does not press "Don't Save" (pilot-0266: the dialog was still open; pilot-0181: a file got
saved instead), so every spot that ends in a dialog button is unverified: close/quit without saving (Alt+D),
delete sheet (Alt+S menu, then Alt+Y) and Save As over an existing file (Alt+R).  For each dialog this reads its
buttons through pyatspi (name and key binding), then tries each route from a fresh start and judges it by what
actually happened: windows from wmctrl, the file from the digest.  The last route is always a direct press of the
named button through the accessibility interface, issued from the same pyautogui context the spots run in.

19 Oct, before any run: the recorded trees of pilot2 already name the keys (rig/dialog_keys.py: Don't Save = Alt+N,
the replace and delete-sheet questions = Alt+Y), so those routes go first and the probe confirms them.  Cases E and F
check the two top-up spots (rows 0301 and 0311): Save As over a second workbook, and deleting that workbook from the
Save As dialog's file list, whose keyboard route is the one thing nobody has seen yet.

Writes rig/out/dialog_probe/log.json.  Run: OSWorld/.venv/bin/python -I -u rig/probe_dialogs.py
"""
import json, os, pathlib, signal, sys, time
HERE = pathlib.Path(__file__).resolve().parent; BASE = HERE.parent; OSWORLD = BASE / "OSWorld"
sys.path.insert(0, str(BASE)); sys.path.insert(0, str(OSWORLD)); os.chdir(OSWORLD)
from desktop_env.desktop_env import DesktopEnv
from rig.dialog_keys import CONFIRM_YES, DONT_SAVE, press_code, select_file_code

CONFIRM_DELETE_FILE = "pyautogui.hotkey('alt', 'd')"   # GTK's _Delete; the dialog never came up (19 Oct run)
from rig.freshstart import fresh_start, prime_cache, switch_task
from rig.snapshot import WINDOWS_SCRIPT, _digest
from rig.vm import vm_out
from rig.vmprep import prepare_vm

OUT = BASE / "rig" / "out" / "dialog_probe"; OUT.mkdir(parents=True, exist_ok=True)
_spots = json.load(open(BASE / "rig" / "clickspots_pilot.json"))
ROWS = {r["row_id"]: r for r in (_spots["rows"] if isinstance(_spots, dict) else _spots)}
EDIT = "pyautogui.hotkey('ctrl', 'end'); pyautogui.press('down'); pyautogui.press('down'); pyautogui.typewrite('probe'); pyautogui.press('enter'); time.sleep(1)"
SAVE = "pyautogui.hotkey('ctrl', 's'); time.sleep(4); pyautogui.press('enter'); time.sleep(3)"
log = {}

# Buttons of every dialog/alert window LibreOffice shows, with their key bindings, and the Sheet menu's items.
DIALOG_READ = r"""python3 - <<'PY' 2>/dev/null
import sys, json, logging, subprocess
logging.disable(logging.CRITICAL)
sys.path.insert(0, "/home/user/server")
try:
    import main as srv
except Exception:
    pass
import pyatspi
def role(n):
    try: return n.getRoleName()
    except Exception: return ""
def kids(n):
    try: return list(n)
    except Exception: return []
def binding(n):
    try:
        a = n.queryAction()
        return [a.getName(i) + "=" + (a.getKeyBinding(i) or "") for i in range(a.nActions)]
    except Exception:
        return []
def buttons(n, d=0, out=None):
    out = [] if out is None else out
    if role(n) in ("push button", "toggle button", "menu item", "check menu item", "check box", "radio button"):
        out.append({"name": n.name, "keys": binding(n)})
    if d < 20:
        for c in kids(n):
            buttons(c, d + 1, out)
    return out
pids = set(int(x) for x in subprocess.run(["pgrep", "-f", "soffice"], capture_output=True, text=True).stdout.split())
res = {"dialogs": []}
for app in pyatspi.Registry.getDesktop(0):
    try: pid = int(app.get_process_id())
    except Exception: pid = -1
    if pid not in pids:
        continue
    for w in kids(app):
        if role(w) in ("dialog", "alert", "file chooser") or (role(w) == "frame" and "LibreOffice" not in (w.name or "")):
            res["dialogs"].append({"title": w.name, "role": role(w), "buttons": buttons(w)})
print(json.dumps(res))
PY"""

def windows(env):
    return [l.split(None, 3)[3] for l in vm_out(env, WINDOWS_SCRIPT, timeout=20).splitlines()
            if l.startswith("0x") and len(l.split(None, 3)) == 4 and not l.split(None, 3)[3].startswith("@!")]


def file_row(env, path):
    d, _ = _digest(env)
    return d.get(path, {})


def run(env, task, setup, route, judge, name, path):
    fresh_start(env, task)
    before = file_row(env, path)
    env.step(setup, pause=2)
    seen = json.loads(vm_out(env, DIALOG_READ, timeout=60) or "{}")
    w_mid = windows(env)
    env.step(route, pause=3)
    w_after = windows(env)
    after = file_row(env, path)
    verdict = judge(w_mid, w_after, before, after, env)
    rec = {"route": route[:200], "dialog_seen": seen.get("dialogs"), "windows_with_dialog": w_mid, "windows_after": w_after,
           "file_k_same": before.get("k") == after.get("k"), "file_h_same": before.get("h") == after.get("h"), "verdict": verdict}
    log.setdefault(name, []).append(rec)
    print(f"[{name}] {route[:70]!r}: {verdict}  windows {w_mid} -> {w_after}", flush=True)
    return verdict == "works"


def main():
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError("probe over 60 min")))
    signal.alarm(60 * 60)
    env = DesktopEnv(provider_name="modal", action_space="pyautogui", headless=True, require_a11y_tree=False, os_type="Ubuntu")
    t0 = time.time()
    try:
        def task_of(row_id):
            r = ROWS[row_id]
            return json.load(open(f"evaluation_examples/examples/libreoffice_calc/{r['task_id']}.json")), r["open_path"]

        task, path = task_of("pilot-0261")
        env.reset(task_config=task)
        print(f"ready {time.time()-t0:.0f}s; {prepare_vm(env)}; {prime_cache(env, task)}", flush=True)
        base = os.path.basename(path)

        # A. close without saving: the document window goes, nothing else opens, the file is untouched
        def closed(w_mid, w_after, before, after, env):
            if any(base in w for w in w_after):
                return "document still open" + (" (dialog still up)" if any("Save" in w for w in w_after) else "")
            return "works" if before.get("h") == after.get("h") else "closed but the file changed (it was saved)"
        for route in (DONT_SAVE + "; time.sleep(2)", "pyautogui.hotkey('alt', 'd'); time.sleep(2)",
                      "pyautogui.hotkey('alt', 'w'); time.sleep(2)", press_code("Don't Save")):
            if run(env, task, EDIT + "; pyautogui.hotkey('ctrl', 'w'); time.sleep(2)", route, closed, "close_unsaved", path):
                log["close_unsaved_route"] = route
                break

        # B. quit without saving: no LibreOffice window at all afterwards, file untouched
        # every case below is another task's workbook: switch_task brings its files in (env.reset would tear the
        # Modal sandbox down, and fresh_start alone only restores the files of a task already cached)
        task, path = task_of("pilot-0291"); base = os.path.basename(path)
        print("switch:", switch_task(env, task), flush=True)
        def quit_(w_mid, w_after, before, after, env):
            if any("LibreOffice" in w or base in w for w in w_after):
                return "LibreOffice still open"
            return "works" if before.get("h") == after.get("h") else "quit but the file changed"
        routes = [log["close_unsaved_route"]] if log.get("close_unsaved_route") else []
        routes += [r for r in (DONT_SAVE + "; time.sleep(3)", press_code("Don't Save")) if r not in routes]
        for route in routes:
            if run(env, task, EDIT + "; pyautogui.hotkey('ctrl', 'q'); time.sleep(2)", route, quit_, "quit_unsaved", path):
                log["quit_unsaved_route"] = route
                break

        # C. Save As over the open file's own name: the replace question, then the keep-format question
        task, path = task_of("pilot-0271")
        print("switch:", switch_task(env, task), flush=True)
        step1 = ROWS["pilot-0271"]["code"]
        def replaced(w_mid, w_after, before, after, env):
            if any(w for w in w_after if "LibreOffice" not in w and w.strip()):
                return f"a dialog is still open: {w_after}"
            return "works" if before.get("h") != after.get("h") else "file bytes unchanged (not saved)"
        for route in (CONFIRM_YES + "; time.sleep(4); pyautogui.press('enter'); time.sleep(3)",
                      "pyautogui.hotkey('alt', 'r'); time.sleep(4); pyautogui.press('enter'); time.sleep(3)",
                      press_code("Replace") + "; time.sleep(4); pyautogui.press('enter'); time.sleep(3)",
                      press_code("Yes") + "; time.sleep(4); pyautogui.press('enter'); time.sleep(3)"):
            if run(env, task, step1, route, replaced, "replace", path):
                log["replace_route"] = route
                break

        # D. delete sheet: is the menu route reaching "Delete Sheet...", and which key confirms
        task, path = task_of("pilot-0281")
        print("switch:", switch_task(env, task), flush=True)
        step1 = ROWS["pilot-0281"]["code"]
        fresh_start(env, task)
        before = file_row(env, path)
        log["delete_sheet_sheets_before"] = [s["name"] for s in before.get("v", [])]
        env.step(step1, pause=2)
        log["delete_sheet_step1_dialog"] = json.loads(vm_out(env, DIALOG_READ, timeout=60) or "{}").get("dialogs")
        print("delete sheet, after step 1:", log["delete_sheet_step1_dialog"], "sheets:", log["delete_sheet_sheets_before"], flush=True)
        def deleted(w_mid, w_after, before, after, env):
            env.step(SAVE, pause=3)
            now = [s["name"] for s in file_row(env, path).get("v", [])]
            return "works" if len(now) == len(log["delete_sheet_sheets_before"]) - 1 else f"sheets now {now}"
        for route in (CONFIRM_YES + "; time.sleep(2)", "pyautogui.press('enter'); time.sleep(2)", press_code("Yes")):
            if run(env, task, step1, route, deleted, "delete_sheet", path):
                log["delete_sheet_route"] = route
                break
        # E. top-up: Save As over the second workbook (row 0301): the replace question, Yes, keep format
        other = "/home/user/pilot_other.xlsx"
        r = ROWS["pilot-0301"]
        task, path = task_of("pilot-0301")
        print("switch:", switch_task(env, task), flush=True)
        def other_overwritten(w_mid, w_after, before, after, env):
            o = file_row(env, other)
            if not o:
                return "the second workbook is gone"
            if any("Question" in w or "Save" == w.strip() or "Keep" in w for w in w_after):
                return f"a dialog is still open: {w_after}"
            # the second workbook is another task's file (never equal to this one), so it was overwritten exactly
            # when its cells now equal the task file's
            return "works" if o.get("k") == before.get("k") else "second workbook not overwritten with this document"
        for route in (ROWS["pilot-0306"]["code"],
                      press_code("Yes") + "; time.sleep(4); pyautogui.press('enter'); time.sleep(3)"):
            if run(env, task, r["setup"] + "; " + r["code"], route, other_overwritten, "save_over_other", path):
                log["save_over_other_route"] = route
                break

        # F. top-up: delete the second workbook from the Save As dialog's list (row 0311).  First read what the
        # dialog offers once the file is selected (buttons, the context menu after Shift+F10), then try the routes.
        r = ROWS["pilot-0311"]
        task, path = task_of("pilot-0311")
        print("switch:", switch_task(env, task), flush=True)
        env.step(r["setup"], pause=2)
        env.step("pyautogui.hotkey('ctrl', 'shift', 's'); time.sleep(4); " + select_file_code("pilot_other.xlsx"), pause=1)
        log["delete_file_after_select"] = json.loads(vm_out(env, DIALOG_READ, timeout=60) or "{}").get("dialogs")
        env.step("pyautogui.hotkey('shift', 'f10'); time.sleep(2)", pause=1)
        log["delete_file_context_menu"] = json.loads(vm_out(env, DIALOG_READ, timeout=60) or "{}").get("dialogs")
        print("file dialog after select / Shift+F10:", json.dumps(log["delete_file_context_menu"])[:1500], flush=True)
        def other_deleted(w_mid, w_after, before, after, env):
            gone = not file_row(env, other)
            log.setdefault("delete_file_windows", []).append(w_after)
            return "works" if gone else "second workbook still on disk"
        open_select = "pyautogui.hotkey('ctrl', 'shift', 's'); time.sleep(4); " + select_file_code("pilot_other.xlsx")
        for name, step1 in (("delete key", open_select + "; pyautogui.press('delete'); time.sleep(2)"),
                            ("shift+delete", open_select + "; pyautogui.hotkey('shift', 'delete'); time.sleep(2)"),
                            ("context menu", open_select + "; pyautogui.hotkey('shift', 'f10'); time.sleep(2); " + press_code("Delete", settle=2))):
            for confirm in (CONFIRM_DELETE_FILE + "; time.sleep(2)", press_code("Delete", settle=2)):
                if run(env, task, r["setup"] + "; " + step1, confirm, other_deleted, "delete_file", path):
                    log["delete_file_step1"] = step1
                    log["delete_file_route"] = confirm
                    log["delete_file_how"] = name
                    break
            if log.get("delete_file_route"):
                break
        print("routes:", {k: v[:90] for k, v in log.items() if k.endswith("_route")}, flush=True)
    finally:
        (OUT / "log.json").write_text(json.dumps(log, indent=1, ensure_ascii=False))
        try:
            env.close(); print("env closed", flush=True)
        except Exception as e:
            print("close error", repr(e)[:200])
        print(f"done in {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
