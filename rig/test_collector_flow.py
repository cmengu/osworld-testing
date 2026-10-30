"""Offline run of Collector.run_row on recorded snapshots, with the VM faked: catches errors in the row logic (the
undo search, the shorter-undo search, guess B's zero-shot run, labels at every K, the baselines, the forced tier)
before a sandbox is paid for.  The fake VM shows the before-state S after the candidate GOOD and the after-state
S' after anything else.

    OSWorld/.venv/bin/python -I rig/test_collector_flow.py
"""
import argparse
import json
import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import rig.collect_pilot as cp          # noqa: E402  (chdirs into OSWorld)
from rig import teacher, undo as U     # noqa: E402
from rig.snapshot import load_snapshot  # noqa: E402

REC = HERE / "out" / "pilot_run2" / "pilot-0003"   # a type_text row: Ctrl+Z undoes it
S_REC, S1_REC = load_snapshot(REC / "S"), load_snapshot(REC / "S1")


class Fake(cp.Collector):
    good = None          # the candidate whose code brings S back

    def ensure_task(self, task_id):
        return "fake"

    def reset_to_before(self, row, fresh=False):
        self.state = S_REC
        return {"fresh_start": "fake"}

    def act(self, row):
        self.state = S_REC if row.get("code") == "noop" else S1_REC

    def reset_to_after(self, row, expect_windows="", expect_digest=None, independent=False):
        self.state = S1_REC
        return {"fresh_start": "fake"}

    def step(self, code, pause=1.0):
        if code == U.candidate_code(self.good, {"doc_path": "/home/user/x.xlsx", "office_running": True, "reopen_cmd": None}):
            self.state = S_REC

    def snapshot(self, path, meta, expect_kind="calc", office_expected=True):
        import shutil
        shutil.copytree(self.state.path, path, dirs_exist_ok=True)
        snap = cp.load_snapshot(path)
        snap.meta["ok"] = True
        return snap

    def quick_state(self):
        return self.state.windows, self.state.digest, ""


def run(good, guess_steps, forced=None, budget=55):
    teacher.guess_a = lambda *a, **k: {"reversible": True, "model": "fake"}
    teacher.guess_b = lambda *a, **k: {"reversible": True, "shortest_undo": guess_steps, "model": "fake"}
    out = tempfile.mkdtemp()
    args = argparse.Namespace(out=out, mask=str(HERE / "out" / "mask_run" / "mask.json"), spots=str(HERE / "clickspots_pilot.json"),
                              mnemonics="", rows="", spots_filter="", limit=0, budget=budget, blind=4, row_minutes=60,
                              no_teacher=False, no_proposer=True, no_replay=True, no_zero_shot=False, shorter_tries=8, no_confirm_matches=False)
    c = Fake(args)
    Fake.good = good
    row = dict(next(r for r in c.rows_all if r["row_id"] == "pilot-0003"), open_path="/home/user/x.xlsx")
    if forced:
        row["forced_candidates"] = forced
    return c.run_row(row)


# Ctrl+Z works: first candidate, K=1 everywhere, both baselines known
r = run(["key:ctrl+z"], ["key:ctrl+z"])
assert r["executed_label"] == "REVERSIBLE" and r["shortest_undo"] == ["key:ctrl+z"] and r["undo_actions"] == 1
assert r["labels_by_k"] == {str(k): "REVERSIBLE" for k in range(1, 6)}
assert r["baseline"] == {"ctrl+z": True, "escape": None}
assert r["guess_b_zero_shot"]["source"] == "search" and r["guess_b_zero_shot"]["matched"] is True
assert r["undo_search"][0]["confirm"] == "confirmed"

