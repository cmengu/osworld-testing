"""Low-level VM access shared by the rig: run a shell script inside the VM.

Goes through the server's /execute endpoint, the one every mouse and keyboard action uses.
The newer /run_bash_script endpoint is broken in the current VM image ("name '_append_event'
is not defined"), so nothing here touches it.  Server-side limit is 120 s per call.
"""
import threading

import requests


def _post(url, payload, timeout, box):
    try:
        box["r"] = requests.post(url, json=payload, timeout=timeout)
    except Exception as e:  # network / timeout
        box["e"] = e


def vm_shell(env, script: str, timeout: int = 110) -> dict:
    """requests' timeout bounds each socket read, not the call: rerun2 0231 c10 (19 Oct) spent ~21 min in one
    tree fetch through the Modal tunnel and the SIGALRM watchdog did not cut it.  So the call runs in a daemon
    thread and is abandoned after a hard wall-clock limit."""
    url = env.controller.http_server + "/execute"
    box: dict = {}
    t = threading.Thread(target=_post, args=(url, {"command": script, "shell": True}, timeout + 30, box), daemon=True)
    t.start()
    t.join(timeout + 60)
    if t.is_alive():
        return {"status": "error", "output": "", "error": f"no answer within {timeout + 60}s (abandoned)", "returncode": -1}
    if "e" in box:
        return {"status": "error", "output": "", "error": repr(box["e"])[:300], "returncode": -1}
    r = box["r"]
    if r.status_code == 200:
        return r.json()
    return {"status": "error", "output": "", "error": f"HTTP {r.status_code}: {r.text[:300]}", "returncode": -1}


def vm_out(env, script: str, timeout: int = 110) -> str:
    return (vm_shell(env, script, timeout).get("output") or "").strip()
