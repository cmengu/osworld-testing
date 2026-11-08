"""Compact text rendering of a snapshot for a language model: window chrome from the tree, the sheet as a
dump of non-empty cells, the office files in the home directory.

Decided 16 Oct 2026 after the tree probe: a raw Calc tree is ~270K tokens and the OSWorld linearisation
~17.7K, of which 726 of 820 lines are table cells; the chrome is what identifies the window state and the
cells are the document.  Target: well under 8K tokens for a typical sheet.
"""
import os
import re
from typing import Dict, List

from .treediff import Canon, tag_of

OFFICE_EXT = (".xlsx", ".xlsm", ".ods", ".csv", ".docx", ".odt")
CHROME_TAGS = {"dialog", "frame", "alert", "file-chooser", "window"}
WIDGET_TAGS = {"push-button", "toggle-button", "check-box", "radio-button", "label", "text", "combo-box", "entry",
               "spin-button", "list-item", "page-tab", "menu", "heading", "paragraph"}


def _last(path: str) -> str:
    return path.rsplit("/", 1)[-1]


def _name(path: str) -> str:
    last = _last(path)
    return last[last.index("[") + 1: last.rindex("]")]


USER_ROOTS = ("/home/user/Desktop/", "/home/user/Documents/", "/home/user/Downloads/", "/home/user/.local/share/Trash/")


def render(canon: Canon, digest: Dict[str, dict], windows: str = "", max_cells: int = 900, files: str = "office",
           system: dict = None) -> str:
    """One text block: open windows and dialogs (with their controls), the Calc document cells, home files.
    files='office' (Calc rows, unchanged since 16 Oct): office files directly in /home/user.  files='user' (Files,
    multi_apps rows, 19 Oct): every file and folder in the user's folders and the Trash, with size and mode."""
    lines: List[str] = []
    # ---- top-level windows per application
    tops = sorted(p for p in canon if p.count("/") == 3 and tag_of(p) in CHROME_TAGS)
    apps = sorted({p.split("/")[2] for p in canon if p.count("/") >= 3})
    office = [a for a in apps if "soffice" in a or "LibreOffice" in a or "libreoffice" in a.lower()]
    if not tops and not office:
        lines.append("WINDOWS: no LibreOffice window is open (the application is not running).")
    for top in tops:
        tag = tag_of(top)
        nm = _name(top)
        lines.append(f"{tag.upper()}: {nm!r}")
        if tag != "frame" or not nm.endswith("LibreOffice Calc"):
            # a dialog, the Start Center or a second window: list its visible controls, briefly
            controls = []
            for p, attrs in canon.items():
                if not p.startswith(top + "/"):
                    continue
                t = tag_of(p)
                if t in WIDGET_TAGS:
                    label = attrs.get("name") or attrs.get("text") or ""
                    if label and len(label) < 80:
                        controls.append(f"{t}:{label!r}")
            seen = []
            for c in controls:
                if c not in seen:
                    seen.append(c)
            if seen:
                lines.append("  controls: " + ", ".join(seen[:40]) + (" ..." if len(seen) > 40 else ""))
    # ---- menus and toolbars of the Calc frame, names only
    menus = sorted({_name(p) for p in canon if tag_of(p) == "menu" and p.count("/") <= 9 and _name(p)})
    if menus:
        lines.append("MENU BAR: " + " | ".join(menus))
    bars = []
    for p in canon:
        if tag_of(p) == "tool-bar" and _name(p) and _name(p) not in bars:
            bars.append(_name(p))
    if bars:
        lines.append("TOOLBARS: " + ", ".join(bars))
    # ---- cursor cell and input line
    for p, attrs in canon.items():
        if "Formula Tool Bar" in p and tag_of(p) == "text" and attrs.get("text"):
            lines.append(f"NAME BOX (cursor): {attrs['text']}")
            break
    # ---- document cells per sheet
    tables = sorted({p for p in canon if tag_of(p) == "table" and "document-spreadsheet" in p})
    for tb in tables:
        sheet = _name(tb)
        cells = []
        for p, attrs in canon.items():
            if p.startswith(tb + "/") and tag_of(p) == "table-cell":
                ref = attrs.get("name", _name(p))
                text = attrs.get("text", "")
                formula = attrs.get("Formula", "")
                if not text and not formula:
                    continue
                item = f"{ref}={text!r}" if not formula else f"{ref}={text!r}[{formula}]"
                marks = []
                if attrs.get("Note"):
                    marks.append("note")
                if attrs.get("selected") == "true":
                    marks.append("sel")
                if marks:
                    item += "{" + ",".join(marks) + "}"
                cells.append((_cell_key(ref), item))
        cells.sort()
        shown = [c for _, c in cells[:max_cells]]
        lines.append(f"SHEET {sheet!r}: {len(cells)} visible non-empty cells" + (f" (first {max_cells})" if len(cells) > max_cells else ""))
        if shown:
            lines.append("  " + " ".join(shown))
    # ---- sheet tabs (page tabs) if present
    tabs = [a.get("name") for p, a in canon.items() if tag_of(p) == "page-tab" and "document-spreadsheet" not in p and a.get("name")]
    tabs = [t for t in tabs if t and len(t) < 40]
    if tabs:
        lines.append("SHEET TABS: " + ", ".join(dict.fromkeys(tabs)))
    # ---- files
    if files == "user":
        lines.extend(_user_files(digest))
    home_files = sorted(p for p in digest if p.count("/") == 3 and p.lower().endswith(OFFICE_EXT) and not os.path.basename(p).startswith("."))
    if home_files:
        lines.append("FILES IN /home/user: " + ", ".join(f"{os.path.basename(p)} ({digest[p].get('s')} B)" for p in home_files))
    locks = sorted(os.path.basename(p) for p in digest if os.path.basename(p).startswith(".~lock."))
    if locks:
        lines.append("OPEN-DOCUMENT LOCKS: " + ", ".join(locks))
    if system:
        lines.extend(system_lines(system))
    return "\n".join(lines)


