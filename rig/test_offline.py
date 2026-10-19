"""Offline checks of the canonicaliser, differ and mask on the real Calc tree from the probe."""
import json
import pathlib
import sys
import xml.etree.ElementTree as ET

BASE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
from rig.mask import build_mask, describe, states_equal  # noqa: E402
from rig.treediff import NODE, canonicalize, diff, tag_of  # noqa: E402

xml_text = (BASE / "calc-tree" / "tree_raw.xml").read_text()
A = canonicalize(xml_text)
cells = [p for p in A if tag_of(p) == "table-cell"]
print(f"nodes={len(A)} table-cells={len(cells)}")
raw_cells = [e for e in ET.fromstring(xml_text).iter() if e.tag.rsplit("}", 1)[-1] == "table-cell"]
assert len(A) > 800 and len(raw_cells) > 500 and 20 < len(cells) < len(raw_cells)   # empty cells are dropped

# identical input -> identical canonical form, zero differences
assert canonicalize(xml_text) == A and diff(A, A) == []
# geometry and focus never reach the canonical form
assert not any(k in ("screencoord", "size", "focused", "active") for v in A.values() for k in v)


def local(tag):
    return tag.split("}", 1)[1] if tag.startswith("{") else tag


def variant(mutator):
    root = ET.fromstring(xml_text)
    mutator(root)
    return canonicalize(ET.tostring(root, encoding="unicode"))


def nth_cell(root, n):
    """n-th cell that carries text (empty cells are dropped by the canonicaliser)."""
    return [e for e in root.iter() if local(e.tag) == "table-cell" and (e.text or "").strip()][n]


def nth_empty_cell(root, n):
    return [e for e in root.iter() if local(e.tag) == "table-cell" and not (e.text or "").strip()][n]


def first_label(root):
    return next(e for e in root.iter() if local(e.tag) == "label")


def add_banner(root, text):
    """A notification-like subtree hanging off the root, as GNOME shows for a banner."""
    n = ET.SubElement(root, "notification")
    p = ET.SubElement(n, "panel")
    lab = ET.SubElement(p, "label")
    lab.set("name", text)


# Focus and geometry changes are invisible after canonicalisation.
F = variant(lambda root: (nth_cell(root, 3).set("focused", "true"), nth_cell(root, 4).set("screencoord", "(1, 1)")))
assert F == A

# Noise samples: a synthetic 'expanded' flag wandering over cells, a clock-like label whose
# NAME changes every sample (a churn site), and a banner that shows in one sample only.
noise = [A]
for k in range(1, 6):
    def mut(root, k=k):
        nth_cell(root, k).set("expanded", "true")
        first_label(root).set("name", f"Oct 16 12:{k:02d}")
        if k == 2:
            add_banner(root, "Updates available")
    noise.append(variant(mut))

XLSX = "/home/user/Desktop/hours.xlsx"


# Digests: one real-looking file set; the registry file and three cache files flicker.
def digest(i):
    d = {
        XLSX: {"s": 9000, "m": 1, "h": "bytes-v1", "c": "content-v1"},
        "/home/user/.config/libreoffice/4/user/registrymodifications.xcu": {"s": 100 + i, "m": i, "h": f"x{i}"},
    }
    for j in range(3):
        d[f"/home/user/.config/libreoffice/4/user/uno_packages/cache/f{j}"] = {"s": j, "m": i, "h": f"c{i}{j}"}
    return d


digests = [digest(i) for i in range(len(noise))]
mask = build_mask(noise, digests)
print(describe(mask))
assert "expanded" in mask["tree_attr_by_tag"].get("table-cell", []), mask["tree_attr_by_tag"]
assert mask["tree_churn_sites"], "the renamed label must become a churn site"
assert "/home/user/.config/libreoffice/4/user/registrymodifications.xcu" in mask["file_paths"]
assert "/home/user/.config/libreoffice/4/user/uno_packages/cache" in mask["file_dirs"]
assert XLSX not in mask["file_paths"]

# Pure noise must compare equal after masking: a never-seen flagged cell, a never-seen clock
# value, and a banner with never-seen text (its subtree is dropped wholesale).
B = variant(lambda root: (nth_cell(root, 15).set("expanded", "true"),
                          first_label(root).set("name", "Oct 16 12:59"),
                          add_banner(root, "Battery low")))
eq, td, fd = states_equal(A, digests[0], B, digests[1], mask)
assert eq, (td[:3], fd[:3])

# ... a real content change must not.
C = variant(lambda root: nth_cell(root, 10).set("name", "CHANGED"))
eq, td, fd = states_equal(A, digests[0], C, digests[0], mask)
assert not eq and td, "content change must survive the mask"
assert all(d["attr"] in (NODE, "name") for d in td), td[:3]

