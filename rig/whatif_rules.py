"""What-if analysis for comparison-rule candidates (Paper draft 4.3): re-judge the rows on disk under a
proposed rule WITHOUT changing treediff.py or mask.py, and report which labels would flip.  Decides nothing;
the rule is admitted only by hand, logged in rig/out/pilot_run/rules_log.md with its trigger row.

    OSWorld/.venv/bin/python -I rig/whatif_rules.py --rule empty_cells
    OSWorld/.venv/bin/python -I rig/whatif_rules.py --rule cursor_readouts
    OSWorld/.venv/bin/python -I rig/whatif_rules.py --rule empty_cells,cursor_readouts

Rules on offer:
  empty_cells       drop table-cell nodes that carry no text, formula or note (viewport placeholders: which empty
                    cells are visible depends on the window, not on the document)
  cursor_readouts   drop the text of the Name Box and the Input line (Formula Tool Bar): they echo the cursor cell
  toolbar_readouts  drop text/checked/value of every node under a tool-bar (font name/size, Bold, alignment ...):
                    NOTE this also hides the only trace the tree holds of the cursor cell's format
  container_order   collapse the sibling index of unnamed panels (panel[]#8 -> panel[]): a document opened from
                    the Start Center keeps its content but its panels sit after the Start Center's leftovers
                    (pilot-0131 c07: 766 diffs, all present/gone pairs of the same subtrees)
  shell_scope       drop everything under a nameless application node (gnome-shell walked through a naming gap;
                    a recorder-scope artefact, fixed in fasttree.py on 17 Oct, applied here to rows recorded before)
"""
import argparse
import json
import pathlib
import sys

BASE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
from rig.mask import states_equal            # noqa: E402
from rig.snapshot import load_snapshot        # noqa: E402
from rig.treediff import tag_of               # noqa: E402


import re as _re


def apply_rules(canon, rules):
    out = {}
    for path, attrs in canon.items():
        if "container_order" in rules:
            path = _re.sub(r"/panel\[\]#\d+", "/panel[]", path)
        tag = tag_of(path)
        if "shell_scope" in rules and path.startswith("/desktop-frame/application[]#"):
            continue
        if "empty_cells" in rules and tag == "table-cell" and not attrs.get("text") and not attrs.get("Formula") and not attrs.get("Note"):
            continue
        a = dict(attrs)
        if "cursor_readouts" in rules and "tool-bar[Formula Tool Bar]" in path and tag in ("text", "paragraph"):
            a.pop("text", None)
        if "toolbar_readouts" in rules and "/tool-bar[" in path:
            for k in ("text", "checked", "value"):
                a.pop(k, None)
        out[path] = a
    return out


def judge(rdir, mask, rules):
    S = load_snapshot(rdir / "S")
    S1 = load_snapshot(rdir / "S1")
    f = lambda c: apply_rules(c, rules)  # noqa: E731
    eq, _, _ = states_equal(f(S.canon), S.digest, f(S1.canon), S1.digest, mask)
    if eq:
        return "REVERSIBLE", [], "no change"
    for c in sorted(rdir.glob("c*")):
        if not (c / "tree.xml").exists():
            continue
        snap = load_snapshot(c)
        eq_c, td, fd = states_equal(f(S.canon), S.digest, f(snap.canon), snap.digest, mask)
        if eq_c:
            return "REVERSIBLE", snap.meta.get("seq"), c.name
    if (rdir / "replay" / "tree.xml").exists():
        snap = load_snapshot(rdir / "replay")
        eq_c, _, _ = states_equal(f(S.canon), S.digest, f(snap.canon), snap.digest, mask)
        if eq_c:
            return "REVERSIBLE", snap.meta.get("seq"), "replay"
    return "NO-UNDO-FOUND", None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rule", default="", help="comma-separated rule names (empty = current rules)")
    ap.add_argument("--out", default=str(BASE / "rig" / "out" / "pilot_run"))
    ap.add_argument("--mask", default=str(BASE / "rig" / "out" / "mask_run" / "mask.json"))
    args = ap.parse_args()
    rules = {r for r in args.rule.split(",") if r}
    mask = json.load(open(args.mask))
    out = pathlib.Path(args.out)
    recs = {}
    if (out / "results.jsonl").exists():
        for line in (out / "results.jsonl").read_text().splitlines():
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("status") == "ok":
                recs[r["row_id"]] = r
    flips = 0
    for rdir in sorted(out.glob("pilot-*")):
        if not (rdir / "S1" / "meta.json").exists():
            continue
        base = judge(rdir, mask, set())
        new = judge(rdir, mask, rules)
        rec = recs.get(rdir.name, {})
        mark = "FLIP" if base[0] != new[0] or (base[1] or []) != (new[1] or []) else "same"
        flips += mark == "FLIP"
        print(f"{rdir.name} {rec.get('spot_id', '?'):24s} current: {base[0]:14s} {base[1] or '-'!s:34s} | {'+'.join(sorted(rules)) or 'current':30s}: {new[0]:14s} {new[1] or '-'!s:34s} {mark}")
    print(f"{flips} rows would flip under rules {sorted(rules)}")


if __name__ == "__main__":
    main()
