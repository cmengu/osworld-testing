"""Developer probe on a spare sandbox: time the server's tree walk against the fast walk,
check the LibreOffice subtree matches, exercise the fast fresh start and the digest.

Usage: OSWorld/.venv/bin/python -I rig/dev_probe.py
"""
import json
import os
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
BASE = HERE.parent
OSWORLD = BASE / "OSWorld"
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(OSWORLD))
os.chdir(OSWORLD)

from desktop_env.desktop_env import DesktopEnv       # noqa: E402
from rig.fasttree import fast_tree                   # noqa: E402
from rig.freshstart import fresh_start, prime_cache  # noqa: E402
from rig.snapshot import take_snapshot               # noqa: E402
from rig.treediff import canonicalize, diff          # noqa: E402
from rig.vmprep import prepare_vm                    # noqa: E402

TASK = "evaluation_examples/examples/libreoffice_calc/357ef137-7eeb-4c80-a3bb-0951f26a8aff.json"
OUT = BASE / "rig" / "out" / "dev_probe"
SOFFICE = "/desktop-frame/application[soffice]"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    task = json.load(open(TASK))
    t0 = time.time()
    env = DesktopEnv(provider_name="modal", action_space="pyautogui", headless=True,
                     require_a11y_tree=False, os_type="Ubuntu")
    try:
        env.reset(task_config=task)
        print(f"task ready at {time.time() - t0:.0f}s; prep: {prepare_vm(env)}; cache: {prime_cache(env, task)}", flush=True)
        time.sleep(5)

        t = time.time()
        slow = env.controller.get_accessibility_tree() or ""
        print(f"server walk: {time.time() - t:.1f}s, {len(slow)} chars", flush=True)
        t = time.time()
        fast, info = fast_tree(env)
        print(f"fast walk:   {time.time() - t:.1f}s, {len(fast)} chars; {info}", flush=True)
        (OUT / "slow.xml").write_text(slow)
        (OUT / "fast.xml").write_text(fast)
        if slow and fast:
            a = {p: v for p, v in canonicalize(slow).items() if p.startswith(SOFFICE)}
            b = {p: v for p, v in canonicalize(fast).items() if p.startswith(SOFFICE)}
            d = diff(a, b)
            print(f"LibreOffice subtree: server={len(a)} fast={len(b)} differences={len(d)}", flush=True)
            for x in d[:8]:
                print("   ", x["path"][-90:], x["attr"], repr(x["old"])[:30], "->", repr(x["new"])[:30], flush=True)

        t = time.time()
        fast2, _ = fast_tree(env)
        print(f"fast walk again: {time.time() - t:.1f}s; identical: {fast2 == fast}", flush=True)

        t = time.time()
        how = fresh_start(env, task)
        print(f"fresh start: {how} in {time.time() - t:.0f}s", flush=True)
        snap = take_snapshot(env, OUT / "after_restart", {"kind": "dev"})
        office = [p for p, v in snap.digest.items() if "c" in v]
        print(f"snapshot ok={snap.ok} nodes={snap.meta['nodes']} files={snap.meta['files']} "
              f"tree {snap.meta['tree_seconds']}s ({snap.meta['tree_info'].get('source')}) digest {snap.meta['digest_seconds']}s; "
              f"office files hashed: {len(office)} {office[:3]}", flush=True)
        if fast:
            b2 = {p: v for p, v in snap.canon.items() if p.startswith(SOFFICE)}
            b1 = {p: v for p, v in canonicalize(fast).items() if p.startswith(SOFFICE)}
            d = diff(b1, b2)
            print(f"LibreOffice subtree before vs after fresh start: {len(d)} differences", flush=True)
            for x in d[:8]:
                print("   ", x["path"][-90:], x["attr"], repr(x["old"])[:30], "->", repr(x["new"])[:30], flush=True)
    finally:
        try:
            env.close()
            print("env closed", flush=True)
        except Exception as e:  # pragma: no cover
            print("close error:", repr(e)[:200], flush=True)


if __name__ == "__main__":
    main()
