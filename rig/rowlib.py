"""Helpers shared by the row generators (make_probe_rows.py grew them; make_rows_v2.py reuses them, 24 Oct 2026).

Every helper returns a string of Python that runs inside the VM through the collector's step (pyautogui and the
standard library are available there).  Waits poll the window manager instead of sleeping a fixed time: a
dialog or a window takes anything from one to forty seconds to come up on this VM.
"""
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
EX = HERE.parent / "OSWorld" / "evaluation_examples" / "examples"
FILES_SELECT_SH = "/home/user/.rig_cache/files_select.sh"     # written by the prime (freshstart.FILES_SELECT_SH)

NOOP = "pyautogui.press('shift'); time.sleep(1)"
TERMINAL_TITLE = "user@user-virtual-machine: ~"

# accessibility bus names, from the probe's before-state trees (23 Oct)
SOFFICE = "apps:soffice"
NAUTILUS = "apps:org.gnome.Nautilus"
TERMINAL = "apps:gnome-terminal-server"
VSCODE = "apps:code"
THUNDERBIRD = "apps:Thunderbird"
EVINCE = "apps:evince"


def task(domain: str, prefix: str) -> dict:
    (f,) = EX.glob(f"{domain}/{prefix}*.json")
    return json.loads(f.read_text())


def task_id(domain: str, prefix: str) -> str:
    return task(domain, prefix)["id"]


def task_files(t: dict, suffix: str = "") -> list:
    """Paths the task downloads into the VM, optionally filtered by suffix."""
    out = []
    for c in t.get("config", []):
        if c.get("type") == "download":
            out += [f["path"] for f in c["parameters"].get("files", []) if f["path"].lower().endswith(suffix)]
    return out


def wait_windows(n: int, secs: int = 20) -> str:
    """Wait until at least n windows besides the desktop are listed (a question dialog has come up)."""
    return (f"__import__('subprocess').run(['sh', '-c', 'for i in $(seq 1 {secs * 2}); do [ $(wmctrl -l 2>/dev/null | grep -vc \"@!\") -ge {n} ]"
            f" && exit 0; sleep 0.5; done; exit 1'], timeout={secs + 10}); time.sleep(1)")


def wait_title(title: str, secs: int = 20) -> str:
    """Wait until a window whose title ends with this text is listed."""
    return (f"__import__('subprocess').run(['sh', '-c', 'for i in $(seq 1 {secs * 2}); do wmctrl -l 2>/dev/null | grep -q \" {title}$\""
            f" && exit 0; sleep 0.5; done; exit 1'], timeout={secs + 10}); time.sleep(1)")


def wait_title_part(part: str, secs: int = 25) -> str:
    """Wait until a listed window title contains this text."""
    return (f"__import__('subprocess').run(['sh', '-c', 'for i in $(seq 1 {secs * 2}); do wmctrl -l 2>/dev/null | grep -q {json.dumps(part)}"
            f" && exit 0; sleep 0.5; done; exit 1'], timeout={secs + 10}); time.sleep(1)")


def wait_viewable(title: str, secs: int = 25) -> str:
    """Wait until a window with this title is listed AND drawn (xwininfo IsViewable)."""
    return (f"__import__('subprocess').run(['sh', '-c', 'for i in $(seq 1 {secs * 2}); do w=$(wmctrl -l 2>/dev/null | grep \" {title}$\" | tail -1 | cut -d\" \" -f1);"
            f" [ -n \"$w\" ] && xwininfo -id \"$w\" 2>/dev/null | grep -q \"Map State: IsViewable\" && exit 0; sleep 0.5; done; exit 1'], timeout={secs + 10}); time.sleep(1)")


def activate(title_part: str) -> str:
    """Bring the window whose title contains this text to the front (wmctrl -a matches a substring)."""
    return f"__import__('subprocess').run(['wmctrl', '-a', {json.dumps(title_part)}], timeout=15); time.sleep(1.5)"


def open_terminal() -> str:
    """Ctrl+Alt+T, then wait until the terminal is drawn and the shell has had a moment (23 Oct: a listed but
    undrawn terminal lost the typed command)."""
    return ("pyautogui.hotkey('ctrl', 'alt', 't'); time.sleep(2); " + wait_viewable(TERMINAL_TITLE) + "; time.sleep(2)")


def shell(cmd: str, settle: float = 3) -> str:
    """Type a command into the focused terminal and run it."""
    return f"pyautogui.typewrite({json.dumps(cmd)}, interval=0.02); pyautogui.press('enter'); time.sleep({settle})"


def typed(text: str, settle: float = 2) -> str:
    return f"pyautogui.typewrite({json.dumps(text)}); time.sleep({settle})"


def keys(*chords, settle: float = 2) -> str:
    """Chords like 'ctrl+s', 'enter', 'f5', each followed by a short pause; the last by `settle` seconds."""
    parts = []
    for ch in chords:
        ks = ch.split("+")
        parts.append(f"pyautogui.hotkey({', '.join(repr(k) for k in ks)})" if len(ks) > 1 else f"pyautogui.press({ks[0]!r})")
        parts.append("time.sleep(1)")
    parts[-1] = f"time.sleep({settle})"
    return "; ".join(parts)


def nautilus_select(path: str) -> str:
    """Restart Files on `path` selected, through the prime's script (returns when the window is drawn)."""
    return f"__import__('subprocess').run(['sh', '{FILES_SELECT_SH}', '{path}'], timeout=70); time.sleep(1)"


# LibreOffice: save a .docx/.pptx/.xlsx in place keeps the format through the Keep Current Format question (Enter
# is its default button); Don't Save in the Save Document? question is Alt+N on this image (19 Oct)
LO_SAVE = keys("ctrl+s", settle=3) + "; pyautogui.press('enter'); time.sleep(4)"
LO_DONT_SAVE = "pyautogui.hotkey('alt', 'n'); time.sleep(3)"
