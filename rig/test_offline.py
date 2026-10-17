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
assert len(A) > 800 and len(cells) > 500

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
    return [e for e in root.iter() if local(e.tag) == "table-cell"][n]


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
B = variant(lambda root: (nth_cell(root, 40).set("expanded", "true"),
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

json.dumps(mask)  # serialisable
print("ALL OFFLINE CHECKS PASSED")
