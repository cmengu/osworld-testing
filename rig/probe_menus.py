"""One-sandbox probe before the pilot: screenshots of the menus and dialogs the click-spots rely on, so the
menu mnemonics (Sheet > Insert Sheet at End, Sheet > Delete Sheet, Edit > Undo, File > Reload) and the
dialog buttons (Don't Save, Replace, Yes) can be read off the image instead of guessed.  Also exercises the
GNOME run dialog (Alt+F2) that the `reopen` undo step uses after Ctrl+Q, and Ctrl++ for insert row.

    OSWorld/.venv/bin/python -I rig/probe_menus.py            # ~10 min of sandbox, screenshots in rig/out/menu_probe/
"""
import json
import os
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
BASE = HERE.parent
OSWORLD = BASE / "OSWorld"
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(OSWORLD))
os.chdir(OSWORLD)

from desktop_env.desktop_env import DesktopEnv                 # noqa: E402
from rig.freshstart import fresh_start, prime_cache            # noqa: E402
from rig.vm import vm_out                                      # noqa: E402
from rig.vmprep import prepare_vm                              # noqa: E402

TASK = "evaluation_examples/examples/libreoffice_calc/357ef137-7eeb-4c80-a3bb-0951f26a8aff.json"
OUT = BASE / "rig" / "out" / "menu_probe"