# Only a 2-action undo works: found in tier 1, the shorter search finds nothing shorter, labels split at K=2
r = run(["key:ctrl+z", "key:ctrl+home"], ["key:escape"])
assert r["shortest_undo"] == ["key:ctrl+z", "key:ctrl+home"] and r["undo_actions"] == 2
assert r["labels_by_k"]["1"] == "NO-UNDO-FOUND" and r["labels_by_k"]["2"] == "REVERSIBLE"
assert r["shorter_search"]["tries"] >= 1 and r["baseline"]["ctrl+z"] is False
assert r["guess_b_zero_shot"]["matched"] is False

# Nothing in the fixed tiers works, but guess B's own undo does and the search never tried it (it was out of budget):
# the separate zero-shot run executes it and the label turns round
odd = ["key:ctrl+z", "key:ctrl+z", "key:ctrl+home", "key:ctrl+home"]
r = run(odd, odd, budget=3)
assert r["guess_b_zero_shot"]["source"] == "separate" and r["found_tier"] == "B0", (r["guess_b_zero_shot"], r["found_tier"])
assert r["executed_label"] == "REVERSIBLE" and r["shortest_undo"] == odd and r["undo_actions"] == 4
assert r["labels_by_k"]["3"] == "NO-UNDO-FOUND" and r["labels_by_k"]["4"] == "REVERSIBLE"

# A forced candidate (tier F) runs first
r = run(["key:ctrl+z", "key:ctrl+home", "key:ctrl+home"], [], forced=[["key:ctrl+z", "key:ctrl+home", "key:ctrl+home"]])
assert r["found_tier"] == "F" and r["undo_search"][0]["tier"] == "F"

# An action that changes nothing (probe no-op rows): REVERSIBLE with an empty undo, no search, K labels all reversible
teacher.guess_b = lambda *a, **k: {"reversible": True, "shortest_undo": [], "model": "fake"}
args = argparse.Namespace(out=tempfile.mkdtemp(), mask=str(HERE / "out" / "mask_run" / "mask.json"), spots=str(HERE / "clickspots_probe.json"),
                          mnemonics="", rows="", spots_filter="", limit=0, budget=12, blind=0, row_minutes=20,
                          no_teacher=False, no_proposer=True, no_replay=True, no_zero_shot=False, shorter_tries=8, no_confirm_matches=False)
c = Fake(args)
r = c.run_row(dict(next(x for x in c.rows_all if x["spot_id"] == "noop"), code="noop"))
assert r["executed_label"] == "REVERSIBLE" and r["undo_actions"] == 0 and not r.get("broken_action") and r["budget_used"] == 0
assert r["labels_by_k"]["1"] == "REVERSIBLE" and r["guess_b_zero_shot"]["source"] == "no change"

# probe-0007's failure: resets whose action silently failed leave S on screen, so every candidate "matches".
# Confirmation re-reads the full state after the reset; it is never S', so no match survives and the label is no-undo.
class Broken(Fake):
    def reset_to_after(self, row, expect_windows="", expect_digest=None, independent=False):
        self.state = S_REC
        return {"fresh_start": "fake"}


Broken.good = ["key:ctrl+z"]
teacher.guess_b = lambda *a, **k: {"reversible": False, "shortest_undo": [], "model": "fake"}
b = Broken(argparse.Namespace(**{**vars(args), "out": tempfile.mkdtemp(), "spots": str(HERE / "clickspots_pilot.json"), "budget": 3}))
r = b.run_row(dict(next(x for x in b.rows_all if x["row_id"] == "pilot-0003"), open_path="/home/user/x.xlsx"))
assert r["executed_label"] == "UNCONFIRMED", r["executed_label"]       # matched once, never confirmed (23 Oct label)
assert r["unconfirmed_match"]["seq"] == ["key:ctrl+z"] and r["labels_by_k"]["1"] == "UNCONFIRMED", r["unconfirmed_match"]
assert all(x.get("result", "").startswith("match not confirmed") for x in r["undo_search"] if x.get("tier") != "-")

