"""Track C (8 Nov 2026): one status page for a running batch, written by the driver side, plus a desktop alert on
every event, so updates no longer depend on this chat session being awake (cron prompts arrived late or never on
7-8 Nov, and the laptop slept through a run).

Every --every seconds: per collector log (rows labelled / selected, last label line, exited or not, USD so far from
its report), Modal containers, battery and sleep setting, a subscription-limit wait if one is on
(rig/out/limit_wait.json).  Writes rig/out/status.md (human) and rig/out/status.json (machine).  A macOS notification
fires when a row is labelled, a collector exits, a traceback appears, the battery drops below 15%, or a limit wait starts.

    python3 rig/runstatus.py --logs 'rig/out/prr_*.log' --every 60          # loop (run it in tmux)
    python3 rig/runstatus.py --logs 'rig/out/prr_*.log' --once
"""
import argparse
import glob
import json
import pathlib
import re
import subprocess
import time

BASE = pathlib.Path(__file__).resolve().parent.parent
OUT = BASE / "rig" / "out"
LABEL = re.compile(r"^\[(pr-\d+|[a-z0-9]+-\d+)\] (REVERSIBLE|NO-UNDO-FOUND|INCOMPLETE|None) ", re.M)


def sh(cmd, t=30):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=t).stdout
    except Exception:  # noqa: BLE001
        return ""


def running(out_name):
    return f"--out rig/out/{out_name} " in sh("ps -axo command")


def notify(msg):
    sh(f"osascript -e {json.dumps('display notification ' + json.dumps(msg[:200]) + ' with title \"osguard run\"')}")


def collect(pattern):
    st = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "collectors": []}
    for log in sorted(glob.glob(str(BASE / pattern))):
        text = pathlib.Path(log).read_text(errors="replace")
        sel = re.search(r"(\d+) rows selected", text)
        labels = LABEL.findall(text)
        rep = pathlib.Path(log[:-4]) / "report.md"
        usd = re.search(r"≈ ([\d.]+) USD", rep.read_text()) if rep.exists() else None
        st["collectors"].append({"log": pathlib.Path(log).name, "selected": int(sel.group(1)) if sel else None,
                                 "labelled": len(labels), "last": " ".join(labels[-1]) if labels else "",
                                 # the launch line echoes "[collector exited]" to the tmux pane, not the log: also
                                 # count the collector as exited when no process writes to its --out folder any more
                                 "exited": "[collector exited]" in text or not running(pathlib.Path(log[:-4]).name),
                                 "tracebacks": text.count("Traceback"), "usd": float(usd.group(1)) if usd else None})
    st["containers"] = len(re.findall(r"ta-[A-Z0-9]+", sh(f"{BASE}/OSWorld/.venv/bin/modal container list 2>/dev/null", 60)))
    batt = sh("pmset -g batt")
    m = re.search(r"(\d+)%; ([a-z ]+);", batt)
    st["battery"] = {"pct": int(m.group(1)) if m else None, "state": m.group(2) if m else "?"}
    st["sleep_disabled"] = "SleepDisabled\t\t1" in sh("pmset -g")
    lw = OUT / "limit_wait.json"
    st["limit_wait"] = json.loads(lw.read_text()) if lw.exists() else None
    return st


def events(prev, cur):
    ev = []
    pc = {c["log"]: c for c in (prev or {}).get("collectors", [])}
    for c in cur["collectors"]:
        p = pc.get(c["log"], {})
        if c["labelled"] > p.get("labelled", 0):
            ev.append(f"{c['log']}: {c['last']}")
        if c["exited"] and not p.get("exited"):
            ev.append(f"{c['log']} exited ({c['labelled']}/{c['selected']} rows, {c['usd']} USD)")
        if c["tracebacks"] > p.get("tracebacks", 0):
            ev.append(f"{c['log']}: new traceback")
    b = cur["battery"]
    if b["pct"] is not None and b["pct"] < 15 and "discharging" in b["state"] and ((prev or {}).get("battery", {}).get("pct") or 100) >= 15:
        ev.append(f"battery {b['pct']}% and discharging")
    if cur["limit_wait"] and not (prev or {}).get("limit_wait"):
        ev.append(f"subscription limit: waiting until {cur['limit_wait']['until']}")
    return ev


def page(st):
    lines = [f"# Run status {st['at']}", "",
             f"battery {st['battery']['pct']}% {st['battery']['state']}; sleep disabled: {st['sleep_disabled']}; "
             f"Modal containers {st['containers']}" + (f"; LIMIT WAIT until {st['limit_wait']['until']}" if st["limit_wait"] else ""), "",
             "| collector | rows | last label | exited | tracebacks | USD |", "|---|---|---|---|---|---|"]
    for c in st["collectors"]:
        lines.append(f"| {c['log']} | {c['labelled']}/{c['selected']} | {c['last']} | {c['exited']} | {c['tracebacks']} | {c['usd']} |")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--logs", required=True)
    ap.add_argument("--every", type=int, default=60)
    ap.add_argument("--once", action="store_true")
    a = ap.parse_args()
    prev = json.loads((OUT / "status.json").read_text()) if (OUT / "status.json").exists() else None
    while True:
        cur = collect(a.logs)
        (OUT / "status.json").write_text(json.dumps(cur, indent=1))
        (OUT / "status.md").write_text(page(cur))
        for e in events(prev, cur):
            print(time.strftime("%H:%M"), e, flush=True)
            notify(e)
        prev = cur
        if a.once:
            print(page(cur))
            return
        if cur["collectors"] and all(c["exited"] for c in cur["collectors"]):
            notify("all collectors exited")
            print("ALL DONE", flush=True)
            return
        time.sleep(a.every)


if __name__ == "__main__":
    main()
