"""Offline test of the guard hook in OSWorld/lib_run_single.py (7 Nov 2026): stub env, stub agent, stub guard.
A blocked action must not reach env.step, the agent's next turn must carry the note, other actions must run.

    OSWorld/.venv/bin/python -I rig/test_guard_loop.py
"""
import os
import pathlib
import sys
import tempfile
import types

BASE = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(BASE / "OSWorld"), str(BASE)]
os.environ["RIG_GUARD"] = "ours"
import lib_run_single as L  # noqa: E402
import rig.guard_live as G  # noqa: E402

L.time.sleep = lambda s: None
L.log_task_completion = lambda *a, **k: None
L.RIG_RECORD = False


class Env:
    def __init__(self):
        self.ran, self.vm_ip = [], "x"
        self.controller = types.SimpleNamespace(start_recording=lambda: None, end_recording=lambda p: None)
    def reset(self, task_config): pass
    def _get_obs(self): return {"screenshot": b""}
    def step(self, a, s):
        self.ran.append(a)
        return {"screenshot": b""}, 0, a == "DONE", {}
    def evaluate(self): return 1.0


class Agent:
    def __init__(self): self.seen = []
    def reset(self, *a, **k): pass
    def predict(self, instr, obs):
        self.seen.append(instr)
        return "", [["pyautogui.click(1, 1)", "rm -rf ~/Documents", "pyautogui.click(2, 2)"], ["pyautogui.click(3, 3)"], ["DONE"]][len(self.seen) - 1]


class FakeGuard:
    def __init__(self): self.calls = []
    def check(self, instruction, state_dir, step, action):
        self.calls.append((step, action, os.path.basename(state_dir)))
        return G.BLOCKED.format(keys=action) if "rm -rf" in action else None


fg = FakeGuard()
G.from_env = lambda d, e: fg
env, agent = Env(), Agent()
with tempfile.TemporaryDirectory() as d:
    L.run_single_example(agent, env, {"id": "t"}, 5, "fix the bugs", types.SimpleNamespace(sleep_after_execution=0), d, [])
assert env.ran == ["pyautogui.click(1, 1)", "pyautogui.click(3, 3)", "DONE"], env.ran
assert "safety check blocked" in agent.seen[1] and agent.seen[2] == "fix the bugs", agent.seen
assert [c[1] for c in fg.calls] == ["pyautogui.click(1, 1)", "rm -rf ~/Documents", "pyautogui.click(3, 3)", "DONE"], fg.calls
print("ok: blocked action skipped, the rest of that turn dropped, note given once, other actions ran")
