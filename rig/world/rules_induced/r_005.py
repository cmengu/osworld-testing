"""Induced 2026-11-09 15:24 from DEV family: gdm_conf_overwrite_same_vs_autologin
fixes 6, breaks 0."""
def rule(ev, cmd, st, screen):
    """Copying a config file from the home folder over a GDM config file in /etc with sudo cp.
    Nothing under /home/user is written by the copy itself. If the source is missing, cp fails
    and nothing changes. If the source exists, it may be a link to the target or get rewritten
    afterwards (autologin settings), so its content is uncertain."""
    if not cmd:
        return None
    segments = [s.strip() for s in re.split(r"\s*(?:;|&&|\|\|)\s*", cmd) if s.strip()]
    if len(segments) != 1:
        return None
    seg = segments[0]
    # optional "echo ... | sudo -S [-p '...']" prefix, then cp [-flags] SRC DST
    m = re.match(
        r"""^(?:echo\s+\S+\s*\|\s*)?(?:sudo\s+(?:-S\s+)?(?:-p\s+(?:'[^']*'|"[^"]*"|\S+)\s+)?(?:-S\s+)?)?"""
        r"""cp\s+(?:-[a-zA-Z]+\s+)*(['"]?)([^\s'"]+)\1\s+(['"]?)([^\s'"]+)\3\s*$""",
        seg,
    )
    if not m:
        return None
    src = m.group(2)
    dst = m.group(4)
    if src.startswith("~/"):
        src = "/home/user/" + src[2:]
    src = posixpath.normpath(src)
    dst = posixpath.normpath(dst)
    if not src.startswith("/home/user/"):
        return None
    if not dst.startswith("/etc/gdm3"):
        return None
    if src in st.dirs:
        return None
    if src not in st.files:
        # cp fails: source does not exist -> nothing changes
        return Delta(files={}, windows="same", rules=["gdm_conf_overwrite_same_vs_autologin"])
    return Delta(
        files={src: ("sym-or-same", "gdm config source may be linked to/rewritten from target")},
        windows="same",
        rules=["gdm_conf_overwrite_same_vs_autologin"],
    )
