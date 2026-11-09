"""T(s, a) -> predicted change set (P1 of rig/plan_forward_model.md, 9 Nov 2026).

A prediction is a Delta:
    files    path -> value, for every path the step changes:
                ("absent",)            the path no longer exists
                ("content", src)       it holds exactly what `src` held before the step
                ("empty",)             an empty file
                ("dir",)               a folder exists there
                ("sym", why)           it exists with content the state cannot know (an editor's buffer, a command's output)
             paths not listed are predicted unchanged
    windows  "same" | "closes" | "opens" | "unknown"     (the set of window titles before vs after)
    system   set of system keys predicted to change (crontab, sudoers_d_sha, hosts, ...)
T returns None when no rule covers the step (the guard then asks Claude).

Rules are those of rig/symbolic.py and rig/symbolic_gui.py, rewritten to say WHAT changes instead of whether it can be
undone; harm and reversibility are derived from the Delta in P2.
"""
import fnmatch
import posixpath
import re
import shlex
from dataclasses import dataclass, field
from typing import Dict, Optional, Set

from rig.symbolic import HOME, READ_ONLY, TRASH, _SUDO, _abs, typed_command, terminal_focused
from rig.symbolic_gui import Screen, events

TRASH_INFO = "/home/user/.local/share/Trash/info/"


@dataclass
class Delta:
    files: Dict[str, tuple] = field(default_factory=dict)
    windows: str = "same"
    system: Set[str] = field(default_factory=set)
    rules: list = field(default_factory=list)          # the rules that fired, for the ledger

    def merge(self, other: "Delta"):
        self.files.update(other.files)
        order = ["same", "opens", "closes", "unknown"]
        if order.index(other.windows) > order.index(self.windows):
            self.windows = other.windows
        self.system |= other.system
        self.rules += other.rules


class WState:
    """The parts of a snapshot T reads."""

    def __init__(self, snap):
        self.digest = snap.digest
        self.files = {p: v for p, v in snap.digest.items() if not p.endswith("/") and not p.startswith("/@")}
        self.dirs = {p.rstrip("/") for p in snap.digest if p.endswith("/")}
        self.windows = snap.windows or ""
        self.titles = [l.split(None, 3)[3] for l in self.windows.splitlines() if len(l.split(None, 3)) == 4 and "@!" not in l]
        self.tree = snap.tree_xml or ""
        self.system = snap.system or {}

    def exists(self, p):
        return p in self.files or p in self.dirs

    def under(self, d):
        d = d.rstrip("/") + "/"
        return [p for p in self.files if p.startswith(d)], [x for x in self.dirs if x.startswith(d)]

    def doc_path(self, basename):
        hits = [p for p in self.files if posixpath.basename(p) == basename]
        return hits[0] if len(hits) == 1 else None

    def lock_of(self, path):
        return posixpath.join(posixpath.dirname(path), ".~lock." + posixpath.basename(path) + "#")


# ------------------------------------------------------------------------------------------------------------ shell
def shell(cmd: str, st: WState) -> Optional[Delta]:
    m = _SUDO.match(cmd)
    if m:
        cmd = cmd[m.end():]
    cmd = re.sub(r"\s[12]?>\s*/dev/null|\s2>&1", "", cmd)
    d, cwd = Delta(), HOME
    for part in [p.strip().strip("()").strip() for p in re.split(r"\s*(?:&&|\|\||;)\s*", cmd) if p.strip()]:
        one, cwd = _shell_one(part, st, cwd)
        if one is None:
            return None
        d.merge(one)
    return d


def _new(d, path, value, rule):
    d.files[path] = value
    d.rules.append(rule)


