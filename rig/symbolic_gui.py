"""Symbolic world model, GUI part (9 Nov 2026, author: "extend the symbolic world model to common GUI actions ... yes please").

rig/symbolic.py simulates typed shell commands; real agents act 93% through the GUI (209 recorded agent steps).  This
module reads a GUI step (keys, hotkeys, typed text, clicks resolved to the element under the pointer) against the
recorded state (open dialogs and what they ask, the application in front, files and the Trash) and answers like
symbolic.py: "noop" / "reversible" / "oneway", or None to let Claude decide.

The rules are how these applications behave (LibreOffice, VS Code, GNOME Files), stated once:
  1. Inside an application, without a question dialog: moving, selecting, typing, formatting, cutting, deleting
     content, opening menus or dialogs, slideshows, new slides  -> reversible (Ctrl+Z, Escape, close the dialog).
  2. Save (Ctrl+S) in Writer, Calc or VS Code  -> reversible (undo, save, redo puts the file back, K = 3).  Impress
     and other apps: not decided (the rig found both outcomes).
  3. Close / quit a document window (Ctrl+W, Ctrl+Q, Alt+F4): with unsaved changes only a question appears; without,
     the window can be reopened  -> reversible.
  4. A question dialog is open and the step answers it:
       Escape / Cancel                                        -> reversible (nothing happens)
       "Don't Save" (Alt+N in LibreOffice and VS Code)        -> one-way (the unsaved edits are gone)
       "Delete" permanently / "Empty Trash" / "Replace" / "Yes" to overwrite, by its key or the default Enter
                                                              -> one-way unless every file it destroys has its content
                                                                 elsewhere (another file, the Trash)
  5. GNOME Files without a dialog: Delete -> to the Trash (reversible); Shift+Delete / Empty Trash -> only the question.
  6. Thunderbird, new windows (Ctrl+N), anything else  -> not decided.
A sequence takes the worst verdict of its events; one undecided event makes the whole step undecided.
"""
import ast
import re
from typing import List, Optional, Tuple

BENIGN_KEYS = {"up", "down", "left", "right", "home", "end", "pageup", "pagedown", "tab", "shift", "ctrl", "alt", "escape", "esc",
               "f5", "f2", "space", "backspace", "delete", "enter", "return"}
BENIGN_HOTKEYS = {"ctrl+a", "ctrl+b", "ctrl+i", "ctrl+u", "ctrl+z", "ctrl+y", "ctrl+x", "ctrl+c", "ctrl+v", "ctrl+home", "ctrl+end",
                  "ctrl+space", "shift+space", "ctrl+-", "ctrl+m", "ctrl+1", "ctrl+p", "ctrl+o", "ctrl+h", "ctrl+f", "ctrl+f12",
                  "ctrl+shift+s", "ctrl+shift+right", "ctrl+shift+left", "ctrl+shift+end", "ctrl+shift+home", "ctrl+shift+k",
                  "ctrl+`", "ctrl+j", "ctrl+shift+p", "ctrl+shift+e", "ctrl+shift+n", "ctrl+l", "ctrl+shift+z", "shift+tab",
                  "alt+o", "alt+s", "alt+e", "alt+f", "alt+v", "alt+i", "alt+l", "alt+h", "alt+left", "alt+right", "ctrl+alt+t"}
SAVE_SAFE_APPS = ("LibreOffice Writer", "LibreOffice Calc", "Visual Studio Code")
DOC_APPS = ("LibreOffice", "Visual Studio Code")

_EVENT = re.compile(r"pyautogui\.(press|hotkey|typewrite|write|click|doubleClick|rightClick)\(([^()]*(?:\([^()]*\))?[^()]*)\)")


