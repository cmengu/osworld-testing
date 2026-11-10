"""P2 (rig/plan_forward_model.md): harm, reversibility and the revert plan DERIVED from the forward prediction.

Conservation of content: apply T's change set to the before-state; every piece of content the before-state holds (a
file's content signature, the system's crontab / sudoers rules / hosts / login config, an editor's unsaved edits) must
still exist somewhere afterwards: another file, the Trash, an application's undo history, or a plain-text editor holding
a deleted file.  Nothing lost -> undoable, and the revert plan is read off the change set (each change has an inverse
operation; at most K = 3 operations).  Something lost -> one-way; the plan is the BACKUP to take before the step.

    derive(code, snapshot) -> {"verdict": noop|reversible|oneway|None, "lost": [...], "plan": [...], "backup": [...]}
"""
import os
import posixpath
import shlex

from rig.mask import _fsig, _is_lock
from rig.world.T import T, WState, TRASH_INFO
from rig.symbolic import TRASH

K = 3


def _csig(v):
    if v is None:
        return None
    if v.get("d"):
        return ("dir",)
    return (v.get("s"), v.get("c") or v.get("h"), v.get("k"))


def apply(st: WState, d):
    """The predicted digest after the step (values the state cannot know become opaque symbols)."""
    files = dict(st.files)
    dirs = set(st.dirs)
    for p, v in d.files.items():
        q = p.rstrip("/")
        kind = v[0]
        if kind in ("absent",):
            files.pop(q, None); dirs.discard(q)
        elif kind == "maybe-absent":
            files.pop(q, None)                       # a lock file: presence only, never content
        elif kind == "content":
            if v[1] in st.files:
                files[q] = dict(st.files[v[1]])
        elif kind == "empty":
            files[q] = {"s": 0, "h": "EMPTY"}
        elif kind == "dir":
            dirs.add(q)
        elif kind in ("sym", "sym-or-same"):
            # "sym-or-same": may change.  For harm the old content counts as gone (10 Nov fix: this used to depend on
            # the rule's label text, so an induced sed -i rule with another label read as "unchanged").  An app that
            # keeps the old content (d.app_keeps) still makes it undoable; see SYM_OR_SAME in derive().
            files[q] = {"s": None, "h": f"SYM:{v[1]}:{q}"}
        elif kind == "mode":
            if q in files:
                files[q] = dict(files[q], mode=v[1])
        elif kind == "link":
            files[q] = {"l": v[1]}
    return files, dirs


def backup_restore(out, dst):
    """Shell for the backup to take BEFORE a one-way step, and the restore script that undoes the step (P4/P5).
    Files and any folders the step removes go into one tar (permission bits kept); a crontab is saved with crontab -l.
    Returns (backup shell line, restore command)."""
    files = [p for p in out.get("lost", []) if p.startswith("/")]
    dirs = out.get("removed_dirs", [])
    lines = [f"mkdir -p {dst}"]
    restore = []
    # 10 Nov fix (P5 mv draft over final): first the inverse of every change the model can undo itself (mv the moved
    # content back, rm new files), then extract the backup over what was lost.  Order matters: the mv frees the name.
    for op in out.get("ops", []):
        if op[0] in ("mv", "cp"):
            restore.append(f"{op[0]} -f {shlex.quote(op[1])} {shlex.quote(op[2])}")
        elif op[0] == "rm":
            restore.append(f"rm -f {shlex.quote(op[1])}")
        elif op[0] == "rmdir":
            restore.append(f"rmdir {shlex.quote(op[1])}")
    if files or dirs:
        rel = [p.lstrip("/") for p in dirs]
        relf = [p.lstrip("/") for p in files]
        lines.append(f"tar -cpf {dst}/b.tar -C / --no-recursion {' '.join(shlex.quote(x) for x in rel + relf)}")
        restore.append(f"tar -xpf {dst}/b.tar -C /")
    if any("crontab" in p for p in out.get("lost", [])):
        lines.append(f"crontab -l > {dst}/crontab")
        restore.append(f"crontab {dst}/crontab")
    lines.append(f"printf '%s\\n' {shlex.quote(' ; '.join(restore) or 'true')} > {dst}/restore.sh")
    return " ; ".join(lines), f"sh {dst}/restore.sh"


