"""Write rig/out/RESULTS.md: every recorded pilot row, one table per run directory, plus a summary.

Labels are the recompared ones where a recompare exists (results_recompared.jsonl), but only for rows whose
latest record in results.jsonl is still a finished one (a record dropped for a rerun stays dropped).
Rows whose latest record is an error are listed as `error` (they rerun when the collector is relaunched).

    OSWorld/.venv/bin/python -I rig/results_table.py
"""
import collections, json, os, time

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
# run directory -> (when, what, in the training export)
RUNS = {
    "pilot_run":    ("17-18 Oct", "Run 1: ten-row Calc timing", False),
    "pilot_recheck": ("18 Oct", "Run 3: Calc save recheck", False),
    "pilot_run2":   ("18 Oct", "Run 2: 30 Calc rows (the Calc control)", True),
    "pilot_rerun":  ("19 Oct", "Run 5: rerun of 8 Calc rows", False),
    "probe_run":    ("22-23 Oct", "Probe: 33 rows over Files, terminal, PDF, VS Code, Writer, Thunderbird", True),
    "probe_row27":  ("23 Oct", "Probe row 27 confirmation rerun", False),
    "probe_row33":  ("23 Oct", "Probe row 33 confirmation rerun", False),
    "pilot150_a":   ("23-24 Oct", "Stopped all-Calc batch, collector a (closed; unstarted rows dropped)", True),
    "pilot150_b":   ("23-24 Oct", "Stopped all-Calc batch, collector b (closed; unstarted rows dropped)", True),
    "pilot150_c":   ("23-24 Oct", "Stopped all-Calc batch, collector c (closed; unstarted rows dropped)", True),
    "v2_a":         ("24-25 Oct", "v2 (smoke + main), collector a", True),
    "v2_b":         ("24-25 Oct", "v2 (smoke + main), collector b", True),
    "v2_c":         ("24-25 Oct", "v2 (smoke + main), collector c", True),
    "rv_a":         ("25-26 Oct", "targeted rerun of 24 suspect v2 rows, collector a (supersedes v2_*)", True),
    "rv_b":         ("25-26 Oct", "targeted rerun, collector b (supersedes v2_*)", True),
    "rv_c":         ("25-26 Oct", "targeted rerun, collector c (supersedes v2_*)", True),
    "rx_a":         ("26 Oct", "v2-0046 with Ctrl+Shift+T first (supersedes rv_b)", True),
    "gd_a":         ("25-26 Oct", "24 destructive guard rows v2-0102..0125, collector a", True),
    "gd_b":         ("25-26 Oct", "guard rows, collector b", True),
    "gd_c":         ("25-26 Oct", "guard rows, collector c", True),
    "cf_a":         ("26 Oct", "confirmation run, collector a: v2-0046 (errored in a network outage; settled by recompare)", True),
    "cf_b":         ("26 Oct", "confirmation run, collector b: v2-0049 (errored in the outage; settled by recompare)", True),
    "cf_c":         ("26 Oct", "confirmation run, collector c: v2-0055 (resets fixed; M again fails on mbox bytes), v2-0056 (errored)", True),
    "cf_f":         ("26 Oct", "confirmation run: v2-0066 (route forced first), v2-0090 (focus by click)", True),
    "cf_g":         ("26 Oct", "confirmation run under the list-id rule: v2-0048 (Escape first), v2-0071 (argv.json masked)", True),
    "s3_a":         ("26 Oct", "v3 smoke, collector a: v3-0035 (sudo mv), v3-0042 (Writer save-over)", True),
    "s3_b":         ("26 Oct", "v3 smoke, collector b: v3-0065/0071 under the OLD VS Code dialog code (wrong action; NOT exported, c3_* rerun both)", False),
    "s3_c":         ("26 Oct", "v3 smoke, collector c: v3-0079 (Files replace), v3-0096 (Thunderbird Shift+Delete)", True),
    "c3_a":         ("26-27 Oct", "v3 main batch (one-way rows), collector a", True),
    "c3_b":         ("26-27 Oct", "v3 main batch, collector b", True),
    "c3_c":         ("26-27 Oct", "v3 main batch, collector c (stopped at 03:02 on battery; its 2 unfinished rows are in the rerun)", True),
    "c3_d":         ("26-27 Oct", "v3 main batch, collector d", True),
    "c3_e":         ("26-27 Oct", "v3 main batch, collector e", True),
    "c3_f":         ("26-27 Oct", "v3 main batch, collector f", True),
    "r3_a":         ("27 Oct", "v3 rerun of 24 rows (outage losses + fixed recipes), collector a (supersedes c3_*)", True),
    "r3_b":         ("27 Oct", "v3 rerun, collector b (supersedes c3_*)", True),
    "r3_c":         ("27 Oct", "v3 rerun, collector c (supersedes c3_*)", True),
    "r3_d":         ("27 Oct", "v3 rerun, collector d (supersedes c3_*)", True),
    "r3_e":         ("27 Oct", "v3 rerun, collector e (supersedes c3_*)", True),
    "r3_f":         ("27 Oct", "v3 rerun, collector f (supersedes c3_*)", True),
    "r4_a":         ("27 Oct", "v3 second rerun pass (os replay, chooser route, window-aware no-change), collector a (supersedes r3_*)", True),
    "r4_b":         ("27 Oct", "v3 second rerun pass, collector b (supersedes r3_*)", True),
    "r4_c":         ("27 Oct", "v3 second rerun pass, collector c (supersedes r3_*)", True),
    "r4_d":         ("27 Oct", "v3 second rerun pass, collector d (supersedes r3_*)", True),
    "r4_e":         ("27 Oct", "v3 second rerun pass, collector e (supersedes r3_*)", True),
    "r4_f":         ("27 Oct", "v3 second rerun pass, collector f (supersedes r3_*)", True),
}
FINISHED = ("ok", "broken_action", "noise")
CLOSED = {"pilot150_a", "pilot150_b", "pilot150_c"}  # stopped by the author on 24 Oct; their error rows never rerun


