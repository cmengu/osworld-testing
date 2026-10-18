"""Deterministic accessibility-tree canonicaliser and differ.

A tree becomes a flat mapping  path -> {attribute: value}.  The path of a node is its
chain of (tag, name, index-among-same-tag-and-name siblings), so two trees of the same
window can be compared attribute by attribute.  Namespaces are stripped from tags and
attribute names (OSWorld's tree uses several).

Pixel geometry (screencoord, size) and keyboard-focus flags (focused, active) are dropped
at this stage: the state we care about is content and structure, and both of those
attribute groups were measured to move between identical fresh starts.  Two kinds of node are
dropped as well: childless defunct nodes (dead registrations of a killed process that the bus
removes a little later; a defunct node that still has children is kept) and childless application nodes (placeholders for applications the scoped walker
never descends into: they carry a name and nothing else, and they come and go between identical
fresh starts, so a snapshot taken 40 s later would differ by them alone).  Toolbar buttons keep their
names and values but lose their enabled/sensitive flags (see TOOLBAR_STATE_ATTRS).

Four rules added on 18 Oct 2026 after the ten-row measurement (logged in rig/out/pilot_run/rules_log.md):
  * empty cells: a table-cell with no text, formula, note, border, shadow or non-plain format is dropped.  Which empty cells the
    accessibility table exposes depends on the viewport, not on the document (one to three extra rows of them
    appeared after an undo, same window and scroll).
  * cursor readouts: the Name Box and Input line (Formula Tool Bar) lose their text.  They echo the cell under
    the cursor, so they say where the cursor is, not what the document holds.
  * empty unnamed panels: a childless panel with no name and no text is dropped before siblings are numbered.
    A document reopened from the Start Center keeps such leftovers in front of its content panels, which
    shifted every path (pilot-0131, 766 differences, identical content).  Dropping them, instead of erasing
    the index, keeps every remaining path unique.
  * nameless non-office applications are not walked (the recorder's own scope fix of 17 Oct, applied here too
    so rows recorded before it compare the same way).
"""
from typing import Dict, List
import xml.etree.ElementTree as ET

Canon = Dict[str, Dict[str, str]]
NODE = "__node__"  # pseudo-attribute meaning "the node itself exists"
IGNORED_ATTRS = frozenset({"screencoord", "size", "focused", "active"})
# Toolbar enablement is derived UI state that LibreOffice refreshes asynchronously after a command.  The
# smoke test caught 2 of 20 click-spots differing on exactly these flags (Paste after a cut, Data Sources
# after a row delete) with the document identical, so they are dropped on every node under a tool-bar.
TOOLBAR_STATE_ATTRS = frozenset({"enabled", "sensitive"})
# A cell carrying any of these is content or visible formatting and is never dropped as empty.
CELL_CONTENT_ATTRS = ("text", "Formula", "Note", "TopBorder", "BottomBorder", "LeftBorder", "RightBorder", "Shadow", "format")
CURSOR_READOUT_BAR = "/tool-bar[Formula Tool Bar]"


def _local(name: str) -> str:
    return name.split("}", 1)[1] if name.startswith("{") else name


def _defunct(el: ET.Element) -> bool:
    return any(_local(k) == "defunct" and v == "true" for k, v in el.attrib.items())


def _office_app(el: ET.Element) -> bool:
    """An application node whose top-level window is a LibreOffice window."""
    return any("LibreOffice" in (w.get("name") or "") for w in list(el))


def _empty_cell(el: ET.Element) -> bool:
    if len(el) or (el.text or "").strip():
        return False
    attrs = {_local(k): v for k, v in el.attrib.items()}
    return not any(attrs.get(a) for a in CELL_CONTENT_ATTRS[1:])


def canonicalize(xml_text: str, ignored=IGNORED_ATTRS) -> Canon:
    root = ET.fromstring(xml_text)
    out: Canon = {}

    def record(node: ET.Element, path: str, name: str) -> None:
        attrs = {}
        for k, v in node.attrib.items():
            lk = _local(k)
            if lk in ignored:
                continue
            if lk in TOOLBAR_STATE_ATTRS and "/tool-bar[" in path:
                continue
            attrs[lk] = v
        text = (node.text or "").strip()
        if text:
            attrs["text"] = text
        attrs["name"] = name
        if CURSOR_READOUT_BAR in path and _local(node.tag) in ("text", "paragraph"):
            attrs.pop("text", None)     # Name Box / Input line: echo of the cursor cell
        out[path] = attrs

    def walk(node: ET.Element, prefix: str) -> None:
        counts: Dict[tuple, int] = {}
        for child in list(node):
            tag = _local(child.tag)
            name = child.get("name", "")
            if tag == "application" and not name and _office_app(child):
                name = "soffice"        # the accessibility bus reports no name right after launch
            if _defunct(child) and len(child) == 0:
                continue                # dead, childless registration of a killed process, gone a little later
            if tag == "application" and len(child) == 0:
                continue                # placeholder for an app the walker never enters: name only
            if tag == "application" and not name:
                continue                # nameless non-office application (gnome-shell through a naming gap)
            if tag == "panel" and not name and len(child) == 0 and not (child.text or "").strip():
                continue                # empty unnamed panel: Start Center leftovers sit in front of content
            if tag == "table-cell" and _empty_cell(child):
                continue                # viewport placeholder: no content, no formatting
            key = (tag, name)
            idx = counts.get(key, 0)
            counts[key] = idx + 1
            path = f"{prefix}/{tag}[{name}]#{idx}"
            record(child, path, name)
            walk(child, path)

    root_path = "/" + _local(root.tag)
    record(root, root_path, root.get("name", ""))
    walk(root, root_path)
    return out


def tag_of(path: str) -> str:
    """The tag of the last path component: '/a[x]#0/table-cell[B2]#3' -> 'table-cell'."""
    last = path.rsplit("/", 1)[-1]
    return last.split("[", 1)[0]


def diff(a: Canon, b: Canon) -> List[dict]:
    """Every (path, attribute) that differs between two canonical trees."""
    out: List[dict] = []
    for path in sorted(set(a) | set(b)):
        if path not in a:
            out.append({"path": path, "attr": NODE, "old": None, "new": "present"})
            continue
        if path not in b:
            out.append({"path": path, "attr": NODE, "old": "present", "new": None})
            continue
        aa, bb = a[path], b[path]
        for attr in sorted(set(aa) | set(bb)):
            if aa.get(attr) != bb.get(attr):
                out.append({"path": path, "attr": attr, "old": aa.get(attr), "new": bb.get(attr)})
    return out


def summarize(diffs: List[dict], limit: int = 15) -> str:
    lines = [f"{len(diffs)} differences"]
    for d in diffs[:limit]:
        lines.append(f"  {d['path']} :: {d['attr']}: {d['old']!r} -> {d['new']!r}")
    if len(diffs) > limit:
        lines.append(f"  ... {len(diffs) - limit} more")
    return "\n".join(lines)
