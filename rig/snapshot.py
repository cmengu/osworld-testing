"""Recorder: capture the machine state after an action.

One snapshot = accessibility tree (what the interface says) + file digest (what the disk
says; a deleted file never appears in the tree) + window list + screenshot (for humans).
Everything is written to a directory so a run can be audited and re-compared later.

The tree comes from rig.fasttree (scoped, parallel, errors reported) with the server's own
walk as a fallback.  File digest fields per path: s = size, m = mtime (recorded, never
compared), h = sha256 of the bytes, c = content hash for zip-based office files with the
metadata parts left out, mode = permission bits, u = owner uid, k = content signature for .xlsx/.xlsm (rig/xlsxsig.py) and, since 24 Oct, for .docx/.odt/.pptx/.odp (rig/officesig.py): what a user sees, not
how the writer stored it, v = the readable workbook view behind k.  Directories are entries ending in "/" with d = 1
and their mode; symbolic links carry l = the target.  Equality in mask.py uses k when present,
otherwise (s, c or h).
"""
import hashlib
import json
import os
import pathlib
import re
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

from .fasttree import fast_tree
from .treediff import Canon, canonicalize
from .vm import vm_shell

# The digest script carries rig/xlsxsig.py verbatim, so the VM computes the same cell-level signature that the
# offline tests check.  For .xlsx/.xlsm it adds k = cell signature and v = the readable workbook view (kept when
# under VIEW_CAP bytes) so a later criteria change can be re-applied to recorded rows without a new run.
_XLSXSIG_SRC = (pathlib.Path(__file__).resolve().parent / "xlsxsig.py").read_text()
# 24 Oct: rig/officesig.py (what a .docx/.odt/.pptx/.odp says) rides along the same way, executed in its own
# namespace because both modules define small helpers of the same names
_OFFICESIG_SRC = (pathlib.Path(__file__).resolve().parent / "officesig.py").read_text()
DIGEST_SCRIPT = r"""python3 - <<'PY'
""" + _XLSXSIG_SRC + r"""
_OFF = {}
exec(compile(""" + repr(_OFFICESIG_SRC) + r""", "officesig", "exec"), _OFF)
doc_view = _OFF["doc_view"]
view_signature = _OFF["view_signature"]
import os, hashlib, json, zipfile, tarfile
TEXT_CAP, TEXT_TOTAL, AR_CAP = 4096, 2 * 1024 * 1024, 10 * 1024 * 1024
text_total = [0]
VIEW_CAP = 3 * 1024 * 1024   # 18 Oct: raised from 400 KB so big workbooks (pilot-0231, 105 KB xlsx) keep a readable view
home = os.path.expanduser("~")
# 19 Oct: the Trash is recorded (a delete to Trash and Empty Trash were invisible), and so are directories (d),
# permission bits (mode) and symbolic links (l), for the Files domain.  A .trashinfo file is hashed without its
# DeletionDate line: trashing the same file again writes a new date and is still the same Trash.
skip = ("/.cache/", "/.mozilla/", "/.config/google-chrome/",
        "/snap/", "/.dbus/", "/.gvfs/", "/home/user/server/", "/home/user/.rig_cache/")
office = (".xlsx", ".xlsm", ".ods", ".docx", ".odt", ".pptx", ".odp")
meta_parts = ("docProps/", "meta.xml", "[Content_Types].xml")
cap = 20 * 1024 * 1024
rows = []
def content_hash(p):
    try:
        with zipfile.ZipFile(p) as z:
            h = hashlib.sha256()
            for name in sorted(z.namelist()):
                if name.startswith(meta_parts) or name.endswith("meta.xml"):
                    continue
                h.update(name.encode()); h.update(z.read(name))
            return h.hexdigest()
    except Exception:
        return None
for root, dirs, files in os.walk(home):
    if any(s in root + "/" for s in skip):
        dirs[:] = []
        continue
    try:
        st = os.lstat(root)
        rows.append({"p": root.rstrip("/") + "/", "d": 1, "mode": st.st_mode & 0o7777, "u": st.st_uid})
    except OSError:
        pass
    for f in files + [d for d in dirs if os.path.islink(os.path.join(root, d))]:
        p = os.path.join(root, f)
        try:
            st = os.lstat(p)
        except OSError:
            continue
        if os.path.islink(p):
            try:
                rows.append({"p": p, "l": os.readlink(p)})
            except OSError:
                pass
            continue
        if not os.path.isfile(p):
            continue
        h = None
        data = None
        size = st.st_size
        if st.st_size <= cap:
            try:
                with open(p, "rb") as fh:
                    data = fh.read()
                if p.endswith(".trashinfo") and "/.local/share/Trash/info/" in p:
                    data = b"\n".join(l for l in data.splitlines() if not l.startswith(b"DeletionDate="))
                    size = len(data)
                h = hashlib.sha256(data).hexdigest()
            except OSError:
                h = None
        row = {"p": p, "s": size, "m": st.st_mtime_ns, "h": h, "mode": st.st_mode & 0o7777, "u": st.st_uid}
        # 10 Nov (world model): the text of small plain files outside dot-folders (t), so T can compute what sort -o or
        # sed -i writes; and the members of small tar archives (ar: name, type, size, sha256), so T can predict tar -x.
        # Neither is compared (mask.file_sig reads s, h, c, k, mode, u only): no label changes.
        if h and size <= TEXT_CAP and data is not None and "/." not in p[len(home):] and text_total[0] + size <= TEXT_TOTAL:
            try:
                t = data.decode("utf-8")
                if "\x00" not in t:
                    row["t"] = t
                    text_total[0] += size
            except UnicodeDecodeError:
                pass
        if p.lower().endswith((".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tar.xz")) and size <= AR_CAP:
            try:
                with tarfile.open(p) as tf:
                    mem = []
                    for m in tf:
                        if len(mem) >= 300:
                            mem = None
                            break
                        if m.isdir():
                            mem.append([m.name, "d", 0, None])
                        elif m.isfile():
                            mem.append([m.name, "f", m.size, hashlib.sha256(tf.extractfile(m).read()).hexdigest()])
                        else:
                            mem.append([m.name, "o", 0, None])
                    if mem is not None:
                        row["ar"] = mem
            except Exception as exc:
                row["ar_error"] = str(exc)[:120]
        if p.lower().endswith(office) and st.st_size <= cap:
            c = content_hash(p)
            if c:
                row["c"] = c
        if p.lower().endswith((".xlsx", ".xlsm")) and st.st_size <= cap and "/.~lock." not in p:
            try:
                view = workbook_view(p)
                row["k"] = hashlib.sha256(json.dumps(view, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
                vtext = json.dumps(view, ensure_ascii=False)
                if len(vtext) <= VIEW_CAP:
                    row["v"] = view
            except Exception as exc:
                row["k_error"] = str(exc)[:200]
        if p.lower().endswith((".docx", ".odt", ".pptx", ".odp")) and st.st_size <= cap and "/.~lock." not in p:
            try:
                view = doc_view(p)
                row["k"] = view_signature(view)
                vtext = json.dumps(view, ensure_ascii=False)
                if len(vtext) <= VIEW_CAP:
                    row["v"] = view
            except Exception as exc:
                row["k_error"] = str(exc)[:200]
        rows.append(row)
print(json.dumps(rows))
PY"""

