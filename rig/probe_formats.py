"""Probe of 18 Oct 2026, about 12 min of sandbox: three things only a real Calc can answer.

1. The digest script now carries the cell-level workbook signature (rig/xlsxsig.py).  Does it run in the VM,
   and does a plain save of an untouched workbook keep the signature (pilot-0121 save_clean)?
2. Can cell formats be read directly through the accessibility Text interface (weight, style, underline),
   independent of where the cursor is?  Bold A1 (has text) and D8 (empty), move the cursor away, read again.
3. Which key route hides a column and a row on this image (Ctrl+0 / Ctrl+9 did nothing)?  The Format menu's
   item order is read through pyatspi (the server's full walk came back empty), the route is tried, and the
   result is judged from the saved file's hidden columns/rows.
Results, 18 Oct 2026: (1) a plain save keeps the cell signature (bytes and zip hash change); (2) weight/style read
correctly with the cursor elsewhere, once LibreOffice is on the bus (the first two reads after a fresh start saw no
soffice); (3) Format > Rows/Columns > Hide is 6/7 downs, Right, 2 downs, Enter.  --skip-save skips part 1.
Writes rig/out/format_probe/log.json.
"""
import json, os, pathlib, re, signal, sys, time
HERE = pathlib.Path(__file__).resolve().parent; BASE = HERE.parent; OSWORLD = BASE / "OSWorld"
sys.path.insert(0, str(BASE)); sys.path.insert(0, str(OSWORLD)); os.chdir(OSWORLD)
from desktop_env.desktop_env import DesktopEnv
from rig.freshstart import fresh_start, prime_cache
from rig.snapshot import _digest
from rig.vm import vm_out
from rig.vmprep import prepare_vm

TASK = "evaluation_examples/examples/libreoffice_calc/347ef137-7eeb-4c80-a3bb-0951f26a8aff.json"
FILE = "/home/user/Create_column_charts_using_statistics.xlsx"
OUT = BASE / "rig" / "out" / "format_probe"; OUT.mkdir(parents=True, exist_ok=True)
SAVE = "pyautogui.hotkey('ctrl', 's'); time.sleep(4); pyautogui.press('enter'); time.sleep(3)"
log = {}

FORMAT_READ = r"""python3 - <<'PY' 2>/dev/null
import sys, logging
logging.disable(logging.CRITICAL)
sys.path.insert(0, "/home/user/server")
try:
    import main as srv          # the walker's own setup: connects to the session's accessibility bus
except Exception as e:
    print("__SRV__" + repr(e)[:200])
import json, subprocess, pyatspi
REFS = {"A1": (0, 0), "B2": (1, 1), "D8": (7, 3)}
def role(n):
    try: return n.getRoleName()
    except Exception: return ""
def find(n, d=0):
    if role(n) == "table" and (n.name or "").startswith("Sheet"): return n
    if d > 14: return None
    try: kids = list(n)
    except Exception: return None
    for c in kids:
        r = find(c, d + 1)
        if r is not None: return r
    return None
pids = set(int(x) for x in subprocess.run(["pgrep", "-f", "soffice"], capture_output=True, text=True).stdout.split())
t = None; apps = []
for app in pyatspi.Registry.getDesktop(0):
    try: frames = list(app)
    except Exception: continue
    try: pid = int(app.get_process_id())
    except Exception: pid = -1
    apps.append((app.name, pid in pids, [f.name for f in frames][:3]))
    if pid in pids or any("LibreOffice" in (f.name or "") for f in frames):
        t = find(app)
        if t is not None: break
out = {"table": t.name if t is not None else None, "apps": apps}
if t is not None:
    tab = t.queryTable()
    for ref, (r, c) in REFS.items():
        cell = tab.getAccessibleAt(r, c); d = {"name": cell.name}
        try:
            tx = cell.queryText(); d["chars"] = tx.characterCount
            d["run"] = repr(tx.getAttributeRun(0, True))[:600]
            d["default"] = repr(tx.getDefaultAttributes())[:600]
        except Exception as e: d["text_err"] = repr(e)[:200]
        try: d["obj"] = {k: v for k, v in dict(cell.get_attributes()).items()}
        except Exception as e: d["obj_err"] = repr(e)[:200]
        out[ref] = d
print(json.dumps(out))
PY"""


