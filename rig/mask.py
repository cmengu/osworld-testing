"""Noise mask: what changes on its own, so it must be ignored when two states are compared.

How it works.  Take many snapshots of the SAME nominal state (idle waits, then harmless
no-op inputs).  Anything that differs between any two of them cannot be the effect of an
action, so it is noise: a clock label, a blinking selection flag, an autosave or registry
file.  The mask is the union of those differences, generalised a little:
  * an attribute that flickers on three or more nodes of one tag (e.g. 'focused' on
    table-cell) is masked for every node of that tag;
  * a node that comes and goes is masked together with everything under it (a
    notification banner's text differs next time, the banner's place does not);
  * a place in the tree where three or more differently named nodes of one tag come and
    go under the same parent (the top-bar clock: label[11:49], label[11:50], ...) is a
    "churn site": every node of that tag under that parent is ignored, descendants too;
  * a file that flickers inside a directory with three or more flickering files masks
    the whole directory.
Files compare by (size, content hash): the modified time is never compared, and for
office files the content hash leaves the embedded metadata out (see snapshot.py).
Comparing two states = apply the mask to both, then require exact equality of the rest.
"""
import os
import re
from collections import Counter, defaultdict
from typing import Dict, List, Tuple

from .treediff import NODE, Canon, diff, tag_of

Digest = Dict[str, dict]
GENERALISE_AT = 3
# System journals inside the home directory that grow on their own and never hold document state: the X
# server log (the smoke test caught it growing by 5 KB between two replays of Save As) and the GNOME
# file-metadata journal (rewritten across VM boots).  Ignored on both sides of every comparison.  19 Oct: the
# file manager's tag database (nautilus/tags/meta.db*, .meta.isrunning), created when LibreOffice is started on a
# file after a full quit (rerun 0141 c07, c11: windows equal, these three files the only difference).
# 20 Oct: LibreOffice's whole user profile folder (registry, template-folder cache store/.templdir.cache, extension
# caches): configuration, never document state (Paper draft 3.1 exclusions); the stricter reset check of 20 Oct met
# .templdir.cache changing between two resets of probe-0003, a file the noise mask had never seen change.
# 23 Oct: Thunderbird's profile housekeeping, 8 files that change under a no-op (probe-0032): telemetry pings and
# session state (datareporting/), the instance lock, the places/storage databases and their journals, prefs.js (run
# timestamps), the add-on registry.  Mail itself (Mail/, ImapMail/, drafts, the address book) stays compared.
_TB = "/home/user/.thunderbird/t5q2a5hp.default-release/"
_TB_HOUSEKEEPING = ("datareporting/", "crashes/", "lock", ".parentlock", "places.sqlite", "storage.sqlite", "storage/",
                    "prefs.js", "extensions.json", "addons.json", "addonStartup.json.lz4", "compatibility.ini",
                    "sessionCheckpoints.json", "cookies.sqlite", "settings/", "xulstore.json",
                    "content-prefs.sqlite",   # per-site settings (zoom, spell-check language), written when a compose window closes (probe-0033 c14)
                    "folderCache.json")       # the folder pane's cache (sizes, timestamps), rewritten at every start: v2-0055/0056 rerun, 26 Oct, every reset differed on it alone
IGNORED_FILE_PREFIXES = ("/home/user/.local/share/xorg/", "/home/user/.local/share/gvfs-metadata/",
                         "/home/user/.local/share/nautilus/", "/home/user/.config/libreoffice/",
                         "/home/user/.local/share/gnome-shell/",   # the shell's notification log (21 Oct, probe-0012 c05)
                         "/home/user/.config/Code/",               # VS Code's cache, storage and logs: 56 files change under a no-op (23 Oct, probe-0026)
                         "/home/user/.vscode/argv.json",           # written by VS Code's first launch (a crash-reporter id and comments), the same housekeeping as above; 26 Oct, decided for v2-0071
                         ) + tuple(_TB + f for f in _TB_HOUSEKEEPING)  # Thunderbird's profile housekeeping (23 Oct, probe-0032), see above
