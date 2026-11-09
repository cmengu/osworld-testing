"""Induced 2026-11-09 15:23 from DEV family: Ctrl+N, type 'pilot' into To: a modified compose window
fixes 8, breaks 0."""
def rule(ev, cmd, st, screen):
    """Thunderbird: Ctrl+N opens a new compose window, then text is typed into it
    (e.g. into the To: field).  Nothing is saved or sent, so no file changes;
    a new window opens."""
    if ev is None or cmd is not None:
        return None
    if not ev:
        return None

    titles = st.titles or []
    if not any("Mozilla Thunderbird" in t or t.endswith("- Thunderbird") for t in titles):
        return None

    # Do not interfere when a question dialog is open.
    if screen is not None and screen.question() is not None:
        return None

    # Skip leading no-op view events.
    i = 0
    while i < len(ev) and ev[i][0] == "view":
        i += 1
    if i >= len(ev):
        return None

    first = ev[i]
    if first[0] != "hotkey":
        return None
    keys = str(first[1]).lower().replace(" ", "")
    if keys not in ("ctrl+n", "control+n"):
        return None

    # After Ctrl+N, accept only plain typing and view events.  Anything that
    # could send or save the message (Enter, Ctrl+Enter, Ctrl+S, clicks) makes
    # the outcome uncertain.
    rest = ev[i + 1:]
    typed = False
    for e in rest:
        kind = e[0]
        if kind == "type":
            text = e[1] if len(e) > 1 else ""
            if "\n" in text or "\r" in text:
                return None
            typed = True
        elif kind == "view":
            continue
        else:
            return None

    # Ctrl+N with nothing typed also only opens a window, so the result is the same.
    return Delta(files={}, windows="opens",
                 rules=["thunderbird-compose-new-type" if typed else "thunderbird-compose-new"])
