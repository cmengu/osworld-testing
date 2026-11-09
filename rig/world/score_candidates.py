"""P2 second score: predict which recorded undo attempts restore the before-state's files.

For every row with S and S1 and every undo candidate the rig executed and judged (file_diffs recorded), start from the
recorded after-state S1, apply the candidate's steps with T one after another (the digest is updated, windows and tree
stay as recorded), and predict "files equal S again" (rig/mask.py equality).  Compare with the rig: file_diffs == 0.
Only candidates whose steps are all modelled are scored (coverage reported).  Pass line: >= 90% right where covered.
"""
import ast, glob, json, pathlib, sys, collections
BASE = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path[:0] = [str(BASE), str(BASE / "rig")]
from rig.mask import _fsig, apply_file_mask, _is_lock
from rig.snapshot import load_snapshot
from rig.world.T import shell, gui, WState
from rig.world.derive import apply
from rig.world.score_forward import MASK, TEST_PREFIX


class Pseudo:
    """A snapshot whose digest was updated by predictions."""
    def __init__(self, snap, digest):
        self.digest, self.windows, self.tree_xml, self.system = digest, snap.windows, snap.tree_xml, snap.system


def step_delta(step, st):
    kind, _, arg = step.partition(":")
    if kind in ("wait", "focus", "pointer"):
        return "skip"
    if kind == "shell":
        return shell(arg, st)
    if kind == "key":
        keys = arg.split("+")
        code = f"pyautogui.hotkey({', '.join(repr(k) for k in keys)})" if len(keys) > 1 else f"pyautogui.press({keys[0]!r})"
        return gui(code, st)
    return None


def files_sig(digest):
    m = apply_file_mask({p: v for p, v in digest.items() if not p.startswith("/@")}, MASK)
    return {p: _fsig(p, v) for p, v in m.items()}                 # lock files count by presence, as in the rig


def run():
    tally = collections.Counter()
    wrong = []
    for f in sorted(glob.glob(str(BASE / "rig/out/*/results*.jsonl"))):
        run_ = pathlib.Path(f).parent.name
        if run_.startswith(TEST_PREFIX) or run_.startswith(("agent", "parta")):
            continue                                                   # DEV only
        for l in open(f):
            try:
                r = json.loads(l)
            except json.JSONDecodeError:
                continue
            if "row_id" not in r:
                continue
            row = BASE / "rig/out" / run_ / r["row_id"]
            if not (row / "S").is_dir() or not (row / "S1").is_dir() or not r.get("undo_search"):
                continue
            S, S1 = load_snapshot(row / "S"), load_snapshot(row / "S1")
            target = files_sig(S.digest)
            for c in r["undo_search"]:
                if "file_diffs" not in c or c.get("error") or c.get("reset_failed"):
                    continue
                tally["candidates"] += 1
                try:
                    seq = ast.literal_eval(c["seq"]) if isinstance(c["seq"], str) else c["seq"]
                except (ValueError, SyntaxError):
                    continue
                digest, ok = dict(S1.digest), True
                for step in seq:
                    st = WState(Pseudo(S1, digest))
                    d = step_delta(step, st)
                    if d is None:
                        ok = False
                        break
                    if d == "skip":
                        continue
                    files, dirs = apply(st, d)
                    # keep each folder's recorded entry (mode, owner); a new folder gets the terminal's 775 and the user
                    digest = {**files, **{x + "/": st.digest.get(x + "/") or {"d": 1, "mode": 0o775, "u": 1000} for x in dirs}}
                if not ok:
                    continue
                tally["covered"] += 1
                pred = files_sig(digest) == target
                truth = int(c["file_diffs"]) == 0
                tally["right" if pred == truth else "wrong"] += 1
                tally[f"truth_restored={truth}"] += 1
                if pred != truth and len(wrong) < 12:
                    wrong.append((run_, r["row_id"], seq, "pred", pred, "rig", truth))
    print(dict(tally))
    print(f"accuracy where covered: {tally['right'] / max(1, tally['covered']):.3f}; coverage {tally['covered'] / max(1, tally['candidates']):.3f}")
    for w in wrong:
        print("  wrong:", w)


if __name__ == "__main__":
    run()
