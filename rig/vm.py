"""Low-level VM access shared by the rig: run a shell script inside the VM.

Goes through the server's /execute endpoint, the one every mouse and keyboard action uses.
The newer /run_bash_script endpoint is broken in the current VM image ("name '_append_event'
is not defined"), so nothing here touches it.  Server-side limit is 120 s per call.
"""
import requests


def vm_shell(env, script: str, timeout: int = 110) -> dict:
    url = env.controller.http_server + "/execute"
    try:
        r = requests.post(url, json={"command": script, "shell": True}, timeout=timeout + 30)
        if r.status_code == 200:
            return r.json()
        return {"status": "error", "output": "", "error": f"HTTP {r.status_code}: {r.text[:300]}", "returncode": -1}
    except Exception as e:  # network / timeout
        return {"status": "error", "output": "", "error": repr(e)[:300], "returncode": -1}


def vm_out(env, script: str, timeout: int = 110) -> str:
    return (vm_shell(env, script, timeout).get("output") or "").strip()
