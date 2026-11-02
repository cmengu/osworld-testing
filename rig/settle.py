"""Wait for a typed action to finish before its after-state is read (2 November 2026).

On agent steps the state could be read before typing landed: agr-optimize_refactor-05 shows no file change where the
replay shows the file overwritten, and agr-fix_todo_list-12's picture shows one typed character after todo.py had
changed.  A still screen is therefore not enough, because the screen stayed still in both cases.  So this waits for
the VM's CPU to go idle as well, and late_file_changes reads the files once more after the state, to record any change
that arrived after all.

It never fails a row: anything it cannot read is reported in the returned dict.  The thresholds are untested on a real
VM; the first cloud run reports what they cost through the dict's "seconds".
"""
import io
import re
import time

# what can leave work queued in the VM: typed text, Enter, a save.  A plain click or menu key does not wait.
TYPED = re.compile(r"\b(typewrite|write)\(|press\(\s*['\"]enter['\"]|hotkey\(\s*['\"]ctrl['\"]\s*,\s*['\"]s['\"]")
IDLE_PERCENT = 60       # CPU idle at or above this counts as quiet (70 never settled on part A, 2 Nov: 68 to 69 read; 60 is untested)
RESET_CAP = 15          # seconds for an action replayed as a reset, not the row's recorded action
FRAME_CHANGE = 0.005    # share of pixels that may differ between two quiet frames (a blinking cursor)
TOP_BAR = 8             # rows of the 270-row frame holding the clock


def needs_settle(code: str) -> bool:
    return bool(TYPED.search(code or ""))


def _idle(env):
    from rig.vm import vm_shell
    out = (vm_shell(env, "vmstat 1 2 | tail -1 | awk '{print $15}'", timeout=10) or {}).get("output") or ""
    return int(out.strip())


def _frame(env):
    from PIL import Image
    img = Image.open(io.BytesIO(env.controller.get_screenshot())).convert("L").resize((480, 270))
    return img.crop((0, TOP_BAR, 480, 270)).tobytes()


def _changed(a: bytes, b: bytes) -> float:
    return sum(abs(x - y) > 40 for x, y in zip(a, b)) / max(1, len(a))


def wait_settled(env, cap: float = 60, interval: float = 2, need: int = 2, idle_of=_idle, frame_of=_frame,
                 clock=time.time, sleep=time.sleep) -> dict:
    """Wait until CPU idle and an unchanged frame hold for `need` polls in a row, or `cap` seconds pass.  If neither
    signal can be read, return at once with settled None.  If only one can, wait on that one."""
    t0 = clock()
    prev, quiet, polls, idle = None, 0, 0, None
    while True:
        polls += 1
        try:
            idle = idle_of(env)
        except Exception:
            idle = None
        try:
            frame = frame_of(env)
        except Exception:
            frame = None
        if idle is None and frame is None:
            return {"settled": None, "seconds": round(clock() - t0, 1), "polls": polls, "reason": "no signal"}
        ok_idle = idle is None or idle >= IDLE_PERCENT
        ok_frame = frame is None or (prev is not None and _changed(prev, frame) <= FRAME_CHANGE)
        quiet = quiet + 1 if ok_idle and ok_frame else 0
        prev = frame
        if quiet >= need:
            return {"settled": True, "seconds": round(clock() - t0, 1), "polls": polls, "idle": idle}
        if clock() - t0 >= cap:
            return {"settled": False, "seconds": round(clock() - t0, 1), "polls": polls, "idle": idle}
        sleep(interval)


def late_file_changes(env, digest: dict, mask: dict, limit: int = 10) -> list:
    """Files that differ from `digest` when read again now; [] if none or if they cannot be read."""
    from rig.mask import _fsig, apply_file_mask
    from rig.snapshot import _digest
    try:
        now, err = _digest(env)
        if err:
            return []
        a, b = apply_file_mask(digest, mask), apply_file_mask(now, mask)
        return sorted(p for p in set(a) | set(b) if _fsig(p, a.get(p)) != _fsig(p, b.get(p)))[:limit]
    except Exception:
        return []
