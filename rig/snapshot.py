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
import json
import pathlib
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
import os, hashlib, json, zipfile
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

    @property
    def ok(self) -> bool:
        return bool(self.meta.get("ok"))


def apps_ready(stats: dict, expect_apps) -> bool:
    """Every expected non-office application (bus name, e.g. org.gnome.Nautilus, gnome-terminal-server) is in the
    tree with at least one window under it.  Added 19 Oct for the Files and multi_apps rows: the walker always
    walked these applications in full, but readiness was judged by the LibreOffice window alone."""
    have = stats.get("app_children") or {}
    return all(have.get(a, 0) >= 1 for a in expect_apps or [])


def fetch_tree(env, attempts: int = 4, delay: float = 4.0, expect: str = "LibreOffice", expect_apps=None):
    """Fast scoped walk first; the server's full walk as a last resort.  Returns (xml, info).

    A dump taken before the application has registered on the accessibility bus comes back
    without it, so a tree that lacks `expect` (a window-title fragment) or one of `expect_apps` is retried.
    """
    info = {}
    last_xml = ""
    for i in range(attempts):
        xml, stats = fast_tree(env)
        formats_whole = not stats.get("format_skipped") and not stats.get("format_error")
        if xml and (not expect or expect in xml) and apps_ready(stats, expect_apps) and formats_whole:
            info = {"source": "fast", **stats, "attempt": i + 1}
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


def _digest(env):
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
                  expect: Optional[str] = "LibreOffice", require_office: bool = EXPECT_OFFICE, expect_apps=None) -> Snapshot:
    """expect: window-title fragment the tree must contain (None when the application may be closed);
    require_office: whether `ok` demands a LibreOffice frame with a shallow menu bar (False for states
    after Ctrl+Q, where the tree legitimately holds no office window); expect_apps: non-office applications that
    must be in the tree with a window (apps_ready)."""
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = dict(meta or {})
    meta["taken_at"] = time.time()

    t = time.time()
    tree_xml, tree_info = fetch_tree(env, expect=expect or "", expect_apps=expect_apps)
    meta["tree_seconds"] = round(time.time() - t, 1)
    meta["tree_info"] = tree_info
    (out_dir / "tree.xml").write_text(tree_xml)
    canon = canonicalize(tree_xml) if tree_xml else {}
    if not canon:
        meta["tree_error"] = f"no accessibility tree: {tree_info}"

    t = time.time()
    digest, digest_err = _digest(env)
    meta["digest_seconds"] = round(time.time() - t, 1)
    if digest_err:
        meta["digest_error"] = digest_err
    (out_dir / "digest.json").write_text(json.dumps(digest, sort_keys=True))

    windows = vm_shell(env, WINDOWS_SCRIPT, timeout=20).get("output") or ""
    (out_dir / "windows.txt").write_text(windows)

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
    return Snapshot(out_dir, tree_xml, canon, digest, windows, meta)


def load_snapshot(out_dir: pathlib.Path) -> Snapshot:
    out_dir = pathlib.Path(out_dir)
    tree_xml = (out_dir / "tree.xml").read_text() if (out_dir / "tree.xml").exists() else ""
    digest = json.loads((out_dir / "digest.json").read_text()) if (out_dir / "digest.json").exists() else {}
    windows = (out_dir / "windows.txt").read_text() if (out_dir / "windows.txt").exists() else ""
    meta = json.loads((out_dir / "meta.json").read_text()) if (out_dir / "meta.json").exists() else {}
    canon = canonicalize(tree_xml) if tree_xml else {}
    meta.setdefault("ok", bool(canon) and bool(digest))
    return Snapshot(out_dir, tree_xml, canon, digest, windows, meta)