SYM_OR_SAME = os.environ.get("WORLD_SYM_OR_SAME", "changed")   # "changed" | "abstain"  (chosen on DEV, 10 Nov)


def derive(code, snap):
    st = WState(snap)
    d = T(code, st)
    if d is None:
        return {"verdict": None, "why": "no rule covers the step"}
    if "touches a file an application has open" in d.rules:
        return {"verdict": None, "why": "an application holds a file the step changes: undo depends on the app", "delta": d}
    unsure = [p for p, v in d.files.items() if v[0] == "sym-or-same" and p in st.files and not _is_lock(p) and p not in d.app_keeps
              and st.files[p].get("s")]
    if unsure and SYM_OR_SAME == "abstain":
        return {"verdict": None, "why": f"the step may or may not change {unsure[0]}: the state does not say", "delta": d}
    after, after_dirs = apply(st, d)
    kept = {_csig(v) for v in after.values() if v.get("s")}
    vscode = {t.lstrip("●* ").split(" - ")[0] for t in st.titles if t.endswith(" - Visual Studio Code")}
    lost, plan, backup, ops = [], [], [], []
    for p, v in st.files.items():
        if _is_lock(p) or not v.get("s"):
            continue
        before_here = _csig(v)
        if p in after and _csig(after[p]) == before_here:
            continue                                 # unchanged
        if p in d.app_keeps:
            plan.append(f"restore {p} from the {d.app_keeps[p]}")
            continue
        if before_here in kept:
            src = next((q for q, w in after.items() if _csig(w) == before_here), None)
            if src and src.startswith(TRASH):
                plan.append(f"restore {posixpath.basename(src)} from the Trash to {p}")
            elif src:
                verb = "mv" if src not in st.files else "cp"
                plan.append(f"{verb} {src} {p}")
                ops.append((verb, src, p))
            continue
        if p not in after and posixpath.basename(p) in vscode:
            plan.append(f"re-save {p} from VS Code")
            continue
        lost.append(p)
        backup.append(f"cp -p {p} <backup dir>")
    for p in after:
        if p not in st.files and not _is_lock(p) and not p.startswith((TRASH, TRASH_INFO)):
            if not any(f.endswith(p) for f in plan):
                plan.append(f"rm {p}")
                ops.append(("rm", p))
    for x in after_dirs - st.dirs:
        plan.append(f"rmdir {x}")
        ops.append(("rmdir", x))
    for x in st.dirs - after_dirs:
        if x.startswith("/home/user") and not any(f.startswith(x + "/") for f in st.files if f not in after):
            plan.append(f"mkdir -m {oct(st.digest.get(x + '/', {}).get('mode', 0o755))[2:]} {x}")
    sysd = d.system
    if "crontab" in sysd:
        if st.system.get("crontab"):
            lost.append("the user's crontab"); backup.append("crontab -l > <backup>")
        else:
            plan.append("crontab -r")
    if "sudoers_d_sha" in sysd:
        if "sudoers_d" in sysd:
            plan.append("sudo rm the new /etc/sudoers.d rule")
        else:
            lost.append("an existing /etc/sudoers.d rule"); backup.append("sudo cp -p the rule <backup>")
    if "hosts" in sysd:
        lost.append("/etc/hosts (if it differs from the copy)"); backup.append("sudo cp -p /etc/hosts <backup>")
    lost += d.lost
    if d.lost:
        backup.append("save the document under a backup name first")
    if lost:
        removed_dirs = sorted(x for x in st.dirs - after_dirs if x.startswith("/home/user/"))
        return {"verdict": "oneway", "lost": lost, "backup": backup, "plan": plan, "ops": ops, "rules": d.rules, "removed_dirs": removed_dirs}
    if not d.files and not d.system and d.windows == "same":
        return {"verdict": "noop", "plan": [], "rules": d.rules}
    return {"verdict": "reversible", "plan": plan or ["Escape / Ctrl+Z / close or reopen the window"], "ops": len(set(plan)),
            "rules": d.rules}
