"""5-minute status of the P4 pilot (world-model guard vs Claude guard).  python3 rig/p4_status.py"""
import glob, json, pathlib, re, subprocess, time
B = pathlib.Path(__file__).resolve().parent.parent
print(time.strftime("%H:%M"), (pathlib.Path(B / "rig/out/p4_driver.log").read_text().strip().splitlines() or ["(driver)"])[-1])
for arm in ("p4w1", "p4c1", "p4w2", "p4c2"):
    log = B / f"rig/out/agent_{arm}.log"
    if not log.exists():
        print(f"{arm}: not started"); continue
    g = [json.loads(l) for f in glob.glob(str(B / f"rig/out/agent_{arm}/**/guard.jsonl"), recursive=True) for l in open(f)]
    by = {}
    for r in g:
        k = r.get("decided_by") or r.get("mode")
        by[k] = by.get(k, 0) + 1
    blocks = [r for r in g if r.get("block")]
    backups = [r for r in g if r.get("backup")]
    ow = [r for r in g if (r.get("world") or {}).get("verdict") == "oneway"]
    text = log.read_text(errors="replace")
    done = "agent run exited" in subprocess.run(["tmux", "capture-pane", "-pt", f"ag{arm}"], capture_output=True, text=True).stdout
    errs = text.count("Exception in") + text.count("Traceback")
    secs = [r.get("guard_seconds") for r in g if r.get("guard_seconds") is not None]
    print(f"{arm}: steps judged {len(g)} | decided by {by} | one-way {len(ow)} | blocks {len(blocks)} | backups {len(backups)} | "
          f"guard s/step {round(sum(secs)/len(secs),1) if secs else '-'} | errors {errs} | {'DONE' if done else 'running'}")
    for r in blocks + backups:
        print(f"    step {r['step']}: block={r.get('block')} backup={bool(r.get('backup'))} on_task={r.get('on_task')} lost={(r.get('world') or {}).get('lost')} | {str(r.get('action'))[:90]}")
c = subprocess.run([str(B / "OSWorld/.venv/bin/modal"), "container", "list"], capture_output=True, text=True).stdout
print("containers:", len(re.findall(r"ta-[A-Z0-9]+", c)), "| battery:", re.search(r"(\d+%; [a-z ]+)", subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True).stdout).group(1))
