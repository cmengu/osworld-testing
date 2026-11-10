"""Status of the e2e pilot batches (rig/out/e2e_N): per task arm A/B results, the running task and step, errors,
containers, battery, and a sandbox-cost estimate (wall time since each batch's first log line x 0.76 USD/h)."""
import glob, json, os, re, subprocess, time, datetime
B = "rig/out"
tot_h = 0
rows = []
for log in sorted(glob.glob(f"{B}/e2e_[0-9].log")):
    b = log.split("_")[-1][:-4]
    txt = open(log, errors="replace").read()
    first = re.search(r"\[(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)", txt)
    alive = subprocess.run(["pgrep", "-f", f"batch_e2e{b}.json"], capture_output=True).stdout.strip() != b""
    if first:
        t0 = datetime.datetime.strptime(first.group(1), "%Y-%m-%d %H:%M:%S").timestamp()
        last = os.path.getmtime(log) if not alive else time.time()
        tot_h += (last - t0) / 3600
    steps = re.findall(r"rig state s(\d+) recorded", txt)
    branch = txt.count("e2e: branch at")
    done = [json.load(open(f)) for f in glob.glob(f"{B}/e2e_{b}/**/e2e.json", recursive=True)]
    errs = len(re.findall(r"Traceback|Error in example|RuntimeError", txt))
    rows.append((b, alive, len(done), steps[-1] if steps else "-", branch, errs, done))
bat = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True).stdout
bat = re.search(r"(\d+%; [a-z ]+)", bat)
try:
    nc = len(json.loads(subprocess.run(["modal", "container", "list", "--json"], capture_output=True, text=True, timeout=60).stdout))
except Exception:
    nc = "?"
print(f"battery {bat.group(1) if bat else '?'} | containers {nc} | running batches {sum(r[1] for r in rows)} | est. {tot_h * 0.76:.2f} USD")
print("| batch | running | tasks done | last state | branches | errors |\n|---|---|---|---|---|---|")
for b, alive, n, st, br, er, _ in rows:
    print(f"| e2e_{b} | {alive} | {n} | s{st} | {br} | {er} |")
for *_, done in rows:
    for d in done:
        a, bb = d["A"], d["B"]
        print(f"  {d['task']:20s} A lost={a.get('lost')} done={a.get('success')} | B lost={bb.get('lost')} backup={bb.get('recoverable_backup')} "
              f"done={bb.get('success')} | branch={bool(d.get('branch'))}{' (same as A)' if d.get('B_same_as_A') else ''}")
