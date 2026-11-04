"""Training files with the rare undo kinds repeated (4 November 2026, author's go: "retrain with the rare kinds weighted").

In the H3 run Model-E never produced a terminal undo or undo-then-save: 70% of UNDO targets were Ctrl+Z or Escape.
This copies an export and, in each fold's TRAIN file only, repeats every UNDO line whose target uses a shell command,
a save, a reopen or a window close REPEAT times in all.  Test files, all.jsonl and the other tasks are unchanged.

    python3 rig/train/make_weighted.py data_k3_v5 data_k3_v5w 3
"""
import json
import pathlib
import shutil
import sys

HERE = pathlib.Path(__file__).resolve().parent
RARE = ("shell:", "ctrl+s", "reopen", "alt+f4", "ctrl+w")


def main(src, dst, repeat):
    s, d = HERE / src, HERE / dst
    if d.exists():
        shutil.rmtree(d)
    shutil.copytree(s, d)
    for f in sorted(d.glob("fold*_train.jsonl")):
        out, extra = [], 0
        for line in f.read_text().splitlines():
            out.append(line)
            r = json.loads(line)
            if r["task"] == "UNDO" and any(k in r["target"] for k in RARE):
                out += [line] * (repeat - 1)
                extra += repeat - 1
        f.write_text("\n".join(out) + "\n")
        print(f"{f.name}: +{extra} repeated UNDO lines")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]))
