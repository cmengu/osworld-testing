"""Step 4 trial (6 Nov 2026, author: "lets do all steps"): can the rig read web app state well enough to LABEL web
actions?  Free: a local headless Chromium drives the team-hosted OSWorld-web sites (2026.08.08 release, site.hku.icu)
with real clicks and typing; the state is the app's /api/state JSON (rig/web/webstate.py).

For each action: a fresh user, setup steps, read S; the action, read S' and the diff.  Then an undo search like the
rig's: every candidate sequence of up to K = 3 GUI steps starts from S' (restored by one PUT, page reloaded at the URL
the action left), and REVERSIBLE means the state equals S again (bookkeeping fields ignored).  Checks of the reader
itself: S read twice at rest is equal, and the PUT restore of S' reads back equal.

MailHub is mocked: nothing leaves the site.  The one send goes to test@example.invalid (a reserved, undeliverable name).

    OSWorld/.venv/bin/python -I rig/web/web_trial.py      # -> rig/out/web/trial.json
"""
import itertools
import json
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import webstate as W  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

OUT = HERE.parent / "out" / "web"
APP = "mailhub"
ICON = {"back": (290, 112), "archive": (340, 112), "delete": (382, 112), "unread": (424, 112)}


def step(pg, s):
    kind, _, arg = s.partition(":")
    if kind == "nav":
        pg.locator(f"a:has-text('{arg}')").first.click(timeout=3000)
    elif kind == "open":
        pg.locator(f"text={arg}").first.click(timeout=3000)
    elif kind == "icon":
        pg.mouse.click(*ICON[arg])
    elif kind == "star":
        box = pg.locator(f"text={arg}").first.bounding_box(timeout=3000)
        pg.mouse.click(310, box["y"] + box["height"] / 2)
    elif kind == "check":                       # the row's checkbox in a mail list
        box = pg.locator(f"text={arg}").first.bounding_box(timeout=3000)
        pg.mouse.click(282, box["y"] + box["height"] / 2)
    elif kind == "tool":                        # a toolbar button by its title (shown once a row is checked)
        pg.locator(f"button[title='{arg}']").first.click(timeout=3000)
    elif kind == "key":
        pg.keyboard.press(arg)
    elif kind == "compose":
        pg.locator("button:has-text('Compose')").click(timeout=3000)
        pg.wait_for_timeout(600)
        pg.mouse.click(900, 461); pg.keyboard.type("test@example.invalid"); pg.keyboard.press("Enter")
        pg.mouse.click(900, 506); pg.keyboard.type("rig trial")
        pg.mouse.click(900, 620); pg.keyboard.type("hello from the rig")
    elif kind == "send":
        pg.locator("button:has-text('Send')").first.click(timeout=3000)
    else:
        raise ValueError(s)
    pg.wait_for_timeout(900)


CASES = [
    # name, setup steps, action steps, undo alphabet (the list toolbar's buttons appear once a row is checked)
    ("open an unread email (marks it read)", [], ["open:Bob Jones"],
     ["icon:back", "check:Bob Jones", "tool:Mark as read", "icon:unread"]),
    ("star an email in the list", [], ["star:Bob Jones"],
     ["star:Bob Jones", "open:Bob Jones", "nav:Starred"]),
    ("archive the open email", ["open:Bob Jones"], ["icon:archive"],
     ["nav:All Mail", "nav:Inbox", "check:Bob Jones", "tool:Archive", "tool:Labels", "icon:back"]),
    ("delete the open email (to Trash)", ["open:Bob Jones"], ["icon:delete"],
     ["nav:Trash", "nav:Inbox", "check:Bob Jones", "tool:Archive", "tool:Delete", "icon:back"]),
    ("delete an email that is already in Trash", ["open:Bob Jones", "icon:delete", "nav:Trash", "open:Bob Jones"], ["icon:delete"],
     ["nav:Trash", "nav:All Mail", "check:Bob Jones", "tool:Archive", "icon:back"]),
    ("send a composed email", ["compose:"], ["send:"],
     ["nav:Sent", "nav:Trash", "check:rig trial", "tool:Delete", "tool:Empty Trash Now", "nav:Drafts"]),
]


def settled(uid, secs=12):
    """Read the state until two reads 2 s apart agree (a compose window autosaves a draft; a send may trigger a reply)."""
    a = W.read(APP, uid)
    for _ in range(secs // 2):
        time.sleep(2)
        b = W.read(APP, uid)
        if not W.diff(a, b):
            return b, True
        a = b
    return a, False


def search(pg, uid, S, Sp, url, alphabet, k=3, cap=300):
    tried, t0 = 0, time.time()
    for n in range(1, k + 1):
        for seq in itertools.product(alphabet, repeat=n):
            if tried >= cap:
                return None, tried
            tried += 1
            W.write(APP, uid, Sp)
            pg.goto(url, wait_until="networkidle")
            ok = True
            for s in seq:
                try:
                    step(pg, s)
                except Exception:
                    ok = False
                    break
            if ok and not W.diff(S, W.read(APP, uid)):
                return list(seq), tried
    return None, tried


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    res = []
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=W.chromium())
        for name, setup, action, alphabet in CASES:
            t0 = time.time()
            uid = W.new_user(APP)
            pg = b.new_page(ignore_https_errors=True, viewport={"width": 1280, "height": 900})
            pg.goto(f"{W.base(APP)}/?cookie={uid}", wait_until="networkidle")
            for s in setup:
                step(pg, s)
            S, rest_equal = settled(uid)
            for s in action:
                step(pg, s)
            Sp, after_settled = settled(uid)
            url = pg.url
            d = W.diff(S, Sp)
            W.write(APP, uid, Sp)
            restore_equal = not W.diff(Sp, W.read(APP, uid))
            undo, tried = search(pg, uid, S, Sp, url, alphabet)
            row = {"case": name, "diff": [[".".join(map(str, pa)), str(o)[:60], str(n)[:60]] for pa, o, n in d],
                   "reader_equal_at_rest": rest_equal, "after_state_settled": after_settled, "put_restore_equal": restore_equal,
                   "label": "REVERSIBLE" if undo else "NO-UNDO-FOUND", "undo": undo, "candidates_tried": tried,
                   "seconds": round(time.time() - t0)}
            print(json.dumps(row), flush=True)
            res.append(row)
            pg.close()
        b.close()
    (OUT / "trial.json").write_text(json.dumps({"app": APP, "suffix": W.SUFFIX, "rows": res}, indent=1))


if __name__ == "__main__":
    main()
