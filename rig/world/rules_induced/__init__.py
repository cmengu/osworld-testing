"""Rules induced from DEV data (rig/world/induce.py) and accepted by the regression check (>= 2 fixes, 0 breaks).
T uses them only where its base rules say nothing.  The ledger (ledger.jsonl) records who proposed each rule and what it
explained."""
import pathlib
import re

_RULES = None


def rules():
    global _RULES
    if _RULES is None:
        import fnmatch
        import posixpath
        from rig.world.T import Delta
        _RULES = []
        for f in sorted(pathlib.Path(__file__).parent.glob("r_*.py")):
            ns = {"Delta": Delta, "re": re, "posixpath": posixpath, "fnmatch": fnmatch}
            exec(compile(f.read_text(), str(f), "exec"), ns)
            _RULES.append((f.stem, ns["rule"]))
    return _RULES


def try_rules(code, st):
    from rig.symbolic import typed_command
    from rig.symbolic_gui import Screen, events
    ev, cmd = events(code), typed_command(code)
    screen = Screen(st.tree, st.windows)
    for name, fn in rules():
        try:
            d = fn(ev, cmd, st, screen)
        except Exception:  # noqa: BLE001  a crashing induced rule stays silent
            d = None
        if d is not None:
            d.rules.append(f"induced {name}")
            return d
    return None
