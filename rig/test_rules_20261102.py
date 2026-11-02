"""Offline checks of the 2 November rules: the looser state comparison, the undo candidates and the settling wait.

    OSWorld/.venv/bin/python -I rig/test_rules_20261102.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from rig import undo as U                              # noqa: E402
from rig.mask import NODE, relax, states_equal, strict_states_equal  # noqa: E402
from rig.settle import needs_settle, wait_settled      # noqa: E402

MASK = {"samples": 2, "tree_pairs": [], "tree_attr_by_tag": {}, "tree_churn_sites": [], "file_paths": [], "file_dirs": [],
        "stats": {}}
FR = "/desktop-frame/application[soffice]#0/frame[a.pptx - LibreOffice Impress]#0"
DOC = FR + "/document-presentation[a]#0"
EXP = "/desktop-frame/application[code]#0/frame[x]#0/push-button[Explorer Section: app]#0"
FILE = {"/home/user/a.txt": {"s": 1, "m": 1, "h": "a"}}
FILE2 = {"/home/user/a.txt": {"s": 2, "m": 2, "h": "b"}}


def same(a, b, da=FILE, db=FILE):
    return states_equal(a, da, b, db, MASK)[0]


base = {"/desktop-frame": {"name": ""}, FR: {"name": "a.pptx - LibreOffice Impress"}}

# R1 Welcome page, R2 hover toolbar, R3 hover label: dropped, and the strict comparison still sees them
welcome = {**base, "/x/document-frame[Overview of how to get up to speed]#0/progress-bar[]#0": {"name": ""}}
assert same(base, welcome) and not strict_states_equal(base, FILE, welcome, FILE, MASK)[0]
assert same(base, {**base, EXP + "/section[]#1/tool-bar[app actions]#0": {"name": "app actions"}})
assert same(base, {**base, FR + "/panel[]#1": {"name": ""}, FR + "/panel[]#1/label[BACKGROUND]#0": {"name": "BACKGROUND"}})

# a hover toolbar's rule does not reach other Explorer content
assert not same(base, {**base, EXP + "/section[]#0/tree-item[new.py]#0": {"name": "new.py"}})
# nor does the label rule reach a label deeper in the document
assert not same(base, {**base, DOC + "/panel[]#1/label[x]#0": {"name": "x"}})

# R4 renumbered objects with the same contents are the same; different text, or a lost object, is a change
a = {**base, DOC + "/panel[Title1]#0": {"name": "Title1"}, DOC + "/panel[Title1]#0/paragraph[]#0": {"text": "Goals"}}
b = {**base, DOC + "/panel[Title2]#0": {"name": "Title2"}, DOC + "/panel[Title2]#0/paragraph[]#0": {"text": "Goals"}}
c = {**base, DOC + "/panel[Title2]#0": {"name": "Title2"}, DOC + "/panel[Title2]#0/paragraph[]#0": {"text": "Other"}}
assert same(a, b)
assert not same(a, c), "different text under a renumbered object must count"
assert not same(a, base), "an object present in one state only must count"

# R5 Chrome memory text; R6 a page's CSS class
T = "/desktop-frame/application[chrome]#0/frame[n]#0/page-tab[New Tab - Memory usage - %s MB]#0"
assert same({**base, T % "51.3": {"name": "New Tab - Memory usage - 51.3 MB"}}, {**base, T % "56.3": {"name": "New Tab - Memory usage - 56.3 MB"}})
W = "/desktop-frame/application[chrome]#0/frame[n]#0/document-web[]#0/landmark[]#0"
assert same({**base, W: {"class": "a"}}, {**base, W: {"class": "b"}})
assert not same({**base, W: {"text": "a"}}, {**base, W: {"text": "b"}}), "only the class attribute is exempt"

# a file difference is never relaxed
assert not same(base, welcome, FILE, FILE2)
assert relax([{"path": "/p", "attr": NODE, "old": None, "new": "present"}], {}, {})[0], "an ordinary new node stays"

# candidates: Revert File first in VS Code, Ctrl+Z then Ctrl+End for Impress; both within K = 3
assert U.VSCODE_FIRST[0] == ["menu:alt+f,v"] and U.action_count(U.VSCODE_FIRST[0]) == 1
assert ["key:ctrl+z", "key:ctrl+end"] in U.IMPRESS_FIRST and U.action_count(U.IMPRESS_FIRST[0]) == 2

# settling: which actions wait
assert needs_settle("pyautogui.typewrite('ls', interval=0.03)")
assert needs_settle("pyautogui.press('enter')") and needs_settle("pyautogui.hotkey('ctrl', 's')")
assert not needs_settle("pyautogui.click(10, 20)") and not needs_settle("pyautogui.hotkey('ctrl', 'z')")


class Clock:
    def __init__(self):
        self.t = 0

    def now(self):
        return self.t

    def sleep(self, s):
        self.t += s


def wait(idles, frames, cap=60):
    idles, frames, c = iter(idles), iter(frames), Clock()

    def of(it):
        v = next(it)
        if isinstance(v, Exception):
            raise v
        return v
    return wait_settled(None, cap=cap, idle_of=lambda e: of(idles), frame_of=lambda e: of(frames), clock=c.now, sleep=c.sleep)


F, G = bytes(100), bytes([200]) * 100
# busy, then quiet: a still screen alone must not end the wait
r = wait([10, 10, 95, 95, 95], [F, F, F, F, F])
# (idle 68 now counts as quiet, as part A read it)
assert r["settled"] is True and r["polls"] == 4, r
# screen still changing while the CPU is idle
r = wait([95] * 5, [F, G, F, F, F])
assert r["settled"] is True and r["polls"] == 5, r
# never quiet: stops at the cap and says so
r = wait([5] * 100, [F] * 100, cap=6)
assert r["settled"] is False and r["seconds"] >= 6, r
# no signal at all: returns at once, row goes on
r = wait([RuntimeError()], [RuntimeError()])
assert r["settled"] is None and r["polls"] == 1, r
# one signal only: waits on that one
r = wait([RuntimeError()] * 5, [F, F, F])
assert r["settled"] is True, r

r = wait([68] * 3, [F] * 3)
assert r["settled"] is True, r
print("RULES CHECKS PASSED")
