"""Second probe: read open menus and the insert-row result from the accessibility tree (screenshots did not
show dialogs or menus on this image; wmctrl and the tree do).  ~8 min of sandbox."""
import json, os, pathlib, re, sys, time
HERE = pathlib.Path(__file__).resolve().parent; BASE = HERE.parent; OSWORLD = BASE / "OSWorld"
sys.path.insert(0, str(BASE)); sys.path.insert(0, str(OSWORLD)); os.chdir(OSWORLD)
from desktop_env.desktop_env import DesktopEnv
from rig.freshstart import fresh_start, prime_cache
from rig.fasttree import fast_tree
from rig.treediff import canonicalize
from rig.vm import vm_out
from rig.vmprep import prepare_vm
TASK = "evaluation_examples/examples/libreoffice_calc/357ef137-7eeb-4c80-a3bb-0951f26a8aff.json"
OUT = BASE / "rig" / "out" / "menu_probe"; OUT.mkdir(parents=True, exist_ok=True)

def menu_items(xml):
    """names of menu items visible anywhere in the tree (open popup menus show their items)."""
    return re.findall(r'<menu-item[^>]*name="([^"]*)"', xml)[:80]

def cell(canon, ref):
    for p, a in canon.items():
        if p.endswith(f"/table-cell[{ref}]#0"):
            return a.get("text")
    return None

PROBES = [
    ("alt_s", "pyautogui.hotkey('alt', 's'); time.sleep(2)"),
    ("f10_then_right5", "pyautogui.press('f10'); time.sleep(1); " + "pyautogui.press('right'); " * 5 + "time.sleep(1); pyautogui.press('down'); time.sleep(1.5)"),
    ("insert_row_plus", "pyautogui.hotkey('shift', 'space'); pyautogui.hotkey('ctrl', '+'); time.sleep(2)"),
    ("insert_row_add", "pyautogui.hotkey('shift', 'space'); pyautogui.hotkey('ctrl', 'add'); time.sleep(2)"),
    ("insert_row_shift_equal", "pyautogui.hotkey('shift', 'space'); pyautogui.keyDown('ctrl'); pyautogui.keyDown('shift'); pyautogui.press('='); pyautogui.keyUp('shift'); pyautogui.keyUp('ctrl'); time.sleep(2)"),
]

def main():
    task = json.load(open(TASK))
    env = DesktopEnv(provider_name="modal", action_space="pyautogui", headless=True, require_a11y_tree=False, os_type="Ubuntu")
    t0 = time.time(); log = []
    try:
        env.reset(task_config=task)
        print(f"ready at {time.time()-t0:.0f}s; {prepare_vm(env)}; {prime_cache(env, task)}", flush=True)
        for name, code in PROBES:
            fresh_start(env, task)
            env.step("pyautogui.hotkey('ctrl', 'home')", pause=1)
            env.step(code, pause=1)
            xml, stats = fast_tree(env)
            canon = canonicalize(xml) if xml else {}
            items = menu_items(xml)
            win = vm_out(env, "wmctrl -l 2>/dev/null", timeout=15)
            entry = {"probe": name, "nodes": len(canon), "menu_items": items, "A2": cell(canon, "A2"), "A3": cell(canon, "A3"),
                     "windows": win, "stats": {k: stats.get(k) for k in ("office_frames", "menus_shallow", "seconds")}}
            (OUT / f"tree_{name}.xml").write_text(xml or "")
            log.append(entry)
            print(json.dumps(entry)[:900], flush=True)
            env.step("pyautogui.press('esc'); pyautogui.press('esc'); pyautogui.hotkey('ctrl', 'z')", pause=1)
        (OUT / "log_tree.json").write_text(json.dumps(log, indent=1))
    finally:
        try:
            env.close(); print("env closed", flush=True)
        except Exception as e:
            print("close error", repr(e)[:200])
    print(f"done in {time.time()-t0:.0f}s")

if __name__ == "__main__":
    main()
