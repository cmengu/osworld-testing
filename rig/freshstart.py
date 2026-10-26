"""Fresh start without snapshot revert (Modal has none).

Slow path = OSWorld's own env.reset: re-downloads the task file and relaunches the app,
two to four minutes.  Fast path, after the first reset primed a cache inside the VM: close
LibreOffice, remove its lock and recovery files, copy the task files back from the cache,
relaunch LibreOffice on the file, wait for its window, maximise it, let it settle.  About
30 seconds.  Falls back to the slow path if the window does not appear.
"""
import time
from typing import List

from .dialog_keys import DONT_SAVE
from .vm import vm_out, vm_shell

CACHE_DIR = "/home/user/.rig_cache"
SETTLE_SECONDS = 8   # the accessibility bridge is slow for the first seconds after launch
CLEAN_SCRIPT = r"""
# -x (exact process name), never -f: the VM runs this script as sh -c "<text>", so a -f pattern matches
# that shell and kills the script on its first line, leaving every cleanup below unrun.
pkill -x soffice.bin 2>/dev/null; pkill -x oosplash 2>/dev/null; sleep 2; pkill -9 -x soffice.bin 2>/dev/null; pkill -9 -x oosplash 2>/dev/null
pkill -x crashreporter 2>/dev/null   # a leftover Mozilla Crash Reporter window (26 Oct, v2-0055)
rm -f "$HOME"/.~lock.* "$HOME"/Desktop/.~lock.* "$HOME"/Documents/.~lock.* 2>/dev/null
rm -rf "$HOME"/.config/libreoffice/4/user/backup 2>/dev/null
# drop only the crash-recovery entries (one <item> per line) and keep the rest of the profile, so the
# relaunch matches the restart regime the mask was built from and never shows the Document Recovery dialog
sed -i "/org\\.openoffice\\.Office\\.Recovery/d" "$HOME"/.config/libreoffice/4/user/registrymodifications.xcu 2>/dev/null
rm -f "$HOME"/.config/libreoffice/4/.lock 2>/dev/null
# files written by actions under test (the Save As click-spot); never part of the task
rm -f "$HOME"/smoke_copy* "$HOME"/Documents/smoke_copy* "$HOME"/Desktop/smoke_copy* 2>/dev/null
rm -f "$HOME"/pilot_* "$HOME"/Documents/pilot_* "$HOME"/Desktop/pilot_* 2>/dev/null
true
"""


def task_files(task: dict) -> List[str]:
    """Paths the task setup downloads into the VM, in order."""
    paths = []
    for step in task.get("config", []):
        if step.get("type") == "download":
            for f in step.get("parameters", {}).get("files", []):
                if f.get("path"):
                    paths.append(f["path"])
    return paths


def task_open_path(task: dict):
    for step in task.get("config", []):
        if step.get("type") == "open":
            return step.get("parameters", {}).get("path")
    return None


def prime_cache(env, task: dict) -> str:
    """Call once right after the first env.reset: keep pristine copies of the task files (generic tasks: the
    folders, the top-level listing and the window titles, prime_generic)."""
    if not is_calc_task(task):
        return prime_generic(env, task)
    files = task_files(task)
    if not files:
        return "no task files"
    cmds = [f"mkdir -p {CACHE_DIR}"] + [f'cp -f "{p}" {CACHE_DIR}/' for p in files]
    return vm_out(env, "; ".join(cmds) + "; ls -1 " + CACHE_DIR)


def _restore_files(env, task: dict) -> None:
    cmds = [f'cp -f {CACHE_DIR}/"$(basename "{p}")" "{p}"' for p in task_files(task)]
    if cmds:
        vm_shell(env, "; ".join(cmds) + "; true", timeout=30)