# A re-saved spreadsheet: new mtime and new raw bytes but identical content hash -> equal.
d_resaved = dict(digests[0])
d_resaved[XLSX] = {"s": 9000, "m": 99, "h": "bytes-v2", "c": "content-v1"}
eq, td, fd = states_equal(A, digests[0], A, d_resaved, mask)
assert eq, fd

# ... a changed document (new content hash) is caught ...
d_changed = dict(digests[0])
d_changed[XLSX] = {"s": 9001, "m": 2, "h": "bytes-v3", "c": "content-v2"}
eq, td, fd = states_equal(A, digests[0], A, d_changed, mask)
assert not eq and fd == [XLSX], fd

# ... a plain file is compared by raw hash, mtime ignored ...
plain = "/home/user/Desktop/notes.txt"
d_a = dict(digests[0]); d_a[plain] = {"s": 10, "m": 1, "h": "p1"}
d_b = dict(digests[0]); d_b[plain] = {"s": 10, "m": 2, "h": "p1"}
assert states_equal(A, d_a, A, d_b, mask)[0]
d_b[plain] = {"s": 10, "m": 2, "h": "p2"}
assert not states_equal(A, d_a, A, d_b, mask)[0]

# ... and a deleted file is caught by the digest even though the tree is unchanged.
d_deleted = {p: v for p, v in digests[0].items() if p != XLSX}
eq, td, fd = states_equal(A, digests[0], A, d_deleted, mask)
assert not eq and fd == [XLSX], fd

# --- the four rules of 18 Oct 2026 ---
# An empty viewport cell that comes or goes changes nothing ...
E = variant(lambda root: list(root.iter())[0].append(ET.fromstring('<table-cell name="Z999" Formula="" Note="" />')))
assert E == A
# ... but a border on an empty cell is visible formatting and is kept.
def border(root):
    for k, v in list(nth_empty_cell(root, 7).attrib.items()):
        if k.rsplit("}", 1)[-1] == "TopBorder":
            nth_empty_cell(root, 7).set(k, "solid")
            return
    nth_empty_cell(root, 7).set("TopBorder", "solid")
Bd = variant(border)
assert Bd != A and diff(A, Bd), "a bordered empty cell must survive"

# The Name Box / Input line echo the cursor cell: their text never counts.
def move_cursor(root):
    for e in root.iter():
        if local(e.tag) == "tool-bar" and e.get("name") == "Formula Tool Bar":
            for t in e.iter():
                if local(t.tag) in ("text", "paragraph") and (t.text or "").strip():
                    t.text = "Q42"
            return
    raise AssertionError("fixture has no Formula Tool Bar")
assert variant(move_cursor) == A

# The Formatting toolbar echoes the cursor cell too (font box, Bold lit, Currency vs General): never counts.
def format_readouts(root):
    for e in root.iter():
        if local(e.tag) == "tool-bar" and e.get("name") == "Formatting":
            touched = 0
            for t in e.iter():
                if local(t.tag) in ("text", "paragraph") and (t.text or "").strip():
                    t.text = "Some Other Font"; touched += 1
                for k in list(t.attrib):
                    if k.rsplit("}", 1)[-1] in ("checked", "value"):
                        t.set(k, "true" if t.get(k) != "true" else "false"); touched += 1
            assert touched, "Formatting toolbar in the fixture has nothing to vary"
            return
    raise AssertionError("fixture has no Formatting toolbar")
assert variant(format_readouts) == A
# The selection is not state: highlighted cells compare equal.
def select_cells(root):
    n = 0
    for e in root.iter():
        if local(e.tag) == "table-cell":
            e.set("selected", "true"); n += 1
            if n >= 30:
                return
    raise AssertionError("fixture has too few cells")
assert variant(select_cells) == A
# ...but a toolbar that disappears is still a difference
def drop_formatting(root):
    for parent in root.iter():
        for c in list(parent):
            if local(c.tag) == "tool-bar" and c.get("name") == "Formatting":
                parent.remove(c); return
    raise AssertionError("fixture has no Formatting toolbar")
assert variant(drop_formatting) != A

# Empty unnamed panels in front of content panels (Start Center leftovers) shift nothing.
def leftovers(root):
    for parent in root.iter():
        kids = [c for c in parent if local(c.tag) == "panel" and not c.get("name") and len(c)]
        if len(kids) >= 1:
            for _ in range(5):
                parent.insert(0, ET.Element(kids[0].tag))
            return
    raise AssertionError("no unnamed content panel in fixture")
assert variant(leftovers) == A

# A nameless non-office application is not part of the state.
def shell(root):
    app = ET.SubElement(root, "application")
    ET.SubElement(ET.SubElement(app, "frame", name="top bar"), "label", name="12:01")
assert variant(shell) == A

