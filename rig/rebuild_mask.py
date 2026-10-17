"""Rebuild mask.json from the snapshots already on disk (after a change to mask.py).

Usage: OSWorld/.venv/bin/python -I rig/rebuild_mask.py --run rig/out/mask_run
"""
import argparse
import json
import pathlib
import shutil
import sys

BASE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
from rig.mask import build_mask, describe      # noqa: E402
from rig.snapshot import load_snapshot         # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=str(BASE / "rig" / "out" / "mask_run"))
    args = ap.parse_args()
    run = pathlib.Path(args.run)
    dirs = sorted(run.glob("idle_*")) + sorted(run.glob("noop_*")) + sorted(run.glob("restart_*"))
    snaps = [load_snapshot(d) for d in dirs if (d / "meta.json").exists()]
    def complete(s):
        ti = s.meta.get("tree_info", {})
        return (s.ok and ti.get("source", "fast") == "fast"
                and ti.get("office_frames", 1) >= 1 and ti.get("menus_shallow", 1) >= 1)
    valid = [s for s in snaps if complete(s)]
    print(f"{len(valid)}/{len(snaps)} usable snapshots")
    if len(valid) < 2:
        sys.exit("not enough usable snapshots")
    mask = build_mask([s.canon for s in valid], [s.digest for s in valid],
                      groups=[s.meta.get("kind") for s in valid])
    target = run / "mask.json"
    if target.exists():
        shutil.copy(target, run / "mask.prev.json")
    target.write_text(json.dumps(mask, indent=1))
    report = describe(mask)
    (run / "report.md").write_text(report + "\n")
    print(report)
    print(f"written {target}")


if __name__ == "__main__":
    main()
