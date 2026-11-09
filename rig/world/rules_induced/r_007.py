"""Induced 2026-11-09 15:30 from DEV family: Empty Trash, confirmed: the trashed file is gone for good
fixes 5, breaks 0."""
def rule(ev, cmd, st, screen):
    """Empty Trash confirmed in the GNOME Files dialog: every trashed item and its .trashinfo is gone."""
    if not ev or cmd is not None:
        return None
    try:
        q = screen.question()
    except Exception:
        return None
    if q not in ("delete", "empty-trash"):
        return None
    titles = list(getattr(st, "titles", None) or [])
    in_trash_view = any(t.strip() == "Trash" or t.strip().startswith("Trash ") for t in titles)
    if q == "delete":
        # A "delete" question that names a file is a per-item permanent delete, not Empty Trash.
        try:
            if screen.named_file():
                return None
        except Exception:
            return None
        if not in_trash_view:
            return None

    # The step must confirm. Accept alt+t (mnemonic for "Empty _Trash")
    # or a click on a button that says "Empty Trash" / "Empty" / "Delete".
    confirmed = False
    for e in ev:
        if not e:
            continue
        kind = e[0]
        if kind == "hotkey" and len(e) > 1:
            keys = str(e[1]).lower().replace(" ", "")
            if keys in ("alt+t",):
                confirmed = True
        elif kind == "click" and len(e) >= 3:
            try:
                tag, name = screen.at(e[1], e[2])
            except Exception:
                continue
            nm = (name or "").strip().lower().replace("_", "")
            if nm in ("empty trash", "empty", "empty all"):
                confirmed = True
            elif nm == "delete" and q == "empty-trash":
                confirmed = True
        elif kind in ("key", "type", "maybe-enter"):
            # an unclear confirmation (e.g. Enter on the default button): not sure
            continue
    if not confirmed:
        return None

    # Find the trash folders (…/.local/share/Trash/files and …/info) under /home/user.
    marker = "/.local/share/Trash/"
    roots = set()
    for p in list(st.files.keys()) + list(st.dirs):
        i = p.find(marker)
        if i >= 0:
            roots.add(p[: i + len(marker)])
    if not roots:
        return None

    changes = {}
    for root in roots:
        subs = (root + "files/", root + "info/")
        for p in st.files:
            if p.startswith(subs):
                changes[p] = ("absent",)
        for d in st.dirs:
            dd = d.rstrip("/")
            for s in subs:
                if dd.startswith(s) and len(dd) > len(s) - 1 and dd + "/" != s:
                    changes[dd + "/"] = ("absent",)
    if not changes:
        return None
    return Delta(files=changes, windows="same", rules=["empty-trash-confirmed"])
