"""Induced 2026-11-09 15:31 from DEV family: Enter in the question: the message is deleted without passing the Trash
fixes 4, breaks 0."""
def rule(ev, cmd, st, screen):
    """Thunderbird 'Confirm Deletion' dialog answered with Enter: the selected
    message is deleted permanently, without passing the Trash. The folder's mbox
    file is rewritten (the message is marked deleted, so the size stays the same),
    the global search database is updated, and the dialog closes."""
    if not ev or cmd is not None:
        return None
    # The step must be just an Enter press.
    if len(ev) != 1 or tuple(ev[0]) not in (("key", "enter"), ("key", "return")):
        return None
    titles = list(st.titles or [])
    if not any(t.strip() == "Confirm Deletion" for t in titles):
        return None

    # The main Thunderbird window title is "<folder> - <account> - Mozilla Thunderbird".
    folder = account = None
    for t in titles:
        m = re.match(r"^(.*) - (.*) - Mozilla Thunderbird$", t.strip())
        if m:
            folder, account = m.group(1).strip(), m.group(2).strip()
            break
    if not folder:
        return None

    # Find the mbox file for that folder in a Thunderbird profile.
    cands = []
    for p in st.files:
        if "/.thunderbird/" not in p or p.endswith(".msf"):
            continue
        if posixpath.basename(p) != folder:
            continue
        if "/Mail/" not in p and "/ImapMail/" not in p:
            continue
        cands.append(p)
    if account and len(cands) > 1:
        narrowed = [p for p in cands if ("/" + account + "/") in p]
        if narrowed:
            cands = narrowed
    if len(cands) != 1:
        return None
    mbox = cands[0]

    files = {mbox: ("sym", "message expunged/marked deleted in mbox")}

    # The global search database in the same profile is updated too.
    m = re.match(r"^(.*?/\.thunderbird/[^/]+)/", mbox)
    if m:
        gdb = m.group(1) + "/global-messages-db.sqlite"
        if gdb in st.files:
            files[gdb] = ("sym", "gloda index updated after deletion")

    return Delta(files=files, windows="closes",
                 rules=["thunderbird-confirm-permanent-delete"])