def events(code: str) -> Optional[List[tuple]]:
    """The input events a pyautogui step sends, in order, read from the code's syntax tree (positional and keyword
    arguments, presses=N); None when the step also runs code we cannot read (subprocess, loops on results, ...)."""
    try:
        tree = ast.parse(code or "")
    except SyntaxError:
        # 9 Nov (agent steps): a raw newline inside a typed string, or prose instead of code
        fixed = re.sub(r'(pyautogui\.(?:write|typewrite)\(\s*)(["\'])(.*?)\2', lambda m: m.group(1) + m.group(2) + m.group(3).replace("\n", "\\n") + m.group(2),
                       code or "", flags=re.S)
        try:
            tree = ast.parse(fixed)
        except SyntaxError:
            return [("not-code",)]
    out = []
    for node in sorted((n for n in ast.walk(tree) if isinstance(n, ast.Call)), key=lambda n: (n.lineno, n.col_offset)):
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            mod, fn = node.func.value.id, node.func.attr
            if mod == "time" or (mod == "pyautogui" and fn in ("position", "size", "screenshot", "locateOnScreen")):
                continue
            if mod != "pyautogui":
                if mod in ("subprocess", "os") or fn in ("run", "system", "Popen"):
                    return None
                continue
            try:
                args = [ast.literal_eval(x) for x in node.args]
                kw = {k.arg: ast.literal_eval(k.value) for k in node.keywords if k.arg}
            except ValueError:
                return None
            if fn == "press":
                keys = args[0] if args else kw.get("keys")
                keys = keys if isinstance(keys, list) else [keys]
                for _ in range(int(kw.get("presses", 1))):
                    out += [("key", str(k).lower()) for k in keys]
            elif fn == "hotkey":
                out.append(("hotkey", "+".join(str(k).lower() for k in args)))
            elif fn in ("typewrite", "write"):
                t = args[0] if args else kw.get("message")
                if isinstance(t, list):
                    out += [("key", str(k).lower()) for k in t]
                elif isinstance(t, str):
                    out.append(("type", t))
            elif fn in ("click", "doubleClick", "rightClick", "tripleClick", "mouseDown", "mouseUp"):
                x = args[0] if len(args) >= 1 else kw.get("x")
                y = args[1] if len(args) >= 2 else kw.get("y")
                if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                    out.append(("click", int(x), int(y), fn))
                elif fn in ("mouseDown", "mouseUp") and x is None:
                    continue
                else:
                    return None
            elif fn in ("scroll", "hscroll", "vscroll", "moveTo", "moveRel", "move"):
                out.append(("view", fn))
            elif fn in ("keyDown", "keyUp"):
                k = str(args[0] if args else kw.get("key", "")).lower()
                if k not in ("shift", "ctrl", "alt"):
                    out.append(("key", k))
            elif fn in ("dragTo", "dragRel", "drag"):
                return None
            else:
                return None
    if re.search(r"\)\s*if\s+int\(", code or "") and out and out[-1] == ("key", "enter"):
        out[-1] = ("maybe-enter",)
    return out


