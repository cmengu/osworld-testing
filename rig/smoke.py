"""Smoke test: the same action from a fresh start, replayed, must give the same masked state.

Usage (from ~/ai-research/osworld-testing, inside tmux):
    OSWorld/.venv/bin/python -I rig/smoke.py --mask rig/out/mask_run/mask.json --replays 3
Resumable: finished (spot, replay) pairs are read back from rig/out/smoke_run/results.jsonl.
Pass rule: masked states agree across all replays for at least 90% of click-spots.
"""
import argparse
import itertools
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

from desktop_env.desktop_env import DesktopEnv                 # noqa: E402
from rig.freshstart import fresh_start, prime_cache            # noqa: E402
from rig.mask import states_equal                              # noqa: E402
from rig.snapshot import load_snapshot, take_snapshot          # noqa: E402
from rig.treediff import summarize                             # noqa: E402
from rig.vmprep import prepare_vm                              # noqa: E402

DEFAULT_TASK = "evaluation_examples/examples/libreoffice_calc/357ef137-7eeb-4c80-a3bb-0951f26a8aff.json"


def complete(s) -> bool:
    """Same completeness rule as rebuild_mask.py: capture ok, scoped walker, a LibreOffice frame found,
    menus recorded one level deep.  Anything else is retaken once and never judged."""
    ti = s.meta.get("tree_info", {})
    return bool(s.ok and ti.get("source", "fast") == "fast"
                and ti.get("office_frames", 1) >= 1 and ti.get("menus_shallow", 1) >= 1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default=DEFAULT_TASK)
    ap.add_argument("--spots", default=str(HERE / "clickspots_calc.json"))
    ap.add_argument("--mask", default=str(BASE / "rig" / "out" / "mask_run" / "mask.json"))
    ap.add_argument("--replays", type=int, default=3)
    ap.add_argument("--limit", type=int, default=0, help="only the first N click-spots (0 = all)")
    ap.add_argument("--out", default=str(BASE / "rig" / "out" / "smoke_run"))
    ap.add_argument("--provider", default="modal")
    ap.add_argument("--compare-only", action="store_true", help="skip the VM; just compare what is on disk")
    args = ap.parse_args()

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    spots = json.load(open(args.spots))
    if args.limit:
        spots = spots[: args.limit]
    mask = json.load(open(args.mask))
    results_path = out / "results.jsonl"
    done = set()
    if results_path.exists():
        for line in results_path.read_text().splitlines():
            row = json.loads(line)
            if row.get("ok", True) and row.get("complete", True):
                done.add((row["spot"], row["replay"]))

    if not args.compare_only:
        task = json.load(open(args.task))
        t0 = time.time()
        env = DesktopEnv(provider_name=args.provider, action_space="pyautogui", headless=True,
                         require_a11y_tree=False, os_type="Ubuntu")
        try:
            env.reset(task_config=task)
            print(f"task ready at {time.time() - t0:.0f}s; vm prep: {prepare_vm(env)}; cache: {prime_cache(env, task)}", flush=True)
            for spot in spots:
                for r in range(args.replays):
                    if (spot["id"], r) in done:
                        continue
                    t = time.time()
                    how = fresh_start(env, task)        # every replay starts the same way
                    t_fs = time.time() - t
                    env.step(spot["code"], pause=spot.get("pause", 2))
                    meta = {"spot": spot["id"], "replay": r, "code": spot["code"], "fresh_start": how}
                    snap = take_snapshot(env, out / spot["id"] / f"r{r}", meta)
                    if not complete(snap):  # one retake (tunnel reset, fallback walker, expanded menus) before giving up
                        time.sleep(3)
                        snap = take_snapshot(env, out / spot["id"] / f"r{r}", meta)
                    with results_path.open("a") as fh:
                        fh.write(json.dumps({"spot": spot["id"], "replay": r, "dir": str(snap.path), "ok": snap.ok, "complete": complete(snap),
                                             "nodes": snap.meta["nodes"], "files": snap.meta["files"],
                                             "fresh_start": how, "fresh_start_seconds": round(t_fs),
                                             "tree_seconds": snap.meta.get("tree_seconds")}) + "\n")
                    flag = "" if snap.ok else f"  NOT OK ({snap.meta.get('tree_error') or snap.meta.get('digest_error')})"
                    print(f"{spot['id']} r{r}: nodes={snap.meta['nodes']} files={snap.meta['files']} "
                          f"fresh={how}/{t_fs:.0f}s tree={snap.meta.get('tree_seconds')}s at {time.time() - t0:.0f}s{flag}", flush=True)
        finally:
            try:
                env.close()
                print("env closed", flush=True)
            except Exception as e:  # pragma: no cover
                print("close error:", repr(e)[:200], flush=True)

    # ---- compare ----
    lines = []
    agree = 0
    judged = 0
    for spot in spots:
        dirs = sorted((out / spot["id"]).glob("r*")) if (out / spot["id"]).exists() else []
        snaps = [s for s in (load_snapshot(d) for d in dirs) if complete(s)]
        if len(snaps) < 2:
            lines.append(f"- {spot['id']}: only {len(snaps)} usable replay(s) on disk, not judged")
            continue
        judged += 1
        ok = True
        first_fail = None
        for a, b in itertools.combinations(snaps, 2):
            eq, tdiffs, fdiffs = states_equal(a.canon, a.digest, b.canon, b.digest, mask)
            if not eq:
                ok = False
                first_fail = (a.path.name, b.path.name, tdiffs, fdiffs)
                break
        if ok:
            agree += 1
            lines.append(f"- {spot['id']}: agree ({len(snaps)} replays)")
        else:
            an, bn, tdiffs, fdiffs = first_fail
            lines.append(f"- {spot['id']}: DISAGREE {an} vs {bn}: {len(tdiffs)} tree diffs, {len(fdiffs)} file diffs")
            lines.append("    " + summarize(tdiffs, limit=6).replace("\n", "\n    "))
            for p in fdiffs[:6]:
                lines.append(f"    file {p}")
    rate = agree / judged if judged else 0.0
    verdict = "PASS" if judged and rate >= 0.9 else "FAIL"
    header = f"# Smoke test: {agree}/{judged} click-spots agree ({rate:.0%}) -> {verdict} (threshold 90%)\n"
    (out / "report.md").write_text(header + "\n" + "\n".join(lines) + "\n")
    print(header + "\n".join(lines), flush=True)


if __name__ == "__main__":
    main()
