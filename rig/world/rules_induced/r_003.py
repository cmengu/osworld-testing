"""Induced 2026-11-09 15:22 from DEV family: Yes in the replace question (Keep Current Format): the other document is overwritten
fixes 8, breaks 0."""
def rule(ev, cmd, st, screen):
    """Yes in the replace question (Keep Current Format) of LibreOffice's Save As dialog:
    the other document is overwritten with the current one, its lock file appears,
    and the lock file of the old document goes away."""
    if not ev:
        return None
    hot = [e for e in ev if e and e[0] == "hotkey"]
    if not hot or str(hot[0][1]).lower().replace(" ", "") not in ("alt+y",):
        return None
    # The first hotkey must be the alt+y answer
    if ev[0][0] != "hotkey":
        return None

    titles = list(getattr(st, "titles", None) or [])
    if not any(t.strip() == "Save" for t in titles):
        return None
    q = screen.question() if screen is not None else None
    if q not in ("replace", None):
        return None

    # Find the current LibreOffice document.
    cur_name = None
    for t in titles:
        m = re.match(r"^(.*\S)\s+-\s+LibreOffice\s+(Writer|Impress|Calc|Draw)\s*$", t)
        if m:
            cur_name = m.group(1)
            break
    if not cur_name:
        return None
    cur = st.doc_path(cur_name)
    if not cur:
        return None
    cur_dir = posixpath.dirname(cur)
    cur_ext = posixpath.splitext(cur)[1].lower()
    if not cur_ext:
        return None

    def is_lock(p):
        return posixpath.basename(p).startswith(".~lock.")

    def resolve(name):
        if not name:
            return None
        name = name.strip()
        if name.startswith("/"):
            return name if name in st.files else None
        cand = posixpath.join(cur_dir, name)
        if cand in st.files:
            return cand
        p = st.doc_path(posixpath.basename(name))
        return p

    target = None
    # 1. File named in the question dialog
    try:
        nf = screen.named_file()
    except Exception:
        nf = None
    t1 = resolve(nf)
    if t1 and t1 != cur and not is_lock(t1):
        target = t1

    # 2. File name typed in a text entry of the Save dialog
    if target is None:
        tree = getattr(st, "tree", None) or ""
        found = set()
        for m in re.finditer(r"<([\w:-]*(?:entry|text)[\w:-]*)\b[^>]*\bname=\"([^\"]*)\"", tree, re.I):
            nm = (m.group(2).replace("&amp;", "&").replace("&quot;", '"')
                  .replace("&lt;", "<").replace("&gt;", ">").replace("&apos;", "'"))
            p = resolve(nm)
            if p and p != cur and not is_lock(p) and posixpath.splitext(p)[1].lower() == cur_ext:
                found.add(p)
        if len(found) == 1:
            target = found.pop()

    # 3. Unique other document of the same type in the same folder
    if target is None:
        cands = [p for p in st.files
                 if posixpath.dirname(p) == cur_dir and p != cur and not is_lock(p)
                 and posixpath.splitext(p)[1].lower() == cur_ext]
        if len(cands) != 1:
            return None
        target = cands[0]

    files = {target: ("sym", "overwritten with the current document (Keep Current Format)")}
    old_lock = st.lock_of(cur)
    if old_lock and old_lock in st.files:
        files[old_lock] = ("absent",)
    new_lock = st.lock_of(target)
    if new_lock and new_lock not in st.files:
        files[new_lock] = ("sym", "LibreOffice lock of the newly saved document")
    return Delta(files=files, windows="unknown", rules=["save-as-replace-keep-format"])
