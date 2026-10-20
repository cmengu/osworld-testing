"""Low-level VM access shared by the rig: run a shell script inside the VM.

Goes through the server's /execute endpoint, the one every mouse and keyboard action uses.
The newer /run_bash_script endpoint is broken in the current VM image ("name '_append_event'
is not defined"), so nothing here touches it.  Server-side limit is 120 s per call.

Two guards live here because every VM call passes through (20 Oct, probe-0007: the sandbox reached its 3 h
lifetime in the middle of a row, and the row went on for 5.8 h of failing resets, 4.4 USD, before it ended):
  ROW_DEADLINE   a wall-clock time set by the collector for the current row; a call past it raises RowCapped,
                 which the collector turns into "not judged" and the row ends with what it has;
  SandboxLost    raised after LOST_AFTER consecutive failed calls: the VM is not answering any more, so the row
                 is retried from a new sandbox instead of looping on a dead one.
"""
import threading
import time

import requests

ROW_DEADLINE = None       # set by the collector per row (time.time() value); None = no cap
LOST_AFTER = 5            # consecutive failed calls before the sandbox counts as lost
_failures = 0


class RowCapped(BaseException):
    """BaseException like the collector's Watchdog: OSWorld's controller wraps its calls in `except Exception`."""


class SandboxLost(RuntimeError):
    """The VM stopped answering (lifetime over, tunnel gone): the caller restarts the sandbox."""


def _post(url, payload, timeout, box):
    try:
        box["r"] = requests.post(url, json=payload, timeout=timeout)
    except Exception as e:  # network / timeout
        box["e"] = e


def _failed(err: str) -> dict:
    global _failures
    _failures += 1
    if _failures >= LOST_AFTER:
        _failures = 0
        raise SandboxLost(f"{LOST_AFTER} VM calls in a row failed; last: {err}")
    return {"status": "error", "output": "", "error": err, "returncode": -1}


def vm_shell(env, script: str, timeout: int = 110) -> dict:
    """requests' timeout bounds each socket read, not the call: rerun2 0231 c10 (19 Oct) spent ~21 min in one
    tree fetch through the Modal tunnel and the SIGALRM watchdog did not cut it.  So the call runs in a daemon
    thread and is abandoned after a hard wall-clock limit."""
    global _failures
    if ROW_DEADLINE is not None and time.time() > ROW_DEADLINE:
        raise RowCapped(f"row time cap passed by {time.time() - ROW_DEADLINE:.0f}s")
    url = env.controller.http_server + "/execute"
    box: dict = {}
    t = threading.Thread(target=_post, args=(url, {"command": script, "shell": True}, timeout + 30, box), daemon=True)
    t.start()
    t.join(timeout + 60)
    if t.is_alive():
        return _failed(f"no answer within {timeout + 60}s (abandoned)")
    if "e" in box:
        return _failed(repr(box["e"])[:300])
    r = box["r"]
    if r.status_code == 200:
        _failures = 0
        return r.json()
    return _failed(f"HTTP {r.status_code}: {r.text[:300]}")


def vm_out(env, script: str, timeout: int = 110) -> str:
    return (vm_shell(env, script, timeout).get("output") or "").strip()
