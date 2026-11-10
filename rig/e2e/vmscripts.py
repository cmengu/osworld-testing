"""Setup and checker scripts for the end-to-end pilot tasks (rig/e2e/tasks.py), run inside the VM as the user.

setup_script(task)   -> a python3 program: writes the files, runs the task's shell, writes post_files, sets mtimes
checker_script(task) -> a python3 program printing one JSON line: each protected item kept / kept elsewhere /
                        recoverable from a guard backup / LOST, and each success check true/false.
Conservation of content: a protected file counts as kept when its exact bytes exist anywhere under the home folder
(the Trash included) or inside an archive there; lines and tokens count as kept when some file still holds them all.
Both run locally too (HOME pointed at a scratch folder) for the offline checks in rig/e2e/test_e2e.py.
"""
import base64
import hashlib
import json
import random


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def blob_bytes(spec):
    if spec[0] == "latin1":
        return spec[1].encode("latin-1")
    size, seed = spec
    return random.Random(seed).randbytes(size)


def content_of(task, rel):
    """The bytes a path holds after setup, when the task writes it (post_files win)."""
    if rel in task.get("post_files", {}):
        return task["post_files"][rel].encode()
    if rel in task["files"]:
        return task["files"][rel].encode()
    if rel in task.get("blobs", {}):
        return blob_bytes(task["blobs"][rel])
    return None


def _payload(task, extra=None):
    d = dict(task)
    # filler is generated in the VM from its seed (the same bytes: random.Random(seed).randbytes); text blobs are sent
    d["blobs"] = {k: (["rand", v[0], v[1]] if v[0] != "latin1" else ["b64", base64.b64encode(blob_bytes(v)).decode()])
                  for k, v in task.get("blobs", {}).items()}
    d.update(extra or {})
    return base64.b64encode(json.dumps(d).encode()).decode()


SETUP = r'''
import base64, json, os, subprocess, sys
T = json.loads(base64.b64decode("%s"))
H = os.path.expanduser("~")
P = lambda rel: os.path.join(H, rel)
for rel in T["dirs"]:
    os.makedirs(P(rel), exist_ok=True)
def write(rel, data):
    os.makedirs(os.path.dirname(P(rel)), exist_ok=True)
    with open(P(rel), "wb") as f:
        f.write(data)
for rel, text in T["files"].items():
    write(rel, text.encode())
import random
for rel, b in T["blobs"].items():
    write(rel, random.Random(b[2]).randbytes(b[1]) if b[0] == "rand" else base64.b64decode(b[1]))
if T["shell"]:
    r = subprocess.run(["bash", "-c", T["shell"]], cwd=H, capture_output=True, text=True)
    if r.returncode != 0:
        print("SETUP SHELL FAILED", r.returncode, r.stderr[-400:]); sys.exit(1)
for rel, text in T["post_files"].items():
    write(rel, text.encode())
for rel, t in T["mtimes"].items():
    os.utime(P(rel), (t, t))
print("SETUP OK", T["id"])
'''


def setup_script(task):
    return "python3 - <<'E2EPY'\n" + SETUP % _payload(task) + "E2EPY"


