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
echo prepared
"""


def prepare_vm(env) -> str:
    res = vm_shell(env, PREPARE_SCRIPT, timeout=30)
    return (res.get("output") or res.get("error") or "").strip()