def _launch_and_wait(env, path: str, title_hint: str = "LibreOffice Calc", wait_s: int = 75) -> bool:
    """Wait for the DOCUMENT window ("LibreOffice Calc"): the splash screen and the Document Recovery
    dialog are also titled LibreOffice and must not count as ready."""
    vm_shell(env, f'nohup libreoffice --calc "{path}" >/dev/null 2>&1 &', timeout=20)
    deadline = time.time() + wait_s
    while time.time() < deadline:
        time.sleep(2)
        windows = vm_out(env, "wmctrl -l 2>/dev/null", timeout=15)
        if "Document Recovery" in windows:
            return False      # recovery dialog: the caller cleans again and takes the slow path
        if title_hint in windows:
            break
    else:
        return False
    time.sleep(3)  # let the document finish laying out
    vm_shell(env, f'wmctrl -r "{title_hint}" -b add,maximized_vert,maximized_horz 2>/dev/null; true', timeout=15)
    time.sleep(SETTLE_SECONDS)
    return True


def fresh_start(env, task: dict, fast: bool = True) -> str:
    """Returns which path ran: 'fast', 'slow' or 'slow-after-fast-failed'; for tasks that are not one spreadsheet,
    the generic path below ('generic' or 'generic-incomplete:...')."""
    if not is_calc_task(task):
        return generic_fresh_start(env, task)
    # graceful close first so LibreOffice does not leave a recovery entry behind
    try:
        env.step("pyautogui.hotkey('ctrl', 'q'); time.sleep(3); " + DONT_SAVE + "; time.sleep(3)", pause=0.5)
    except Exception:
        pass
    vm_shell(env, CLEAN_SCRIPT, timeout=60)
    open_path = task_open_path(task)
    if fast and open_path and task_files(task):
        _restore_files(env, task)
        if _launch_and_wait(env, open_path):
            return "fast"
        vm_shell(env, CLEAN_SCRIPT, timeout=60)
        env.reset(task_config=task)
        time.sleep(SETTLE_SECONDS)
        return "slow-after-fast-failed"
    env.reset(task_config=task)
    time.sleep(SETTLE_SECONDS)
    return "slow"


def switch_task(env, task: dict) -> str:
    """Bring another task's files into the VM without env.reset (which on Modal tears the sandbox down):
    download them where the task config puts them, prime the cache, then take the fast fresh-start path.
    Returns the fresh_start result or 'download-failed'."""
    import shlex
    cmds = []
    for step in task.get("config", []):
        if step.get("type") == "download":
            for f in step.get("parameters", {}).get("files", []):
                if f.get("url") and f.get("path"):
                    cmds.append(f'(wget -q -O {shlex.quote(f["path"])} {shlex.quote(f["url"])} || curl -sL -o {shlex.quote(f["path"])} {shlex.quote(f["url"])})')
    if cmds:
        res = vm_shell(env, " && ".join(cmds) + " && echo DOWNLOADED", timeout=110)
        if "DOWNLOADED" not in (res.get("output") or ""):
            return "download-failed"
    prime_cache(env, task)
    return fresh_start(env, task)


# ---------------------------------------------------------------------------------------------------------
# Generic fresh start (19 Oct 2026), for tasks that are not "LibreOffice on one spreadsheet": Files, terminal and
# multi_apps rows.  Of the 27 usable multi_apps tasks, 13 open nothing, 11 run setup commands and 5 launch an
# application, so "copy the workbook back and relaunch Calc" does not reset them.  Instead:
#   prime (once, right after the task's own env.reset):  tar the user's folders as the setup left them (as root, so
#       root-owned folders are archived with their owner), and record
#       the top-level entries of $HOME and the window titles the setup produced;
#   reset (every time):  close every application, restore the folders from the tar as root (files, folders, modes,
#       owners, Trash; a folder made with sudo is removed and comes back root-owned),
#       replay only the setup steps that open windows (open, launch, and execute/command steps that start a GUI
#       program), wait for the recorded windows, maximise them, settle.
# Setup steps that only change files (mkdir, unzip, tar, pip, history -c) are not replayed: their result is in the
# tar.  A different task gets a new sandbox (collect_pilot.ensure_task), so tasks never see each other's files.
# ---------------------------------------------------------------------------------------------------------
import json as _json
import shlex as _shlex

