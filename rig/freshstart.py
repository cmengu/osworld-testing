"""Fresh start without snapshot revert (Modal has none).

Slow path = OSWorld's own env.reset: re-downloads the task file and relaunches the app,
two to four minutes.  Fast path, after the first reset primed a cache inside the VM: close
LibreOffice, remove its lock and recovery files, copy the task files back from the cache,
relaunch LibreOffice on the file, wait for its window, maximise it, let it settle.  About
30 seconds.  Falls back to the slow path if the window does not appear.
"""
import time
from typing import List

from .vm import vm_out, vm_shell

CACHE_DIR = "/home/user/.rig_cache"
SETTLE_SECONDS = 8   # the accessibility bridge is slow for the first seconds after launch
CLEAN_SCRIPT = r"""
# -x (exact process name), never -f: the VM runs this script as sh -c "<text>", so a -f pattern matches
# that shell and kills the script on its first line, leaving every cleanup below unrun.
pkill -x soffice.bin 2>/dev/null; pkill -x oosplash 2>/dev/null; sleep 2; pkill -9 -x soffice.bin 2>/dev/null; pkill -9 -x oosplash 2>/dev/null
rm -f "$HOME"/.~lock.* "$HOME"/Desktop/.~lock.* "$HOME"/Documents/.~lock.* 2>/dev/null
rm -rf "$HOME"/.config/libreoffice/4/user/backup 2>/dev/null
# drop only the crash-recovery entries (one <item> per line) and keep the rest of the profile, so the
# relaunch matches the restart regime the mask was built from and never shows the Document Recovery dialog
sed -i "/org\\.openoffice\\.Office\\.Recovery/d" "$HOME"/.config/libreoffice/4/user/registrymodifications.xcu 2>/dev/null
rm -f "$HOME"/.config/libreoffice/4/.lock 2>/dev/null
# files written by actions under test (the Save As click-spot); never part of the task
rm -f "$HOME"/smoke_copy* "$HOME"/Documents/smoke_copy* "$HOME"/Desktop/smoke_copy* 2>/dev/null
true
"""


def task_files(task: dict) -> List[str]:
    """Paths the task setup downloads into the VM, in order."""
    paths = []
    for step in task.get("config", []):
        if step.get("type") == "download":
            for f in step.get("parameters", {}).get("files", []):
                if f.get("path"):
                    paths.append(f["path"])
    return paths


def task_open_path(task: dict):
    for step in task.get("config", []):
        if step.get("type") == "open":
            return step.get("parameters", {}).get("path")
    return None


def prime_cache(env, task: dict) -> str:
    """Call once right after the first env.reset: keep pristine copies of the task files."""
    files = task_files(task)
    if not files:
        return "no task files"
    cmds = [f"mkdir -p {CACHE_DIR}"] + [f'cp -f "{p}" {CACHE_DIR}/' for p in files]
    return vm_out(env, "; ".join(cmds) + "; ls -1 " + CACHE_DIR)


def _restore_files(env, task: dict) -> None:
    cmds = [f'cp -f {CACHE_DIR}/"$(basename "{p}")" "{p}"' for p in task_files(task)]
    if cmds:
        vm_shell(env, "; ".join(cmds) + "; true", timeout=30)


def _launch_and_wait(env, path: str, title_hint: str = "LibreOffice Calc", wait_s: int = 75) -> bool:
    """Wait for the DOCUMENT window ("LibreOffice Calc"): the splash screen and the Document Recovery
    dialog are also titled LibreOffice and must not count as ready."""
    vm_shell(env, f'nohup libreoffice --calc "{path}" >/dev/null 2>&1 &', timeout=20)
    deadline = time.time() + wait_s
    while time.time() < deadline:
        time.sleep(2)
        windows = vm_out(env, "wmctrl -l 2>/dev/null", timeout=15)
        if "Document Recovery" in windows:
            return False      # recovery dialog: the caller cleans again and takes the slow path
        if title_hint in windows:
            break
    else:
        return False
    time.sleep(3)  # let the document finish laying out
    vm_shell(env, f'wmctrl -r "{title_hint}" -b add,maximized_vert,maximized_horz 2>/dev/null; true', timeout=15)
    time.sleep(SETTLE_SECONDS)
    return True


def fresh_start(env, task: dict, fast: bool = True) -> str:
    """Returns which path ran: 'fast', 'slow' or 'slow-after-fast-failed'."""
    # graceful close first so LibreOffice does not leave a recovery entry behind
    try:
        env.step("pyautogui.hotkey('ctrl', 'q'); time.sleep(3); pyautogui.hotkey('alt', 'd'); time.sleep(3)", pause=0.5)
    except Exception:
        pass
    vm_shell(env, CLEAN_SCRIPT, timeout=60)
    open_path = task_open_path(task)
    if fast and open_path and task_files(task):
        _restore_files(env, task)
        if _launch_and_wait(env, open_path):
            return "fast"
        vm_shell(env, CLEAN_SCRIPT, timeout=60)
        env.reset(task_config=task)
        time.sleep(SETTLE_SECONDS)
        return "slow-after-fast-failed"
    env.reset(task_config=task)
    time.sleep(SETTLE_SECONDS)
    return "slow"