def _shell_one(part, st, cwd):
    d = Delta()
    try:
        toks = shlex.split(part)
    except ValueError:
        return None, cwd
    if not toks:
        return d, cwd
    ops = [i for i, t in enumerate(toks) if t in (">", ">>")]
    if ops and ops[-1] == len(toks) - 2 and toks[0] not in ("find", "rsync"):
        i = ops[-1]
        lhs, op, target = toks[:i], toks[i], _abs(cwd, toks[i + 1])
        if lhs in ([], [":"], ["true"]):
            if target in st.files and op == ">>":
                return d, cwd
            if not (target in st.files and st.files[target].get("s") == 0):   # an empty file stays as it is
                _new(d, target, ("empty",), "truncate with a redirect")
            return d, cwd
        _new(d, target, ("sym", f"output of {lhs[0]}"), "redirect")
        return d, cwd
    if "|" in part:
        stages = [s.strip().split()[0] for s in part.split("|") if s.strip()]
        return (d, cwd) if all(s in READ_ONLY for s in stages) and " -i" not in part else (None, cwd)
    cmd, args = toks[0], toks[1:]
    flags = {a for a in args if a.startswith("-")}
    pos = [a for a in args if not a.startswith("-")]
    if cmd == "cd":
        return d, (_abs(cwd, pos[0]) if pos else HOME)
    if cmd in READ_ONLY and not (cmd in ("sed", "awk") and any(a.startswith("-i") for a in args)) \
            and not (cmd == "find" and ("-delete" in args or "-exec" in args)) and not (cmd == "git" and args[:1] not in (["status"], ["log"], ["diff"], ["show"])):
        return d, cwd
    if cmd == "mkdir":
        for p in pos:
            a = _abs(cwd, p)
            if not st.exists(a):
                _new(d, a + "/", ("dir",), "mkdir")
        return d, cwd
    if cmd == "touch":
        for p in pos:
            a = _abs(cwd, p)
            if not st.exists(a):
                _new(d, a, ("empty",), "touch new")
        return d, cwd
    if cmd == "rmdir":
        for p in pos:
            _new(d, _abs(cwd, p) + "/", ("absent",), "rmdir")
        return d, cwd
    if cmd in ("mv", "cp") and len(pos) >= 2:
        srcs, dst = [_abs(cwd, p) for p in pos[:-1]], _abs(cwd, pos[-1])
        if dst.startswith("/etc/"):
            if dst.startswith("/etc/sudoers.d/"):
                d.system.add("sudoers_d_sha")
                if posixpath.basename(dst) not in st.system.get("sudoers_d", []):
                    d.system.add("sudoers_d")
                d.rules.append("sudo cp into sudoers.d")
                return d, cwd
            if dst in ("/etc/hosts",):
                d.system.add("hosts")
                d.rules.append("cp over /etc/hosts")
                return d, cwd
            return None, cwd
        if not all(st.exists(s) for s in srcs):
            return d, cwd                                  # the command fails: nothing changes
        for s in srcs:
            t = posixpath.join(dst, posixpath.basename(s)) if dst in st.dirs else dst
            if s in st.dirs:
                if cmd == "mv":
                    files, dirs = st.under(s)
                    for f in files:
                        _new(d, t + f[len(s):], ("content", f), "mv dir")
                        _new(d, f, ("absent",), "mv dir")
                    _new(d, s + "/", ("absent",), "mv dir")
                    _new(d, t + "/", ("dir",), "mv dir")
                    continue
                return None, cwd
            if t == s:
                continue
            if cmd == "cp" and t in st.files and st.files[t].get("h") == st.files[s].get("h"):
                continue
            _new(d, t, ("content", s), f"{cmd}")
            if cmd == "mv":
                _new(d, s, ("absent",), "mv")
        return d, cwd
    if cmd == "rm":
        recursive = any(f in flags for f in ("-r", "-rf", "-fr", "-R", "-d"))
        for p in pos:
            a = _abs(cwd, p)
            targets = ([q for q in list(st.files) + list(st.dirs) if posixpath.dirname(q) == posixpath.dirname(a)
                        and fnmatch.fnmatch(posixpath.basename(q), posixpath.basename(a))] if any(c in p for c in "*?[") else [a])
            for t in targets:
                if t in st.files:
                    _new(d, t, ("absent",), "rm")
                elif t in st.dirs and recursive:
                    files, dirs = st.under(t)
                    for f in files:
                        _new(d, f, ("absent",), "rm -r")
                    for x in dirs + [t]:
                        _new(d, x + "/", ("absent",), "rm -r")
        return d, cwd
    if cmd == "truncate" and "-s" in args and pos and pos[0] == "0" and len(pos) > 1:
        t = _abs(cwd, pos[1])
        if t not in st.files or st.files[t].get("s") != 0:
            _new(d, t, ("empty",), "truncate -s 0")
        return d, cwd
    if cmd == "ln" and flags & {"-s", "-sf", "-fs"} and len(pos) == 2:
        _new(d, _abs(cwd, pos[1]), ("link", pos[0]), "ln -s")
        return d, cwd
    if cmd == "find" and "-delete" in args and pos:
        root = _abs(cwd, pos[0])
        pat = args[args.index("-name") + 1] if "-name" in args else "*"
        for f in st.under(root)[0]:
            if fnmatch.fnmatch(posixpath.basename(f), pat):
                _new(d, f, ("absent",), "find -delete")
        return d, cwd
    if cmd == "rsync" and "--delete" in args and len(pos) >= 2:
        src, dst = _abs(cwd, pos[-2]).rstrip("/"), _abs(cwd, pos[-1]).rstrip("/")
        sf, df = st.under(src)[0], st.under(dst)[0]
        rel_s = {p[len(src) + 1:]: p for p in sf}
        rel_d = {p[len(dst) + 1:]: p for p in df}
        for r, p in rel_d.items():
            if r not in rel_s:
                _new(d, p, ("absent",), "rsync --delete")
            elif st.files[p].get("h") != st.files[rel_s[r]].get("h"):
                _new(d, p, ("content", rel_s[r]), "rsync update")
        for r, p in rel_s.items():
            if r not in rel_d:
                _new(d, dst + "/" + r, ("content", p), "rsync add")
        return d, cwd
    if cmd == "gio" and args[:1] == ["trash"]:
        if "--empty" in args:
            for p in st.files:
                if p.startswith((TRASH, TRASH_INFO)):
                    _new(d, p, ("absent",), "empty Trash")
            return d, cwd
        for p in pos[1:]:
            a = _abs(cwd, p)
            if a in st.files:
                _new(d, a, ("absent",), "gio trash")
                _new(d, TRASH + posixpath.basename(a), ("content", a), "gio trash")
                _new(d, TRASH_INFO + posixpath.basename(a) + ".trashinfo", ("sym", "trash info"), "gio trash")
        return d, cwd
    if cmd in ("libreoffice", "soffice", "code", "xdg-open", "nautilus", "gedit", "evince", "eog"):
        d.windows = "opens"
        d.rules.append(f"{cmd} opens a window")
        if cmd in ("libreoffice", "soffice"):
            for p in pos:
                a = _abs(cwd, p)
                if a in st.files:
                    d.files[st.lock_of(a)] = ("sym-or-same", "LibreOffice lock")
        return d, cwd
    if cmd == "crontab" and len(pos) == 1 and not flags:
        d.system.add("crontab")
        d.rules.append("crontab FILE")
        return d, cwd
    if cmd == "chmod" and len(pos) >= 2 and re.fullmatch(r"[0-7]{3,4}", pos[0]):
        for p in pos[1:]:
            a = _abs(cwd, p)
            if a in st.files or a in st.dirs:
                key = a if a in st.files else a + "/"
                _new(d, key, ("mode", int(pos[0], 8)), "chmod")
        return d, cwd
    return None, cwd