SPREADSHEET_EXT = (".xlsx", ".xlsm", ".xls", ".ods", ".csv")
GUI_PROCS = ("soffice.bin", "oosplash", "nautilus", "gnome-terminal-server", "code", "evince", "eog", "gedit",
             "gnome-text-editor", "thunderbird", "thunderbird-bin", "totem", "file-roller",
             "gvfsd-trash")   # the Trash backend: it kept showing "Trash is Empty" after the restore recreated the Trash folder (21 Oct, row 15)
GUI_LAUNCHERS = ("gnome-terminal", "nautilus", "code", "xdg-open", "libreoffice", "soffice", "evince", "eog", "gedit",
                 "thunderbird")
HOME_ROOTS = ("Desktop", "Documents", "Downloads", "Pictures", "Music", "Videos", "Templates", "Public",
              ".local/share/Trash", ".config/Code", ".thunderbird", ".bash_history")
BASELINE_TAR = CACHE_DIR + "/home_baseline.tar"
BASELINE_TOP = CACHE_DIR + "/home_top.txt"
BASELINE_WINDOWS = CACHE_DIR + "/windows.txt"
BASELINE_ACTIVE = CACHE_DIR + "/active.txt"     # the window that had the keyboard after the task's setup


def is_calc_task(task: dict) -> bool:
    """The case the fast path was built for: a Calc task that downloads, then opens one spreadsheet, nothing else.
    A multi_apps task with the same setup (7f35355e) still takes the generic path: its actions reach other programs."""
    if any(a.lower().replace(" ", "_") != "libreoffice_calc" for a in task.get("related_apps", [])):
        return False
    steps = task.get("config", [])
    opens = [s for s in steps if s.get("type") == "open"]
    return (len(opens) == 1 and all(s.get("type") in ("download", "open") for s in steps)
            and str(opens[0].get("parameters", {}).get("path", "")).lower().endswith(SPREADSHEET_EXT))


_GUI_RE = __import__("re").compile(r"(?:^|[\s/;&|])(?:" + "|".join(GUI_LAUNCHERS) + r")(?:\s|$)")


def _cmd_text(params: dict) -> str:
    c = params.get("command")
    return c if isinstance(c, str) else " ".join(map(str, c or []))


def gui_steps(task: dict) -> list:
    """The setup steps that open windows, in order."""
    out = []
    for s in task.get("config", []):
        t, p = s.get("type"), s.get("parameters", {})
        if t in ("open", "launch", "sleep", "activate_window"):
            out.append(s)
        elif t in ("execute", "command") and _GUI_RE.search(_cmd_text(p)):
            out.append(s)
    return out


PRIME_GENERIC = r"""
mkdir -p {cache}; cd "$HOME"
ls -A1 | grep -v '^\.' > {top}
ROOTS=""; for r in {roots}; do [ -e "$r" ] && ROOTS="$ROOTS $r"; done
TOPFILES=$(find . -maxdepth 1 -type f ! -name '.*' -printf '%P\n')
tar -cpf {tar} $ROOTS $TOPFILES 2>/dev/null; echo "tar=$?"; chown -R user:user {cache} 2>/dev/null
"""
# window titles as the user: root has no access to the user's X display
# the title of the window that has the keyboard (xprop; xdotool is not on the image)
ACTIVE_NAME_SH = r"""id=$(xprop -root _NET_ACTIVE_WINDOW 2>/dev/null | awk '{print $NF}'); [ -n "$id" ] && [ "$id" != "0x0" ] && xprop -id "$id" _NET_WM_NAME WM_NAME 2>/dev/null | sed -n 's/^[^=]*= "\(.*\)"$/\1/p' | head -1"""
PRIME_WINDOWS = r"""(wmctrl -l 2>/dev/null | awk '{{ $1=$2=$3=""; sub(/^ +/, ""); print }}' | grep -v '^@!' | sort) > {windows}
({active_name}) > {active}
cat > {select_sh} <<'SH'
#!/bin/sh
# Relaunch Files on "$1" selected, and return only when a Files window is drawn and owned by a live process.
# After a kill the window manager keeps listing the dead window for a while (20 Oct, probe-0007), so a title
# alone proves nothing: the key sent next reached a window that no longer existed.
nautilus -q 2>/dev/null; i=0; while pgrep -x nautilus >/dev/null && [ $i -lt 20 ]; do sleep 0.5; i=$((i+1)); done; pkill -9 -x nautilus 2>/dev/null
(nautilus --select "$1" >/dev/null 2>&1 &)
i=0; while [ $i -lt 80 ]; do
  for id in $(wmctrl -l 2>/dev/null | awk '$2 != "-1" {{print $1}}'); do
    p=$(xprop -id "$id" _NET_WM_PID 2>/dev/null | awk '{{print $NF}}')
    [ -n "$p" ] && kill -0 "$p" 2>/dev/null || continue
    xprop -id "$id" WM_CLASS 2>/dev/null | grep -qi nautilus || continue
    xwininfo -id "$id" 2>/dev/null | grep -q "Map State: IsViewable" || continue
    wmctrl -i -a "$id" 2>/dev/null; wmctrl -i -r "$id" -b add,maximized_vert,maximized_horz 2>/dev/null; sleep 2; echo "ready $id"; exit 0
  done
  sleep 0.5; i=$((i+1))
done
echo "files window not ready"; exit 1
SH
chmod +x {select_sh}
echo PRIMED; cat {windows}; echo "active: $(cat {active})"
"""
FILES_SELECT_SH = CACHE_DIR + "/files_select.sh"

