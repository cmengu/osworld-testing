"""Symbolic world model for shell steps (9 Nov 2026, author: "go with your recommendation" -> the hybrid guard).

The learned model failed to generalise (pair test 9 Nov: ours 11/32, Claude 28/32, held-out families 0/9).  This module
predicts reversibility the way the rig defines it, by simulating the step on the recorded state instead of learning it:

    state   = every file under /home/user with its content hash (digest.json), the Trash, folders, the windows (an editor
              whose title names a file still holds that file's text), and the system section (crontab, sudoers.d hashes).
    step    = a typed shell command (pyautogui.typewrite ... enter), split on && and ;, with cd tracked and an
              "echo PW | sudo -S" prefix understood.
    verdict = "noop"        the command changes nothing (target missing, already empty, nothing matches)   -> undoable
              "reversible"  everything it removes or overwrites survives somewhere (another file with the same
                            content, the Trash, an open editor), or it only adds things                       -> undoable
              "oneway"      some content ends up nowhere                                                       -> one-way
              None          not modelled (GUI actions, git, unknown commands, /etc files whose content the
                            state does not hash): the hybrid asks Claude

The semantics are those of the commands (coreutils, findutils, rsync, gio, crontab), written before looking at how the
learned model or Claude did on any family; the rules were checked on TRAINING rows first.  K = 3 holds for every
"reversible" case modelled here (an inverse command, a re-save, a restore from Trash, at most a chmod).

    OSWorld/.venv/bin/python -I rig/symbolic.py eval      # dev on training rows, then the pair test, the hybrid vs Claude
"""
import ast
import fnmatch
import json
import os
import posixpath
import re
import shlex
import sys
from typing import Dict, List, Optional, Tuple

HOME = "/home/user"
TRASH = "/home/user/.local/share/Trash/files/"
_TYPEWRITE = re.compile(r"""pyautogui\.typewrite\(("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')""")
_SUDO = re.compile(r"^\s*echo\s+\S+\s*\|\s*sudo\s+-S(?:\s+-p\s+(?:''|\"\"))?\s+")


def typed_command(code: str) -> Optional[str]:
    """The shell command a step types into a terminal, or None when the step is not a typed command."""
    m = _TYPEWRITE.search(code or "")
    if not m:
        return None
    try:
        text = ast.literal_eval(m.group(1).replace("\n", "\\n"))      # agent steps carry a raw newline in the string
    except (ValueError, SyntaxError):
        return None
    if not (text.endswith("\n") or "enter" in (code or "")):
        return None                                                     # typed but never run
    cmd = text.strip()
    return cmd if cmd and "\n" not in cmd else None                    # one command line only


class State:
    def __init__(self, digest: Dict[str, dict], windows: str = "", system: dict = None):
        self.files = {p: v.get("h") for p, v in digest.items() if not p.endswith("/") and not p.startswith("/@")}
        self.sizes = {p: v.get("s") for p, v in digest.items() if not p.endswith("/") and not p.startswith("/@")}
        self.dirs = {p.rstrip("/") for p in digest if p.endswith("/")}
        titles = [l.split(None, 3)[3] if len(l.split(None, 3)) == 4 else "" for l in (windows or "").splitlines()]
        self.editor_files = {t.lstrip("●* ").split(" - ")[0] for t in titles if " - " in t}
        self.system = system or {}

    def exists(self, p):
        return p in self.files or p in self.dirs

    def kept_elsewhere(self, h, gone: set) -> bool:
        """Content h survives after the step: another file still holds it (the Trash included)."""
        return any(q not in gone and hh == h for q, hh in self.files.items())

    def held_open(self, p) -> bool:
        return posixpath.basename(p) in self.editor_files

    def under(self, d):
        d = d.rstrip("/") + "/"
        return [p for p in self.files if p.startswith(d)], [x for x in self.dirs if x.startswith(d)]


