"""Fourth V2 boot check (6 Nov 2026): the ported rig/fasttree.py walker on an OSWorld 2.1 VM with Writer open, plus
the rig's sudo helper with the V2 password.  One sandbox, a few minutes."""
import json, os, pathlib, sys, time
HERE = pathlib.Path(__file__).resolve().parent; BASE = HERE.parent; OSWORLD = BASE / "OSWorld"
sys.path.insert(0, str(BASE)); sys.path.insert(0, str(OSWORLD)); os.chdir(OSWORLD)
from desktop_env.desktop_env import DesktopEnv
from rig.snapshot import fetch_tree
from rig.treediff import canonicalize
from rig.vm import vm_out
OUT = BASE / "rig" / "out" / "v2_boot"
env = DesktopEnv(provider_name="modal", path_to_vm="osworld-v2-ubuntu-x86.qcow2", action_space="pyautogui", headless=True,
                 require_a11y_tree=False, os_type="Ubuntu", client_password="osworld-public-evaluation")
res = {}
try:
    vm_out(env, "echo 'hello v2' > ~/Desktop/probe.txt; nohup soffice --writer ~/Desktop/probe.txt >/dev/null 2>&1 &", timeout=20)
    time.sleep(45)
    for i in range(2):
        t = time.time(); xml, info = fetch_tree(env); canon = canonicalize(xml) if xml else {}
        res[f"tree{i}"] = {"seconds": round(time.time() - t, 1), "nodes": len(canon), "source": (info or {}).get("source") if isinstance(info, dict) else str(info)[:200],
                           "writer_frame": any("probe.txt" in p or "probe.txt" in str(a.get("name", "")) for p, a in canon.items()),
                           "hello_text": any("hello v2" in str(a.get("text", "")) for a in canon.values())}
        print(res[f"tree{i}"], flush=True)
    from rig.freshstart import _sudo  # noqa
except ImportError:
    pass
except Exception as e:
    res["error"] = repr(e)[:300]; print(res["error"], flush=True)
finally:
    try:
        res["sudo"] = vm_out(env, "echo osworld-public-evaluation | sudo -S -p '' whoami", timeout=20).strip()
    except Exception as e:
        res["sudo"] = repr(e)[:100]
    env.close()
    (OUT / "tree_check.json").write_text(json.dumps(res, indent=1)); print(res, flush=True)
