"""Induced 2026-11-09 15:29 from DEV family: File > Empty Trash after deleting a message: the message is gone for good
fixes 5, breaks 0."""
def rule(ev, cmd, st, screen):
    """Thunderbird: File menu (Alt+F), optionally followed by the 'y' accelerator
    (Empty Trash). Opening the menu and emptying the trash do not change any
    tracked file under /home/user in the recorded steps. A menu or popup opens."""
    if not ev or cmd is not None:
        return None
    titles = st.titles or []
    if not any("Mozilla Thunderbird" in (t or "") for t in titles):
        return None
    # Thunderbird must be the focused window. Be conservative and require it to be listed first.
    if "Mozilla Thunderbird" not in (titles[0] or ""):
        return None

    # Drop events that do not act on the screen.
    evs = [e for e in ev if e and e[0] not in ("view",)]
    if not evs:
        return None

    first = evs[0]
    if not (first[0] == "hotkey" and str(first[1]).lower().replace(" ", "") in ("alt+f",)):
        return None

    rest = evs[1:]
    if len(rest) == 0:
        # Only the File menu opened.
        return Delta(files={}, windows="opens",
                     rules=["thunderbird-file-menu-open"])
    if len(rest) == 1 and rest[0][0] == "key" and str(rest[0][1]).lower() == "y":
        # File > Empty Trash. The deleted message is purged from the mail store.
        # The recorded steps show no tracked file change. A confirmation dialog may open.
        return Delta(files={}, windows="opens",
                     rules=["thunderbird-file-empty-trash"])
    return None