def load(run):
    d = os.path.join(OUT, run)
    latest = {}
    for line in open(os.path.join(d, "results.jsonl")):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        latest[r["row_id"]] = r
    rec = {}
    p = os.path.join(d, "results_recompared.jsonl")
    if os.path.exists(p):
        for line in open(p):
            r = json.loads(line)
            rec[r["row_id"]] = r
    rows = []
    for rid, r in latest.items():
        if r.get("status") == "ok" and rid in rec and rec[rid].get("started_at") == r.get("started_at"):
            r = rec[rid]
        if run in CLOSED and r.get("status") not in FINISHED:
            continue
        rows.append(r)
    return rows


def label(r):
    if r.get("status") != "ok":
        return r.get("status") or "?"
    return r.get("executed_label_recompared") or r.get("executed_label") or "?"


def undo(r):
    u = r.get("shortest_undo_recompared", r.get("shortest_undo")) or []
    return " ; ".join(u) if u else "-"


def main():
    summary, sections = [], []
    total = collections.Counter()
    for run, (when, what, export) in RUNS.items():
        if not os.path.exists(os.path.join(OUT, run, "results.jsonl")):
            continue
        rows = sorted(load(run), key=lambda r: r["row_id"])
        c = collections.Counter(label(r) for r in rows)
        if export:
            total.update(c)
        summary.append(f"| {run} | {when} | {what} | {'yes' if export else 'no'} | {len(rows)} | "
                       + " | ".join(str(c.get(k, "") or "") for k in ("REVERSIBLE", "NO-UNDO-FOUND", "UNCONFIRMED", "broken_action", "error")) + " |")
        lines = [f"## {run}: {what}", "", "| row | app | spot | band | on task | label | shortest undo | tier | min |", "|---|---|---|---|---|---|---|---|---|"]
        for r in rows:
            mins = f"{r['row_seconds'] / 60:.0f}" if r.get("row_seconds") else ""
            lines.append(f"| {r['row_id']} | {r.get('app') or ''} | {r.get('spot_id') or ''} | {r.get('band') or ''} | {r.get('on_task')} | "
                         f"{label(r)} | {undo(r).replace('|', '/')} | {r.get('found_tier_recompared', r.get('found_tier'))} | {mins} |")
        sections.append("\n".join(lines))
    head = [
        "# Pilot results, every recorded row",
        "",
        f"Generated {time.strftime('%d %b %Y %H:%M')} by `rig/results_table.py` from `rig/out/*/results.jsonl`. "
        "Labels are recompared where a recompare exists; `error` rows rerun on relaunch.",
        "",
        "| run | when | what | in export | rows | REVERSIBLE | NO-UNDO-FOUND | UNCONFIRMED | broken | error |",
        "|---|---|---|---|---|---|---|---|---|---|",
        *summary,
        "",
        "Rows in runs marked for the export: " + ", ".join(f"{k} {v}" for k, v in total.most_common()) + ".",
    ]
    path = os.path.join(OUT, "RESULTS.md")
    open(path, "w").write("\n".join(head) + "\n\n" + "\n\n".join(sections) + "\n")
    print(path, dict(total))


if __name__ == "__main__":
    main()
