"""Write the e2e pilot tasks as OSWorld task files (rig/agentrun/tasks/examples/e2e/<id>.json) and batch files.
The task's own setup and checker run from rig/e2e/runner.py (RIG_E2E=1); the OSWorld config only opens a terminal.

    python3 rig/e2e/make_tasks.py                       # all task files
    python3 rig/e2e/make_tasks.py --batches 3 ID1,ID2   # + batch_e2e{1..3}.json over the given ids
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
from rig.e2e.tasks import TASKS  # noqa: E402

TDIR = HERE.parent / "agentrun" / "tasks"


def main():
    d = TDIR / "examples" / "e2e"
    d.mkdir(parents=True, exist_ok=True)
    for t in TASKS:
        (d / f"{t['id']}.json").write_text(json.dumps({
            "id": t["id"], "snapshot": "os", "instruction": t["instruction"],
            "source": "rig/e2e/tasks.py (10 Nov 2026, TEST ONLY)",
            "config": [{"type": "launch", "parameters": {"command": ["gnome-terminal", "--maximize", "--working-directory=/home/user"]}},
                       {"type": "sleep", "parameters": {"seconds": 3}}],
            "related_apps": ["os", "terminal"], "evaluator": {"func": "infeasible"}}, indent=1) + "\n")
    print(f"{len(TASKS)} task files in {d}")
    if "--batches" in sys.argv:
        n = int(sys.argv[sys.argv.index("--batches") + 1])
        ids = sys.argv[sys.argv.index("--batches") + 2].split(",")
        for i in range(n):
            part = ids[i::n]
            (TDIR / f"batch_e2e{i + 1}.json").write_text(json.dumps({"e2e": part}, indent=1) + "\n")
            print(f"batch_e2e{i + 1}: {part}")


if __name__ == "__main__":
    main()
