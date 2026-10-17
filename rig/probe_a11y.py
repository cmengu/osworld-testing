"""Diagnose why the scoped walker saw no LibreOffice in the second probe: retries, a11y settings, the soffice
environment, and the server's full walk for the open Sheet menu and the insert-row result."""
import json, os, pathlib, re, sys, time
HERE = pathlib.Path(__file__).resolve().parent; BASE = HERE.parent; OSWORLD = BASE / "OSWorld"
sys.path.insert(0, str(BASE)); sys.path.insert(0, str(OSWORLD)); os.chdir(OSWORLD)
from desktop_env.desktop_env import DesktopEnv
from rig.freshstart import fresh_start, prime_cache
from rig.snapshot import fetch_tree
from rig.treediff import canonicalize
from rig.vm import vm_out
from rig.vmprep import prepare_vm
TASK = "evaluation_examples/examples/libreoffice_calc/357ef137-7eeb-4c80-a3bb-0951f26a8aff.json"
OUT = BASE / "rig" / "out" / "menu_probe"; OUT.mkdir(parents=True, exist_ok=True)
DIAG = r"""echo "a11y=$(gsettings get org.gnome.desktop.interface toolkit-accessibility 2>&1)"; pid=$(pgrep -x soffice.bin | head -1); echo "soffice pid=$pid"; [ -n "$pid" ] && tr '\0' '\n' < /proc/$pid/environ | grep -E 'GTK_MODULES|ACCESSIBILITY|AT_SPI|SAL_|DISPLAY|XDG_SESSION' ; echo "at-spi procs: $(pgrep -fc at-spi)"; ps -eo pid,etimes,cmd | grep -E 'soffice|at-spi' | grep -v grep | head"""

def cell(canon, ref):
    for p, a in canon.items():
        if p.endswith(f"/table-cell[{ref}]#0"):
            return a.get("text")
    return None

def main():
    task = json.load(open(TASK))
    env = DesktopEnv(provider_name="modal", action_space="pyautogui", headless=True, require_a11y_tree=False, os_type="Ubuntu")
    t0 = time.time()
    try:
        env.reset(task_config=task)
        print(f"ready at {time.time()-t0:.0f}s; {prepare_vm(env)}; {prime_cache(env, task)}", flush=True)
        print("DIAG after reset:\n" + vm_out(env, DIAG, timeout=30), flush=True)
        xml, info = fetch_tree(env)
        print("tree after reset (setup-launched window):", info, "nodes", len(canonicalize(xml)) if xml else 0, flush=True)
        how = fresh_start(env, task)
        print("fresh start:", how, flush=True)
        print("DIAG after fresh start:\n" + vm_out(env, DIAG, timeout=30), flush=True)
        for i in range(3):
            xml, info = fetch_tree(env)
            canon = canonicalize(xml) if xml else {}
            print(f"tree try {i}: {info} nodes={len(canon)} A2={cell(canon, 'A2')}", flush=True)
            if len(canon) > 100:
                break
            time.sleep(10)
        # menu via the server's full walk (includes popup menus)
        env.step("pyautogui.hotkey('ctrl', 'home'); pyautogui.hotkey('alt', 's'); time.sleep(2)", pause=1)
        t = time.time(); full = env.controller.get_accessibility_tree() or ""
        items = re.findall(r'<menu-item[^>]*name="([^"]*)"', full)
        print(f"server full tree with Alt+S open: {len(full)} chars in {time.time()-t:.0f}s; menu items: {items[:60]}", flush=True)
        (OUT / "full_alt_s.xml").write_text(full)
        env.step("pyautogui.press('esc'); pyautogui.press('esc')", pause=1)
        # insert row variants, judged by the fast tree with retries
        for name, code in [("plus", "pyautogui.hotkey('ctrl', '+')"), ("add", "pyautogui.hotkey('ctrl', 'add')"),
                           ("shift_equal", "pyautogui.keyDown('ctrl'); pyautogui.keyDown('shift'); pyautogui.press('='); pyautogui.keyUp('shift'); pyautogui.keyUp('ctrl')")]:
            fresh_start(env, task)
            env.step("pyautogui.hotkey('ctrl', 'home'); pyautogui.hotkey('shift', 'space'); " + code + "; time.sleep(2)", pause=1)
            xml, info = fetch_tree(env); canon = canonicalize(xml) if xml else {}
            print(f"insert_row_{name}: nodes={len(canon)} A2={cell(canon, 'A2')!r} A3={cell(canon, 'A3')!r} {info.get('attempt')}", flush=True)
    finally:
        try:
            env.close(); print("env closed", flush=True)
        except Exception as e:
            print("close error", repr(e)[:200])
    print(f"done in {time.time()-t0:.0f}s")

if __name__ == "__main__":
    main()
