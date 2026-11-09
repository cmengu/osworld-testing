"""Induced 2026-11-09 15:21 from DEV family: in a terminal: the file-changing command the task itself asks for
fixes 4, breaks 0."""
def rule(ev, cmd, st, screen):
    """find START... [-name/-iname PAT] [-type f] [-maxdepth N] -exec cp|mv [opts] {} DEST \\;  -> copies/moves matched files into DEST."""
    if not cmd:
        return None
    try:
        import shlex
        toks = shlex.split(cmd.strip())
    except Exception:
        return None
    if not toks or toks[0] != "find":
        return None
    # Only handle a single plain command (no pipes / chaining).
    for t in toks:
        if t in ("|", "&&", "||", ">", ">>") or (t.endswith(";") and t != ";"):
            return None
    if toks.count(";") > 1:
        return None

    home = "/home/user"
    cwd = None
    for t in (st.titles or []):
        m = re.match(r"^[^@\s]+@[^:]+:\s*(.*)$", t)
        if m:
            d = m.group(1).strip()
            if d == "~" or d == "":
                cwd = home
            elif d.startswith("~/"):
                cwd = home + d[1:]
            elif d.startswith("/"):
                cwd = d
            break
    if cwd is None:
        return None

    def resolve(p):
        if p.startswith("$HOME"):
            p = home + p[5:]
        if p == "~":
            p = home
        elif p.startswith("~/"):
            p = home + p[1:]
        if not p.startswith("/"):
            p = posixpath.join(cwd, p)
        return posixpath.normpath(p)

    i = 1
    starts = []
    while i < len(toks) and not toks[i].startswith("-"):
        starts.append(toks[i])
        i += 1
    if not starts:
        starts = ["."]

    patterns = []   # (pattern, case_insensitive)
    maxdepth = None
    mindepth = 0
    op = None
    opts = []
    dest = None
    while i < len(toks):
        t = toks[i]
        if t in ("-name", "-iname") and i + 1 < len(toks):
            patterns.append((toks[i + 1], t == "-iname"))
            i += 2
        elif t == "-type" and i + 1 < len(toks):
            if toks[i + 1] != "f":
                return None
            i += 2
        elif t == "-maxdepth" and i + 1 < len(toks):
            try:
                maxdepth = int(toks[i + 1])
            except ValueError:
                return None
            i += 2
        elif t == "-mindepth" and i + 1 < len(toks):
            try:
                mindepth = int(toks[i + 1])
            except ValueError:
                return None
            i += 2
        elif t == "-exec":
            rest = toks[i + 1:]
            if not rest or rest[-1] != ";":
                return None
            rest = rest[:-1]
            if not rest or rest[0] not in ("cp", "mv"):
                return None
            op = rest[0]
            args = rest[1:]
            opts = [a for a in args if a.startswith("-")]
            pos = [a for a in args if not a.startswith("-")]
            if len(pos) != 2 or pos[0] != "{}":
                return None
            for o in opts:
                if o not in ("-f", "-p", "-v", "-n", "-i", "--preserve", "-a", "--force", "--verbose"):
                    return None
            dest = pos[1]
            i = len(toks)
        else:
            return None
    if op is None or dest is None or "{}" in dest:
        return None

    destd = resolve(dest)
    if destd not in st.dirs:
        return None   # copying to a file name / missing dir: unsure
    no_clobber = "-n" in opts

    roots = [resolve(s) for s in starts]
    for r in roots:
        if r not in st.dirs:
            return None

    matched = []
    for path in sorted(st.files):
        for r in roots:
            if not path.startswith(r + "/"):
                continue
            rel = path[len(r) + 1:]
            depth = rel.count("/") + 1
            if maxdepth is not None and depth > maxdepth:
                continue
            if depth < mindepth:
                continue
            base = posixpath.basename(path)
            ok = True
            for pat, ci in patterns:
                if ci:
                    if not fnmatch.fnmatchcase(base.lower(), pat.lower()):
                        ok = False
                else:
                    if not fnmatch.fnmatchcase(base, pat):
                        ok = False
            if ok:
                matched.append(path)
            break

    by_target = {}
    for src in matched:
        if posixpath.dirname(src) == destd:
            continue  # same file: cp/mv complains and does nothing
        tgt = posixpath.join(destd, posixpath.basename(src))
        by_target.setdefault(tgt, []).append(src)

    files = {}
    for tgt, srcs in by_target.items():
        if no_clobber and tgt in st.files:
            continue
        if len(srcs) == 1:
            files[tgt] = ("content", srcs[0])
        else:
            files[tgt] = ("sym", "find -exec %s: several files named %s, last one found wins"
                          % (op, posixpath.basename(tgt)))
        if op == "mv":
            for s in srcs:
                if s not in by_target:
                    files[s] = ("absent",) if len(srcs) == 1 else ("maybe-absent",)
            if len(srcs) > 1:
                for s in srcs:
                    files[s] = ("absent",)

    return Delta(files=files, windows="same", rules=["terminal find -exec %s" % op])