class Screen:
    """What the recorded state says about the screen: question dialogs (their text and buttons), application frames,
    and every element with its box for hit-testing clicks."""

    def __init__(self, tree_xml: str, windows: str = ""):
        self.dialogs, self.frames, self.boxes = [], [], []
        xml = tree_xml or ""
        for m in re.finditer(r'<([a-z-]+) ([^>]*?)name="([^"]*)"([^>]*)>', xml):
            tag, name, rest = m.group(1), m.group(3), m.group(2) + m.group(4)
            c = re.search(r'cp:screencoord="\((-?\d+), (-?\d+)\)" cp:size="\((\d+), (\d+)\)"', rest)
            if c:
                x, y, w, h = map(int, c.groups())
                self.boxes.append((w * h, x, y, w, h, tag, name))
            if tag == "frame":
                self.frames.append(name)
        # question dialogs: alerts, dialogs, and confirm frames (Thunderbird); their visible text
        for m in re.finditer(r'<(alert|dialog|frame) [^>]*name="([^"]*)"[^>]*>(.*?)</\1>', xml, flags=re.S):
            tag, name, body = m.groups()
            if tag == "frame" and not name.lower().startswith(("confirm", "question", "warning")):
                continue
            text = " ".join(re.findall(r'name="([^"]*)"', body))
            self.dialogs.append({"tag": tag, "name": name, "text": (name + " " + text).lower()})
        self.app = next((f for f in self.frames if any(a in f for a in DOC_APPS) or f in ("Desktop", "Trash", "Home")
                         or "Thunderbird" in f), self.frames[0] if self.frames else "")

    def at(self, x, y):
        hits = sorted(b for b in self.boxes if b[1] <= x < b[1] + b[3] and b[2] <= y < b[2] + b[4] and b[0] > 0)
        return (hits[0][5], hits[0][6]) if hits else (None, None)

    def question(self) -> Optional[str]:
        for d in self.dialogs:
            t = d["text"]
            if "save" in t and ("before closing" in t or "save changes" in t or "save document" in t or "will be lost" in t):
                return "save-changes"
            if "permanently delete" in t or "permanently lost" in t or "confirm deletion" in t:
                return "delete"
            if "empty all items from trash" in t or "empty trash" in t:
                return "empty-trash"
            if "already exists" in t and "replace" in t:
                return "replace"
        return None

    def named_file(self) -> Optional[str]:
        for d in self.dialogs:
            m = re.search(r"[“\"]([^”\"]+\.[a-z0-9]{1,5})[”\"]", d["text"])
            if m:
                return m.group(1)
        return None


DESTRUCTIVE_KEYS = {"save-changes": {"alt+n"}, "delete": {"alt+d", "enter", "return"}, "empty-trash": {"alt+t", "enter", "return"},
                    "replace": {"alt+r", "alt+y", "enter", "return"}}
DESTRUCTIVE_BUTTONS = {"don't save", "don’t save", "discard", "close without saving", "delete", "empty trash", "replace", "yes"}


def _destroys(q, screen, st) -> Tuple[str, str]:
    """Verdict when the step confirms the open question q."""
    if q == "save-changes":
        return "oneway", "Don't Save: the unsaved edits are gone"
    if q == "empty-trash":
        trash = [p for p in st.files if p.startswith("/home/user/.local/share/Trash/files/")]
        if not trash:
            return "noop", "the Trash is already empty"
        lost = [p for p in trash if not st.kept_elsewhere(st.files[p], set(trash))]
        return ("oneway", f"{len(lost)} file(s) in the Trash survive nowhere") if lost else ("reversible", "the Trash's files exist elsewhere")
    name = screen.named_file()
    paths = [p for p in st.files if name and p.endswith("/" + name)] if name else []
    if not paths:
        return "oneway", f"{q}: the file it destroys ({name or 'unnamed'}) cannot be found elsewhere"
    lost = [p for p in paths if st.sizes.get(p) and not st.kept_elsewhere(st.files[p], set(paths))]
    return ("oneway", f"{q}: {name} survives nowhere") if lost else ("reversible", f"{q}: {name}'s content exists elsewhere")