# The window tier: more windows after the action than before puts Escape, Ctrl+W, Alt+F4 first; a changed title alone does not
w0 = "0x1 0 host Desktop\n0x2 0 host a.xlsx - LibreOffice Calc\n"
assert cp.window_tier(w0, w0 + "0x3 0 host Format Cells\n") == [list(c) for c in cp.WINDOW_CLOSERS]
assert cp.window_tier(w0, "0x1 0 host Desktop\n0x2 0 host b.xlsx - LibreOffice Calc\n") == []

# The real reset_to_after: a reset whose action left the files as in S (the Delete did not happen) is redone, and three
# such resets make the candidate "not judged" instead of judged against the wrong state (probe-0007, 20 Oct)
import rig.snapshot as _snap, rig.vm as _vm
digests = []
_snap._digest = lambda env: (digests.pop(0), "")
_real_vm_shell = _vm.vm_shell
_vm.vm_shell = lambda env, script, timeout=110: {"output": S1_REC.windows}


class Real(Fake):
    reset_to_after = cp.Collector.reset_to_after
    env = type("E", (), {"controller": type("C", (), {"get_screenshot": staticmethod(lambda: None)})()})()


c = Real(args)
row = c.rows_all[0]
wrong = {k: dict(v) for k, v in S1_REC.digest.items()}
victim = next(p for p in wrong if p.endswith(".xlsx") and "/.~lock" not in p)
wrong[victim]["k"] = "not-the-after-state"                  # a reset whose action did not take effect on disk
digests[:] = [wrong, S1_REC.digest]
info = c.reset_to_after(row, expect_windows=S1_REC.windows, expect_digest=S1_REC.digest)
assert info["reset_attempts"] == 2 and info["reset_checked"] == "windows+files", info
if True:
    digests[:] = [wrong] * 3
    try:
        c.reset_to_after(row, expect_windows=S1_REC.windows, expect_digest=S1_REC.digest)
        raise AssertionError("a reset that never reproduces S' must not be judged")
    except cp.ResetFailed:
        pass

# An action that must change the files and changes nothing (probe-0007, 20 Oct: Delete reached nothing) is retried
# on a fresh instance twice and the row is broken, not searched; an action that changes the named thing proceeds
class Misfire(Fake):
    acted = 0

    def act(self, row):
        Misfire.acted += 1
        self.state = S_REC


teacher.guess_b = lambda *a, **k: {"reversible": True, "shortest_undo": ["key:ctrl+z"], "model": "fake"}
m = Misfire(argparse.Namespace(**{**vars(args), "out": tempfile.mkdtemp(), "spots": str(HERE / "clickspots_pilot.json"), "budget": 3}))
row = dict(next(x for x in m.rows_all if x["row_id"] == "pilot-0003"), open_path="/home/user/x.xlsx", expect_change=["files"])
r = m.run_row(row)
assert Misfire.acted == 3 and r["status"] == "broken_action" and r["executed_label"] is None and r["labels_by_k"] is None, (Misfire.acted, r["status"])
assert len(r["action_misfires"]) == 3 and r["undo_search"] == [] and r["guess_b_zero_shot"]["executed"] is False
assert (m.out / "pilot-0003" / "S1_misfire_1").exists()
Fake.good = ["key:ctrl+z"]
m2 = Fake(argparse.Namespace(**{**vars(args), "out": tempfile.mkdtemp(), "spots": str(HERE / "clickspots_pilot.json"), "budget": 3}))
r = m2.run_row(dict(next(x for x in m2.rows_all if x["row_id"] == "pilot-0003"), open_path="/home/user/x.xlsx", expect_change=["tree"]))
assert r["status"] == "ok" and r["action_misfires"] == [] and r["executed_label"] == "REVERSIBLE", r["status"]

# The VM guards (rig.vm, 20 Oct): a call past the row deadline raises RowCapped; five failed calls raise SandboxLost
import time
from rig import vm as VM
VM.vm_shell = _real_vm_shell
VM.ROW_DEADLINE = time.time() - 1
try:
    VM.vm_shell(None, "true")
    raise AssertionError("a call past the row deadline must raise")
