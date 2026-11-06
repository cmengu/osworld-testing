"""Second V2 boot check (6 Nov 2026): why the screenshot timed out and how the V2 VM server is laid out, so the rig's
fast tree reader (rig/fasttree.py imports the VM server's main.py) can be ported.  One sandbox, a few minutes."""
import json, os, pathlib, sys, time
import requests
HERE = pathlib.Path(__file__).resolve().parent; BASE = HERE.parent; OSWORLD = BASE / "OSWorld"
sys.path.insert(0, str(BASE)); sys.path.insert(0, str(OSWORLD)); os.chdir(OSWORLD)
from desktop_env.desktop_env import DesktopEnv
from rig.vm import vm_out
OUT = BASE / "rig" / "out" / "v2_boot"; OUT.mkdir(parents=True, exist_ok=True)
PROBE = r"""cd /home/user/server; echo "== tree"; find . -maxdepth 3 -name '*.py' | grep -v __pycache__ | head -60
echo "== atspi defs"; grep -rn "def _create_atspi_node\|^MAX_DEPTH\|def _get_libreoffice_version\|libreoffice_version_tuple *=" --include=*.py . | head
echo "== import"; python3 -c "import sys; sys.path.insert(0,'/home/user/server'); import main" 2>&1 | tail -8
echo "== python"; python3 --version; head -5 main.py
echo "== service"; systemctl --user list-units 2>/dev/null | grep -i -E "osworld|server" | head; ps -eo pid,cmd | grep -E "server|uvicorn|main.py" | grep -v grep | head -5
"""
env = DesktopEnv(provider_name="modal", path_to_vm="osworld-v2-ubuntu-x86.qcow2", action_space="pyautogui", headless=True,
                 require_a11y_tree=False, os_type="Ubuntu")
res = {}
try:
    url = f"http://{env.vm_ip}:{env.server_port}/screenshot"
    for i in range(4):
        t = time.time()
        try:
            r = requests.get(url, timeout=90); res[f"shot{i}"] = [r.status_code, len(r.content), round(time.time() - t, 1)]
            if r.ok: (OUT / f"screen{i}.png").write_bytes(r.content)
        except Exception as e:
            res[f"shot{i}"] = [repr(e)[:120], round(time.time() - t, 1)]
        print(res[f"shot{i}"], flush=True)
    res["probe"] = vm_out(env, PROBE, timeout=90); print(res["probe"], flush=True)
finally:
    env.close()
    (OUT / "server_probe.json").write_text(json.dumps(res, indent=1))
