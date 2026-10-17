"""Build the noise mask from one unchanged state: idle snapshots, no-op inputs, and fresh
restarts of the application with no action in between.

Usage (from ~/ai-research/osworld-testing, inside tmux):
    OSWorld/.venv/bin/python -I rig/collect_mask.py --idle 10 --noop 10 --restarts 5
Writes rig/out/mask_run/{idle_XX,noop_XX,restart_XX}/..., mask.json and report.md, and
closes the sandbox.  The restart phase is what teaches the mask the files and flags that
change every time LibreOffice is relaunched (its lock file, dconf, ibus sockets, ...).
"""
import argparse
import json
import os
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
BASE = HERE.parent                      # ~/ai-research/osworld-testing
OSWORLD = BASE / "OSWorld"
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(OSWORLD))
os.chdir(OSWORLD)                       # DesktopEnv resolves task paths from the repo root

from desktop_env.desktop_env import DesktopEnv      # noqa: E402
from rig.freshstart import fresh_start, prime_cache  # noqa: E402
from rig.mask import build_mask, describe            # noqa: E402
from rig.snapshot import take_snapshot               # noqa: E402
from rig.vmprep import prepare_vm                    # noqa: E402

# Inputs that must not change the document: a bare modifier press, a one-pixel mouse wobble.
NOOPS = [
    "pyautogui.press('shift')",
    "pyautogui.moveRel(1, 0); time.sleep(0.2); pyautogui.moveRel(-1, 0)",
    "pyautogui.keyDown('shift'); time.sleep(0.1); pyautogui.keyUp('shift')",
]
DEFAULT_TASK = "evaluation_examples/examples/libreoffice_calc/357ef137-7eeb-4c80-a3bb-0951f26a8aff.json"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default=DEFAULT_TASK)
    ap.add_argument("--idle", type=int, default=10)
    ap.add_argument("--noop", type=int, default=10)
    ap.add_argument("--restarts", type=int, default=5)
    ap.add_argument("--interval", type=float, default=8.0, help="seconds between idle snapshots")
    ap.add_argument("--out", default=str(BASE / "rig" / "out" / "mask_run"))
    ap.add_argument("--provider", default="modal")
    args = ap.parse_args()

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    task = json.load(open(args.task))
    t0 = time.time()
    elapsed = lambda: f"{time.time() - t0:.0f}s"  # noqa: E731

    env = DesktopEnv(provider_name=args.provider, action_space="pyautogui", headless=True,
                     require_a11y_tree=False, os_type="Ubuntu")
    snaps = []

    def shoot(name, meta):
        s = take_snapshot(env, out / name, meta)
        info = s.meta.get("tree_info", {})
        flag = "" if s.ok else f"  SKIPPED ({s.meta.get('tree_error') or s.meta.get('digest_error')})"
        print(f"{name}: nodes={s.meta['nodes']} files={s.meta['files']} tree={s.meta['tree_seconds']}s "
              f"({info.get('source')}) digest={s.meta['digest_seconds']}s at {elapsed()}{flag}", flush=True)
        snaps.append(s)

    try:
        env.reset(task_config=task)
        print(f"task ready at {elapsed()}; vm prep: {prepare_vm(env)}; cache: {prime_cache(env, task)}", flush=True)
        how = fresh_start(env, task)        # same regime as every later replay
        print(f"initial fresh start: {how} at {elapsed()}", flush=True)
        for i in range(args.idle):
            shoot(f"idle_{i:02d}", {"kind": "idle", "i": i})
            time.sleep(args.interval)
        for i in range(args.noop):
            code = NOOPS[i % len(NOOPS)]
            env.step(code, pause=1)
            shoot(f"noop_{i:02d}", {"kind": "noop", "i": i, "code": code})
        for i in range(args.restarts):
            t = time.time()
            how = fresh_start(env, task)
            print(f"restart {i + 1}/{args.restarts}: {how} in {time.time() - t:.0f}s", flush=True)
            shoot(f"restart_{i:02d}", {"kind": "restart", "i": i, "how": how})

        valid = [s for s in snaps if s.ok]
        print(f"{len(valid)}/{len(snaps)} snapshots usable", flush=True)
        if len(valid) < 2:
            print("not enough usable snapshots to build a mask", flush=True)
            return
        mask = build_mask([s.canon for s in valid], [s.digest for s in valid],
                          groups=[s.meta.get("kind") for s in valid])
        (out / "mask.json").write_text(json.dumps(mask, indent=1))
        report = describe(mask)
        (out / "report.md").write_text(report + "\n")
        print(report, flush=True)
        print(f"mask written to {out / 'mask.json'} at {elapsed()}", flush=True)
    finally:
        try:
            env.close()
            print("env closed", flush=True)
        except Exception as e:  # pragma: no cover
            print("close error:", repr(e)[:200], flush=True)


if __name__ == "__main__":
    main()
