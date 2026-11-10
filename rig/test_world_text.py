"""Offline checks for the 10 Nov world-model rules: cp -r, tar -x (archive members in the snapshot), sort -o and
sed -i computed from the text the snapshot now keeps.  States are a real recorded before-state (terminal open) with
synthetic files, so the expected after-states are known exactly.

    OSWorld/.venv/bin/python -I rig/test_world_text.py
"""
import copy
import hashlib
import json
import pathlib
import sys

BASE = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(BASE), str(BASE / "rig")]
from rig.snapshot import load_snapshot                 # noqa: E402
from rig.world.T import T, WState, _sorted_text, _sed_text   # noqa: E402
from rig.world.derive import derive                    # noqa: E402

D = "/home/user/t10"


def base():
    for l in open(BASE / "rig/out/p5a_0/results.jsonl"):
        r = json.loads(l)
        if r["row_id"] == "p5a-0005" and r.get("snapshot_before"):
            return load_snapshot(BASE / "rig/out/p5a_0" / r["snapshot_before"]), r["action"]["code"], "rm /home/user/p5a0/plan.txt"
    raise SystemExit("no base row")


SNAP, CODE, CMD = base()


def f(text, **kw):
    b = text.encode()
    return {"s": len(b), "h": hashlib.sha256(b).hexdigest(), "mode": 0o644, "u": 1000, "t": text, **kw}


def state(files, dirs=()):
    s = copy.copy(SNAP)
    s.digest = {k: v for k, v in SNAP.digest.items()}
    for x in [D, *dirs]:
        s.digest[x + "/"] = {"d": 1, "mode": 0o755, "u": 1000}
    s.digest.update(files)
    return s


def run(cmd, snap):
    code = CODE.replace(CMD, cmd)
    assert code != CODE or cmd == CMD
    return T(code, WState(snap)), derive(code, snap)


def h(t):
    return hashlib.sha256(t.encode()).hexdigest()


checks = []


def check(name, cond):
    checks.append((name, bool(cond)))


# sort -o
assert _sorted_text("cherry 0\napple\nbanana\n") == "apple\nbanana\ncherry 0\n"
s = state({f"{D}/l.txt": f("apple\nbanana\ncherry 0\n")})
d, v = run(f"sort -o {D}/l.txt {D}/l.txt", s)
check("sort -o on a sorted list: no change, noop", not d.files and v["verdict"] == "noop")
s = state({f"{D}/l.txt": f("cherry 0\napple\nbanana\n")})
d, v = run(f"sort -o {D}/l.txt {D}/l.txt", s)
check("sort -o on an unsorted list: exact bytes, one-way", d.files.get(f"{D}/l.txt") == ("bytes", h("apple\nbanana\ncherry 0\n"), 22) and v["verdict"] == "oneway")
s = state({f"{D}/l.txt": f("b\nB\na\n")})
d, v = run(f"sort -o {D}/l.txt {D}/l.txt", s)
check("sort -o where the locale decides: falls back to 'may change'", d.files.get(f"{D}/l.txt", ("",))[0] == "sym-or-same")

# sed -i
assert _sed_text("s/,/;/", "a,1,x\nb,2\n") == "a;1,x\nb;2\n"
assert _sed_text("s/,/;/g", "a,1,x\n") == "a;1;x\n"
assert _sed_text("s/a.b/c/", "x") is None
s = state({f"{D}/data.csv": f("a,1\nb,2\n")})
d, v = run(f"sed -i 's/,/;/' {D}/data.csv", s)
check("sed -i s/,/;/: exact bytes, one-way", d.files.get(f"{D}/data.csv") == ("bytes", h("a;1\nb;2\n"), 8) and v["verdict"] == "oneway")
d, v = run(f"sed -i 's/zz/yy/' {D}/data.csv", s)
check("sed -i with no match: noop", not d.files and v["verdict"] == "noop")
s2 = state({f"{D}/data.csv": f("a,1\nb,2\n"), f"{D}/bak.csv": f("a,1\nb,2\n")})
d, v = run(f"sed -i 's/,/;/' {D}/data.csv", s2)
check("sed -i with an identical copy elsewhere: reversible", v["verdict"] == "reversible")
s3 = state({f"{D}/data.csv": {k: x for k, x in f("a,1\nb,2\n").items() if k != "t"}})
d, v = run(f"sed -i 's/,/;/' {D}/data.csv", s3)
check("sed -i without text (old snapshot): 'may change', one-way", d.files.get(f"{D}/data.csv", ("",))[0] == "sym-or-same" and v["verdict"] == "oneway")