# Since 25 Oct (v2-0055/0056, under the plan the author approved that day): Thunderbird's folder summary files
# (*.msf, Mork) are an index rebuilt from the mailbox, rewritten with fresh internal timestamps on every instance, so
# two replays of the same action never agree on them (v2-0055: "reset did not reproduce the after-state: Bills.msf"
# on every candidate).  The mailbox files themselves (Mail/Local Folders/Bills, Trash, Drafts) stay compared, and the
# read flag the summary carries shows in the message list in the tree.
IGNORED_FILE_SUFFIXES = (".msf",)


# Tree attributes that are never state.  19 Oct, provisional until the Files/multi_apps probe: the text of a
# gnome-terminal (its whole visible buffer, prompt, output and history).  Every typed command changes it and no
# undo brings old scrollback back, so comparing it would make every terminal action one-way by construction; what
# a command does to files is in the digest.  No Calc row has a terminal node.
IGNORED_TREE_ATTRS = {("terminal", "text")}
# Since 22 Oct: the definition says the enabled or disabled look of buttons (Undo, Redo, Forward, Back...) is not
# state; treediff already drops it inside tool-bars, and Files' header bar is not a tool-bar (probe-0014 c11: Alt+Left
# brought the folder back and left the Forward button enabled)
IGNORED_TREE_ATTRS |= {(tag, a) for tag in ("push-button", "toggle-button", "menu-item", "check-menu-item", "radio-menu-item")
                       for a in ("enabled", "sensitive")}
# Rule since 21 Oct (decided with the author): the numeric readouts of scroll bars and split panes (value, min,
# max, step) are scroll position and window geometry, not state.  Files' icon view reports them differently for
# two instances of the same folder (probe-0012 c04: Escape closed the conflict question and left a split-pane
# max 1855 vs 1803 and a scroll-bar step 105.8 vs 100.6; no cell or file ever carries them).
LAYOUT_READOUT_ATTRS = {(tag, a) for tag in ("scroll-bar", "split-pane", "scroll-pane", "viewport")
                        for a in ("value", "min", "max", "step")}
IGNORE_LAYOUT = True


def file_sig(v: dict):
    """What counts as 'the same file'.  Spreadsheets with a cell signature (k): the cells, their formats,
    hidden rows/columns and merges, whoever wrote the file (re-saving rewrites the XML, not the sheet).
    Other files: size and content hash (office files: metadata-free).
    Since 19 Oct also the permission bits (mode), the owner (u), and directories and symbolic links as entries of their own; digests
    recorded before that carry none of these, so old rows compare exactly as they did."""
    if v is None:
        return None
    if v.get("d"):
        return ("dir", v.get("mode"), v.get("u"))
    if "l" in v:
        return ("link", v["l"])
    if isinstance(v.get("v"), dict) and ("slides" in v["v"] or "body" in v["v"]):
        from .officesig import view_signature        # a document view: signed under the current normaliser (24 Oct)
        return ("doc", view_signature(v["v"]), v.get("mode"), v.get("u"))
    if v.get("k"):
        return ("cells", v["k"], v.get("mode"), v.get("u"))
    return (v.get("s"), v.get("c") or v.get("h"), v.get("mode"), v.get("u"))


def _is_lock(path: str) -> bool:
    """A LibreOffice lock file (.~lock.<document>#) holds user, host and a timestamp: its presence says
    a document is open, its bytes change on every launch.  Lock files compare by presence only."""
    name = os.path.basename(path)
    return name.startswith(".~lock.") and name.endswith("#")


def _fsig(path: str, v: dict):
    if v is None:
        return None
    return ("lock",) if _is_lock(path) else file_sig(v)


def _parent_and_tag(path: str) -> Tuple[str, str]:
    parent, last = path.rsplit("/", 1)
    return parent, last.split("[", 1)[0]


def _pairs_within_groups(items, groups):
    """Comparisons: each item against the first of its group and against its predecessor."""
    by_group = defaultdict(list)
    for item, g in zip(items, groups or [None] * len(items)):
        by_group[g].append(item)
    out = []
    for members in by_group.values():
        out += [(members[0], m) for m in members[1:]] + list(zip(members[1:], members[2:]))
    return out


