"""DRAFT, 2 November 2026: a looser state comparison for review.  Nothing imports this module, so it changes no label.

It drops differences that come from the pointer or from how the tree is read, found on the 12 agent steps in
rig/agentrun/rig_no_undo_12_20261102.md.  The file comparison is untouched, and a changed value still counts.

    R1  VS Code Welcome page: the page's own subtree is not user state (progress bars, rebuilt sections).
    R2  VS Code Explorer toolbar: the buttons that appear while the pointer is over the Explorer header.
    R3  Impress hover label: the panel directly under the frame that holds a slide's tooltip.
    R4  Impress numbered objects: Title1 and Title2 are the same object if one state has only one and the other only
        the other, with equal attributes.  Text inside must match too, because attributes are compared node by node.
    R5  Chrome tab names: the "Memory usage - 51.3 MB" part of a hover name.  Same pairing as R4.
    R6  CSS classes inside a web page.
"""
import collections
import re

from rig.mask import NODE, states_equal

_WELCOME = "document-frame[Overview of how to get up to speed"
_TOOLBAR = re.compile(r"push-button\[Explorer Section: [^\]]*\]#\d+/section\[\]#1(/|$)")
_TOOLTIP = re.compile(r"frame\[[^\]]*LibreOffice Impress\]#\d+/panel\[\]#1(/label\[[^\]]*\]#\d+)?$")
_NUMBERED = re.compile(r"panel\[(Title|Subtitle|ContentPlaceholder|TextPlaceholder|PicturePlaceholder)\d+\]")
_MEMORY = re.compile(r" - Memory usage - [\d.]+ [KMG]B")


def _normal(path):
    return _MEMORY.sub("", _NUMBERED.sub(lambda m: f"panel[{m.group(1)}]", path))


def _value(v):
    """A node's own name repeats the number or memory text, so it is normalised too; any other change still counts."""
    return _MEMORY.sub("", re.sub(r"^(Title|Subtitle|ContentPlaceholder|TextPlaceholder|PicturePlaceholder)\d+$", r"\1", str(v)))


def _attrs(canon, path):
    return tuple(sorted((k, _value(v)) for k, v in (canon.get(path) or {}).items()))


def relax(tree_diffs, a_canon, b_canon):
    """The differences that remain, and the count dropped per rule."""
    kept, dropped = [], collections.Counter()
    for d in tree_diffs:
        p, attr = d["path"], d["attr"]
        if _WELCOME in p:
            dropped["R1"] += 1
        elif attr == NODE and _TOOLBAR.search(p):
            dropped["R2"] += 1
        elif attr == NODE and _TOOLTIP.search(p):
            dropped["R3"] += 1
        elif attr == "class" and "/document-web[" in p:
            dropped["R6"] += 1
        else:
            kept.append(d)
    gone, new = collections.defaultdict(list), collections.defaultdict(list)
    for d in kept:
        if d["attr"] == NODE and _normal(d["path"]) != d["path"]:
            if d["new"] is None:
                gone[(_normal(d["path"]), _attrs(a_canon, d["path"]))].append(d)
            elif d["old"] is None:
                new[(_normal(d["path"]), _attrs(b_canon, d["path"]))].append(d)
    paired = set()
    for key in gone.keys() & new.keys():
        for x, y in zip(gone[key], new[key]):
            paired.update((id(x), id(y)))
            rule = "R5" if "Memory usage" in x["path"] else "R4"
            dropped[rule] += 2
    return [d for d in kept if id(d) not in paired], dropped


def states_equal_relaxed(a_canon, a_digest, b_canon, b_digest, mask):
    """(equal?, tree differences left, file differences, count dropped per rule)."""
    _, tree_diffs, file_diffs = states_equal(a_canon, a_digest, b_canon, b_digest, mask)
    left, dropped = relax(tree_diffs, a_canon, b_canon)
    return (not left and not file_diffs), left, file_diffs, dropped
