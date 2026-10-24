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
Added 19 Oct 2026 after the 30-row batch and the save recheck:
  * formatting readouts: under the Formatting toolbar, the font-name and size boxes lose their text and the
    buttons lose checked/value/pressed.  Like the Name Box, they echo the cell under the cursor (Bold lit,
    Currency vs General), so an undo that put every cell back but left the cursor elsewhere was rejected
    (pilot-0079 hide_col_a: Ctrl+Z twice; recheck 0126: undo, save, redo).  Cell formats are recorded on the
    cells themselves since 18 Oct, so nothing about the document is lost.
  * selection: the `selected` flag of the sheet table and its cells, and the status-bar readouts of the selection
    ("Selected: 1,048,576 rows", Sum=...), are dropped.  The written definition given to guess B already said the
    cursor position and the selection are not state; the checker now says the same (recheck 0210: undo, save, redo
    restored file and cells, and differed only in 87 highlighted cells).
"""
import re
from typing import Dict, List
import xml.etree.ElementTree as ET

Canon = Dict[str, Dict[str, str]]
NODE = "__node__"  # pseudo-attribute meaning "the node itself exists"
# "showing" since 23 Oct: whether a widget is inside the viewport is scroll position, not state (the PDF viewer's
# links flip it as the page renders: probe-0024, a no-op, differed in one link's showing flag).  Nodes that are not
# showing outside scroll panes are dropped whole (DROP_HIDDEN below); the attribute itself is never compared.
GENERATED_ID = re.compile(r"[A-Za-z_-]\d{13,}$")   # name + epoch milliseconds + counter, XUL-generated
IGNORED_ATTRS = frozenset({"screencoord", "size", "focused", "active", "showing",
                           "explicit-name"})   # ARIA bookkeeping (whether the name came from a label); flickers on VS Code's
                                               # activity-bar tabs after an undo (v2-0041 c00/c01, 24 Oct)
ZOOM_READOUT = re.compile(r"\[(Set zoom level|Zoom)\]")
WRITER_COUNT_READOUT = re.compile(r"^[\d,]+ words?, [\d,]+ characters?( selected)?$")
# Impress and Draw status bar, 24 Oct (v2-0002, the Impress noise gate): the pointer position and the selection's size,
# "-0.96 / -0.29 0.00 x 0.00", differ between two instances with nothing done; a readout of the mouse, not state
POSITION_READOUT = re.compile(r"^-?\d+[.,]\d+ / -?\d+[.,]\d+ \d+[.,]\d+ x \d+[.,]\d+$")
# Impress/Draw status bar, 24 Oct (v2-0006 c00): "Title text 'Weekday in school'" names what is selected, a readout
OBJECT_READOUT = re.compile(r"^(Title text|Outline text|Subtitle text|Text (Frame|Box)|Image|Shape|Group object|Table|Line|Rectangle|Ellipse|Connector|Custom Shape|Picture|OLE object|\d+ objects? selected|Slide \d+ of \d+)\b")
# Toolbar enablement is derived UI state that LibreOffice refreshes asynchronously after a command.  The
# smoke test caught 2 of 20 click-spots differing on exactly these flags (Paste after a cut, Data Sources
# after a row delete) with the document identical, so they are dropped on every node under a tool-bar.
TOOLBAR_STATE_ATTRS = frozenset({"enabled", "sensitive"})
# A cell carrying any of these is content or visible formatting and is never dropped as empty.
CELL_CONTENT_ATTRS = ("text", "Formula", "Note", "TopBorder", "BottomBorder", "LeftBorder", "RightBorder", "Shadow", "format")
CURSOR_READOUT_BAR = "/tool-bar[Formula Tool Bar]"
FORMAT_READOUT_BAR = "/tool-bar[Formatting]"
FORMAT_READOUT_ATTRS = ("checked", "value", "pressed", "indeterminate")
# The definition (rig/prompts/guess_b_definition.txt) excludes the cursor position and the selection from the state.
SELECTION_TAGS = ("table", "table-cell")          # their `selected` flag is the spreadsheet selection
SIDEBAR_DECKS = frozenset({"Properties", "Styles", "Gallery", "Navigator", "Functions", "Slide Transition", "Animation",
                           "Master Slides", "Shapes", "Page", "Manage Changes", "Design"})   # LibreOffice sidebar decks (24 Oct)
SELECTION_READOUT = re.compile(r"^(Selected:|Sum\b|Average\b|Count\b|Min\b|Max\b)")   # status-bar echoes of it


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


# Rule since 21 Oct (decided with the author): widgets that are not showing on screen are not state.  GTK keeps a
# popover's widgets in the tree, hidden, after it closes (Files: "Rename File" after F2, "Folder name" after
# Ctrl+Shift+N), and their presence shifted every later path, so an undo that restored the files exactly
# (probe-0010 c00: 0 file differences) was rejected on 252 tree differences.  Application and desktop nodes
# carry no showing state and are never dropped.  Re-judged on 49 stored rows: probe-0010 and pilot-0079 flip to
# REVERSIBLE (Ctrl+Z); every Calc cell carries the showing state, so no cell content is affected.
DROP_HIDDEN = True
NEVER_HIDDEN = frozenset({"application", "desktop-frame"})
# Inside a scrolling list the showing state only says what the viewport reaches: the Files sidebar's "Other
# Locations" row was showing in one instance and not in another of the same folder (probe-0012 c04 confirm, 21 Oct:
# the window heights differed), and scroll position is not state.  Content under a scroll pane is kept whether or
# not it is scrolled into view; a closed popover's widgets sit outside any scroll pane and are still dropped.
SCROLLED = ("scroll-pane", "viewport")
# Since 22 Oct: Files' selection readout ('“a.txt” selected', '(6 bytes)', '(containing 1 item)', '3 items selected')
# is the selection, which the definition excludes, as the Calc status-bar readouts already are (probe-0014 c11)
FILES_SELECTION_READOUT = re.compile(r"^(“.*” selected|\(\d+ bytes\)|\([\d.,]+ [kMG]?B\)|\(containing \d+ items?\)|\d+ items? selected.*|\(\d+ items?\))$")


def _showing(el: ET.Element) -> bool:
    return any(_local(k) == "showing" and v == "true" for k, v in el.attrib.items())


def canonicalize(xml_text: str, ignored=IGNORED_ATTRS) -> Canon:
    root = ET.fromstring(xml_text)
    out: Canon = {}

    def record(node: ET.Element, path: str, name: str) -> None:
        attrs = {}
        for k, v in node.attrib.items():
            lk = _local(k)
            if lk in ignored:
                continue
            if lk.endswith(("_desc", "_kb")):
                continue                # accessibility action descriptions and key bindings (act:*): how a widget can
                                        # be driven, not what it shows (VS Code's panels gain them as they load, 23 Oct)
            if lk == "id" and GENERATED_ID.search(v):
                continue                # a widget id with an embedded creation timestamp ("spring17927575650161"):
                                        # Thunderbird's toolbar springs and separators are minted per window and never
                                        # match across instances (probe-0033 confirmation, 23 Oct); identity, not state
            if lk in TOOLBAR_STATE_ATTRS and "/tool-bar[" in path:
                continue
            attrs[lk] = v
        text = (node.text or "").strip()
        if text:
            attrs["text"] = text
        attrs["name"] = name
        if CURSOR_READOUT_BAR in path and _local(node.tag) in ("text", "paragraph"):
            attrs.pop("text", None)     # Name Box / Input line: echo of the cursor cell
            attrs.pop("editable", None)  # and its editable flag, which comes and goes with keyboard focus (pilot-0004
                                         # confirmations, 23 Oct: focused+active+editable on the Input line after Ctrl+Z,
                                         # gone a few seconds later); focused and active are already ignored
        if _local(node.tag) in SELECTION_TAGS or "/document-presentation[" in path:
            attrs.pop("selected", None)     # which cells, or which shapes of a slide, are highlighted is not document state
        if "/status-bar[" in path and SELECTION_READOUT.match(attrs.get("text", "")):
            attrs.pop("text", None)         # "Selected: 3 rows", "Sum=12": echoes of the selection
        if "/status-bar[" in path and "application[soffice]" in path and OBJECT_READOUT.match(attrs.get("text", "")):
            attrs.pop("text", None)         # Impress/Draw: what is selected, which slide is shown
        if "/status-bar[" in path and POSITION_READOUT.match(attrs.get("text", "")):
            attrs.pop("text", None)         # Impress/Draw: pointer position and selection size
        if "/status-bar[" in path and WRITER_COUNT_READOUT.match(attrs.get("text", "")):
            attrs.pop("text", None)         # Writer's "218 words, 1,433 characters": a lazily refreshed echo of the
                                            # document text, which is compared directly (probe-0029 c00, 23 Oct:
                                            # the text was back after Ctrl+Z, the count still said +5)
        if FORMAT_READOUT_BAR in path or ("/tool-bar[" in path and "application[soffice]" in path):
            # every LibreOffice toolbar since 24 Oct: Impress's Select and Text Box buttons light up for the mode (v2-0006 c00)
            if _local(node.tag) in ("text", "paragraph"):
                attrs.pop("text", None) # font name / size boxes: echo of the cursor cell
            for a in FORMAT_READOUT_ATTRS:
                attrs.pop(a, None)      # Bold, Currency, ...: lit for the cursor cell
        if ZOOM_READOUT.search(path):
            attrs.pop("text", None)     # the zoom box (PDF viewer "Set zoom level"): view magnification, like scroll
                                        # position, is not state (probe-0024, 23 Oct: 27% vs 100% between two instances)
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
            if tag == "label" and FILES_SELECTION_READOUT.match(name):
                continue                # the file manager's selection readout: the selection is not state
            if tag == "panel" and name in SIDEBAR_DECKS and "application[soffice]" in prefix:
                continue                # LibreOffice's sidebar deck shows the properties of whatever is selected: a
                                        # readout of the selection, 410 nodes of it when an Impress text box is
                                        # selected (v2-0006, 24 Oct); the document itself is compared directly
            if tag == "status-bar" and "LibreOffice" not in prefix:
                continue                # an editor's status bar is readouts (problems, ports, notifications, cursor
                                        # position; VS Code, 23 Oct); LibreOffice's is masked item by item by the mask run
            if DROP_HIDDEN and tag not in NEVER_HIDDEN and not _showing(child) and not any(f"/{s}[" in prefix for s in SCROLLED):
                continue                # not on screen: a closed popover's widgets, a hidden placeholder
            key = (tag, name)
            idx = counts.get(key, 0)
            counts[key] = idx + 1
            path = f"{prefix}/{tag}[{name}]#{idx}"
            record(child, path, name)
            walk(child, path)

    root_path = "/" + _local(root.tag)
    record(root, root_path, root.get("name", ""))
    walk(root, root_path)
    # unnamed fillers and panels left childless by the drops above are containers of what was dropped (the
    # file manager's selection readout sits in two nested fillers that exist only while something is selected:
    # probe-0007 c00, 22 Oct, 2 tree differences after click:Undo Trash with the files already equal)
    while True:
        empty = [p for p, a in out.items() if tag_of(p) in ("filler", "panel") and not a.get("name") and "text" not in a
                 and not any(q.startswith(p + "/") for q in out)]
        if not empty:
            break
        for p in empty:
            del out[p]
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