# Every recorded window must be listed, drawn (viewable) and owned by a live process: a stale entry for a killed
# window fails the last two checks
WINDOWS_READY_SH = r"""ok=1
while IFS= read -r t; do
  [ -z "$t" ] && continue
  w=$(wmctrl -l 2>/dev/null | awk -v t="$t" '{{id=$1; d=$2; $1=$2=$3=""; sub(/^ +/, ""); if (d != "-1" && ($0 == t || substr($0, length($0) - length(t) + 1) == t)) print id}}' | tail -1)
  if [ -z "$w" ]; then echo "missing: $t"; ok=0; continue; fi
  if ! xwininfo -id "$w" 2>/dev/null | grep -q "Map State: IsViewable"; then echo "not viewable: $t"; ok=0; continue; fi
  p=$(xprop -id "$w" _NET_WM_PID 2>/dev/null | awk '{{print $NF}}')
  if [ -z "$p" ] || ! kill -0 "$p" 2>/dev/null; then echo "no live owner: $t"; ok=0; fi
done < {windows}
[ "$ok" = 1 ] && echo READY"""
ACTIVATE_SH = r"""t={title}
w=$(wmctrl -l 2>/dev/null | awk -v t="$t" '{{id=$1; d=$2; $1=$2=$3=""; sub(/^ +/, ""); if ($0 == t && d != "-1") print id}}' | tail -1)
[ -n "$w" ] && wmctrl -i -a "$w" 2>/dev/null; sleep 1.5
{active_name}"""

RESTORE_GENERIC = r"""
[ -s {tar} ] || {{ echo "no baseline tar: nothing removed"; exit 1; }}
# -x matches the 15-character process name, so gnome-terminal-server and gnome-text-editor never matched (23 Oct,
# row 19: a terminal window more after every reset).  Names longer than that are matched on the command line, with
# the last character bracketed so the pattern does not match this script's own text (see CLEAN_SCRIPT).
for p in {procs}; do pkill -x "$p" 2>/dev/null; [ ${{#p}} -gt 15 ] && {{ l="${{p#"${{p%?}}"}}"; pkill -f "(^|/)${{p%?}}[$l]( |$)" 2>/dev/null; }}; done; sleep 2
for p in {procs}; do pkill -9 -x "$p" 2>/dev/null; [ ${{#p}} -gt 15 ] && {{ l="${{p#"${{p%?}}"}}"; pkill -9 -f "(^|/)${{p%?}}[$l]( |$)" 2>/dev/null; }}; done; true
cd "$HOME" || exit 1
for r in {roots}; do rm -rf "./$r" 2>/dev/null; done
find . -maxdepth 1 -type f ! -name '.*' -delete 2>/dev/null
# top-level folders the agent created (not in the recorded listing); never the VM's server or the rig cache
ls -A1 | grep -v '^\.' | while IFS= read -r e; do grep -qxF "$e" {top} || [ "$e" = server ] || rm -rf "./$e"; done
tar -xpf {tar} --same-owner 2>/dev/null; echo "untar=$?"
"""