MENU_READ = r"""python3 - <<'PY' 2>/dev/null
import sys, logging
logging.disable(logging.CRITICAL)
sys.path.insert(0, "/home/user/server")
try:
    import main as srv          # the walker's own setup: connects to the session's accessibility bus
except Exception as e:
    print("__SRV__" + repr(e)[:200])
import json, subprocess, pyatspi
pids = set(int(x) for x in subprocess.run(["pgrep", "-f", "soffice"], capture_output=True, text=True).stdout.split())
def role(n):
    try: return n.getRoleName()
    except Exception: return ""
def find(n, want, d=0):
    if role(n) == want: return n
    if d > 10 or role(n) in ("table", "menu bar") and want != "menu bar": return None
    try: kids = list(n)
    except Exception: return None
    for c in kids:
        r = find(c, want, d + 1)
        if r is not None: return r
mb = None
for app in pyatspi.Registry.getDesktop(0):
    try: pid = int(app.get_process_id())
    except Exception: pid = -1
    if pid in pids:
        mb = find(app, "menu bar")
        if mb is not None: break
def items(menu):
    out = []
    for c in menu:
        st = c.getState()
        out.append([c.name, role(c), st.contains(pyatspi.STATE_ENABLED)])
    return out
res = {}
if mb is not None:
    for top in mb:
        if top.name.replace("~", "") == "Format":
            res["Format"] = items(top)
            for sub in top:
                if sub.name.replace("~", "") in ("Columns", "Rows"):
                    res[sub.name.replace("~", "")] = items(sub)
print(json.dumps(res))
PY"""


def step(env, code, pause=1):
    env.step(code, pause=pause)


def file_view(env):
    d, err = _digest(env)
    row = d.get(FILE, {})
    return row, err


def check_save(env):
    """Part 1: the digest runs in the VM, and a plain save keeps the cell signature."""
    row0, err = file_view(env)
    log["digest_before"] = {"keys": sorted(row0), "k": row0.get("k"), "k_error": row0.get("k_error"), "err": err,
                            "cells": sum(len(s["cells"]) for s in row0.get("v", [])) if row0.get("v") else None}
    print("digest before save:", log["digest_before"], flush=True)
    step(env, SAVE, pause=3)
    row1, err = file_view(env)
    log["digest_after_save"] = {"k": row1.get("k"), "c_same": row1.get("c") == row0.get("c"), "h_same": row1.get("h") == row0.get("h"),
                                "size": [row0.get("s"), row1.get("s")], "err": err}
    log["save_clean_same_cells"] = bool(row0.get("k")) and row0.get("k") == row1.get("k")
    if not log["save_clean_same_cells"] and row0.get("v") and row1.get("v"):
        diffs = []
        for a, b in zip(row0["v"], row1["v"]):
            for ref in sorted(set(a["cells"]) | set(b["cells"])):
                if a["cells"].get(ref) != b["cells"].get(ref) and len(diffs) < 25:
                    diffs.append([a["name"], ref, a["cells"].get(ref), b["cells"].get(ref)])
            for key in ("name", "state", "hidden_cols", "hidden_rows", "merges"):
                if a[key] != b[key]:
                    diffs.append([a["name"], key, a[key], b[key]])
        log["save_clean_diffs"] = diffs
    print("after plain save:", log["digest_after_save"], "same cells:", log["save_clean_same_cells"], flush=True)