def build_mask(canons: List[Canon], digests: List[Digest], groups=None) -> dict:
    """groups: optional label per snapshot (idle / noop / restart).  Differences are only
    collected between snapshots of the same group, so a different launch regime is not
    mistaken for noise."""
    assert len(canons) >= 2, "need at least two snapshots of the same state"
    pair_hits: Counter = Counter()                                   # (path, attr) -> count
    attr_paths: Dict[Tuple[str, str], set] = defaultdict(set)         # (tag, attr) -> paths
    churn_paths: Dict[Tuple[str, str], set] = defaultdict(set)        # (parent, tag) -> churned node paths
    comparisons = _pairs_within_groups(canons, groups)
    for a, b in comparisons:
        for d in diff(a, b):
            key = (d["path"], d["attr"])
            pair_hits[key] += 1
            if d["attr"] == NODE:
                churn_paths[_parent_and_tag(d["path"])].add(d["path"])
            else:
                attr_paths[(tag_of(d["path"]), d["attr"])].add(d["path"])

    attr_by_tag: Dict[str, List[str]] = defaultdict(list)
    for (tag, attr), paths in attr_paths.items():
        if len(paths) >= GENERALISE_AT:
            attr_by_tag[tag].append(attr)
    churn_sites = sorted(f"{parent}\t{tag}" for (parent, tag), paths in churn_paths.items()
                         if len(paths) >= GENERALISE_AT and parent.count("/") > 1)   # never at the root
    pairs = sorted({f"{p}\t{a}" for (p, a) in pair_hits})

    file_hits: Counter = Counter()
    fcomparisons = _pairs_within_groups(digests, groups)
    for a, b in fcomparisons:
        for p in set(a) | set(b):
            if p.startswith(IGNORED_FILE_PREFIXES):
                continue
            if _fsig(p, a.get(p)) != _fsig(p, b.get(p)):
                file_hits[p] += 1
    dir_counts: Counter = Counter(os.path.dirname(p) for p in file_hits)
    file_dirs = sorted(d for d, n in dir_counts.items() if n >= GENERALISE_AT)
    file_paths = sorted(p for p in file_hits if os.path.dirname(p) not in file_dirs)

    return {
        "samples": len(canons),
        "tree_pairs": pairs,
        "tree_attr_by_tag": {t: sorted(a) for t, a in sorted(attr_by_tag.items())},
        "tree_churn_sites": churn_sites,
        "file_paths": file_paths,
        "file_dirs": file_dirs,
        "stats": {
            "tree_pair_count": len(pairs),
            "tree_attrs_generalised": sum(len(v) for v in attr_by_tag.values()),
            "tree_churn_sites": len(churn_sites),
            "file_path_count": len(file_paths),
            "file_dir_count": len(file_dirs),
        },
    }


def _dropped_prefixes(canon: Canon, mask: dict) -> tuple:
    """Node paths (with trailing '/') whose whole subtree is ignored."""
    prefixes = set()
    for pair in mask.get("tree_pairs", []):
        path, attr = pair.rsplit("\t", 1)
        if attr == NODE:
            prefixes.add(path + "/")
    sites = set(mask.get("tree_churn_sites", []))
    if sites:
        for path in canon:
            parent, tag = _parent_and_tag(path)
            if f"{parent}\t{tag}" in sites:
                prefixes.add(path + "/")
    return tuple(sorted(prefixes))


def apply_tree_mask(canon: Canon, mask: dict) -> Canon:
    masked_pairs = set(mask.get("tree_pairs", []))
    attr_by_tag = {t: set(a) for t, a in mask.get("tree_attr_by_tag", {}).items()}
    prefixes = _dropped_prefixes(canon, mask)
    out: Canon = {}
    for path, attrs in canon.items():
        if prefixes and (path + "/").startswith(prefixes):
            continue
        tag = tag_of(path)
        kept = {}
        for attr, val in attrs.items():
            if f"{path}\t{attr}" in masked_pairs:
                continue
            if attr in attr_by_tag.get(tag, ()):
                continue
            if (tag, attr) in IGNORED_TREE_ATTRS:
                continue
            if IGNORE_LAYOUT and (tag, attr) in LAYOUT_READOUT_ATTRS:
                continue
            kept[attr] = val
        out[path] = kept
    return out


