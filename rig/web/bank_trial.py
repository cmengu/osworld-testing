"""Step 4 second app (7 Nov 2026): vaultbank, a mocked bank (no real money, no real bank).  Does the JSON state separate
"undone" from "compensated"?  For each action: fresh user, read S, act, read S'; PUT S' back and check the read equals S'
(the reader's own check); then try the realistic ways back, each from S' restored by one PUT, and report what differs
from S.  Each way back is ONE user-level step (a form sent, or a Cancel), not the rig's K-step search, and the list is
hand-written, so NO-UNDO-FOUND here means "none of these".

    OSWorld/.venv/bin/python -I rig/web/bank_trial.py     # -> rig/out/web/bank_trial.json
"""
import json
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import webstate as W  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

OUT = HERE.parent / "out" / "web"
APP = "vaultbank"
FUTURE = "2026-12-15"


def go(pg, uid, path):
    pg.goto(f"{W.base(APP)}{path}?cookie={uid}", wait_until="networkidle", timeout=45000)


def transfer(pg, uid, src, dst, amount, date=None):
    go(pg, uid, "/transfers")
    sel = pg.locator("select:visible")
    sel.nth(0).select_option(index=src)
    pg.wait_for_timeout(300)
    sel.nth(1).select_option(index=dst)
    pg.locator("input[type=text]:visible").last.fill(str(amount))
    if date:
        pg.locator("input[type=date]:visible").last.fill(date)
    pg.locator("button:has-text('Review Transfer')").click()
    pg.wait_for_timeout(900)
    pg.locator("button:has-text('Confirm Transfer')").click(timeout=4000)
    pg.wait_for_timeout(2500)


def billpay(pg, uid, amount, date=None):
    go(pg, uid, "/bill-pay")
    pg.select_option("select[name=fromAccountId]", index=1)
    pg.select_option("select[name=payeeId]", index=1)
    pg.fill("input[name=amount]", str(amount))
    if date:
        pg.fill("input[name=paymentDate]", date)
    pg.locator("button:has-text('Review Payment')").click()
    pg.wait_for_timeout(900)
    pg.locator("button:has-text('Confirm Payment')").click(timeout=4000)
    pg.wait_for_timeout(2500)


def cancel_in(path, tab):
    def fn(pg, uid):
        go(pg, uid, path)
        pg.locator(f"button:has-text('{tab}')").first.click(timeout=4000)
        pg.wait_for_timeout(800)
        b = pg.locator("main button:has-text('Cancel'), [role=tabpanel] button:has-text('Cancel')")
        b = b.last if b.count() else pg.locator("button:has-text('Cancel')").last
        b.click(timeout=4000)
        pg.wait_for_timeout(900)
        c = pg.locator("[role=dialog] button:has-text('Confirm'), [role=alertdialog] button:has-text('Confirm'), [role=dialog] button:has-text('Yes'), [role=alertdialog] button:has-text('Yes'), [role=dialog] button:has-text('Cancel Payment'), [role=alertdialog] button:has-text('Cancel Payment')")
        if c.count():
            c.first.click(timeout=4000)
            pg.wait_for_timeout(1500)
    return fn


CASES = [
    ("transfer 10 now, checking to savings", lambda pg, u: transfer(pg, u, 1, 1, 10),
     {"send it back": lambda pg, u: transfer(pg, u, 2, 1, 10), "cancel in history": cancel_in("/transfers", "Transfer History")}),
    ("transfer 10 on a future date", lambda pg, u: transfer(pg, u, 1, 1, 10, FUTURE),
     {"cancel in history": cancel_in("/transfers", "Transfer History")}),
    ("pay a bill 20 now", lambda pg, u: billpay(pg, u, 20),
     {"cancel in scheduled": cancel_in("/bill-pay", "Scheduled"), "cancel in history": cancel_in("/bill-pay", "History")}),
    ("pay a bill 20 on a future date", lambda pg, u: billpay(pg, u, 20, FUTURE),
     {"cancel in scheduled": cancel_in("/bill-pay", "Scheduled")}),
]


def show(d):
    return [[".".join(map(str, p)), str(o)[:50], str(n)[:70]] for p, o, n in d]


def money(d):
    return [x for x in d if "balance" in str(x[0][-1])]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    res = []
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=W.chromium())
        for name, act, ways in CASES:
            t0 = time.time()
            uid = W.new_user(APP)
            pg = b.new_page(ignore_https_errors=True, viewport={"width": 1280, "height": 900})
            go(pg, uid, "/")
            S = W.read(APP, uid)
            time.sleep(4)
            rest = not W.diff(S, W.read(APP, uid))
            act(pg, uid)
            time.sleep(4)
            Sp = W.read(APP, uid)
            d = W.diff(S, Sp)
            W.write(APP, uid, Sp)
            restore = not W.diff(Sp, W.read(APP, uid))
            tried = {}
            for wn, fn in ways.items():
                W.write(APP, uid, Sp)
                try:
                    fn(pg, uid)
                    time.sleep(3)
                    left = W.diff(S, W.read(APP, uid))
                    tried[wn] = {"state_equal": not left, "money_equal": not money(left), "left": len(left), "sample": show(left)[:6]}
                except Exception as e:
                    tried[wn] = {"state_equal": False, "error": repr(e)[:120]}
            W.write(APP, uid, S)
            row = {"case": name, "changed": len(d), "money_changed": bool(money(d)), "diff": show(d), "reader_equal_at_rest": rest, "put_restore_equal": restore,
                   "put_back_to_S_equal": not W.diff(S, W.read(APP, uid)), "ways_back": tried,
                   "label": "REVERSIBLE" if any(v.get("state_equal") for v in tried.values()) else "NO-UNDO-FOUND (of these)", "seconds": round(time.time() - t0)}
            print(json.dumps({k: v for k, v in row.items() if k != "diff"}), flush=True)
            res.append(row)
            pg.close()
        b.close()
    (OUT / "bank_trial.json").write_text(json.dumps({"app": APP, "suffix": W.SUFFIX, "rows": res}, indent=1))


if __name__ == "__main__":
    main()