def _abs(cwd, p):
    p = HOME + p[1:] if p.startswith("~") else p          # the VM's home, never this machine's
    return posixpath.normpath(p if p.startswith("/") else posixpath.join(cwd, p))


def _loses(st: State, paths: List[str], gone: set) -> Tuple[bool, str]:
    """Does removing/overwriting these files lose content?  (True, why) when some content ends up nowhere."""
    for p in paths:
        if p not in st.files:
            continue
        if st.sizes.get(p) == 0:
            continue                                      # an empty file: nothing to lose
        if st.kept_elsewhere(st.files[p], gone) or st.held_open(p):
            continue
        return True, f"{p} ({st.sizes.get(p)} B) survives nowhere"
    return False, ""


def simulate(cmd: str, st: State) -> Tuple[Optional[str], str]:
    sudo = False
    m = _SUDO.match(cmd)
    if m:
        sudo, cmd = True, cmd[m.end():]
    parts = [p.strip() for p in re.split(r"\s*(?:&&|;)\s*", cmd) if p.strip()]
    cwd, verdicts = HOME, []
    for part in parts:
        v, why, cwd = _one(part, st, cwd, sudo)
        if v is None:
            return None, why
        verdicts.append((v, why))
    for want in ("oneway", "reversible", "noop"):
        for v, why in verdicts:
            if v == want:
                return v, why
    return None, "empty command"


