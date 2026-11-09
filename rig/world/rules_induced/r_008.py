"""Induced 2026-11-09 15:31 from DEV family: in a terminal: sed -i rewrites a task file in place
fixes 4, breaks 0."""
def rule(ev, cmd, st, screen):
    """sed -i (in-place edit) typed into a terminal: the named existing files are rewritten in place."""
    if not cmd or "sed" not in cmd:
        return None
    if any(c in cmd for c in ("|", ">", "<", "&&", "||", "`", "$(")):
        return None

    home = "/home/user"

    # Work out the terminal's current directory from its window title ("user@host: ~/dir").
    cwd = None
    for t in st.titles or []:
        m = re.match(r"^[^@\s]+@[^:]+:\s*(.*)$", t)
        if m:
            p = m.group(1).strip()
            if p == "~" or p.startswith("~/"):
                p = home + p[1:]
            if not p.startswith("/"):
                continue
            if cwd is not None and cwd != p:
                return None  # Several terminals in different folders: ambiguous.
            cwd = p
    if cwd is None:
        cwd = home

    # Split the command into words, honouring quotes.
    def split(s):
        try:
            import shlex
            return shlex.split(s)
        except Exception:
            return None

    segments = [s.strip() for s in cmd.split(" ; ") if s.strip()]
    if not segments:
        return None

    targets = []
    saw_sed = False
    for seg in segments:
        toks = split(seg)
        if not toks:
            return None

        # Allow a leading "cd DIR" that changes the working directory.
        if toks[0] == "cd":
            if len(toks) > 2:
                return None
            d = toks[1] if len(toks) == 2 else "~"
            if d == "~" or d.startswith("~/"):
                d = home + d[1:]
            d = posixpath.normpath(posixpath.join(cwd, d))
            if d not in st.dirs and d != home:
                return None
            cwd = d
            continue

        if posixpath.basename(toks[0]) != "sed":
            return None  # Some other command whose effect we don't model here.
        saw_sed = True

        inplace = False
        have_script = False
        files = []
        i = 1
        while i < len(toks):
            t = toks[i]
            if t in ("-i", "--in-place"):
                inplace = True
            elif t.startswith("--in-place="):
                return None  # Backup suffix: an extra file would appear.
            elif t.startswith("-i") and len(t) > 2:
                return None  # e.g. -i.bak creates a backup file.
            elif t in ("-e", "--expression", "-f", "--file"):
                if i + 1 >= len(toks):
                    return None
                have_script = True
                i += 1
            elif t.startswith("--expression=") or t.startswith("--file="):
                have_script = True
            elif t in ("-E", "-r", "-n", "-s", "-z", "-u",
                       "--regexp-extended", "--quiet", "--silent",
                       "--separate", "--null-data", "--posix", "--follow-symlinks"):
                pass
            elif t.startswith("-") and len(t) > 1 and re.fullmatch(r"-[Ernsuz]*i?[Ernsuz]*", t):
                if "i" in t:
                    if not t.endswith("i") and t.index("i") != len(t) - 1:
                        return None  # Combined flags with a suffix after i.
                    inplace = True
            elif t.startswith("-"):
                return None  # Unknown option.
            elif not have_script:
                have_script = True  # First non-option word is the script.
            else:
                files.append(t)
            i += 1

        if not inplace or not have_script or not files:
            return None

        for f in files:
            if f == "~" or f.startswith("~/"):
                f = home + f[1:]
            full = posixpath.normpath(posixpath.join(cwd, f))
            if any(ch in f for ch in "*?["):
                matched = [p for p in st.files
                           if posixpath.dirname(p) == posixpath.dirname(full)
                           and fnmatch.fnmatch(posixpath.basename(p), posixpath.basename(full))]
                if not matched:
                    return None
                targets.extend(matched)
            else:
                if full not in st.files:
                    return None  # Missing file: sed errors, nothing changes (or unknown).
                targets.append(full)

    if not saw_sed or not targets:
        return None

    files = {p: ("sym-or-same", "sed -i edits in place") for p in targets}
    return Delta(files=files, windows="same", rules=["terminal-sed-inplace"])