def as_root(env, script: str) -> str:
    """The script run by root with HOME=/home/user, the way OSWorld's own setup steps use sudo (os/e0df059f:
    `echo {CLIENT_PASSWORD} | sudo -S ...`).  Root is needed for what the setup or the agent made with sudo: a
    root-owned folder (e0df059f's todo_list_Jan_1) can be neither archived nor removed by the user, and only root
    restores its owner.  The password is the provider's VM password (DesktopEnv.client_password), never stored."""
    pw = getattr(env, "client_password", "") or "password"
    return (f"echo {_shlex.quote(pw)} | sudo -S -p '' env HOME=/home/user DISPLAY=:0 sh -c {_shlex.quote(script)}")


def prime_generic(env, task: dict) -> str:
    script = PRIME_GENERIC.format(cache=CACHE_DIR, top=BASELINE_TOP, tar=BASELINE_TAR, windows=BASELINE_WINDOWS,
                                  roots=" ".join(_shlex.quote(r) for r in HOME_ROOTS))
    # the window list is recorded only once the task's windows are up and their titles have stopped changing: on
    # 23 Oct (probe-0026) the prime ran before VS Code's window existed, the baseline was empty, every reset was
    # "ready" at once, and the before-state was read while VS Code was still loading
    if gui_steps(task):
        deadline, prev, stable = time.time() + 120, None, 0
        while time.time() < deadline:
            cur = _windows_now(env)
            stable = stable + 1 if (cur and cur == prev) else 0
            prev = cur
            # VS Code titles itself "Visual Studio Code" until the file or folder is open, then "<name> - Visual
            # Studio Code" (v2-0040, 24 Oct: the bare title was recorded and every reset then looked incomplete)
            loading = any(t.strip() == "Visual Studio Code" for t in cur) and time.time() < deadline - 30
            if stable >= 2 and not loading:
                break
            time.sleep(5)
    return (vm_out(env, as_root(env, script), timeout=110) + "\n"
            + vm_out(env, PRIME_WINDOWS.format(windows=BASELINE_WINDOWS, active=BASELINE_ACTIVE, select_sh=FILES_SELECT_SH,
                                               active_name=ACTIVE_NAME_SH), timeout=20))


def _windows_now(env) -> list:
    out = vm_out(env, "wmctrl -l 2>/dev/null | awk '{ $1=$2=$3=\"\"; sub(/^ +/, \"\"); print }' | grep -v '^@!' | sort", timeout=15)
    return [l for l in out.splitlines() if l.strip()]


def _replay_step(env, s: dict) -> None:
    t, p = s.get("type"), s.get("parameters", {})
    if t == "sleep":
        time.sleep(min(float(p.get("seconds", 1)), 30))
    elif t == "open":
        vm_shell(env, f"nohup xdg-open {_shlex.quote(p['path'])} >/dev/null 2>&1 &", timeout=20)
        time.sleep(5)
    elif t == "activate_window":
        vm_shell(env, f"wmctrl -a {_shlex.quote(p.get('window_name', ''))} 2>/dev/null; true", timeout=15)
    else:   # launch, or execute/command that starts a GUI program
        c = p.get("command")
        text = c if isinstance(c, str) else " ".join(_shlex.quote(str(x)) for x in c)
        if p.get("shell") or isinstance(c, str):
            text = "sh -c " + _shlex.quote(text)
        # MOZ_CRASHREPORTER_DISABLE: a Thunderbird killed by the reset reported the crash at its next start and the
        # "Mozilla Crash Reporter" window broke every reset (v2-0055 rerun, 26 Oct); harmless for every other program
        vm_shell(env, f"export DISPLAY=:0 MOZ_CRASHREPORTER_DISABLE=1; nohup {text} >/dev/null 2>&1 &", timeout=20)
        time.sleep(5)