def _one(part, st: State, cwd, sudo):
    redirect = re.match(r"^(.*?)\s(>>?)\s*(\S+)\s*$", part)
    if redirect and not part.startswith(("find ", "rsync ")):
        lhs, op, target = redirect.group(1).strip(), redirect.group(2), _abs(cwd, redirect.group(3))
        if lhs in (":", "true", ""):
            if op == ">>" or target not in st.files:
                return ("reversible" if target not in st.files else "noop"), f"{part}: creates or keeps {target}", cwd
            if st.sizes.get(target) == 0:
                return "noop", f"{target} is already empty", cwd
            lost, why = _loses(st, [target], {target})
            return ("oneway" if lost else "reversible"), why or f"{target}'s content survives", cwd
        if op == ">>":
            return "reversible", f"appends to {target} (truncate back)", cwd
        if target not in st.files or st.sizes.get(target) == 0:
            return "reversible", f"writes a new or empty {target} (remove or empty it again)", cwd
        lost, why = _loses(st, [target], {target})
        return ("oneway" if lost else "reversible"), (why or f"{target}'s old content survives"), cwd
    try:
        argv = shlex.split(part)
    except ValueError:
        return None, f"cannot parse {part!r}", cwd
    if not argv:
        return "noop", "empty", cwd
    cmd, args = argv[0], argv[1:]
    flags = {a for a in args if a.startswith("-")}
    pos = [a for a in args if not a.startswith("-")]
    if cmd == "cd":
        return "noop", "cd", _abs(cwd, pos[0]) if pos else HOME
    if cmd in ("ls", "cat", "pwd", "echo", "printf", "head", "tail", "wc", "grep", "stat", "du", "df", "date", "true"):
        return "noop", f"{cmd} reads only", cwd
    if any(p.startswith(("/etc", "/usr", "/var", "/boot")) for p in pos) and cmd not in ("cp",):
        return None, f"{cmd} on a system path is not modelled", cwd
    if cmd in ("mkdir", "touch"):
        new = [_abs(cwd, p) for p in pos if not st.exists(_abs(cwd, p))]
        return ("reversible" if new else "noop"), f"{cmd} {'creates ' + ', '.join(new) if new else 'changes nothing'}", cwd
    if cmd == "rmdir":
        return "reversible", "rmdir of an empty folder (mkdir back)", cwd
    if cmd in ("mv", "cp") and len(pos) >= 2:
        srcs, dst = [_abs(cwd, p) for p in pos[:-1]], _abs(cwd, pos[-1])
        if dst.startswith("/etc/"):
            return _sys_cp(st, srcs, dst, sudo), f"{cmd} into {dst}", cwd
        if not all(st.exists(s) for s in srcs):
            return "noop", f"{cmd}: a source is missing, the command fails", cwd
        overwritten = []
        for s in srcs:
            t = posixpath.join(dst, posixpath.basename(s)) if dst in st.dirs else dst
            if t in st.files and t != s:
                if s in st.files and st.files[s] == st.files[t] and cmd == "cp":
                    continue                              # same content already there
                overwritten.append(t)
        if not overwritten:
            return "reversible", f"{cmd} to a free name ({'mv back' if cmd == 'mv' else 'rm the copy'})", cwd
        lost, why = _loses(st, overwritten, set(overwritten))
        return ("oneway" if lost else "reversible"), why or "the overwritten content survives", cwd
    if cmd == "rm":
        targets = [_abs(cwd, p) for p in pos]
        recursive = any(f in flags for f in ("-r", "-rf", "-fr", "-R", "-d"))
        gone, dirs_gone = [], []
        for t in targets:
            if t in st.files:
                gone.append(t)
            elif t in st.dirs:
                if not recursive:
                    return "noop", f"rm without -r refuses the folder {t}", cwd
                f, d = st.under(t)
                gone += f
                dirs_gone.append(t)
        if not gone and not dirs_gone:
            return "noop", "rm: nothing to remove", cwd
        lost, why = _loses(st, gone, set(gone))
        if lost:
            return "oneway", why, cwd
        return "reversible", ("only empty folders or content kept elsewhere/open in an editor (mkdir, re-save or copy back)"), cwd
    if cmd == "truncate" and ("-s" in args) and pos and pos[0] == "0":
        t = _abs(cwd, pos[1]) if len(pos) > 1 else None
        if t is None:
            return None, "truncate form not modelled", cwd
        if t not in st.files:
            return "reversible", f"truncate creates an empty {t}", cwd
        if st.sizes.get(t) == 0:
            return "noop", f"{t} is already empty", cwd
        lost, why = _loses(st, [t], {t})
        return ("oneway" if lost else "reversible"), why or "the content survives", cwd
    if cmd == "ln" and flags & {"-s", "-sf", "-fs"} and len(pos) == 2:
        link = _abs(cwd, pos[1])
        if link not in st.files:
            return "reversible", "a new link (rm it)", cwd
        if "-f" not in "".join(flags) and "f" not in "".join(flags):
            return "noop", "ln without -f refuses an existing name", cwd
        lost, why = _loses(st, [link], {link})
        return ("oneway" if lost else "reversible"), why or "the replaced file's content survives", cwd
    if cmd == "find" and "-delete" in args and pos:
        root = _abs(cwd, pos[0])
        pat = args[args.index("-name") + 1] if "-name" in args else "*"
        files, _ = st.under(root)
        hit = [p for p in files if fnmatch.fnmatch(posixpath.basename(p), pat)]
        if not hit:
            return "noop", f"find: nothing matches {pat}", cwd
        lost, why = _loses(st, hit, set(hit))
        return ("oneway" if lost else "reversible"), why or "the deleted files' content survives", cwd
    if cmd == "rsync" and "--delete" in args and len(pos) >= 2:
        src, dst = _abs(cwd, pos[-2]), _abs(cwd, pos[-1])
        sf, _ = st.under(src)
        df, _ = st.under(dst)
        rel_s = {p[len(src) + 1:]: st.files[p] for p in sf}
        rel_d = {p[len(dst) + 1:]: st.files[p] for p in df}
        gone = [dst + "/" + r for r in rel_d if r not in rel_s or rel_s[r] != rel_d[r]]
        if not gone and set(rel_s) <= set(rel_d):
            return "noop", "rsync: the target already equals the source", cwd
        if not gone:
            return "reversible", "rsync only adds files (rm them)", cwd
        lost, why = _loses(st, gone, set(gone))
        return ("oneway" if lost else "reversible"), why or "deleted/overwritten content survives", cwd
    if cmd == "gio" and args[:1] == ["trash"]:
        if "--empty" in args:
            in_trash = [p for p in st.files if p.startswith(TRASH)]
            if not in_trash:
                return "noop", "the Trash is already empty", cwd
            lost, why = _loses(st, in_trash, set(in_trash))
            return ("oneway" if lost else "reversible"), why or "the Trash's content survives elsewhere", cwd
        return "reversible", "moved to the Trash (restore it)", cwd
    if cmd == "crontab" and len(pos) == 1 and not flags:
        jobs = st.system.get("crontab")
        if jobs is None:
            return None, "crontab not recorded", cwd
        if not jobs:
            return "reversible", "no crontab before (crontab -r)", cwd
        return "oneway", "the user's existing jobs are replaced", cwd
    return None, f"{cmd} is not modelled", cwd


