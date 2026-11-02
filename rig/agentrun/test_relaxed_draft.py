"""Offline test of the 2 November rules in rig/mask.py on saved states; no VM.  Writes rig/out/model_on_agent/relaxed_draft_test.json.
    OSWorld/.venv/bin/python -I rig/agentrun/test_relaxed_draft.py
For each row: does the action still count as a change, and does any recorded undo attempt now match?"""
import collections, json, multiprocessing as mp, pathlib, sys
BASE = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE))
from rig.snapshot import load_snapshot
from rig.mask import apply_tree_mask, relax, strict_states_equal as states_equal

def states_equal_relaxed(ac, ad, bc, bd, mask):
    _, td, fd = states_equal(ac, ad, bc, bd, mask)
    left, dr = relax(td, apply_tree_mask(ac, mask), apply_tree_mask(bc, mask))
    return (not left and not fd), left, fd, dr
MASK = json.load(open(BASE / "rig/out/mask_run/mask.json"))
OUT = BASE / "rig/out"

def check(job):
    rid, d, group, label = job
    d = pathlib.Path(d)
    rec = {"row": rid, "group": group, "label": label, "dir": str(d.relative_to(BASE)), "matches": [], "attempts": 0}
    try:
        S = load_snapshot(d / "S")
        if (d / "S1/tree.xml").exists():
            s1 = load_snapshot(d / "S1")
            rec["strict_no_change"] = states_equal(S.canon, S.digest, s1.canon, s1.digest, MASK)[0]
            eq, left, fd, dr = states_equal_relaxed(S.canon, S.digest, s1.canon, s1.digest, MASK)
            rec["relaxed_no_change"], rec["action_left"], rec["action_files"], rec["action_dropped"] = eq, len(left), len(fd), dict(dr)
        for m in sorted(d.glob("c*/meta.json")):
            c = m.parent
            if not (c / "tree.xml").exists():
                continue
            rec["attempts"] += 1
            sn = load_snapshot(c)
            strict = states_equal(S.canon, S.digest, sn.canon, sn.digest, MASK)[0]
            eq, left, fd, dr = states_equal_relaxed(S.canon, S.digest, sn.canon, sn.digest, MASK)
            if eq and not strict:
                rec["matches"].append({"seq": json.load(open(m)).get("seq"), "dropped": dict(dr)})
    except Exception as e:
        rec["error"] = repr(e)[:200]
    return rec

def main():
    jobs = []
    for rid, src in [("ags3-change_permissions-%02d" % n, "agent_snap3_label") for n in (1, 2, 5, 6)] + [
        ("agr-change_permissions-10", "agent_rec_e"), ("agr-fix_text_search-08", "agent_rec_f"), ("agr-fix_todo_list-12", "agent_rec_i"),
        ("agr-optimize_refactor-05", "agent_rec_h"), ("ag-delete_slides_save-01", "agent_nuf_a"), ("ag-delete_slides_save-02", "agent_nuf_a"),
        ("ag-delete_slides_save-03", "agent_nuf_a"), ("ag-user_change-07", "agent_label_a"), ("ag-user_change-07", "agent_nuf_c")]:
        jobs.append((rid, str(OUT / src / rid), "agent12", "NO-UNDO-FOUND"))
    seen = {}
    for l in open(BASE / "rig/train/data_k3_v3/all.jsonl"):
        d = json.loads(l)
        seen[d["row_id"]] = (d["source"], d.get("executed_label"), d.get("band"), d.get("app"))
    for rid, (src, lab, band, app) in seen.items():
        jobs.append((rid, str(OUT / src / rid), "train", lab))
    with mp.Pool(4) as p:
        res = p.map(check, jobs, chunksize=2)
    for r in res:
        if r["group"] == "train":
            r["band"], r["app"] = seen[r["row"]][2], seen[r["row"]][3]
    (OUT / "model_on_agent/relaxed_draft_test.json").write_text(json.dumps(res, indent=1))
    print("jobs", len(res), "errors", sum("error" in r for r in res), "no S1", sum("strict_no_change" not in r for r in res))
    for r in res:
        if r["group"] == "agent12":
            print(r["row"], r["dir"].split("/")[2], "attempts", r["attempts"], "action: strict same", r.get("strict_no_change"), "relaxed same", r.get("relaxed_no_change"), "| new matches", [("+".join(m["seq"] or []), m["dropped"]) for m in r["matches"]])
    t = [r for r in res if r["group"] == "train"]
    print("train labels", collections.Counter(r["label"] for r in t))
    print("NUF with a new match", [(r["row"], r["band"], r["app"], "+".join(r["matches"][0]["seq"] or [])) for r in t if r["label"] == "NO-UNDO-FOUND" and r["matches"]])
    print("action became no-change", [(r["row"], r["label"], r["band"], r["app"], r["action_dropped"]) for r in t if r.get("relaxed_no_change") and not r.get("strict_no_change")])
    print("rules fired on train, action", sum(bool(r.get("action_dropped")) for r in t))
if __name__ == "__main__":
    main()