# (name, code, settle seconds, cleanup code).  Each probe starts from a fresh start + Ctrl+Home.
PROBES = [
    ("menu_sheet", "pyautogui.keyDown('alt'); time.sleep(0.5); pyautogui.press('s'); time.sleep(1.5)", 1, "pyautogui.keyUp('alt'); pyautogui.press('esc'); pyautogui.press('esc')"),
    ("menu_sheet_released", "pyautogui.hotkey('alt', 's'); time.sleep(1.5)", 1, "pyautogui.press('esc'); pyautogui.press('esc')"),
    ("menu_edit", "pyautogui.hotkey('alt', 'e'); time.sleep(1.5)", 1, "pyautogui.press('esc'); pyautogui.press('esc')"),
    ("menu_file", "pyautogui.hotkey('alt', 'f'); time.sleep(1.5)", 1, "pyautogui.press('esc'); pyautogui.press('esc')"),
    ("menu_data", "pyautogui.hotkey('alt', 'd'); time.sleep(1.5)", 1, "pyautogui.press('esc'); pyautogui.press('esc')"),
    ("delete_sheet_d", "pyautogui.hotkey('alt', 's'); time.sleep(1.5); pyautogui.press('d'); time.sleep(2)", 1, "pyautogui.press('esc'); pyautogui.press('esc')"),
    ("insert_sheet_end_t", "pyautogui.hotkey('alt', 's'); time.sleep(1.5); pyautogui.press('t'); time.sleep(2)", 1, "pyautogui.press('esc'); pyautogui.press('esc')"),
    ("insert_row_ctrl_plus", "pyautogui.hotkey('shift', 'space'); pyautogui.hotkey('ctrl', '+'); time.sleep(1.5)", 1, "pyautogui.hotkey('ctrl', 'z')"),
    ("backspace_dialog", "pyautogui.press('backspace'); time.sleep(1.5)", 1, "pyautogui.press('esc')"),
    ("paste_special", "pyautogui.hotkey('ctrl', 'c'); pyautogui.press('right'); pyautogui.hotkey('ctrl', 'shift', 'v'); time.sleep(2)", 1, "pyautogui.press('esc'); pyautogui.press('esc')"),
    ("paste_over_used_range", "pyautogui.hotkey('ctrl', 'c'); pyautogui.hotkey('ctrl', 'shift', 'end'); pyautogui.hotkey('ctrl', 'v'); time.sleep(2)", 1, "pyautogui.press('esc'); pyautogui.hotkey('ctrl', 'home')"),
    ("save_as_dialog", "pyautogui.hotkey('ctrl', 'shift', 's'); time.sleep(4)", 1, "pyautogui.press('esc')"),
    ("close_unsaved_dialog", "pyautogui.typewrite('pilot'); pyautogui.press('enter'); pyautogui.hotkey('ctrl', 'w'); time.sleep(2)", 1, "pyautogui.press('esc')"),
    ("print_dialog", "pyautogui.hotkey('ctrl', 'p'); time.sleep(3)", 1, "pyautogui.press('esc')"),
    ("ctrl_n", "pyautogui.hotkey('ctrl', 'n'); time.sleep(3)", 1, "pyautogui.hotkey('ctrl', 'w')"),
    ("quit_then_alt_f2", "pyautogui.hotkey('ctrl', 'q'); time.sleep(3); pyautogui.hotkey('alt', 'f2'); time.sleep(2)", 1, "pyautogui.press('esc')"),
    ("reopen_via_alt_f2", "pyautogui.hotkey('ctrl', 'q'); time.sleep(3); pyautogui.hotkey('alt', 'f2'); time.sleep(2); pyautogui.typewrite('libreoffice --calc /home/user/Multiply_Time_Number.xlsx'); time.sleep(1); pyautogui.press('enter'); time.sleep(15); pyautogui.hotkey('super', 'up'); time.sleep(3)", 1, ""),
    ("start_center_open", "pyautogui.hotkey('ctrl', 'w'); time.sleep(2); pyautogui.hotkey('ctrl', 'o'); time.sleep(3); pyautogui.typewrite('/home/user/Multiply_Time_Number.xlsx'); time.sleep(1); pyautogui.press('enter'); time.sleep(8)", 1, ""),
    ("replace_dialog", "pyautogui.typewrite('pilot'); pyautogui.press('enter'); pyautogui.hotkey('ctrl', 'shift', 's'); time.sleep(4); pyautogui.typewrite('pilot_copy'); time.sleep(1); pyautogui.press('enter'); time.sleep(4); pyautogui.press('enter'); time.sleep(3); pyautogui.hotkey('ctrl', 'shift', 's'); time.sleep(4); pyautogui.typewrite('Multiply_Time_Number'); time.sleep(1); pyautogui.press('enter'); time.sleep(3)", 1, "pyautogui.press('esc'); pyautogui.press('esc')"),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    task = json.load(open(TASK))
    env = DesktopEnv(provider_name="modal", action_space="pyautogui", headless=True, require_a11y_tree=False, os_type="Ubuntu")
    t0 = time.time()
    log = []
    try:
        env.reset(task_config=task)
        print(f"ready at {time.time() - t0:.0f}s; {prepare_vm(env)}; {prime_cache(env, task)}", flush=True)
        for name, code, settle, cleanup in PROBES:
            t = time.time()
            how = fresh_start(env, task)
            env.step("pyautogui.hotkey('ctrl', 'home')", pause=1)
            env.step(code, pause=settle)
            shot = env.controller.get_screenshot()
            if shot:
                (OUT / f"{name}.png").write_bytes(shot)
            windows = vm_out(env, "wmctrl -l 2>/dev/null; echo ---; xdotool getactivewindow getwindowname 2>/dev/null", timeout=15)
            files = vm_out(env, "ls -la /home/user/*.xlsx /home/user/pilot_* 2>/dev/null", timeout=15)
            entry = {"probe": name, "fresh": how, "windows": windows, "files": files, "seconds": round(time.time() - t)}
            log.append(entry)
            print(f"{name}: fresh={how} windows={windows.replace(chr(10), ' | ')[:200]} ({entry['seconds']}s)", flush=True)
            if cleanup:
                env.step(cleanup, pause=1)
        (OUT / "log.json").write_text(json.dumps(log, indent=1))
    finally:
        try:
            env.close()
            print("env closed", flush=True)
        except Exception as e:
            print("close error:", repr(e)[:200], flush=True)
    print(f"done in {time.time() - t0:.0f}s; screenshots in {OUT}")


if __name__ == "__main__":
    main()