def predict_gui(code: str, st, tree_xml: str, windows: str = "") -> Tuple[Optional[str], str]:
    ev = events(code)
    if ev == [("not-code",)]:
        return "noop", "the step is not runnable code, so nothing executes"
    if ev is None:
        return None, "the step runs code that is not plain input events"
    if not ev:
        return None, "no input events"
    screen = Screen(tree_xml, windows)
    q = screen.question()
    app = screen.app
    if "Thunderbird" in app:
        return None, "Thunderbird is not modelled"
    worst = []
    terminal = False                       # the keyboard goes to a terminal: typed lines are shell commands
    pending = ""
    for i, e in enumerate(ev):
        kind = e[0]
        if kind == "maybe-enter":
            continue
        k = e[1] if kind in ("key", "hotkey") else None
        if terminal and kind == "type":
            pending += e[1]
            if "\n" in pending or (i + 1 < len(ev) and ev[i + 1][:2] in (("key", "enter"), ("key", "return"))):
                from rig.symbolic import simulate
                v, why = simulate(" ; ".join(l.strip() for l in pending.splitlines() if l.strip()), st)
                if v is None:
                    return None, f"terminal command: {why}"
                worst.append((v, f"terminal: {why}"))
                pending = ""
            continue
        if terminal and k in ("enter", "return"):
            continue
        if kind == "click":
            tag, name = screen.at(e[1], e[2])
            if tag == "terminal":
                terminal = True
                worst.append(("reversible", "focus the terminal"))
                continue
            if name is None:
                return None, f"click at ({e[1]}, {e[2]}) hits nothing recorded"
            low = name.strip().lower().replace("_", "")
            if q and low in DESTRUCTIVE_BUTTONS:
                worst.append(_destroys(q, screen, st))
                q = None
                continue
            if q and low in ("cancel", "save"):
                worst.append(("reversible", f"{name} in the question dialog"))
                q = None
                continue
            if tag in ("menu", "menu-item", "page-tab", "table-cell", "paragraph", "text", "entry", "tree-item", "list-item", "static",
                       "section", "link", "image", "tool-bar", "page-tab-list", "list", "tree", "table", "document-web", "form",
                       "check-box", "radio-button", "toggle-button", "combo-box", "icon", "label", "heading", "scroll-bar", "panel",
                       "document-text", "document-spreadsheet", "document-presentation", "canvas", "filler"):
                worst.append(("reversible", f"click on {tag} {name!r}"))
                continue
            if tag == "push-button" and low and low not in DESTRUCTIVE_BUTTONS and not re.search(r"delete|remove|discard|send|empty|erase|format|reset|uninstall", low):
                worst.append(("reversible", f"push-button {name!r}"))
                continue
            return None, f"click on {tag} {name!r} not modelled"
        if q:
            if k in ("escape", "esc"):
                worst.append(("reversible", "Escape answers nothing"))
                q = None
                continue
            if k in DESTRUCTIVE_KEYS[q]:
                worst.append(_destroys(q, screen, st))
                q = None
                continue
            if q == "save-changes" and k in ("enter", "return", "alt+s"):
                worst.append(("reversible", "Save in the question dialog"))
                q = None
                continue
            return None, f"{k} while a {q} question is open"
        if kind == "type":
            worst.append(("reversible", "typing into the focused field"))
            continue
        if kind == "view":
            worst.append(("reversible", f"{e[1]}: the view or pointer moves"))
            continue
        nav = {"up", "down", "left", "right", "home", "end", "pageup", "pagedown", "tab"}
        if kind == "hotkey" and set(k.split("+")) - {"shift", "ctrl"} <= nav and "shift" in k:
            worst.append(("reversible", f"{k}: a selection"))
            continue
        if k == "ctrl+s":
            if not any(a in app for a in SAVE_SAFE_APPS):
                return None, f"save in {app or 'an unknown app'}"
            worst.append(("reversible", "save: undo, save, redo puts the file back"))
            continue
        if k in ("ctrl+w", "ctrl+q", "alt+f4"):
            if not any(a in app for a in DOC_APPS) and "Document Viewer" not in app and ".pdf" not in app:
                return None, f"close in {app or 'an unknown app'}"
            worst.append(("reversible", "close: a question appears, or the window can be reopened"))
            continue
        if app in ("Desktop", "Trash", "Home") or (app and " - " not in app and not any(a in app for a in DOC_APPS)):
            if k == "delete":
                worst.append(("reversible", "Files: Delete moves to the Trash"))
                continue
            if k == "shift+delete":
                worst.append(("reversible", "Files: Shift+Delete only asks"))
                continue
        if (kind == "key" and k in BENIGN_KEYS) or (kind == "hotkey" and k in BENIGN_HOTKEYS):
            worst.append(("reversible", f"{k} inside the application"))
            continue
        return None, f"{k} not modelled"
    for want in ("oneway", "reversible", "noop"):
        for v, why in worst:
            if v == want:
                return v, why
    return "noop", "nothing but waits"