# cp -r
s = state({f"{D}/new/index.html": f("index\n")}, dirs=[f"{D}/new", f"{D}/site"])
d, v = run(f"cp -r {D}/new/. {D}/site/", s)
check("cp -r new/. into an empty site: content, reversible (rm)", d.files.get(f"{D}/site/index.html") == ("content", f"{D}/new/index.html")
      and v["verdict"] == "reversible" and any(p.startswith("rm ") for p in v["plan"]))
s = state({f"{D}/new/index.html": f("index\n"), f"{D}/site/index.html": f("the live index\n")}, dirs=[f"{D}/new", f"{D}/site"])
d, v = run(f"cp -r {D}/new/. {D}/site/", s)
check("cp -r new/. over a clashing file: one-way", v["verdict"] == "oneway" and f"{D}/site/index.html" in v["lost"])
s = state({f"{D}/new/index.html": f("index\n")}, dirs=[f"{D}/new", f"{D}/site"])
d, v = run(f"cp -r {D}/new {D}/site", s)
check("cp -r new site (site exists): goes to site/new/", d.files.get(f"{D}/site/new/index.html") == ("content", f"{D}/new/index.html")
      and f"{D}/site/new/" in d.files)
d, v = run(f"cp -r {D}/new {D}/fresh", s)
check("cp -r new fresh (fresh absent): fresh/index.html", d.files.get(f"{D}/fresh/index.html") == ("content", f"{D}/new/index.html"))

# tar -x
mem = [["notes.txt", "f", 7, h("packed\n")]]
pack = {"s": 10240, "h": "x" * 64, "mode": 0o644, "u": 1000, "ar": mem}
s = state({f"{D}/pack.tar": pack}, dirs=[f"{D}/out"])
d, v = run(f"tar -xf {D}/pack.tar -C {D}/out", s)
check("tar -x into an empty folder: exact bytes, reversible (rm)", d.files.get(f"{D}/out/notes.txt") == ("bytes", h("packed\n"), 7)
      and v["verdict"] == "reversible")
s = state({f"{D}/pack.tar": pack, f"{D}/out/notes.txt": f("my own notes\n")}, dirs=[f"{D}/out"])
d, v = run(f"tar -xf {D}/pack.tar -C {D}/out", s)
check("tar -x over a clashing file: one-way", v["verdict"] == "oneway" and f"{D}/out/notes.txt" in v["lost"])
s = state({f"{D}/pack.tar": pack, f"{D}/out/notes.txt": f("packed\n")}, dirs=[f"{D}/out"])
d, v = run(f"tar -xf {D}/pack.tar -C {D}/out", s)
check("tar -x over an identical file: noop", not d.files and v["verdict"] == "noop")
d, v = run(f"tar -xkf {D}/pack.tar -C {D}/out", state({f"{D}/pack.tar": pack, f"{D}/out/notes.txt": f("mine\n")}, dirs=[f"{D}/out"]))
check("tar -xk keeps an existing file: noop", not d.files)
d, v = run(f"tar -tf {D}/pack.tar", s)
check("tar -t changes nothing", d is not None and not d.files)
s = state({f"{D}/pack.tar": {k: x for k, x in pack.items() if k != "ar"}}, dirs=[f"{D}/out"])
d, v = run(f"tar -xf {D}/pack.tar -C {D}/out", s)
check("tar -x without a member list (old snapshot): no prediction", d is None)
mem2 = [["dir/", "d", 0, None], ["dir/a.txt", "f", 2, h("a\n")]]
s = state({f"{D}/p2.tar": dict(pack, ar=mem2)}, dirs=[f"{D}/out"])
d, v = run(f"tar -xf {D}/p2.tar -C {D}/out", s)
check("tar -x with a folder: folder made, file bytes", f"{D}/out/dir/" in d.files and d.files.get(f"{D}/out/dir/a.txt") == ("bytes", h("a\n"), 2))

bad = [n for n, ok in checks if not ok]
for n, ok in checks:
    print("ok  " if ok else "FAIL", n)
print(f"{len(checks) - len(bad)}/{len(checks)} passed")
sys.exit(1 if bad else 0)