def _sys_cp(st: State, srcs, dst, sudo):
    if dst.startswith("/etc/sudoers.d/") and len(srcs) == 1:
        name = posixpath.basename(dst)
        if name not in st.system.get("sudoers_d", []):
            return "reversible"                          # a new rule (rm it)
        old = {l.split()[-1]: l.split()[0] for l in st.system.get("sudoers_d_sha", [])}.get(dst)
        new = (st.files.get(srcs[0]) or "")[:16]
        if old and new and old == new:
            return "noop"
        if old and any(h and h[:16] == old for h in st.files.values()):
            return "reversible"                          # the old rule is kept in a file
        return "oneway"
    return None                                          # /etc/hosts, gdm config: content not hashed in the state


def terminal_focused(windows: str) -> Optional[bool]:
    """Is the active window a terminal?  (9 Nov: agents also type file names into Save As dialogs and values into
    cells and press Enter; that is not a shell command.)  None when the windows text names no active window."""
    if "--- active ---" not in (windows or ""):
        return None
    active = windows.split("--- active ---", 1)[1].strip().splitlines()
    if not active:
        return None
    return bool(re.search(r"\S+@\S+:|Terminal|terminal", active[0]))


def predict(code: str, digest: dict, windows: str = "", system: dict = None) -> Tuple[Optional[str], str]:
    cmd = typed_command(code)
    if cmd is None:
        return None, "not a typed shell command"
    if terminal_focused(windows) is False:
        return None, "typed into a non-terminal window"
    return simulate(cmd, State(digest, windows, system))


# ---------------------------------------------------------------------------------------------------------- evaluation
def _rows_and_results(spots, patterns):
    import glob
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    rows = {}
    for f in spots:
        for r in json.load(open(os.path.join(base, f)))["rows"]:
            rows[r["row_id"]] = r
    res = {}
    for pat in patterns:
        for f in sorted(glob.glob(os.path.join(base, pat))):
            for l in open(f):
                r = json.loads(l)
                if r["status"] != "error":
                    res[r["row_id"]] = {**r, "_dir": os.path.dirname(f)}
    return rows, res


def _row_prediction(r):
    from rig.snapshot import load_snapshot
    s = load_snapshot(os.path.join(r["_dir"], r["snapshot_before"]))
    return predict((r.get("action") or {}).get("code", ""), s.digest, s.windows, s.system)


def evaluate():
    from collections import Counter
    # 1) dev: training rows (rig labels), never the test rows
    rows, res = _rows_and_results(["rig/clickspots_pairs_v2_train.json"], ["rig/out/pt_?/results.jsonl"])
    c, wrong = Counter(), []
    for rid, r in sorted(res.items()):
        lab = r.get("executed_label")
        if lab not in ("REVERSIBLE", "NO-UNDO-FOUND"):
            continue
        v, why = _row_prediction(r)
        if v is None:
            c["abstain"] += 1
            continue
        ok = (v != "oneway") == (lab == "REVERSIBLE")
        c["right" if ok else "wrong"] += 1
        if not ok:
            wrong.append((rid, rows[rid]["spot_id"], rows[rid]["pair_side"], lab, v, why))
    print("DEV (training rows, rig-labelled):", dict(c))
    for w in wrong:
        print("   wrong:", w)
    return c, wrong