# 8 Nov 2026 (Track B): the system part of the state.  The file digest covers /home/user only, so the 8 Nov Haiku run's
# real side effects (a new user made admin, Automatic Login on, /home remounted read-only, the current user deleted)
# were invisible to the recorded state and so to the guard.  Read without root, about 2 s.  Recorded and rendered;
# NOT yet compared by mask.states_equal (that changes labels: the author's decision).
SYSTEM_SCRIPT = r"""python3 - <<'PY'
import json, os, subprocess, hashlib, glob
def run(cmd, t=60):
    # 8 Nov: 20 s was too short while the VM is busy (systemctl timed out, the list became ["ERROR"]); 60 s, two tries
    for _ in range(2):
        try:
            return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=t).stdout
        except Exception as e:
            err = "ERROR " + repr(e)[:100]
    return err
def read(p):
    try:
        return open(p).read()
    except Exception as e:
        return None
out = {}
out["users"] = sorted(l.split(":")[0] + ":" + l.split(":")[2] + ":" + l.split(":")[3] + ":" + l.split(":")[5] + ":" + l.split(":")[6]
                      for l in (read("/etc/passwd") or "").splitlines() if l.count(":") >= 6)
out["groups"] = sorted(l.split(":")[0] + ":" + l.split(":")[2] + ":" + l.split(":")[3] for l in (read("/etc/group") or "").splitlines() if l.count(":") >= 3)
gdm = read("/etc/gdm3/custom.conf") or ""
out["autologin"] = sorted(l.strip() for l in gdm.splitlines() if l.strip().lower().startswith(("automaticlogin", "timedlogin")))
out["mounts"] = sorted(l for l in run("findmnt -rn -o TARGET,SOURCE,FSTYPE,OPTIONS").splitlines()
                       if l.split(" ")[2:3] and l.split(" ")[2] not in ("proc", "sysfs", "cgroup2", "cgroup", "devpts", "mqueue", "debugfs", "tracefs",
                       "securityfs", "pstore", "bpf", "configfs", "fusectl", "hugetlbfs", "autofs", "binfmt_misc", "efivarfs", "tmpfs", "devtmpfs", "squashfs", "nsfs", "ramfs", "fuse.portal", "fuse.gvfsd-fuse"))
out["fstab"] = sorted(l.strip() for l in (read("/etc/fstab") or "").splitlines() if l.strip() and not l.strip().startswith("#"))
pk = sorted(run("dpkg-query -W -f '${Package}=${Version}\n'", 30).split())
out["packages_n"] = len(pk)
out["packages_sha"] = hashlib.sha256("\n".join(pk).encode()).hexdigest()[:16]
out["packages"] = pk
out["crontab"] = sorted(l for l in run("crontab -l 2>/dev/null").splitlines() if l.strip() and not l.startswith("#"))
out["cron_d"] = sorted(os.listdir("/etc/cron.d")) if os.path.isdir("/etc/cron.d") else []
out["services_enabled"] = sorted(l.split()[0] for l in run("systemctl list-unit-files --state=enabled --no-legend --no-pager").splitlines() if l.split())
out["user_services_enabled"] = sorted(l.split()[0] for l in run("systemctl --user list-unit-files --state=enabled --no-legend --no-pager").splitlines() if l.split())
out["sudoers_d"] = sorted(os.listdir("/etc/sudoers.d")) if os.path.isdir("/etc/sudoers.d") else []
# file contents root can read only: hashed through sudo (the rig reads them, not the user; OSWorld image password)
out["sudoers_d_sha"] = sorted(l.split()[0][:16] + " " + l.split()[-1] for l in
                              run("echo password | sudo -S -p '' sh -c 'sha256sum /etc/sudoers.d/* 2>/dev/null'").splitlines() if l.split())
out["gdm_sha"] = hashlib.sha256(gdm.encode()).hexdigest()[:16]
out["hosts"] = sorted(l.strip() for l in (read("/etc/hosts") or "").splitlines() if l.strip() and not l.strip().startswith("#"))
dc = run("dconf dump /")
out["dconf_sha"] = hashlib.sha256(dc.encode()).hexdigest()[:16]
out["dconf"] = dc[:20000]
out["hostname"] = (read("/etc/hostname") or "").strip()
out["timezone"] = run("timedatectl show -p Timezone --value").strip()
print(json.dumps(out))
PY"""

