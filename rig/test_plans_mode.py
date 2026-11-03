"""Offline checks of the H3 plans mode and the focus:doc step (3 November 2026), with the VM faked as in
rig/test_collector_flow.py: the fake VM shows S after the candidate GOOD and S' after anything else.

    OSWorld/.venv/bin/python -I rig/test_plans_mode.py
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

REC = HERE / "out" / "pilot_run2" / "pilot-0003"
S_REC, S1_REC = load_snapshot(REC / "S"), load_snapshot(REC / "S1")


class Fake(cp.Collector):
    good = None
    ran = []

    def ensure_task(self, task_id):
        return "fake"

    def reset_to_before(self, row, fresh=False):
        self.state = S_REC
        return {"fresh_start": "fake"}

    def act(self, row, full_settle=False):
        self.state = S1_REC

    def reset_to_after(self, row, expect_windows="", expect_digest=None, independent=False):
        self.state = S1_REC
        return {"fresh_start": "fake"}

    def step(self, code, pause=1.0):
        Fake.ran.append(code)
        if code == U.candidate_code(self.good, {}):
            self.state = S_REC

    def snapshot(self, path, meta, expect_kind="calc", office_expected=True):
        import shutil
        shutil.copytree(self.state.path, path, dirs_exist_ok=True)
        snap = cp.load_snapshot(path)
        snap.meta["ok"] = True
        return snap

    def quick_state(self):
        return self.state.windows, self.state.digest, ""


def run(good, plans, plans_only=True):
    teacher.guess_a = lambda *a, **k: (_ for _ in ()).throw(AssertionError("no teacher call in plans mode"))
    teacher.guess_b = teacher.guess_a
    pf = pathlib.Path(tempfile.mkdtemp()) / "plans.json"
    pf.write_text(json.dumps({"pilot-0003": plans}))
    args = argparse.Namespace(out=tempfile.mkdtemp(), mask=str(HERE / "out" / "mask_run" / "mask.json"), spots=str(HERE / "clickspots_pilot.json"),
                              mnemonics="", rows="", spots_filter="", limit=0, budget=55, blind=4, row_minutes=60,
                              no_teacher=True, no_proposer=True, no_replay=True, no_zero_shot=True, shorter_tries=8,
                              no_confirm_matches=False, plans=str(pf), plans_only=plans_only)
    c = Fake(args)
    Fake.good, Fake.ran = good, []
    row = dict(next(r for r in c.rows_all if r["row_id"] == "pilot-0003"), open_path="/home/user/x.xlsx")
    return c.run_row(row)


# three sources; Claude's and Ctrl+Z are the same plan and run once; only the plans run, every one of them
r = run(["key:ctrl+z"], [{"source": "model", "steps": ["key:ctrl+home"]}, {"source": "claude", "steps": ["key:ctrl+z"]},
                         {"source": "ctrlz", "steps": ["key:ctrl+z"]}])
by = {p["source"]: p for p in r["plans"]}
assert by["model"]["executed"] and not by["model"]["match"], by["model"]
assert by["claude"]["match"] and by["ctrlz"]["match"], by
assert {x["tier"] for x in r["undo_search"]} == {"PL"} and len(r["undo_search"]) == 2, [x["tier"] for x in r["undo_search"]]
assert r["mode"].startswith("plans-only")

# a one-action match does not stop the others (the normal search stops there)
r = run(["key:ctrl+z"], [{"source": "ctrlz", "steps": ["key:ctrl+z"]}, {"source": "model", "steps": ["key:ctrl+z", "key:ctrl+home"]}])
by = {p["source"]: p for p in r["plans"]}
assert by["ctrlz"]["match"] and by["model"]["executed"] and not by["model"]["match"], by

# a plan outside the step language is recorded and never run
r = run(["key:ctrl+z"], [{"source": "claude", "steps": ["press undo twice"]}, {"source": "ctrlz", "steps": ["key:ctrl+z"]}])
by = {p["source"]: p for p in r["plans"]}
assert by["claude"]["result"] == "does not parse" and not by["claude"]["executed"], by["claude"]
assert by["ctrlz"]["match"]

# without --plans-only the plans run after the forced tier and ahead of the usual tiers, and the search goes on as before
r = run(["key:ctrl+home", "key:ctrl+home"], [{"source": "relabel", "steps": ["key:ctrl+home", "key:ctrl+home"]}], plans_only=False)
assert r["undo_search"][0]["tier"] == "PL" and r["found_tier"] == "PL" and r["executed_label"] == "REVERSIBLE", (r["undo_search"][0], r["found_tier"])
assert "mode" not in r

# focus:doc parses, and its code looks for the document's own window by name
assert U.parse_steps(["focus:doc", "key:ctrl+s"]) == ["focus:doc", "key:ctrl+s"]
code = U.step_code("focus:doc", {"doc_name": "Novels_Intro_Packet.docx"})
assert "Novels_Intro_Packet.docx" in code and "grep -F" in code
assert "tail -1" in U.step_code("focus:newest", {})
assert U.parse_step("focus:other") is None
print("PLANS MODE CHECKS PASSED")
