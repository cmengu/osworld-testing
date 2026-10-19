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

    def reset_to_before(self, row):
        self.state = S_REC
        return {"fresh_start": "fake"}

    def act(self, row):
        self.state = S1_REC

    def reset_to_after(self, row, expect_windows=""):
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
                              no_teacher=False, no_proposer=True, no_replay=True, no_zero_shot=False, shorter_tries=8)
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
r = run(["type:pilot", "key:enter"], [], forced=[["type:pilot", "key:enter"]])
assert r["found_tier"] == "F" and r["undo_search"][0]["tier"] == "F"

print("COLLECTOR FLOW CHECKS PASSED")