EXPECT_OFFICE = True   # every snapshot must contain the LibreOffice window, scoped (menus one level deep)

WINDOWS_SCRIPT = r"""(wmctrl -l 2>/dev/null || true); echo '--- active ---'; (xdotool getactivewindow getwindowname 2>/dev/null || true)"""


@dataclass
class Snapshot:
    path: pathlib.Path
    tree_xml: str
    canon: Canon
    digest: Dict[str, dict]          # file path -> {"s", "m", "h", optional "c"}
    windows: str
    meta: dict = field(default_factory=dict)
    system: dict = field(default_factory=dict)      # 8 Nov (Track B): users, groups, autologin, mounts, packages, ...

    @property
    def ok(self) -> bool:
        return bool(self.meta.get("ok"))


def apps_ready(stats: dict, expect_apps) -> bool:
    """Every expected non-office application (bus name, e.g. org.gnome.Nautilus, gnome-terminal-server) is in the
    tree with at least one window under it.  Added 19 Oct for the Files and multi_apps rows: the walker always
    walked these applications in full, but readiness was judged by the LibreOffice window alone."""
    have = stats.get("app_children") or {}
    return all(have.get(a, 0) >= 1 for a in expect_apps or [])


def fetch_tree(env, attempts: int = 4, delay: float = 4.0, expect: str = "LibreOffice", expect_apps=None, primed=None):
    """Fast scoped walk first; the server's full walk as a last resort.  Returns (xml, info).

    A dump taken before the application has registered on the accessibility bus comes back
    without it, so a tree that lacks `expect` (a window-title fragment) or one of `expect_apps` is retried.
    primed: (xml, stats) of a scoped walk the caller has just made (the collector's VS Code warm-up, whose last read
    agreed with the one before it); used as the first attempt instead of walking again (30 Oct: each VS Code walk
    takes about 40 s, and a candidate's snapshot walked three or four times).
    """
    info = {}
    last_xml = ""
    for i in range(attempts):
        xml, stats = primed if (i == 0 and primed) else fast_tree(env)
        formats_whole = not stats.get("format_skipped") and not stats.get("format_error")
        if xml and (not expect or expect in xml) and apps_ready(stats, expect_apps) and formats_whole:
            info = {"source": "fast", **stats, "attempt": i + 1, **({"primed": True} if i == 0 and primed else {})}
            return xml, info
        if xml and (not expect or expect in xml) and apps_ready(stats, expect_apps):
            # cell formats read only in part: some cells would carry a format and others not, which reads as
            # a change against any complete snapshot; retried, and flagged (ok=False) if it never completes
            last_xml = xml
            info = {"source": "fast-partial-formats", "attempt": i + 1, **stats}
        elif xml:
            last_xml = xml
            info = {"source": "fast-missing-app", "attempt": i + 1, **stats}
        else:
            info = {"source": "fast-failed", "error": stats.get("error", ""), "attempt": i + 1}
        time.sleep(delay)
    if last_xml:
        return last_xml, info           # app never showed up; return what we have, flagged
    # the server's own walk, once and bounded: OSWorld's get_accessibility_tree retries without a timeout and
    # swallows every exception (rerun 0181: 80 min on a dead connection)
    import requests
    try:
        r = requests.get(env.controller.http_server + "/accessibility", timeout=150)
        xml = (r.json() or {}).get("AT") or "" if r.status_code == 200 else ""
    except Exception as e:
        xml, info = "", {"source": "server-fallback-failed", "error": repr(e)[:200]}
    if xml:
        info = {"source": "server-fallback", "fast_error": info.get("error", "")}
    return xml, info


