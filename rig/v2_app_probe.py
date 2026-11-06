"""Third V2 boot check (6 Nov 2026): fetch the V2 VM server's accessibility code (to port rig/fasttree.py) and check
that an app opens and shows in the screenshot and the server's own tree.  One sandbox, a few minutes."""
import json, os, pathlib, sys, time
HERE = pathlib.Path(__file__).resolve().parent; BASE = HERE.parent; OSWORLD = BASE / "OSWorld"
sys.path.insert(0, str(BASE)); sys.path.insert(0, str(OSWORLD)); os.chdir(OSWORLD)
from desktop_env.desktop_env import DesktopEnv
from rig.vm import vm_out
OUT = BASE / "rig" / "out" / "v2_boot"; OUT.mkdir(parents=True, exist_ok=True)
env = DesktopEnv(provider_name="modal", path_to_vm="osworld-v2-ubuntu-x86.qcow2", action_space="pyautogui", headless=True,
                 require_a11y_tree=False, os_type="Ubuntu")
res = {}
try:
    for f in ("src/accessibility.py", "src/http_routes.py", "src/platform_runtime.py"):
        b = env.controller.get_file(f"/home/user/server/{f}")
        if b: (OUT / pathlib.Path(f).name).write_bytes(b)
        res[f] = len(b or b"")
    vm_out(env, "echo 'hello v2' > ~/Desktop/probe.txt; nohup soffice --writer ~/Desktop/probe.txt >/dev/null 2>&1 &", timeout=20)
    time.sleep(45)
    shot = env.controller.get_screenshot()
    if shot: (OUT / "writer.png").write_bytes(shot)
    tree = env.controller.get_accessibility_tree()
    res["writer_shot"] = len(shot or b""); res["tree_chars"] = len(tree or ""); res["tree_has_writer"] = "probe.txt" in (tree or "")
    res["windows"] = vm_out(env, "wmctrl -l 2>/dev/null || xdotool search --name . getwindowname 2>/dev/null | head", timeout=20)
    print(res, flush=True)
finally:
    env.close()
    (OUT / "app_probe.json").write_text(json.dumps(res, indent=1))