# -------------------------------------------------------------------------------------------------------------- GUI
DOC_RE = re.compile(r"^(.+?) - (LibreOffice (?:Writer|Calc|Impress)|Visual Studio Code)$")


def gui(code: str, st: WState) -> Optional[Delta]:
    ev = events(code)
    if ev == [("not-code",)]:
        return Delta(rules=["not code"])
    if not ev:
        return None
    screen = Screen(st.tree, st.windows)
    q = screen.question()
    front = next((t for t in st.titles if DOC_RE.match(t.lstrip("●* "))), None)
    if front is None and any(t.endswith("Mozilla Thunderbird") for t in st.titles):
        return None                                         # Thunderbird rewrites its mail store: not modelled
    folder = _files_folder(st) if front is None else None
    selected = _selected(st, folder) if folder else []
    d = Delta()
    i = 0
    while i < len(ev):
        e = ev[i]
        i += 1
        kind = e[0]
        k = e[1] if kind in ("key", "hotkey") else None
        if kind in ("maybe-enter", "view"):
            continue
        nxt = ev[i:]
        # Save As: Ctrl+Shift+S, a name, Enter -> a new file, or the replace question when the name exists
        if k == "ctrl+shift+s" and nxt[:1] and nxt[0][0] == "type" and front and (len(nxt) > 1 and nxt[1][:2] in (("key", "enter"), ("key", "return"))):
            m = DOC_RE.match(front.lstrip("●* "))
            cur = st.doc_path(m.group(1)) if m else None
            if cur is None:
                return None
            name = nxt[0][1]
            if "." not in name:
                name += posixpath.splitext(cur)[1]
            target = name if name.startswith("/") else posixpath.join(posixpath.dirname(cur), name)
            i += 2
            if target in st.files:
                d.windows = "opens"; d.rules.append("Save As onto an existing name: the replace question")
                q = "replace"; screen_named = target
                continue
            d.files[target] = ("sym", "the document saved under a new name")
            d.files[st.lock_of(target)] = ("sym-or-same", "LibreOffice lock")
            if st.lock_of(cur) in st.files:
                d.files[st.lock_of(cur)] = ("maybe-absent",)
            d.rules.append("Save As to a new name")
            continue
        if q == "replace" and k in ("alt+y", "alt+r", "enter", "return"):
            name = screen.named_file()
            target = st.doc_path(name) if name else None
            if target is None:
                return None
            d.files[target] = ("sym", "overwritten by the saved document")
            d.files[st.lock_of(target)] = ("sym-or-same", "LibreOffice lock")
            if front:
                m = DOC_RE.match(front.lstrip("●* "))
                cur = st.doc_path(m.group(1)) if m else None
                if cur and st.lock_of(cur) in st.files:
                    d.files[st.lock_of(cur)] = ("maybe-absent",)
            d.windows = "unknown"; d.rules.append("Replace: the other file is overwritten"); q = None
            continue
        # GNOME Files: Delete -> Trash, Shift+Delete -> question, F2 name Enter -> rename
        if folder and k == "delete" and selected:
            for p in selected:
                name = posixpath.basename(p)
                d.files[p] = ("absent",)
                d.files[TRASH + name] = ("content", p)
                d.files[TRASH_INFO + name + ".trashinfo"] = ("sym", "trash info")
            d.rules.append("Files: Delete moves the selection to the Trash")
            continue
        if folder and k == "shift+delete":
            d.windows = "opens"; d.rules.append("Files: Shift+Delete asks first")
            continue
        if folder and k == "f2" and nxt[:1] and nxt[0][0] == "type" and len(selected) == 1:
            new = posixpath.join(posixpath.dirname(selected[0]), nxt[0][1])
            d.files[new] = ("content", selected[0]); d.files[selected[0]] = ("absent",)
            d.rules.append("Files: F2 renames the selection")
            i += 2 if len(nxt) > 1 and nxt[1][:2] in (("key", "enter"), ("key", "return")) else 1
            continue
        # menus: Alt+letter opens a menu; arrows and Enter pick an in-app command (not the File menu)
        if kind == "hotkey" and re.fullmatch(r"alt\+[a-z]", k or "") and not q:
            if k == "alt+f" and any(x[:2] in (("key", "enter"), ("key", "return")) for x in nxt):
                return None
            d.rules.append("menu"); continue
        if q:
            if k in ("escape", "esc"):
                d.windows = "closes"; d.rules.append("Escape closes the question"); q = None; continue
            if q == "save-changes" and k in ("alt+n",):
                d.windows = "closes"; d.rules.append("Don't Save closes the document")
                if front:
                    m = DOC_RE.match(front.lstrip("●* "))
                    p = st.doc_path(m.group(1)) if m else None
                    if p and st.lock_of(p) in st.files:
                        d.files[st.lock_of(p)] = ("absent",)
                q = None; continue
            if q == "delete" and k in ("alt+d", "enter", "return"):
                name = screen.named_file()
                p = st.doc_path(name) if name else None
                if p is None:
                    return None
                d.files[p] = ("absent",); d.windows = "closes"; d.rules.append("permanent delete"); q = None; continue
            if q == "empty-trash" and k in ("alt+t", "enter", "return"):
                for p in st.files:
                    if p.startswith((TRASH, TRASH_INFO)):
                        d.files[p] = ("absent",)
                d.windows = "closes"; d.rules.append("Empty Trash"); q = None; continue
            return None
        if kind == "type" or (kind == "key" and k in ("up", "down", "left", "right", "home", "end", "pageup", "pagedown", "tab",
                                                       "shift", "space", "backspace", "delete", "enter", "return", "f5", "escape")):
            if k == "delete" and front is None and any(t in ("Desktop", "Home", "Documents", "Downloads") for t in st.titles):
                return None                                 # Files: Delete moves the selection to the Trash; selection unknown here
            d.rules.append("in-app edit: no file changes yet")
            continue
        if kind == "hotkey" and k in ("ctrl+a", "ctrl+b", "ctrl+i", "ctrl+u", "ctrl+z", "ctrl+y", "ctrl+x", "ctrl+c", "ctrl+v",
                                      "ctrl+home", "ctrl+end", "ctrl+space", "shift+space", "ctrl+-", "ctrl+m", "ctrl+shift+right",
                                      "ctrl+shift+left", "ctrl+shift+end", "ctrl+shift+home", "ctrl+shift+k", "ctrl+f12", "shift+tab"):
            d.rules.append("in-app edit: no file changes yet")
            continue
        if kind == "hotkey" and k in ("ctrl+p", "ctrl+o", "ctrl+h", "ctrl+1", "ctrl+shift+s", "ctrl+f", "ctrl+shift+p"):
            d.windows = "opens" if k in ("ctrl+p", "ctrl+o", "ctrl+shift+s") else d.windows
            d.rules.append("opens a dialog or panel")
            continue
        if k in ("ctrl+w", "ctrl+q", "alt+f4"):
            d.windows = "unknown"                           # closes, or a question opens: the dirty flag decides
            if front:
                m = DOC_RE.match(front.lstrip("●* "))
                p = st.doc_path(m.group(1)) if m else None
                if p and st.lock_of(p) in st.files:
                    d.files[st.lock_of(p)] = ("maybe-absent",)   # a clean document closes and its lock goes
            d.rules.append("close")
            continue
        if k == "ctrl+s":
            if front is None:
                return None
            m = DOC_RE.match(front.lstrip("●* "))
            p = st.doc_path(m.group(1)) if m else None
            if p is None:
                return None
            d.files[p] = ("sym-or-same", "the editor's buffer")
            d.rules.append("save writes the buffer")
            continue
        return None
    return d


def _files_folder(st: WState) -> Optional[str]:
    """The folder a GNOME Files window shows (its title is the folder's name)."""
    for t in st.titles:
        if t == "Home":
            return HOME
        hits = [x for x in st.dirs if posixpath.basename(x) == t and x.startswith(HOME)]
        if len(hits) == 1:
            return hits[0]
    return None


def _selected(st: WState, folder: str):
    names = set(re.findall(r'name="([^"]+)"[^>]*st:selected="true"', st.tree)) | set(re.findall(r'st:selected="true"[^>]*name="([^"]+)"', st.tree))
    return [p for p in st.files if posixpath.dirname(p) == folder and posixpath.basename(p) in names]


def T(code: str, st: WState) -> Optional[Delta]:
    cmd = typed_command(code)
    if cmd is not None and terminal_focused(st.windows) is not False:
        return shell(cmd, st)
    return gui(code, st)