def generic_fresh_start(env, task: dict, wait_s: int = 90) -> str:
    """Returns 'generic' or 'generic-incomplete:<missing windows>'."""
    # LibreOffice first, gracefully, so it leaves no recovery entry (as in the fast path); only when it is running
    if "soffice" in vm_out(env, "pgrep -x soffice.bin >/dev/null && echo soffice; true", timeout=15):
        try:
            vm_shell(env, "wmctrl -a 'LibreOffice' 2>/dev/null; true", timeout=15)
            env.step("pyautogui.hotkey('ctrl', 'q'); time.sleep(3); " + DONT_SAVE + "; time.sleep(3)", pause=0.5)
        except Exception:
            pass
    # Files quits gracefully first (its own -q), so the next launch does not start against a killed instance's
    # leftovers: after a plain kill a relaunched Files sometimes took 40 s or more to show its window (21 Oct
    # 12:40, live poll: process alive, no window), the 90 s wait ran out, and the action's key reached the desktop
    vm_shell(env, "pgrep -x nautilus >/dev/null && { nautilus -q 2>/dev/null; sleep 1.5; }; true", timeout=20)
    vm_shell(env, CLEAN_SCRIPT, timeout=60)
    vm_shell(env, as_root(env, RESTORE_GENERIC.format(procs=" ".join(GUI_PROCS), top=BASELINE_TOP, tar=BASELINE_TAR,
                                                      roots=" ".join(_shlex.quote(r) for r in HOME_ROOTS))), timeout=110)
    want = [l for l in vm_out(env, f"cat {BASELINE_WINDOWS} 2>/dev/null", timeout=15).splitlines() if l.strip()]
    # every recorded window must be drawn and owned by a live process, not merely listed: after the kill the window
    # manager kept listing the dead Files window, the title check passed at once, and the action's key went to a
    # window that no longer existed (probe-0007, 20 Oct: Delete reached nothing in about half of the resets).
    # A launch whose window has not come after wait_s is repeated once.
    t_wait = time.time()
    missing = ["(not checked)"]
    for launch in range(2):
        for s in gui_steps(task):
            _replay_step(env, s)
        deadline = time.time() + wait_s
        while time.time() < deadline:
            out = vm_out(env, WINDOWS_READY_SH.format(windows=BASELINE_WINDOWS), timeout=20)
            missing = [l for l in out.splitlines() if l.strip() and l.strip() != "READY"]
            if "READY" in out.splitlines():
                # ready twice, 4 s apart, with the same titles: a window still loading changes its title
                # ("Visual Studio Code" -> "doc_proc - Visual Studio Code"; 23 Oct, probe-0026)
                titles_a = _windows_now(env)
                time.sleep(4)
                if _windows_now(env) == titles_a and "READY" in vm_out(env, WINDOWS_READY_SH.format(windows=BASELINE_WINDOWS), timeout=20).splitlines():
                    missing = []
                    break
            time.sleep(3)
        if not missing:
            break
        print(f"  fresh start: windows not ready after {wait_s}s ({'; '.join(missing)[:100]}); launching again", flush=True)
    wait_note = f";wait={time.time() - t_wait:.0f}s" if launch or time.time() - t_wait > 45 else ""
    vm_shell(env, "for w in $(wmctrl -l | awk '$2 != \"-1\" {print $1}'); do wmctrl -i -r $w -b add,maximized_vert,maximized_horz; done; true",
             timeout=20)
    # the keyboard goes to the window that had it after the task's setup (or the last recorded one), checked
    want_active = vm_out(env, f"cat {BASELINE_ACTIVE} 2>/dev/null", timeout=15).strip() or (want[-1] if want else "")
    active = ""
    if want_active:
        for _ in range(2):
            active = vm_out(env, ACTIVATE_SH.format(title=_shlex.quote(want_active), active_name=ACTIVE_NAME_SH), timeout=20).strip()
            if active == want_active:
                break
    time.sleep(SETTLE_SECONDS)
    how = "generic" if not missing else "generic-incomplete:" + _json.dumps(missing)[:200]
    if want_active and active != want_active:
        how += f";active={active or '?'}!={want_active}"
    return how + wait_note