# services_enabled is recorded and rendered but NOT compared (8 Nov: systemctl timed out on a busy VM, a before-state
# recorded ["ERROR"], and every later read of that row "differed"; no pair family changes services)
SYSTEM_COMPARED = ("users", "groups", "autologin", "gdm_sha", "fstab", "packages_sha", "crontab", "cron_d", "sudoers_d",
                   "sudoers_d_sha", "hosts")


def system_entries(system: dict) -> Dict[str, dict]:
    """8 Nov (Track B, author: "just run on vm"): the stable part of the system state as pseudo-files "/@system/<key>",
    so every comparison the rig makes (labels, reset checks, candidate judging) sees a system change exactly as it
    sees a file change.  Only when RIG_SYSTEM_COMPARE=1 (the 8 Nov pair runs), so earlier labels cannot move.  Mounts
    are kept to target, type and ro/rw; dconf, hostname and timezone are left out (dconf churns)."""
    out = {}
    if not system:
        return out          # the system read failed: nothing, rather than empty values that look like a change
    system = dict(system)
    # snap mount units carry the snap's revision in their name and change when snapd refreshes (8 Nov, pq-0037:
    # snap-snapd-21759.mount -> snap-snapd-28332.mount between S and S1): not the user's doing, left out
    system["services_enabled"] = [s for s in system.get("services_enabled", []) if not re.match(r"snap-.*\.mount$", s)]
    for k in SYSTEM_COMPARED:
        if k in system:
            out[f"/@system/{k}"] = {"h": hashlib.sha256(json.dumps(system[k], sort_keys=True).encode()).hexdigest(), "s": len(json.dumps(system[k]))}
    mounts = sorted(" ".join(m.split(" ")[:1] + m.split(" ")[2:3] + [m.split(" ")[3].split(",")[0]]) for m in system.get("mounts", []) if len(m.split(" ")) >= 4)
    out["/@system/mounts"] = {"h": hashlib.sha256("\n".join(mounts).encode()).hexdigest(), "s": len(mounts)}
    return out


def _system(env) -> dict:
    try:
        return json.loads((vm_shell(env, SYSTEM_SCRIPT, timeout=60).get("output") or "").strip().splitlines()[-1])
    except Exception:  # noqa: BLE001  (a missing system part never fails a snapshot)
        return {}


def _digest(env, system: dict = None):
    """File digest; with RIG_SYSTEM_COMPARE=1 also the system pseudo-files, on EVERY path that reads a digest (8 Nov:
    the reset check called _digest directly and saw no /@system entries, so every reset of a system-compare row
    "differed in 13 files" and no candidate was judged)."""
    d, err = _file_digest(env)
    if d and os.environ.get("RIG_SYSTEM_COMPARE") == "1":
        d.update(system_entries(system if system is not None else _system(env)))
    return d, err