def apply_file_mask(digest: Digest, mask: dict) -> Digest:
    masked_paths = set(mask.get("file_paths", []))
    masked_dirs = tuple(d.rstrip("/") + "/" for d in mask.get("file_dirs", []))
    return {p: v for p, v in digest.items()
            if p not in masked_paths and not p.startswith(masked_dirs) and not p.startswith(IGNORED_FILE_PREFIXES)
            and not (p.startswith(_TB) and p.endswith(IGNORED_FILE_SUFFIXES))}


_CELL = re.compile(r"(.*/table\[[^\]]*\]#\d+)/table-cell\[([A-Z]+)(\d+)\]#\d+$")


def _col(letters: str) -> int:
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n


def _visible_boxes(canon: Canon) -> Dict[str, Tuple[int, int, int, int]]:
    """Per spreadsheet table, the (min row, max row, min col, max col) of the cells the tree shows."""
    box: Dict[str, List[int]] = {}
    for path in canon:
        m = _CELL.match(path)
        if not m:
            continue
        t, r, c = m.group(1), int(m.group(3)), _col(m.group(2))
        b = box.setdefault(t, [r, r, c, c])
        b[0], b[1], b[2], b[3] = min(b[0], r), max(b[1], r), min(b[2], c), max(b[3], c)
    return {t: tuple(b) for t, b in box.items()}


def drop_viewport_cells(tree_diffs: List[dict], a_canon: Canon, b_canon: Canon) -> List[dict]:
    """Rule since 25 Oct (v2-0089, under the plan the author approved that day): a sheet cell present in one state
    only, outside the range of cells the other state shows, is a viewport difference, not state.  The tree shows the
    cells in view; after Ctrl+Z restored a deleted column the view reached row 45 instead of 37, so rows 38-45 (real
    data, unchanged in the file) appeared as 23 new nodes.  A cell inside the other state's visible range still
    counts, so a deleted or emptied cell in view is still caught."""
    boxes = (_visible_boxes(a_canon), _visible_boxes(b_canon))
    out = []
    for d in tree_diffs:
        m = _CELL.match(d["path"]) if d["attr"] == NODE else None
        if m:
            other = boxes[0] if d["old"] is None else boxes[1]      # the state that lacks the node
            box = other.get(m.group(1))
            r, c = int(m.group(3)), _col(m.group(2))
            if box and not (box[0] <= r <= box[1] and box[2] <= c <= box[3]):
                continue
        out.append(d)
    return out


def states_equal(a_canon: Canon, a_digest: Digest, b_canon: Canon, b_digest: Digest, mask: dict):
    """(equal?, tree differences, file differences) after masking."""
    ma, mb = apply_tree_mask(a_canon, mask), apply_tree_mask(b_canon, mask)
    tree_diffs = drop_viewport_cells(diff(ma, mb), ma, mb)
    fa, fb = apply_file_mask(a_digest, mask), apply_file_mask(b_digest, mask)
    file_diffs = sorted(p for p in set(fa) | set(fb) if _fsig(p, fa.get(p)) != _fsig(p, fb.get(p)))
    return (not tree_diffs and not file_diffs), tree_diffs, file_diffs


def describe(mask: dict, limit: int = 12) -> str:
    s = mask["stats"]
    lines = [
        f"mask from {mask['samples']} snapshots: {s['tree_pair_count']} exact tree pairs, "
        f"{s['tree_attrs_generalised']} tag-wide attributes, {s.get('tree_churn_sites', 0)} churn sites, "
        f"{s['file_path_count']} files, {s['file_dir_count']} directories",
    ]
    for tag, attrs in list(mask["tree_attr_by_tag"].items())[:limit]:
        lines.append(f"  tag {tag}: {', '.join(attrs)}")
    for site in mask.get("tree_churn_sites", [])[:limit]:
        parent, tag = site.split("\t")
        lines.append(f"  churn {tag} under ...{parent[-70:]}")
    for p in mask["file_paths"][:limit]:
        lines.append(f"  file {p}")
    for d in mask["file_dirs"][:limit]:
        lines.append(f"  dir  {d}/")
    return "\n".join(lines)
