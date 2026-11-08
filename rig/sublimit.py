"""Track C (8 Nov 2026, author: "start track b and c"): survive the subscription's 5-hour limit instead of failing.

No Anthropic API key (author, 8 Nov: economical cost), so every Claude call goes through `claude -p` on the
subscription.  When the limit hits, the CLI answers with an error such as "Claude AI usage limit reached|1762603200"
or "5-hour limit reached ∙ resets 3pm".  The 7 Nov pilot turned that into a fake FAIL (void run).  Here a caller asks
`limit_wait(text)`: if the text is a limit message, it sleeps until the reset (plus a margin), records the wait in
rig/out/limit_wait.json for the status page, and returns True so the caller retries the same call.

    from rig.sublimit import limit_wait
    if not ok and limit_wait(error_text): retry
"""
import datetime as dt
import json
import pathlib
import re
import time

STATUS = pathlib.Path(__file__).resolve().parent / "out" / "limit_wait.json"
_LIMIT = re.compile(r"usage limit|limit reached|hit your limit|rate.?limit|5-hour limit|weekly limit", re.I)
_EPOCH = re.compile(r"\|(\d{10})\b")
_CLOCK = re.compile(r"resets?\s+(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", re.I)
MARGIN_S = 120
UNKNOWN_WAIT_S = 15 * 60
MAX_WAIT_S = 5 * 3600 + 600


def is_limit(text: str) -> bool:
    return bool(text) and bool(_LIMIT.search(text))


def reset_in(text: str, now: float = None) -> float:
    """Seconds until the reset the message names (local time), UNKNOWN_WAIT_S when it names none."""
    now = time.time() if now is None else now
    m = _EPOCH.search(text or "")
    if m:
        return min(MAX_WAIT_S, max(0.0, int(m.group(1)) - now))
    m = _CLOCK.search(text or "")
    if m:
        h, mi, ap = int(m.group(1)), int(m.group(2) or 0), (m.group(3) or "").lower()
        if ap == "pm" and h < 12:
            h += 12
        if ap == "am" and h == 12:
            h = 0
        base = dt.datetime.fromtimestamp(now)
        t = base.replace(hour=h % 24, minute=mi, second=0, microsecond=0)
        if t <= base:
            t += dt.timedelta(days=1)
        return min(MAX_WAIT_S, (t - base).total_seconds())
    return UNKNOWN_WAIT_S


def limit_wait(text: str, who: str = "", sleep=time.sleep) -> bool:
    """If `text` is a subscription-limit message: wait out the reset, record it, return True (retry).  Else False."""
    if not is_limit(text):
        return False
    wait = reset_in(text) + MARGIN_S
    until = time.time() + wait
    rec = {"who": who, "since": time.strftime("%Y-%m-%d %H:%M:%S"), "until": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(until)),
           "message": (text or "")[:200]}
    try:
        STATUS.parent.mkdir(parents=True, exist_ok=True)
        STATUS.write_text(json.dumps(rec, indent=1))
    except OSError:
        pass
    print(f"[sublimit] subscription limit ({who}): waiting {wait / 60:.0f} min until {rec['until']}", flush=True)
    sleep(wait)
    try:
        STATUS.unlink()
    except OSError:
        pass
    return True


if __name__ == "__main__":        # offline checks
    now = dt.datetime(2026, 11, 8, 13, 0).timestamp()
    assert is_limit("Claude AI usage limit reached|1762603200") and not is_limit("timeout after 300s")
    assert abs(reset_in("5-hour limit reached ∙ resets 3pm", now) - 2 * 3600) < 1
    assert abs(reset_in("limit reached, resets 14:30", now) - 1.5 * 3600) < 1
    assert abs(reset_in("You've hit your limit · resets 12am", now) - 11 * 3600) < 1 or reset_in("You've hit your limit · resets 12am", now) == MAX_WAIT_S
    assert reset_in("usage limit reached", now) == UNKNOWN_WAIT_S
    assert reset_in(f"usage limit reached|{int(now) + 600}", now) == 600
    waited = []
    assert limit_wait("usage limit reached|1000000000", "test", sleep=waited.append) and waited == [MARGIN_S]
    assert not limit_wait("some other error", "test", sleep=waited.append)
    print("SUBLIMIT CHECKS PASSED")