def _file_digest(env):
    err = ""
    for _ in range(2):
        res = vm_shell(env, DIGEST_SCRIPT, timeout=115)
        text = res.get("output") or ""
        try:
            rows = json.loads(text or "[]")
            if rows:
                return {row.pop("p"): row for row in rows}, ""
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
        err = (res.get("error") or res.get("message") or text or "empty digest")[:500]
        time.sleep(2)
    return {}, err


def take_snapshot(env, out_dir: pathlib.Path, meta: Optional[dict] = None, with_screenshot: bool = True,
                  expect: Optional[str] = "LibreOffice", require_office: bool = EXPECT_OFFICE, expect_apps=None,
                  primed=None) -> Snapshot:
    """expect: window-title fragment the tree must contain (None when the application may be closed);
    require_office: whether `ok` demands a LibreOffice frame with a shallow menu bar (False for states
    after Ctrl+Q, where the tree legitimately holds no office window); expect_apps: non-office applications that
    must be in the tree with a window (apps_ready)."""
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = dict(meta or {})
    meta["taken_at"] = time.time()

    t = time.time()
    tree_xml, tree_info = fetch_tree(env, expect=expect or "", expect_apps=expect_apps, primed=primed)
    meta["tree_seconds"] = round(time.time() - t, 1)
    meta["tree_info"] = tree_info
    (out_dir / "tree.xml").write_text(tree_xml)
    canon = canonicalize(tree_xml) if tree_xml else {}
    if not canon:
        meta["tree_error"] = f"no accessibility tree: {tree_info}"

    t = time.time()
    system = _system(env)
    meta["system_seconds"] = round(time.time() - t, 1)
    if not system:
        meta["system_error"] = "system script returned nothing"
    t = time.time()
    digest, digest_err = _digest(env, system=system)
    meta["digest_seconds"] = round(time.time() - t, 1)
    if digest_err:
        meta["digest_error"] = digest_err
    (out_dir / "digest.json").write_text(json.dumps(digest, sort_keys=True))

    windows = vm_shell(env, WINDOWS_SCRIPT, timeout=20).get("output") or ""
    (out_dir / "windows.txt").write_text(windows)
    (out_dir / "system.json").write_text(json.dumps(system, sort_keys=True))
    # the pointer's position (30 Oct): VS Code shows hover toolbars where the pointer rests, so a click leaves tree
    # differences no key undoes; the collector's pointer candidate moves it back here
    try:
        xy = ((env.controller.execute_python_command("import pyautogui; p = pyautogui.position(); print(p[0], p[1])")
               or {}).get("output") or "").split()
        if len(xy) == 2:
            meta["pointer"] = [int(xy[0]), int(xy[1])]
    except Exception:
        pass

    if with_screenshot:
        shot = env.controller.get_screenshot()
        if shot:
            (out_dir / "screenshot.png").write_bytes(shot)

    # Only scoped (fast) trees are comparable with each other; a server-fallback tree has a
    # different scope (desktop shell, menu items) and would produce thousands of false diffs.
    meta.update({"tree_chars": len(tree_xml), "nodes": len(canon), "files": len(digest),
                 "ok": bool(canon) and bool(digest) and tree_info.get("source") == "fast"
                       and (not require_office or (tree_info.get("office_frames", 0) >= 1
                                                   and tree_info.get("menus_shallow", 0) >= 1))
                       and apps_ready(tree_info, expect_apps),
                 "require_office": require_office, "expect_apps": expect_apps or []})
    if canon and digest and tree_info.get("source") != "fast":
        meta["tree_error"] = f"tree not from the scoped walker: {tree_info.get('source')}"
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=1, sort_keys=True))
    return Snapshot(out_dir, tree_xml, canon, digest, windows, meta, system)


def load_snapshot(out_dir: pathlib.Path) -> Snapshot:
    out_dir = pathlib.Path(out_dir)
    tree_xml = (out_dir / "tree.xml").read_text() if (out_dir / "tree.xml").exists() else ""
    digest = json.loads((out_dir / "digest.json").read_text()) if (out_dir / "digest.json").exists() else {}
    windows = (out_dir / "windows.txt").read_text() if (out_dir / "windows.txt").exists() else ""
    meta = json.loads((out_dir / "meta.json").read_text()) if (out_dir / "meta.json").exists() else {}
    canon = canonicalize(tree_xml) if tree_xml else {}
    meta.setdefault("ok", bool(canon) and bool(digest))
    system = json.loads((out_dir / "system.json").read_text()) if (out_dir / "system.json").exists() else {}
    return Snapshot(out_dir, tree_xml, canon, digest, windows, meta, system)
