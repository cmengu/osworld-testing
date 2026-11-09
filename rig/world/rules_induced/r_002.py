"""Induced 2026-11-09 15:22 from DEV family: git_checkout_clean_vs_dirty
fixes 8, breaks 0."""
def rule(ev, cmd, st, screen):
    """git checkout -- <paths>: tracked files under the pathspec go back to their committed
    content (dirty files change, clean or untracked files stay the same)."""
    if not cmd:
        return None
    try:
        import shlex
    except Exception:
        return None

    home = "/home/user"

    def norm(p, base):
        if p.startswith("~"):
            p = home + p[1:]
        if not p.startswith("/"):
            p = posixpath.join(base, p)
        return posixpath.normpath(p)

    # Split into simple commands; allow an optional leading "cd DIR".
    parts = [p.strip() for p in re.split(r"\s*(?:;|&&)\s*", cmd) if p.strip()]
    if not parts:
        return None
    cwd = home
    git_part = None
    for p in parts:
        try:
            toks = shlex.split(p)
        except Exception:
            return None
        if not toks:
            continue
        if toks[0] == "cd" and git_part is None:
            if len(toks) > 2:
                return None
            cwd = norm(toks[1], cwd) if len(toks) == 2 else home
            continue
        if toks[0] == "git" and git_part is None:
            git_part = toks
            continue
        return None  # any other command: not sure
    if git_part is None:
        return None

    toks = git_part[1:]
    repo_dir = cwd
    # Global options before the subcommand
    while toks and toks[0].startswith("-"):
        if toks[0] == "-C" and len(toks) >= 2:
            repo_dir = norm(toks[1], repo_dir)
            toks = toks[2:]
        elif toks[0] in ("--no-pager", "-q"):
            toks = toks[1:]
        else:
            return None
    if not toks or toks[0] != "checkout":
        return None
    args = toks[1:]

    # Only handle the "restore working tree" form, never a branch switch.
    pathspecs = []
    seen_dd = False
    pre = []
    for a in args:
        if seen_dd:
            pathspecs.append(a)
        elif a == "--":
            seen_dd = True
        elif a in ("-q", "--quiet", "-f", "--force"):
            continue
        elif a.startswith("-"):
            return None
        else:
            pre.append(a)
    if seen_dd:
        if pre:  # e.g. "checkout HEAD -- ." or "checkout branch -- f": content unknown, skip
            return None
    else:
        # Without "--", only accept arguments that are clearly existing paths.
        for a in pre:
            p = norm(a, repo_dir)
            if not (a == "." or p in st.files or p in st.dirs):
                return None
        pathspecs = pre
    if not pathspecs:
        return None

    # The repository must exist (when we can tell).
    if repo_dir not in st.dirs and not any(f.startswith(repo_dir + "/") for f in st.files):
        return None

    targets = [norm(p, repo_dir) for p in pathspecs]
    if any(any(c in t for c in "*?[") for t in targets):
        return None

    files = {}
    for path in st.files:
        if not path.startswith(repo_dir + "/"):
            continue
        rel = path[len(repo_dir) + 1:]
        if rel == ".git" or rel.startswith(".git/") or "/.git/" in "/" + rel:
            continue
        for t in targets:
            if path == t or path.startswith(t.rstrip("/") + "/"):
                files[path] = ("sym-or-same", "git checkout restores tracked file if it was modified")
                break

    return Delta(files=files, windows="same", rules=["git_checkout_clean_vs_dirty"])