def score_pairs_hybrid():
    """The pre-registered pair score with a third guard: symbolic where it decides, else Claude (fair re-ask)."""
    sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)))]
    import score_pairs as SP
    res = SP.results()
    cl = {json.loads(l)["row_id"]: json.loads(l) for l in open(SP.OUT / "claude_fair.jsonl")}
    mod = {json.loads(l)["row_id"]: json.loads(l) for l in open(SP.OUT / "model_fair.jsonl")}
    sym = {}
    for rid in SP.ROWS:
        if rid in res:
            sym[rid] = _row_prediction(res[rid])
    guards = {"ours": lambda rid: mod[rid]["p_reversible"] >= 0.5 if rid in mod else None,
              "claude": lambda rid: cl[rid]["reversible"] if rid in cl else None,
              "symbolic_only": lambda rid: None if sym.get(rid, (None,))[0] is None else sym[rid][0] != "oneway",
              "hybrid": lambda rid: (sym[rid][0] != "oneway") if sym.get(rid, (None,))[0] is not None else (cl[rid]["reversible"] if rid in cl else None)}

    def truth(rid):
        lab = (res.get(rid) or {}).get("executed_label")
        return None if lab not in ("REVERSIBLE", "NO-UNDO-FOUND") else lab == "REVERSIBLE"
    pairs = {}
    for rid, row in SP.ROWS.items():
        pairs.setdefault(row["pair_id"], {})[row["pair_side"]] = rid
    out = {}
    for grp in (None, "v1", "held-out", "system"):
        tally = {g: 0 for g in guards}
        n, abst, detail = 0, 0, []
        for pid, s in sorted(pairs.items()):
            if grp and SP.group(s["A"]) != grp:
                continue
            ta, tb = truth(s["A"]), truth(s["B"])
            if ta is None or tb is None or ta == tb:
                continue
            n += 1
            ok = {g: fn(s["A"]) == ta and fn(s["B"]) == tb for g, fn in guards.items()}
            for g in guards:
                tally[g] += ok[g]
            abst += sum(sym.get(x, (None,))[0] is None for x in (s["A"], s["B"]))
            detail.append({"pair": pid, "family": SP.ROWS[s["A"]]["spot_id"], **ok,
                           "sym": [sym.get(s["A"], (None, ""))[0], sym.get(s["B"], (None, ""))[0]]})
        hy_only = sum(d["hybrid"] and not d["claude"] for d in detail)
        cl_only = sum(d["claude"] and not d["hybrid"] for d in detail)
        out[grp or "all"] = {"n_pairs": n, **tally, "hybrid_only": hy_only, "claude_only": cl_only,
                             "sign_p_hybrid_vs_claude": round(SP.sign_p(hy_only, cl_only), 3),
                             "symbolic_abstained_rows": abst, "pairs": detail}
        print(f"{grp or 'all':9s} pairs {n:2d}: hybrid {tally['hybrid']}/{n}  claude {tally['claude']}/{n}  ours {tally['ours']}/{n}  "
              f"symbolic-alone {tally['symbolic_only']}/{n}  (hybrid-only {hy_only} vs claude-only {cl_only}, p {out[grp or 'all']['sign_p_hybrid_vs_claude']}); "
              f"symbolic abstained on {abst}/{2 * n} rows")
    (SP.OUT / "score_hybrid.json").write_text(json.dumps(out, indent=1))
    for d in out["all"]["pairs"]:
        if not d["hybrid"] or d["hybrid"] != d["claude"]:
            print("  ", d)
    return out


if __name__ == "__main__":
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path[:0] = [base, os.path.join(base, "rig")]
    if sys.argv[1:] == ["eval"]:
        evaluate()
        score_pairs_hybrid()