def system_lines(sy: dict) -> List[str]:
    """8 Nov (Track B): the system part of the state, briefly: people (users from uid 1000, root), who is in which
    group, automatic login, disks and their rw/ro flag, packages (count + hash), scheduled jobs, sudo rules, hosts."""
    out = ["SYSTEM:"]
    users = [u.split(":") for u in sy.get("users", [])]
    people = [u for u in users if len(u) >= 5 and (u[1] == "0" or 1000 <= int(u[1] or 0) < 60000)]
    out.append("  users: " + ", ".join(f"{u[0]} (uid {u[1]}, home {u[3]}, shell {u[4].rsplit('/', 1)[-1]})" for u in people))
    names = {u[0] for u in people}
    grp = [g.split(":") for g in sy.get("groups", [])]
    member = [f"{g[0]}: {g[2]}" for g in grp if len(g) >= 3 and g[2] and set(g[2].split(",")) & names]
    if member:
        out.append("  groups with these users: " + "; ".join(member))
    out.append("  automatic login: " + (", ".join(sy.get("autologin") or []) or "off"))
    mounts = []
    for m in sy.get("mounts", []):
        f = m.split(" ")
        if len(f) >= 4:
            mounts.append(f"{f[0]} {f[2]} {f[3].split(',')[0]}")
    out.append("  mounts: " + "; ".join(mounts))
    out.append(f"  packages: {sy.get('packages_n')} installed (list hash {sy.get('packages_sha')})")
    if sy.get("crontab") or sy.get("cron_d"):
        out.append("  scheduled: " + "; ".join((sy.get("crontab") or []) + [f"/etc/cron.d/{x}" for x in sy.get("cron_d") or []]))
    if sy.get("sudoers_d"):
        out.append("  sudo rules: " + ", ".join(f"/etc/sudoers.d/{x}" for x in sy["sudoers_d"]))
    out.append(f"  services enabled: {len(sy.get('services_enabled') or [])} system, {len(sy.get('user_services_enabled') or [])} user")
    extra = [h for h in sy.get("hosts") or [] if not h.startswith(("127.0.0.1", "127.0.1.1", "::1", "fe00", "ff0", "ff02"))]
    if extra:
        out.append("  hosts: " + "; ".join(extra))
    return out


def _mode(v: dict) -> str:
    return f"{v['mode']:o}" if isinstance(v.get("mode"), int) else "?"


HOME_DIRS = True   # 8 Nov (Track A): folders the user made in /home/user (~/pairs, ~/repo_0, a project) were invisible


def _in_home_dir(p: str) -> bool:
    """A path inside a non-hidden folder of /home/user (any depth), with no hidden component; a repo's .git/ folder
    itself is shown (so a repo is recognisable), its internals are not."""
    if not p.startswith("/home/user/"):
        return False
    parts = p[len("/home/user/"):].rstrip("/").split("/")
    if len(parts) == 1 and not p.endswith("/"):
        return False                      # top-level files: the rule above already decides
    if any(x.startswith(".") for x in parts[:-1]):
        return False
    return not parts[-1].startswith(".") or (parts[-1] == ".git" and p.endswith("/"))


def _user_files(digest: Dict[str, dict], limit: int = 300) -> List[str]:
    keep = sorted(p for p in digest if p.startswith(USER_ROOTS) or (p.count("/") == 3 and not os.path.basename(p.rstrip("/")).startswith(".")
                                                                     and not p.endswith("/"))
                  or (HOME_DIRS and _in_home_dir(p)))
    out = [f"USER FILES ({len(keep)} entries; folders end in /; mode in octal):"]
    for p in keep[:limit]:
        v = digest[p]
        if v.get("d"):
            out.append(f"  {p} mode {_mode(v)}")
        elif "l" in v:
            out.append(f"  {p} -> {v['l']}")
        else:
            out.append(f"  {p} {v.get('s')} B mode {_mode(v)}")
    if len(keep) > limit:
        out.append(f"  ... {len(keep) - limit} more")
    return out


def _cell_key(ref: str):
    m = re.match(r"([A-Z]+)(\d+)", ref)
    if not m:
        return (10 ** 9, ref)
    col = 0
    for ch in m.group(1):
        col = col * 26 + ord(ch) - 64
    return (int(m.group(2)), col)


def file_diff(before: Dict[str, dict], after: Dict[str, dict], mask: dict, limit: int = 40) -> List[dict]:
    """Human-readable file differences (masked), for the row and for the proposer."""
    from .mask import apply_file_mask, file_sig
    a, b = apply_file_mask(before, mask), apply_file_mask(after, mask)
    out = []
    for p in sorted(set(a) | set(b)):
        sa, sb = file_sig(a.get(p)), file_sig(b.get(p))
        if sa != sb:
            out.append({"path": p, "before": _sig_text(a.get(p)), "after": _sig_text(b.get(p))})
    return out[:limit]


def _sig_text(v):
    if v is None:
        return "absent"
    h = v.get("c") or v.get("h") or ""
    return f"{v.get('s')} B sha:{h[:10]}"