except VM.RowCapped:
    pass
VM.ROW_DEADLINE = None
dead = type("E", (), {"controller": type("C", (), {"http_server": "http://127.0.0.1:9"})()})()
n = 0
try:
    for _ in range(6):
        VM.vm_shell(dead, "true", timeout=1)
        n += 1
    raise AssertionError("a dead VM must raise after five failed calls")
except VM.SandboxLost:
    assert n == 4, n
assert cp.rotate_seconds(40) == 10800 - 40 * 60 - 10 * 60 - 5 * 60

# The click: step (22 Oct): parses with its name kept, counts as one action, compiles to an accessibility press
assert U.parse_steps(["click:Undo Trash", "key:ctrl+a", "click: Restore "]) == ["click:Undo Trash", "key:ctrl+a", "click:Restore"]
assert U.parse_step("click:") is None and U.action_count(["click:Trash", "wait:2", "click:Restore"]) == 2
code = U.candidate_code(["click:Undo Trash"], {"proc": "nautilus"})
compile(code, "<click>", "exec")
assert "'Undo Trash'" in code and "'nautilus'" in code and "doAction" in code

# VS Code (30 Oct): an action that moved the pointer gets VS Code's own routes (tier V) and then the same with the
# pointer moved back where S had it (tier P); the agent step 02 of the snapshot trial, recorded states, pointer faked
VS = HERE / "out" / "agent_snap_label" / "ags-change_permissions-02"
if (VS / "S" / "tree.xml").exists() and (VS / "S1" / "tree.xml").exists():
    class FakeVS(Fake):
        def reset_to_before(self, row, fresh=False):
            self.state = VS_S
            return {"fresh_start": "fake"}

        def act(self, row):
            self.state = VS_S1

        def reset_to_after(self, row, expect_windows="", expect_digest=None, independent=False):
            self.state = VS_S1
            return {"fresh_start": "fake"}

        def step(self, code, pause=1.0):
            if code == U.candidate_code(self.good, {"pointer": [10, 20], "proc": "code"}):
                self.state = VS_S

        def snapshot(self, path, meta, expect_kind="calc", office_expected=True):
            snap = Fake.snapshot(self, path, meta, expect_kind, office_expected)
            snap.meta["pointer"] = [10, 20] if self.state is VS_S else [1100, 700]
            return snap

    VS_S, VS_S1 = load_snapshot(VS / "S"), load_snapshot(VS / "S1")
    vs_args = argparse.Namespace(**{**vars(args), "out": tempfile.mkdtemp(), "spots": str(HERE / "clickspots_agent_snap.json"),
                                    "no_zero_shot": True})
    teacher.guess_b = lambda *a, **k: {"reversible": True, "shortest_undo": [], "model": "fake"}
    v = FakeVS(vs_args)
    FakeVS.good = ["key:ctrl+`", "pointer:back"]
    vrow = dict(next(x for x in v.rows_all if x["row_id"] == "ags-change_permissions-02"), band="test", recorded_before=None)
    r = v.run_row(vrow)
    tiers = [x.get("tier") for x in r["undo_search"]]
    assert r["executed_label"] == "REVERSIBLE" and r["found_tier"] == "P" and r["shortest_undo"] == ["key:ctrl+`", "pointer:back"], (r["executed_label"], r["found_tier"], tiers)
    assert tiers[:len(U.VSCODE_FIRST)] == ["V"] * len(U.VSCODE_FIRST), tiers
    code = U.candidate_code(["pointer:back"], {"pointer": [3, 4]})
    compile(code, "<pointer>", "exec")
    assert "moveTo(3, 4" in code and "moveTo" not in U.candidate_code(["pointer:back"], {})

print("COLLECTOR FLOW CHECKS PASSED")
