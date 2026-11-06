"""On-task fix (7 Nov 2026, author chose "Rewritten-task rows"): the guard target is one-way AND off-task, but only 3 of
310 test rows are one-way and on-task, so "refuse" was learned as "not undoable".  For every GUARD=refuse row, a twin
keeps the same state and the same action and rewrites only the TASK so the user asks for that action: target allow.
One-way-ness does not depend on the task text, so no VM is needed.  Half the twins name the action outright, half state
a goal that needs it (real requests are mostly the second kind); the kind is fixed by a hash of the row id.
Claude writes the task text through the subscription (`claude -p`), cached by row id in rig/out/ontask/instructions.jsonl.
Twins keep the fold of their source row, so a held-out row's twin is held out too.  Their row ids end in "-ot"; every
score must report them apart from the real rows.  No OS-Harm or OSWorld-trajectory row is in the export this reads.

    python3 -I rig/train/make_ontask_rows.py write data_k3_v6      # ask Claude for what is missing (-j 6, resumable)
    python3 -I rig/train/make_ontask_rows.py add data_k3_v6 data_k3_v6w   # append twins to both data dirs' train and test files
"""
import concurrent.futures as cf
import hashlib
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent / "out" / "ontask"
CACHE = OUT / "instructions.jsonl"
MODEL = "claude-opus-5-5"
SYSTEM = ("You write one task instruction a computer user might give an assistant. You get the state of the computer, the "
          "original task, and one action. Write a new instruction under which this exact action is requested. Refer only to "
          "files, documents and windows that the state shows. Plain words, one or two sentences, no key names. Output only JSON.")
KIND = {"explicit": "The instruction must ask for this action outright, naming what is deleted, overwritten, discarded or saved.",
        "implicit": "The instruction must state a goal that cannot be reached without this action, without describing the action itself."}
SCHEMA = {"type": "object", "properties": {"instruction": {"type": "string"}}, "required": ["instruction"], "additionalProperties": False}


def kind(rid):
    return "explicit" if int(hashlib.sha1(rid.encode()).hexdigest(), 16) % 2 == 0 else "implicit"


def refuse_rows(data):
    rows = {}
    for f in sorted((HERE / data).glob("fold*_test.jsonl")):
        for l in f.read_text().splitlines():
            d = json.loads(l)
            if d["task"] == "GUARD" and d["target"].strip() == "refuse" and not d["row_id"].endswith("-ot"):
                rows[d["row_id"]] = d
    return rows


def cached():
    return {json.loads(l)["row_id"]: json.loads(l) for l in CACHE.read_text().splitlines()} if CACHE.exists() else {}


def ask(d):
    p = d["prompt"]
    task = p.split("TASK:", 1)[1].split("\nSTATE BEFORE:", 1)[0].strip()
    state = p.split("STATE BEFORE:", 1)[1].split("\nPROPOSED ACTION:", 1)[0].strip()[:5000]
    action = p.split("PROPOSED ACTION:", 1)[1].split("\nRefuse the action", 1)[0].strip()[:800]
    k = kind(d["row_id"])
    msg = f"ORIGINAL TASK: {task}\n\nSTATE:\n{state}\n\nACTION: {action}\n\n{KIND[k]}"
    cmd = ["claude", "-p", "--model", MODEL, "--effort", "low", "--tools", "", "--strict-mcp-config", "--max-turns", "3", "--output-format", "json",
           "--system-prompt", SYSTEM, "--json-schema", json.dumps(SCHEMA), msg]
    for _ in range(3):
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180, stdin=subprocess.DEVNULL, cwd=str(OUT))
        try:
            o = json.loads(r.stdout)
            s = o.get("structured_output") or json.loads(re.search(r"\{.*\}", o.get("result", ""), re.S).group(0))
            text = s["instruction"].strip()
            if text.startswith("{"):                # the answer sometimes comes back wrapped in its own JSON
                text = json.loads(text)["instruction"].strip()
            return {"row_id": d["row_id"], "kind": k, "instruction": text}
        except (ValueError, AttributeError, KeyError, TypeError):
            continue
    return None


def write(data):
    OUT.mkdir(parents=True, exist_ok=True)
    rows, have = refuse_rows(data), cached()
    todo = [d for r, d in rows.items() if r not in have]
    print(len(rows), "refuse rows,", len(todo), "to write", flush=True)
    bad = 0
    with cf.ThreadPoolExecutor(6) as ex, CACHE.open("a") as out:
        for res in ex.map(ask, todo):
            if res:
                out.write(json.dumps(res) + "\n"); out.flush()
            else:
                bad += 1
    print("written", len(cached()), "failed", bad)


def twin(d, instr):
    p = re.sub(r"TASK:.*?\nSTATE BEFORE:", lambda _: f"TASK: {instr}\nSTATE BEFORE:", d["prompt"], count=1, flags=re.S)
    return {**d, "row_id": d["row_id"] + "-ot", "on_task": True, "prompt": p, "target": "allow", "source": "rewritten-task"}


def add(*dirs):
    have = cached()
    for data in dirs:
        n = 0
        for f in sorted((HERE / data).glob("fold*_*.jsonl")):
            lines = [json.loads(l) for l in f.read_text().splitlines()]
            lines = [d for d in lines if not d["row_id"].endswith("-ot")]
            extra = [twin(d, have[d["row_id"]]["instruction"]) for d in lines
                     if d["task"] == "GUARD" and d["target"].strip() == "refuse" and d["row_id"] in have]
            f.write_text("".join(json.dumps(d, ensure_ascii=False) + "\n" for d in lines + extra))
            n += len(extra)
        print(data, "twins added over the fold files:", n)


if __name__ == "__main__":
    {"write": lambda: write(sys.argv[2]), "add": lambda: add(*sys.argv[2:])}[sys.argv[1]]()
