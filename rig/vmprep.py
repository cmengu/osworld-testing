"""One-time quieting of a fresh VM: no notification banners, no screen lock, no auto-updates.

GUI-RobustEval does the same before replaying trajectories.  Everything here is a desktop
setting, so it survives closing and reopening LibreOffice within the same sandbox.
"""
from .vm import vm_shell

PREPARE_SCRIPT = r"""
gsettings set org.gnome.desktop.notifications show-banners false 2>/dev/null
gsettings set org.gnome.desktop.session idle-delay 0 2>/dev/null
gsettings set org.gnome.desktop.screensaver lock-enabled false 2>/dev/null
gsettings set org.gnome.desktop.screensaver idle-activation-enabled false 2>/dev/null
gsettings set org.gnome.software download-updates false 2>/dev/null
gsettings set org.gnome.software allow-updates false 2>/dev/null
python3 - <<'PY' 2>/dev/null
import json, os
p = os.path.expanduser("~/.config/Code/User/settings.json")
os.makedirs(os.path.dirname(p), exist_ok=True)
try:
    d = json.load(open(p))
except Exception:
    d = {}
# 24 Oct: VS Code's Welcome page is absent or differently rendered between instances (probe-0027), and update,
# telemetry and experiment banners come and go; none of them is state, so the rig turns them off like the
# desktop's own notifications above.  Keys a task may grade (autosave, wordWrap, theme...) are left alone.
d.update({"workbench.startupEditor": "none", "update.mode": "none", "telemetry.telemetryLevel": "off",
          "workbench.enableExperiments": False, "extensions.autoUpdate": False, "extensions.autoCheckUpdates": False,
          "workbench.tips.enabled": False, "window.restoreWindows": "none", "security.workspace.trust.enabled": False})
json.dump(d, open(p, "w"), indent=1)
PY
echo prepared
"""


# Agent rows (rig/agentrun, 28 Oct): the VM must look as it did to the agent, so the task's own VS Code settings are
# kept and merged, not replaced.  OS-Harm's settings.json carries // comments, which json.load above rejects, so
# the script above starts from {} and drops every key the task uploaded (its editor settings, and the rig's
# screen-reader line).  It also turns off the Welcome page and the folder-trust question, both of which the agent
# saw and clicked through; here only update, telemetry and tip banners are turned off.
PREPARE_SCRIPT_AGENT = PREPARE_SCRIPT.replace(
    """try:
    d = json.load(open(p))
except Exception:
    d = {}""",
    """import re
try:
    src = open(p).read()
    src = re.sub(r'(?m)^\\s*//.*$', '', src)              # whole-line // comments (JSONC)
    src = re.sub(r',(\\s*[}\\]])', r'\\1', src)          # trailing commas
    d = json.loads(src)
except Exception as e:
    print("settings.json not parsed:", repr(e)[:80]); d = {}""").replace(
    """d.update({"workbench.startupEditor": "none", "update.mode": "none", "telemetry.telemetryLevel": "off",
          "workbench.enableExperiments": False, "extensions.autoUpdate": False, "extensions.autoCheckUpdates": False,
          "workbench.tips.enabled": False, "window.restoreWindows": "none", "security.workspace.trust.enabled": False})""",
    """d.update({"update.mode": "none", "telemetry.telemetryLevel": "off", "workbench.enableExperiments": False,
          "extensions.autoUpdate": False, "extensions.autoCheckUpdates": False, "workbench.tips.enabled": False})""")
assert PREPARE_SCRIPT_AGENT != PREPARE_SCRIPT


def prepare_vm(env, agent: bool = False) -> str:
    res = vm_shell(env, PREPARE_SCRIPT_AGENT if agent else PREPARE_SCRIPT, timeout=30)
    return (res.get("output") or res.get("error") or "").strip()
