"""Scoped, robust accessibility dump.

The VM server's /accessibility route walks the whole desktop and silently drops subtrees
when a query fails mid-walk: its node builder crashes on a widget whose attribute query
returns None, and the parent's loop then stops at that child, dropping every later sibling
too (that is how a replay once came back with no LibreOffice at all).  This runs the
server's own node builder inside the VM, so the XML dialect is identical, with three
changes:
  * the attribute query is made None-safe before the walk, so that crash cannot happen;
  * the desktop shell's internals (gnome-shell, gjs) are not walked: they are huge, change
    on their own, and are not part of the state we compare.  Their application nodes stay
    in the tree, childless; the window list is recorded separately by the recorder;
  * LibreOffice's menu bars are recorded one level deep (the menu names) instead of their
    ~1,200 menu items, which are static definitions, not state.  Container levels above
    them are mirrored node by node; every other subtree is delegated to the builder, so the
    Calc table handling and the rest of the output are the server's own.
LibreOffice is recognised by its window titles, not its application name, which the
accessibility bus reports inconsistently right after launch.  Everything is walked
serially: parallel queries into one application made the accessibility bridge return
truncated subtrees.  A node whose query still fails is dropped as the server drops it, but
counted in stats['dropped'].  The XML is written to a file inside the VM and fetched with
the server's /file route.
"""
import json

from .vm import vm_shell

TREE_PATH = "/tmp/rig_tree.xml"

FAST_TREE_SCRIPT = r"""pkill -f '^python3 - RIG_TREE_WALKER$' 2>/dev/null; exec python3 - RIG_TREE_WALKER <<'PY' 2>&1
import sys, time, json, logging, traceback, signal, os
logging.disable(logging.CRITICAL)
sys.path.insert(0, "/home/user/server")
def _too_slow(signum, frame):
    print("__ERR__walker exceeded 105 s and stopped itself")
    sys.stdout.flush()
    os._exit(3)
signal.signal(signal.SIGALRM, _too_slow)
signal.alarm(105)                       # stay under the server's 120 s limit, never linger
try:
    import main as srv                  # the VM's own server module; importing does not start Flask
    import pyatspi, lxml.etree
    logging.disable(logging.CRITICAL)
    t0 = time.time()
    try:
        srv.libreoffice_version_tuple = srv._get_libreoffice_version()
    except Exception:
        srv.libreoffice_version_tuple = (7, 3)
    MAXD = srv.MAX_DEPTH
    SKIP_APPS = {"gnome-shell", "gjs"}
    CONTAINERS = {"frame", "panel", "root pane", "layered pane", "split pane", "scroll pane", "filler", "viewport", "tool bar"}
    stats = {"apps": [], "office_frames": 0, "skipped": 0, "dropped": 0, "none_attrs": 0, "menus_shallow": 0}

    desktop = pyatspi.Registry.getDesktop(0)
    AccCls = type(desktop)
    _orig_get_attributes = AccCls.get_attributes
    def _safe_get_attributes(self):
        try:
            v = _orig_get_attributes(self)
        except Exception:
            v = None
        if v is None:
            stats["none_attrs"] += 1
            return {}
        return v
    AccCls.get_attributes = _safe_get_attributes

    def build(node, depth):
        try:
            return srv._create_atspi_node(node, depth)
        except Exception:
            stats["dropped"] += 1
            return None

    def shallow(node):
        return build(node, MAXD)        # attributes only, no children

    def kids(node):
        try:
            return list(node)[: srv.MAX_WIDTH]
        except Exception:
            return []

    def name_of(node):
        try:
            return node.name or ""
        except Exception:
            return ""

    def role(node):
        try:
            return node.getRoleName().strip()
        except Exception:
            return ""

    import subprocess
    try:
        office_pids = set(int(x) for x in subprocess.run(["pgrep", "-f", "soffice"], capture_output=True, text=True).stdout.split())
    except Exception:
        office_pids = set()

    def pid_of(node):
        try:
            return int(node.get_process_id())
        except Exception:
            return -1

    def walk_office(node, depth):
        r = role(node)
        if r == "menu bar":
            mb = shallow(node)
            if mb is None:
                return None
            for menu in kids(node):             # menu names only, not their items
                m = shallow(menu)
                if m is not None:
                    mb.append(m)
            stats["menus_shallow"] += 1
            return mb
        if depth > 8 or r not in CONTAINERS:
            return build(node, depth)           # whole subtree by the server's builder
        el = shallow(node)
        if el is None:
            return None
        for ch in kids(node):
            c = walk_office(ch, depth + 1)
            if c is not None:
                el.append(c)
        return el

    root = lxml.etree.Element("desktop-frame", nsmap=srv._accessibility_ns_map_ubuntu)
    for app in desktop:
        name = name_of(app)
        frames = kids(app)
        is_office = pid_of(app) in office_pids or any("LibreOffice" in name_of(f) for f in frames)
        stats["apps"].append(name + ("*" if is_office else ""))
        if name in SKIP_APPS:
            el = shallow(app)
            if el is not None:
                root.append(el)
            stats["skipped"] += 1
        elif is_office:
            app_el = shallow(app)
            if app_el is None:
                continue
            if not name:
                app_el.set("name", "soffice")   # the bus reports no name right after launch
            for frame in frames:
                fe = walk_office(frame, 2)
                if fe is not None:
                    app_el.append(fe)
                    stats["office_frames"] += 1
            root.append(app_el)
        else:
            el = build(app, 1)
            if el is not None:
                root.append(el)
    xml = lxml.etree.tostring(root, encoding="unicode")
    with open("%s", "w") as fh:
        fh.write(xml)
    stats["seconds"] = round(time.time() - t0, 1)
    stats["chars"] = len(xml)
    print("__TREE__" + json.dumps(stats))
except Exception:
    print("__ERR__" + traceback.format_exc()[-3000:])
PY""" % TREE_PATH


def fast_tree(env, timeout: int = 110):
    """Returns (xml_text, stats).  xml_text is '' on failure, with the reason in stats['error']."""
    res = vm_shell(env, FAST_TREE_SCRIPT, timeout=timeout)
    out = res.get("output") or ""
    marker = out.rfind("__TREE__")
    if marker < 0:
        err = out[out.rfind("__ERR__"):] if "__ERR__" in out else (res.get("error") or res.get("message") or out)
        return "", {"error": err[-3000:]}
    try:
        stats = json.loads(out[marker + len("__TREE__"):].strip().splitlines()[0])
    except (json.JSONDecodeError, IndexError):
        stats = {}
    data = env.controller.get_file(TREE_PATH)
    if not data:
        return "", {"error": "tree file could not be fetched", **stats}
    return data.decode("utf-8", errors="replace"), stats