def main():
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError("probe over 25 min")))
    signal.alarm(25 * 60)
    task = json.load(open(TASK))
    env = DesktopEnv(provider_name="modal", action_space="pyautogui", headless=True, require_a11y_tree=False, os_type="Ubuntu")
    t0 = time.time()
    try:
        env.reset(task_config=task)
        print(f"ready {time.time()-t0:.0f}s; {prepare_vm(env)}; {prime_cache(env, task)}", flush=True)
        print("fresh start:", fresh_start(env, task), flush=True)

        # 1. digest in the VM, then a plain save
        if "--skip-save" in sys.argv:
            log["save_clean_same_cells"] = "skipped: passed in the first probe run (same k after a plain save)"
        else:
            check_save(env)

        # 2. formats through the Text interface
        fresh_start(env, task)
        log["formats_before"] = json.loads(vm_out(env, FORMAT_READ, timeout=60) or "{}")
        step(env, "pyautogui.hotkey('ctrl', 'home'); pyautogui.hotkey('ctrl', 'b'); "
                  + "pyautogui.press('right'); " * 3 + "pyautogui.press('down'); " * 7 + "pyautogui.hotkey('ctrl', 'b'); time.sleep(1)")
        log["formats_bold_cursor_on_D8"] = json.loads(vm_out(env, FORMAT_READ, timeout=60) or "{}")
        step(env, "pyautogui.hotkey('ctrl', 'end'); time.sleep(1)")
        log["formats_bold_cursor_away"] = json.loads(vm_out(env, FORMAT_READ, timeout=60) or "{}")
        for k in ("formats_before", "formats_bold_cursor_on_D8", "formats_bold_cursor_away"):
            print(k, json.dumps(log[k])[:1500], flush=True)

        # 3. hide column / row through the Format menu
        fresh_start(env, task)
        menus = json.loads(vm_out(env, MENU_READ, timeout=90) or "{}")
        sep = lambda lst: [(None if r == "separator" else n, r, en) for n, r, en in lst]
        fmt, cols, rows = sep(menus.get("Format", [])), sep(menus.get("Columns", [])), sep(menus.get("Rows", []))
        log["format_menu"] = fmt
        log["columns_menu"], log["rows_menu"] = cols, rows
        print("Format menu:", fmt, "\nColumns:", cols, "\nRows:", rows, flush=True)
        log["routes"] = {}
        for what, sub, select in (("Columns", cols, "pyautogui.hotkey('ctrl', 'space'); "), ("Rows", rows, "pyautogui.hotkey('shift', 'space'); ")):
            names = [n for n, tag, en in fmt if n is not None]
            sub_names = [n for n, tag, en in sub if n is not None]
            if what not in [n.replace("~", "") for n in names] or "Hide" not in [n.replace("~", "") for n in sub_names]:
                log["routes"][what] = "menu entries not found"
                continue
            top = [n.replace("~", "") for n in names].index(what)
            hide = [n.replace("~", "") for n in sub_names].index("Hide")
            found = None
            for dtop in (0, -1, 1):
                code = ("pyautogui.hotkey('ctrl', 'home'); " + select + "pyautogui.hotkey('alt', 'o'); time.sleep(1.5); "
                        + "pyautogui.press('down'); " * max(top + dtop, 0) + "pyautogui.press('right'); time.sleep(1); "
                        + "pyautogui.press('down'); " * hide + "pyautogui.press('enter'); time.sleep(2)")
                fresh_start(env, task)
                step(env, code, pause=2)
                step(env, SAVE, pause=3)
                row, err = file_view(env)
                sheet = (row.get("v") or [{}])[0]
                hidden = sheet.get("hidden_cols" if what == "Columns" else "hidden_rows")
                print(f"{what} route top={top + dtop} hide={hide}: hidden={hidden}", flush=True)
                if hidden in ([[1, 1]], [1]):
                    found = code
                    break
            log["routes"][what] = found or "no route hid exactly the first one"
        print("routes:", json.dumps(log["routes"], indent=1), flush=True)
    finally:
        (OUT / "log.json").write_text(json.dumps(log, indent=1, ensure_ascii=False))
        try:
            env.close(); print("env closed", flush=True)
        except Exception as e:
            print("close error", repr(e)[:200])
        print(f"done in {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
