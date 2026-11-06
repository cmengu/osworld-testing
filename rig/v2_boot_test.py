"""Boot test for the OSWorld 2.1 Ubuntu disk on our Modal provider (6 Nov 2026, author's go: "lets try").

One sandbox: boot the V2 qcow2 (staged by rig/stage_v2_image.py), time it, save a screenshot, read the accessibility
tree with the rig's reader, and run a few shell checks (OS, apps, sudo with the V2 and v1 passwords, disk, network).
No task, no agent, nothing written outside the VM.  About 10-15 sandbox minutes (~0.2 USD).

    OSWorld/.venv/bin/python -I rig/v2_boot_test.py
"""
import json, os, pathlib, sys, time
HERE = pathlib.Path(__file__).resolve().parent; BASE = HERE.parent; OSWORLD = BASE / "OSWorld"
sys.path.insert(0, str(BASE)); sys.path.insert(0, str(OSWORLD)); os.chdir(OSWORLD)
from desktop_env.desktop_env import DesktopEnv
from rig.snapshot import fetch_tree
from rig.treediff import canonicalize
from rig.vm import vm_out

NAME = "osworld-v2-ubuntu-x86.qcow2"
OUT = BASE / "rig" / "out" / "v2_boot"; OUT.mkdir(parents=True, exist_ok=True)
CHECKS = r"""echo "== os"; lsb_release -ds 2>/dev/null; uname -r; whoami
echo "== apps"; for a in soffice code thunderbird google-chrome chromium firefox vlc gimp gnome-terminal nautilus; do printf '%s: ' $a; command -v $a || echo missing; done
echo "== sudo"; echo osworld-public-evaluation | sudo -S -k true 2>/dev/null && echo "v2 password ok" || echo "v2 password no"
echo password | sudo -S -k true 2>/dev/null && echo "v1 password ok" || echo "v1 password no"
echo "== disk"; df -h / | tail -1
echo "== a11y"; gsettings get org.gnome.desktop.interface toolkit-accessibility 2>&1
echo "== net"; getent hosts huggingface.co | head -1 || echo "no dns"
echo "== home"; ls ~ | head -20
echo "== hosts"; grep -v '^#' /etc/hosts | head
"""


def main():
    t0 = time.time()
    env = DesktopEnv(provider_name="modal", path_to_vm=NAME, action_space="pyautogui", headless=True,
                     require_a11y_tree=False, os_type="Ubuntu")
    res = {"disk": NAME}
    try:
        res["boot_seconds"] = round(time.time() - t0)
        print("booted at", res["boot_seconds"], "s", flush=True)
        shot = env.controller.get_screenshot()
        if shot:
            (OUT / "screen.png").write_bytes(shot)
        res["screenshot_bytes"] = len(shot or b"")
        res["checks"] = vm_out(env, CHECKS, timeout=60)
        print(res["checks"], flush=True)
        xml, info = fetch_tree(env)
        res["tree"] = {"info": str(info)[:300], "nodes": len(canonicalize(xml)) if xml else 0}
        print("tree:", res["tree"], flush=True)
    except Exception as e:
        res["error"] = repr(e)[:500]
        print("ERROR", res["error"], flush=True)
    finally:
        try:
            env.close()
        except Exception as e:
            res["close_error"] = repr(e)[:200]
        res["total_seconds"] = round(time.time() - t0)
        (OUT / "result.json").write_text(json.dumps(res, indent=1))
        print("done", res["total_seconds"], "s", flush=True)


if __name__ == "__main__":
    main()