json.dumps(mask)  # serialisable
# Guess B's free-text undo becomes a candidate only when every step is a plain key or a reopen.
from rig.undo import from_guess, step_code
assert from_guess(["ctrl+z (undo typing 'pilot' in H33)", "ctrl+s", "enter (Keep Current Format)", "ctrl+y (redo 'pilot')"]) == \
    ["key:ctrl+z", "key:ctrl+s", "wait:4", "key:enter", "key:ctrl+y"]
assert from_guess(["Esc"]) == ["key:escape"] and from_guess(["reopen the file"]) == ["reopen"]
assert from_guess(["click Undo in the Edit menu"]) is None and from_guess(None) is None and from_guess([]) is None
# reopen after a full quit starts LibreOffice on the file instead of typing into the GNOME run dialog
assert "Popen(['libreoffice', '--calc'" in step_code("reopen", {"doc_path": "/home/user/x.xlsx", "office_running": False})
assert "ctrl', 'o'" in step_code("reopen", {"doc_path": "/home/user/x.xlsx", "office_running": True})

# 19 Oct: guess B answers in the step language; type: is capped at TYPE_MAX; K counts actions, not waits.
from rig.undo import TYPE_MAX, action_count, guess_parse, parse_step, tier2, CALC, FILES
assert guess_parse(["reopen", "key:ctrl+home", "type:pilot", "key:enter", "key:ctrl+w"]) == \
    (["reopen", "key:ctrl+home", "type:pilot", "key:enter", "key:ctrl+w"], "step-language")
assert guess_parse(["ctrl+z (undo)"]) == (["key:ctrl+z"], "free-text")
assert guess_parse(["type 'pilot' and press enter"]) == (None, "unparsed") and guess_parse([]) == (None, "empty")
assert parse_step("type:" + "x" * TYPE_MAX) and parse_step("type:" + "x" * (TYPE_MAX + 1)) is None
try:
    step_code("type:" + "x" * (TYPE_MAX + 1), {})
    raise AssertionError("over-long type: step must not run")
except ValueError:
    pass
assert action_count(["key:ctrl+z", "key:ctrl+s", "wait:4", "key:enter", "wait:3", "key:ctrl+y"]) == 4
assert tier2("libreoffice-calc") == CALC and tier2("files") == FILES and tier2("multi_apps")[:len(FILES)] == FILES
assert "Popen(['nautilus', '/home/user/Desktop']" in step_code("reopen", {"reopen_cmd": ["nautilus", "/home/user/Desktop"]})

# 19 Oct: permission bits, folders and links are state; digests recorded before carry none and compare as before.
from rig.mask import file_sig
assert file_sig({"s": 3, "h": "a", "mode": 0o644}) != file_sig({"s": 3, "h": "a", "mode": 0o600})
assert file_sig({"s": 3, "h": "a"}) == file_sig({"s": 3, "h": "a"})
assert file_sig({"d": 1, "mode": 0o755}) == ("dir", 0o755, None) and file_sig({"l": "Desktop"}) == ("link", "Desktop")
assert file_sig({"d": 1, "mode": 0o755, "u": 0}) != file_sig({"d": 1, "mode": 0o755, "u": 1000})   # a sudo-made folder
assert file_sig({"k": "x", "s": 1, "mode": 0o664}) == file_sig({"k": "x", "s": 2, "mode": 0o664})   # cells, not bytes

# Tasks that are not one spreadsheet take the generic reset; every Calc task keeps the fast path.
import glob as _glob
from rig.freshstart import gui_steps, is_calc_task
_ex = BASE / "OSWorld" / "evaluation_examples" / "examples"
_calc = [json.load(open(f)) for f in _glob.glob(str(_ex / "libreoffice_calc" / "*.json"))]
assert _calc and all(is_calc_task(t) for t in _calc)
_t = lambda i: json.load(open(_glob.glob(str(_ex / "multi_apps" / f"{i}*.json"))[0]))
assert not is_calc_task(_t("3680a5ee")) and not is_calc_task(_t("7f35355e"))         # 7f35355e: download + open xlsx
assert [s["type"] for s in gui_steps(_t("5df7b33a"))] == ["launch", "open"]          # unzip and rm are not replayed
assert [s["type"] for s in gui_steps(_t("ee9a3c83"))] == ["open", "execute"]         # history -c is not; the terminal is
assert gui_steps(_t("f918266a")) == []                                                # 'calculator.zip' is not 'code'

# A terminal's text buffer is not state (provisional, 19 Oct); its other attributes are.
from rig.mask import apply_tree_mask
_c = {"/desktop-frame/application[gnome-terminal-server]#0/frame[t]#0/terminal[]#0": {"text": "$ ls\nfile1", "focused": "true"}}
assert list(apply_tree_mask(_c, {}).values()) == [{"focused": "true"}]

print("ALL OFFLINE CHECKS PASSED")
