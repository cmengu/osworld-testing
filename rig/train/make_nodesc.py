"""The v3 export with the written action description removed, 2 November 2026: every action reads "agent step", as real
agent rows do, so a retrain shows how much the model leaned on the description.  Labels, rows and folds are untouched.

    /usr/bin/python3 -I rig/train/make_nodesc.py     # rig/train/data_k3_v3 -> rig/train/data_k3_v3nodesc
"""
import collections
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
SRC, OUT = HERE / "data_k3_v3", HERE / "data_k3_v3nodesc"
OUT.mkdir(exist_ok=True)
ACTION = re.compile(r"((?:PROPOSED )?ACTION: )[^\n]*\nkeys:")
count = collections.Counter()
for f in sorted(SRC.iterdir()):
    if f.suffix != ".jsonl":
        (OUT / f.name).write_bytes(f.read_bytes())
        continue
    out = []
    for line in f.read_text().splitlines():
        d = json.loads(line)
        d["prompt"], n = ACTION.subn(r"\1agent step\nkeys:", d["prompt"])
        if f.name == "all.jsonl":
            count[(d["task"], n)] += 1
        out.append(json.dumps(d, ensure_ascii=False))
    (OUT / f.name).write_text("\n".join(out) + "\n")
print(sorted(count.items()))