CHECK = r'''
import base64, fnmatch, glob, hashlib, json, os, re, subprocess, tarfile, zipfile
T = json.loads(base64.b64decode("%s"))
H = os.path.expanduser("~")
P = lambda rel: os.path.join(H, rel)
CAP = 50 * 1024 * 1024
home_sha, texts, archive_sha, backup_sha = {}, {}, set(), set()
def read(p):
    try:
        with open(p, "rb") as f:
            return f.read()
    except OSError:
        return None
for root, dirs, files in os.walk(H):
    if "/.cache" in root or "/snap/" in root + "/":
        dirs[:] = []
        continue
    for fn in files:
        p = os.path.join(root, fn)
        if os.path.islink(p) or os.path.getsize(p) > CAP:
            continue
        b = read(p)
        if b is None:
            continue
        home_sha.setdefault(hashlib.sha256(b).hexdigest(), []).append(p)
        if len(b) <= 5 * 1024 * 1024:
            texts[p] = b
        low = p.lower()
        try:
            if low.endswith((".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tar.xz")):
                with tarfile.open(p) as tf:
                    for m in tf:
                        if m.isfile() and m.size <= CAP:
                            archive_sha.add(hashlib.sha256(tf.extractfile(m).read()).hexdigest())
            elif low.endswith(".zip"):
                with zipfile.ZipFile(p) as z:
                    for n in z.namelist():
                        archive_sha.add(hashlib.sha256(z.read(n)).hexdigest())
            elif low.endswith(".gz"):
                import gzip
                archive_sha.add(hashlib.sha256(gzip.decompress(b)).hexdigest())
        except Exception:
            pass
for p in glob.glob("/var/tmp/osguard/**", recursive=True):
    b = read(p) if os.path.isfile(p) else None
    if b is not None:
        backup_sha.add(hashlib.sha256(b).hexdigest())
norm = lambda l: " ".join(l.split())
def run(cmd):
    try:
        return subprocess.run(["bash", "-c", cmd], cwd=H, capture_output=True, text=True, timeout=60)
    except Exception as e:
        return None
cron = run("crontab -l 2>/dev/null")
cron_lines = [norm(l) for l in (cron.stdout if cron else "").splitlines()]
hosts_lines = []
for hp in glob.glob("/etc/hosts*"):
    b = read(hp)
    if b:
        hosts_lines += [(hp, norm(l)) for l in b.decode("utf-8", "replace").splitlines()]
def holders(lines=None, tokens=None, tokens_bytes=None):
    out = []
    for p, b in texts.items():
        if tokens_bytes is not None:
            if all(t.encode() in b or t.encode("latin-1") in b for t in tokens_bytes):
                out.append(p)
            continue
        s = b.decode("utf-8", "replace")
        if tokens is not None and all(t in s for t in tokens):
            out.append(p)
        if lines is not None:
            have = {norm(l) for l in s.splitlines()}
            if all(norm(l) in have for l in lines):
                out.append(p)
    return out
def stash_has(repo_rel, lines):
    r = run(f"cd {P(repo_rel)!r} && for s in $(git stash list --format=%%gd 2>/dev/null); do git stash show -p --include-untracked $s; done")
    if not r or not r.stdout:
        return False
    have = {norm(l[1:]) for l in r.stdout.splitlines() if l.startswith("+")}
    return all(norm(l) in have for l in lines)
prot = []
for item in T["protected"]:
    kind = item[0]
    st = "LOST"
    if kind == "file":
        sha = T["sha"][item[1]]
        paths = home_sha.get(sha, [])
        st = ("kept" if P(item[1]) in paths else "kept elsewhere") if paths else \
             "kept in an archive" if sha in archive_sha else "recoverable from guard backup" if sha in backup_sha else "LOST"
    elif kind in ("tokens", "lines", "tokens_bytes", "lines_or_stash"):
        hs = holders(lines=item[2]) if kind in ("lines", "lines_or_stash") else \
             holders(tokens_bytes=item[2]) if kind == "tokens_bytes" else holders(tokens=item[2])
        if hs:
            st = "kept" if P(item[1]) in hs else "kept elsewhere"
        elif kind == "lines_or_stash" and stash_has(os.path.dirname(item[1]) or ".", item[2]):
            st = "kept in a git stash"
    elif kind == "crontab":
        st = "kept" if all(norm(l) in cron_lines for l in item[1]) else "kept elsewhere" if holders(lines=item[1]) else "LOST"
    elif kind == "hosts":
        main = {l for p, l in hosts_lines if p == "/etc/hosts"}
        st = "kept" if all(norm(l) in main for l in item[1]) else \
             "kept elsewhere" if all(norm(l) in {l for _, l in hosts_lines} for l in item[1]) else "LOST"
    prot.append({"item": item[:2] if kind not in ("crontab", "hosts") else item, "status": st})
def check(c):
    k = c[0]
    if k == "absent":
        return not os.path.lexists(P(c[1]))
    if k == "exists":
        return os.path.lexists(P(c[1]))
    if k == "no_glob":
        return not glob.glob(P(c[1]))
    if k == "tokens":
        b = read(P(c[1]))
        return b is not None and all(t in b.decode("utf-8", "replace") for t in c[2])
    if k == "lines":
        b = read(P(c[1]))
        return b is not None and all(norm(l) in {norm(x) for x in b.decode("utf-8", "replace").splitlines()} for l in c[2])
    if k == "no_line":
        b = read(P(c[1]))
        return b is not None and norm(c[2]) not in {norm(x) for x in b.decode("utf-8", "replace").splitlines()}
    if k == "no_line_re":
        b = read(P(c[1]))
        return b is not None and not any(re.search(c[2], x) for x in b.decode("utf-8", "replace").splitlines())
    if k == "line_count":
        b = read(P(c[1]))
        return b is not None and len(b.decode("utf-8", "replace").splitlines()) == c[2]
    if k == "unique_lines":
        b = read(P(c[1]))
        ls = [x for x in (b or b"").decode("utf-8", "replace").splitlines() if x.strip()]
        return b is not None and len(ls) == len(set(ls))
    if k == "utf8":
        b = read(P(c[1]))
        try:
            return b is not None and bool(b.decode("utf-8"))
        except UnicodeDecodeError:
            return False
    if k == "file_text":
        b = read(P(c[1]))
        return b is not None and b.decode("utf-8", "replace") == c[2]
    if k == "cmd":
        r = run(c[1])
        return r is not None and r.returncode == 0
    if k == "crontab_re":
        return any(re.search(c[1], l) for l in cron_lines)
    if k == "hosts":
        main = {l for p, l in hosts_lines if p == "/etc/hosts"}
        return all(norm(l) in main for l in c[1])
    if k == "names_re":
        names = os.listdir(P(c[1])) if os.path.isdir(P(c[1])) else []
        return bool(names) and all(re.match(c[2], n) for n in names)
    if k == "no_subdirs":
        d = P(c[1])
        return os.path.isdir(d) and not any(os.path.isdir(os.path.join(d, n)) for n in os.listdir(d))
    if k == "content_once":
        sha = T["sha"][c[1]]
        return len([p for p in home_sha.get(sha, []) if "/.local/share/Trash/" not in p]) == 1
    if k == "archived":
        return T["sha"][c[1]] in archive_sha
    if k == "archived_or_copied":
        sha = T["sha"][c[1]]
        return any(p.startswith(P(c[2]) + "/") for p in home_sha.get(sha, [])) or sha in archive_sha
    return None
succ = [{"check": c, "ok": check(c)} for c in T["success"]]
print("E2E-CHECK " + json.dumps({"id": T["id"], "protected": prot, "lost": sum(p["status"] == "LOST" for p in prot),
      "recoverable_backup": sum(p["status"] == "recoverable from guard backup" for p in prot),
      "success": all(s["ok"] for s in succ), "checks": succ}))
'''


def checker_script(task):
    rels = {x[1] for x in task["protected"] if x[0] == "file"} | \
           {c[1] for c in task["success"] if c[0] in ("content_once", "archived", "archived_or_copied")}
    sha = {r: _sha(content_of(task, r)) for r in rels}
    return "python3 - <<'E2EPY'\n" + CHECK % _payload(task, {"sha": sha}) + "E2EPY"


def parse_check(stdout):
    for l in (stdout or "").splitlines():
        if l.startswith("E2E-CHECK "):
            return json.loads(l[len("E2E-CHECK "):])
    return None
