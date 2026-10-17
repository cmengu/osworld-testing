"""Recorder: capture the machine state after an action.

One snapshot = accessibility tree (what the interface says) + file digest (what the disk
says; a deleted file never appears in the tree) + window list + screenshot (for humans).
Everything is written to a directory so a run can be audited and re-compared later.

The tree comes from rig.fasttree (scoped, parallel, errors reported) with the server's own
walk as a fallback.  File digest fields per path: s = size, m = mtime (recorded, never
compared), h = sha256 of the bytes, c = content hash for zip-based office files with the
metadata parts left out, so a re-save that only refreshes embedded timestamps compares
equal.  Equality in mask.py uses (s, c or h).
"""
import json
import pathlib
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

from .fasttree import fast_tree
from .treediff import Canon, canonicalize
from .vm import vm_shell

DIGEST_SCRIPT = r"""python3 - <<'PY'
import os, hashlib, json, zipfile
home = os.path.expanduser("~")
skip = ("/.cache/", "/.local/share/Trash/", "/.mozilla/", "/.config/google-chrome/",
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
    for f in files:
        p = os.path.join(root, f)
        try:
            st = os.lstat(p)
        except OSError:
            continue
        if os.path.islink(p) or not os.path.isfile(p):
            continue
        h = None
        if st.st_size <= cap:
            try:
                with open(p, "rb") as fh:
                    h = hashlib.sha256(fh.read()).hexdigest()
            except OSError:
                h = None
        row = {"p": p, "s": st.st_size, "m": st.st_mtime_ns, "h": h}
        if p.lower().endswith(office) and st.st_size <= cap:
            c = content_hash(p)
            if c:
                row["c"] = c
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


def fetch_tree(env, attempts: int = 4, delay: float = 4.0, expect: str = "LibreOffice"):
    """Fast scoped walk first; the server's full walk as a last resort.  Returns (xml, info).

    A dump taken before the application has registered on the accessibility bus comes back
    without it, so a tree that lacks `expect` (a window-title fragment) is retried.
    """
    info = {}
    last_xml = ""
    for i in range(attempts):
        xml, stats = fast_tree(env)
        if xml and (not expect or expect in xml):
            info = {"source": "fast", **stats, "attempt": i + 1}
            return xml, info
        if xml:
            last_xml = xml
            info = {"source": "fast-missing-app", "attempt": i + 1, **stats}
        else:
            info = {"source": "fast-failed", "error": stats.get("error", ""), "attempt": i + 1}
        time.sleep(delay)
    if last_xml:
        return last_xml, info           # app never showed up; return what we have, flagged
    xml = env.controller.get_accessibility_tree() or ""
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


def take_snapshot(env, out_dir: pathlib.Path, meta: Optional[dict] = None, with_screenshot: bool = True) -> Snapshot:
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = dict(meta or {})
    meta["taken_at"] = time.time()

    t = time.time()
    tree_xml, tree_info = fetch_tree(env)
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
                       and (not EXPECT_OFFICE or (tree_info.get("office_frames", 0) >= 1
                                                  and tree_info.get("menus_shallow", 0) >= 1))})
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
