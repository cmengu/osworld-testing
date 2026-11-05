"""Pilot collector: one row = fresh start, before-snapshot S, the action, after-snapshot S', the four-tier
undo search, confirming replay, two teacher guesses taken before the action, one JSONL row (Paper draft
4.5 to 4.7 with the protocol changes of 17 Oct 2026).

    OSWorld/.venv/bin/python -I rig/collect_pilot.py --rows 1-10 --row-minutes 45     # the timing measurement
    OSWorld/.venv/bin/python -I rig/collect_pilot.py --rows 1-10 --dry                 # plan and cost, no VM
    OSWorld/.venv/bin/python -I rig/collect_pilot.py --recompare                       # re-judge rows on disk after a rule change

Per row: fresh start -> Ctrl+Home -> setup -> S -> [guess A, guess B start] -> action -> S'.  If S' == S after
masking the row is REVERSIBLE with an empty undo.  Otherwise candidates run cheapest tier first, each from a
fresh reset to S' (fresh start + setup + action), and the search stops at the first candidate whose masked
tree and file digest equal S.  A candidate's window list and file digest are read first (6 s); the tree
(about a minute) is read only when both already match.  Every row labelled no-undo reruns its
closest-failing candidate once; a seeded 10% of rows replay their result once more.  Everything is written
under rig/out/pilot_run/<row_id>/ (not committed) and one line per row in results.jsonl.

Keys: OPENAI_API_KEY is read from the git-ignored .env for the proposer; the teacher uses the Claude Code
subscription login.  Nothing prints a key.  The sandbox is closed in a finally.
"""
import argparse
import hashlib
import signal
import json
import os
import pathlib
import random
import re
import shutil
import sys
import threading
import time
import traceback

HERE = pathlib.Path(__file__).resolve().parent
BASE = HERE.parent
OSWORLD = BASE / "OSWorld"
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(OSWORLD))
# Sandbox lifetime 3 h, and the run swaps in a fresh sandbox between rows once the next row could not finish inside
# the lifetime (rotate_seconds below).  It was 10 h until 20 Oct: the Mac went into clamshell sleep at 01:22
# mid-probe, the collector froze, and the sandbox billed ~4 h idle.  A fixed 2.5 h then let probe-0007 start at
# 2.4 h and lose its sandbox mid-row.
os.environ.setdefault("MODAL_SANDBOX_TIMEOUT", "10800")
# --vm-snapshots needs the QMP port opened when the sandbox is created; the provider reads it at import (rig/vmsnap.py)
if "--vm-snapshots" in sys.argv:
    os.environ.setdefault("RIG_QEMU_QMP_PORT", "7102")
SANDBOX_LIFETIME = int(os.environ["MODAL_SANDBOX_TIMEOUT"])
ROW_GRACE_SECONDS = 10 * 60    # past the row cap, every VM call raises RowCapped (rig.vm) and the row ends with what it has


def rotate_seconds(row_minutes: float) -> float:
    """Sandbox age after which the next row starts on a fresh sandbox: lifetime minus the worst row, minus 5 min."""
    return max(1800.0, SANDBOX_LIFETIME - row_minutes * 60 - ROW_GRACE_SECONDS - 5 * 60)
# Modal ends a sandbox with no exec, no stdin and no open tunnel connection for this long.  The longest quiet stretch
# in a row is the wait for the teacher's guesses (at most 900 s), so 20 min never cuts a live row.
SANDBOX_IDLE_SECONDS = int(os.environ.get("RIG_SANDBOX_IDLE_SECONDS", "1200"))


def guard_modal_sandbox():
    """Give every Modal sandbox the rig creates an idle timeout: OSWorld's provider passes only a lifetime.  The
    guard lives in the cloud, so it works while the laptop sleeps, which no local watchdog can."""
    import modal
    orig = modal.Sandbox.create
    if getattr(orig, "_rig_guarded", False):
        return

    def create(*a, **k):
        k.setdefault("idle_timeout", SANDBOX_IDLE_SECONDS)
        return orig(*a, **k)
    create._rig_guarded = True
    modal.Sandbox.create = create
os.chdir(OSWORLD)

from rig.compact import file_diff, render                      # noqa: E402
from rig.freshstart import fresh_start, is_calc_task, prime_cache, switch_task  # noqa: E402
from rig.mask import apply_file_mask, file_sig, states_equal    # noqa: E402
from rig.settle import IDLE_PERCENT, RESET_CAP, late_file_changes, needs_settle, wait_settled    # noqa: E402
from rig.snapshot import load_snapshot, take_snapshot           # noqa: E402
from rig.treediff import summarize                              # noqa: E402
from rig import undo as U                                       # noqa: E402
from rig import vm as VM                                        # noqa: E402
from rig.vm import RowCapped, SandboxLost                       # noqa: E402

SANDBOX_USD_PER_HOUR = 0.76
CANDIDATE_ERRORS_IN_A_ROW = 3
CONFIRMATION_SINCE = 1792425600     # 2026-10-20 00:00 +08: rows started before it were recorded without the confirming re-run (the old value, 19 Oct 08:00 +08, left pilot_rerun's 19 Oct rows outside it; fixed 25 Oct)
WATCHDOG_SECONDS = 900        # no single candidate, snapshot or reset may take longer; a dead tunnel otherwise hangs forever


# spots whose action may legitimately leave no trace (saving an unchanged file); every other "no change" is a
# broken key route
NO_CHANGE_EXPECTED = frozenset({"save_clean", "imp_save_clean", "wr_save_clean", "ma_wr_save_clean", "ma_calc_save_clean", "select_all",   # select_all: the selection is not state (19 Oct)
                                "noop", "term_ls",            # probe rows: a bare Shift press; a command that writes nothing
                                "t3_readonly",                # v3 rows: ls / wc / head in a terminal (26 Oct; v3-0100 was marked broken without this)
                                "agent_step"})                # agent rows (28 Oct): an agent step that changes nothing is data (REVERSIBLE, empty undo), not a broken key route


class ResetFailed(Exception):
    """The fresh start plus action did not reproduce S'; a candidate judged from there would be judged wrongly."""


class CandidatesFailing(Exception):
    """Several candidates in a row errored before they could be judged (30 Oct, agent step 07: nine in an outage, a
    minute each, then a no-undo label).  The row stops, and the run waits for the network and tries it again."""


class Watchdog(BaseException):
    """BaseException, like KeyboardInterrupt: OSWorld's controller wraps its HTTP calls in `except Exception` and
    retries without a timeout, so an Exception raised from the alarm inside one is swallowed (rerun 0181, 19 Oct:
    the after-snapshot's tree fetch hung 80 min past the 15-min watchdog).  Caught by name where it is handled."""


def _alarm(signum, frame):
    raise Watchdog(f"step exceeded {WATCHDOG_SECONDS}s (tunnel or VM unresponsive)")


signal.signal(signal.SIGALRM, _alarm)
PRELUDE = "pyautogui.hotkey('ctrl', 'home')"
GATE_IGNORED = ("/home/user/.config/", "/home/user/.cache/", "/home/user/.local/share/", "/home/user/.mozilla/",
                "/home/user/.thunderbird/", "/home/user/.vscode/", "/home/user/snap/", "/home/user/.pki/", "/home/user/.rig_cache/")
STEP_PAUSE_AGENT = 10.0  # seconds between replayed agent steps (rig/agentrun/make_rows_agent.py); 3 s until 29 Oct 12:22: 13 of the first 20 recorded VS Code rows diverged, e.g. a double-click that opened a file in the agent's run (30-60 s between its steps) did not in the replay
TASK_DIR = OSWORLD / "evaluation_examples" / "examples" / "libreoffice_calc"
EXAMPLES = OSWORLD / "evaluation_examples" / "examples"


def _load_env_file():
    p = BASE / ".env"
    if p.exists():
        for line in p.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def titles(windows_text: str) -> list:
    """Window titles from wmctrl -l output (ids and the desktop entry dropped), sorted."""
    out = []
    for line in windows_text.split("--- active ---")[0].splitlines():
        parts = line.split(None, 3)
        if len(parts) == 4 and not parts[3].startswith("@!"):
            out.append(parts[3].strip())
    return sorted(out)


def content_score(tree_diffs, fdiffs) -> tuple:
    """Rank a failed candidate by how far it is from S in CONTENT first (cell text/formula/note, files,
    windows and dialogs), readouts second.  The closest-failing candidate for the confirming replay is the
    one with the fewest content differences; raw diff counts ranked a cursor move (1 cell still wrong) above a
    real undo (0 cells wrong, 25 readout diffs) on pilot-0003."""
    content = len(fdiffs)
    for d in tree_diffs:
        p, a = d["path"], d["attr"]
        if "table-cell" in p:
            if a in ("text", "Formula", "Note") or (a == NODE_ATTR and (d.get("old") or d.get("new")) and _cell_has_content(d)):
                content += 1
        elif ("/dialog[" in p or "/frame[" in p) and a == NODE_ATTR:
            content += 1
    return (content, len(tree_diffs) + len(fdiffs))


NODE_ATTR = "__node__"

WINDOW_CLOSERS = [["key:escape"],
                  # a question on top of a chooser (VS Code Save As over a sibling, v3-0070/0074, 27 Oct): Escape closes
                  # the question and the keyboard falls back to the main window, so the chooser needs the focus first.
                  # Second, not fourth: on that task every candidate costs 5-6 min (screenshot timeouts) and the fourth
                  # was never reached inside the 30-min row cap (r4f, 22:50)
                  ["key:escape", "wait:1", "focus:newest", "key:escape"],
                  ["focus:newest", "key:ctrl+w"], ["focus:newest", "key:alt+f4"]]
# focus:newest since 25 Oct: the window the action opened may not have the keyboard focus (v2-0090: Writer opened
# from a terminal kept none; Ctrl+W went to the terminal and Alt+F4 closed it).  Escape stays unfocused: a dialog
# the action opened has the focus by construction.


def window_tier(before_windows: str, after_windows: str) -> list:
    """Candidates tried first when the action left MORE windows than it found (a dialog, a new document, a terminal,
    a compose window): closing what opened is the natural undo, and it sat at position 15 of 16 in the generic and
    application tiers (probe rows 31 and 33, 23 Oct: 35 minutes each before Alt+F4 was reached).  Escape stays
    first so a dialog's undo is still recorded as Escape; Ctrl+W before Alt+F4 because it closes a document or tab
    rather than the application.  A title change alone (Save As) does not qualify; the count must grow."""
    if len(titles(after_windows)) > len(titles(before_windows)):
        return [list(c) for c in WINDOW_CLOSERS]
    return []


def _cell_has_content(d) -> bool:
    # a cell node that appears or disappears counts as content only if the differ recorded text on it; the
    # differ reports node presence without attributes, so presence alone is treated as a viewport change
    return False


def classify_diffs(tree_diffs, fdiffs) -> str:
    """Which layer a disagreement lives in: for the flicker_class field and Table 4."""
    if not tree_diffs and not fdiffs:
        return "none"
    kinds = []
    for d in tree_diffs:
        p = d["path"]
        if "table-cell" in p or "/table[" in p:
            kinds.append("cells")
        elif "tool-bar" in p:
            kinds.append("toolbar")
        elif "/menu" in p:
            kinds.append("menu")
        elif "status" in p.lower():
            kinds.append("statusbar")
        elif "/dialog[" in p or "/frame[" in p and p.count("/") <= 4:
            kinds.append("windows")
        else:
            kinds.append("other")
    if fdiffs:
        kinds.append("files")
    from collections import Counter
    return "+".join(k for k, _ in Counter(kinds).most_common(2))


class Collector:
    def __init__(self, args):
        self.args = args
        self.out = pathlib.Path(args.out)
        self.out.mkdir(parents=True, exist_ok=True)
        self.mask = json.load(open(args.mask))
        self.mask_version = _sha(pathlib.Path(args.mask))
        self.rules_version = hashlib.sha256((HERE / "treediff.py").read_bytes() + (HERE / "mask.py").read_bytes() + (HERE / "xlsxsig.py").read_bytes()
                                            + (HERE / "officesig.py").read_bytes()).hexdigest()[:12]   # officesig since 24 Oct
        if getattr(args, "drop_hidden", False):
            from rig import treediff
            treediff.DROP_HIDDEN = True
            self.rules_version += "+hidden"
        if getattr(args, "ignore_layout", False):
            from rig import mask as _mask
            _mask.IGNORE_LAYOUT = True
            self.rules_version += "+layout"
        if getattr(args, "settle_cap", 0):
            self.rules_version += f"+settle{args.settle_cap:g}i{IDLE_PERCENT}"
        self.candidates_version = hashlib.sha256((HERE / "undo.py").read_bytes()).hexdigest()[:12]
        self.last_settle = None
        data = json.load(open(args.spots))
        self.spots = {s["id"]: s for s in data["spots"]}
        self.rows_all = data["rows"]
        # tasks of agent rows (rig/agentrun): their VMs keep the task's own VS Code settings (rig/vmprep.py)
        self.agent_tasks = {r["task_id"] for r in self.rows_all if r.get("band") == "agent"}
        self.mnemonics = dict(data["meta"].get("mnemonic_placeholders", {}))
        if args.mnemonics:
            self.mnemonics.update(json.loads(args.mnemonics))
        self.results_path = self.out / "results.jsonl"
        self.done = set()
        # --plans (3 Nov): undo plans to execute per row, {row_id: [{"source": "model"|"claude"|"ctrlz"|..., "steps": [...]}]}.
        # With --plans-only they are the whole search (the H3 rollback comparison); without it they go first, ahead of
        # the usual tiers (relabelling rows under the 2 November rules).
        self.plans = json.loads(pathlib.Path(args.plans).read_text()) if getattr(args, "plans", "") else {}
        if self.results_path.exists():
            for line in self.results_path.read_text().splitlines():
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if r.get("status") == "ok":
                    self.done.add(r["row_id"])
        self.env = None
        self.env_started = None
        self.sandbox_seconds = 0.0
        self.current_task_id = None
        self.tasks = {}
        self.timings = {"snapshot": [], "fresh_start": [], "row": [], "candidate": []}
        self.env_restarts = 0
        self.vmsnap = None        # rig/vmsnap.py with --vm-snapshots: resets restore a VM snapshot instead of a fresh start
        self._vm_row = None
        self._cur_row = None           # the row run_row is on, for the VS Code snapshot saves in snapshot()
        self._snap_after_walk = False

    # ------------------------------------------------------------------ selection
    def select_rows(self):
        rows = self.rows_all
        if self.args.rows:
            wanted, wanted_ids = set(), set()
            for part in self.args.rows.split(","):
                part = part.strip()
                if re.fullmatch(r"\d+-\d+", part):
                    a, b = part.split("-")
                    wanted.update(range(int(a), int(b) + 1))
                elif re.fullmatch(r"[a-z0-9]+-\d+", part):      # pilot-0300, probe-0012, v2-0045
                    wanted.add(int(part.split("-")[1]))
                elif re.fullmatch(r"\d+", part):
                    wanted.add(int(part))
                elif part:                                        # agent rows: ag-<task>-<nn>, matched whole (28 Oct)
                    wanted_ids.add(part)

            def number(row_id):
                tail = row_id.split("-")[1]
                return int(tail) if tail.isdigit() else None
            rows = [r for r in rows if r["row_id"] in wanted_ids or number(r["row_id"]) in wanted]
        if self.args.spots_filter:
            keep = set(self.args.spots_filter.split(","))
            rows = [r for r in rows if r["spot_id"] in keep]
        if self.args.limit:
            rows = rows[: self.args.limit]
        rows = [r for r in rows if r["row_id"] not in self.done]
        # group by workbook to limit task switches, keep row order inside a group
        order = {}
        for r in rows:
            order.setdefault(r["task_id"], len(order))
        rows.sort(key=lambda r: (order[r["task_id"]], r["row_id"]))
        return rows

    def task(self, task_id):
        if task_id not in self.tasks:
            f = TASK_DIR / f"{task_id}.json"
            if not f.exists():                         # Files, multi_apps, Thunderbird rows (19 Oct)
                f = HERE / "tasks" / f"{task_id}.json"  # hand-built tasks (the Files probe)
            if not f.exists():
                # OS-Harm tasks of the agent run (rig/agentrun, 28 Oct; test only)
                f = next(iter((HERE / "agentrun" / "tasks" / "examples").glob(f"*/{task_id}.json")), f)
            if not f.exists():
                f = next(EXAMPLES.glob(f"*/{task_id}.json"))
            self.tasks[task_id] = json.loads(f.read_text())
        return self.tasks[task_id]

    # ------------------------------------------------------------------ environment
    def start_env(self, task_id):
        from desktop_env.desktop_env import DesktopEnv
        from rig.vmprep import prepare_vm
        if self.args.provider == "modal":
            guard_modal_sandbox()
        t0 = time.time()
        # the watchdog covers the sandbox start too: r3e hung from 19:15 to 22:05 on 27 Oct in a socket read while
        # opening a sandbox during a network outage, with no alarm armed (the row's alarm is set later, in run_row)
        prev = signal.alarm(WATCHDOG_SECONDS)
        try:
            self.env = DesktopEnv(provider_name=self.args.provider, action_space="pyautogui", headless=True,
                                  require_a11y_tree=False, os_type="Ubuntu")
            self.env_started = time.time()
            task = self.task(task_id)
            self.env.reset(task_config=task)
            print(f"[env] task {task_id[:8]} ready after {time.time() - t0:.0f}s; prep: {prepare_vm(self.env, agent=task_id in self.agent_tasks)}; cache: {prime_cache(self.env, task)}", flush=True)
            if getattr(self.args, "vm_snapshots", False):
                from rig.vmsnap import VMSnap
                self.vmsnap = VMSnap(self.env)
                print(f"[env] VM snapshots on (QEMU {self.vmsnap.qemu}, disk node {self.vmsnap.node})", flush=True)
        finally:
            signal.alarm(prev if prev else 0)
        self.current_task_id = task_id

    def wait_for_network(self, max_s: float = 1800) -> bool:
        """Block until Modal's API answers (up to max_s).  A network drop at 11:40 on 21 Oct lost the sandbox on
        row 13, and the run then ran through rows 14-33 in seconds, each an error, while the close of the lost
        sandbox failed and left it billing.  Waiting here keeps the rows for later and lets the close succeed."""
        import socket
        t0 = time.time()
        said = False
        while time.time() - t0 < max_s:
            try:
                socket.create_connection(("api.modal.com", 443), timeout=5).close()
                if said:
                    print(f"[env] network back after {time.time() - t0:.0f}s", flush=True)
                return True
            except OSError:
                if not said:
                    print("[env] network down: waiting (up to 30 min)", flush=True)
                    said = True
                time.sleep(20)
        return False

    def close_env(self):
        if self.vmsnap is not None:      # its snapshots live in the sandbox's disk and go with it
            self.vmsnap.close()
            self.vmsnap = None
        if self.env is None:
            return
        try:
            self.env.close()
            print("[env] closed", flush=True)
        except Exception as e:  # pragma: no cover
            print("[env] close error:", repr(e)[:200], flush=True)
        if self.env_started:
            self.sandbox_seconds += time.time() - self.env_started
        self.env = None
        self.env_started = None

    def ensure_task(self, task_id):
        if self.env is None:
            self.start_env(task_id)
            return "env-start"
        if task_id != self.current_task_id and not (is_calc_task(self.task(task_id)) and is_calc_task(self.task(self.current_task_id))):
            # a task that is not one spreadsheet runs setup commands, launches programs and leaves files and
            # folders behind: it gets a sandbox of its own (about 3 min, 0.04 USD), so no task sees another's files
            self.close_env()
            self.start_env(task_id)
            return "env-restart"
        if task_id != self.current_task_id:
            t0 = time.time()
            how = switch_task(self.env, self.task(task_id))
            if how == "download-failed":
                raise RuntimeError(f"could not download the files of task {task_id}")
            self.current_task_id = task_id
            print(f"[env] switched to task {task_id[:8]} ({how}) in {time.time() - t0:.0f}s", flush=True)
            return "switched:" + how
        return "same-task"

    # ------------------------------------------------------------------ primitives
    def step(self, code: str, pause: float = 1.0):
        self.env.step(code, pause=pause)

    # VM snapshots of a row (--vm-snapshots, rig/vmsnap.py, 29 Oct): "b" is the VM after the row's first reset, saved
    # before anything walks its accessibility tree, so every later reset gets an instance nobody has walked, as a fresh
    # start did (probe-0005, 20 Oct); "a" is the VM right after the action, before S' is read.  A snapshot that fails
    # to save or load falls back to the fresh start; the row's snapshots are deleted when the row ends (each is
    # about 4.6 GB of the sandbox's disk with VS Code and Writer open).
    def _snap_tag(self, row, kind):
        return re.sub(r"[^A-Za-z0-9_]", "_", row["row_id"]) + "_" + kind

    def _snap_save(self, row, kind):
        if self.vmsnap is None:
            return None
        from rig.vmsnap import VMSnapError
        tag = self._snap_tag(row, kind)
        try:
            self.vmsnap.delete(tag)
            dt = self.vmsnap.save(tag)
        except (VMSnapError, OSError) as e:
            # one failed save no longer ends snapshots for the run (30 Oct: a slow save on a full overlay turned the
            # agent's remaining steps into replays); the third does
            self._snap_failures = getattr(self, "_snap_failures", 0) + 1
            if self._snap_failures >= 3:
                print(f"  VM snapshot {tag} not saved ({repr(e)[:160]}): third failure, fresh starts from here on", flush=True)
                self.vmsnap = None
            else:
                print(f"  VM snapshot {tag} not saved ({repr(e)[:160]}): this reset falls back to a fresh start", flush=True)
                self.vmsnap.tags.discard(tag)
            return None
        if self._vm_row is not None:
            self._vm_row["saves"].append(round(dt, 1))
        return dt

    def _snap_load(self, row, kind):
        if self.vmsnap is None:
            return None
        tag = self._snap_tag(row, kind)
        if kind == "b" and row.get("vm_snapshot_before") in self.vmsnap.tags:
            # an agent row in the sandbox its run left behind: the agent's own VM just before this step
            tag = row["vm_snapshot_before"]
        if tag not in self.vmsnap.tags:
            return None
        from rig.vmsnap import VMSnapError
        try:
            dt = self.vmsnap.load(tag)
        except (VMSnapError, OSError) as e:
            print(f"  VM snapshot {tag} not restored ({repr(e)[:160]}): a fresh start instead", flush=True)
            if self._vm_row is not None:
                self._vm_row["load_failures"] += 1
            self.vmsnap.tags.discard(tag)
            return None
        if self._vm_row is not None:
            self._vm_row["loads"].append(round(dt, 1))
        return dt

    def _snap_drop(self, row, kinds=("b", "a")):
        if self.vmsnap is not None:
            for k in kinds:
                self.vmsnap.delete(self._snap_tag(row, k))

    def reset_to_before(self, row, fresh: bool = False) -> dict:
        """Fresh start, Ctrl+Home, setup, or the row's VM snapshot "b" once it exists (fresh=True: never).  Returns timings."""
        dt = None if fresh else self._snap_load(row, "b")
        if dt is not None:
            agent_own = self.vmsnap is not None and row.get("vm_snapshot_before") in self.vmsnap.tags
            return {"fresh_start": "vm-snapshot-agent" if agent_own else "vm-snapshot", "fresh_start_seconds": round(dt, 1), "setup_seconds": 0.0}
        t = time.time()
        how = fresh_start(self.env, self.task(row["task_id"]))
        t_fs = time.time() - t
        self.timings["fresh_start"].append(t_fs)
        if how.startswith("generic-incomplete"):
            # no window to act on: a key sent now goes to the desktop and the "action" changes nothing (21 Oct)
            raise ResetFailed(f"fresh start incomplete after {t_fs:.0f}s: {how[:160]}")
        prelude = row.get("prelude", PRELUDE)
        if prelude:
            self.step(prelude, pause=1.0)
        setup = row.get("setup")
        if isinstance(setup, list):
            # agent rows (rig/agentrun): the agent's earlier steps, one call each as the agent ran them; one joined
            # string breaks multi-line loops and outlasts the VM's 120 s limit on a single command (28 Oct)
            for code in setup:
                self.step(code, pause=STEP_PAUSE_AGENT)
        elif setup:
            self.step(setup, pause=2.0)
        info = {"fresh_start": how, "fresh_start_seconds": round(t_fs, 1), "setup_seconds": round(time.time() - t - t_fs, 1)}
        saved = None if fresh or getattr(self, "_snap_after_walk", False) else self._snap_save(row, "b")
        if saved is not None:
            info["vm_snapshot_saved_seconds"] = round(saved, 1)
        return info

    def act(self, row, full_settle: bool = False):
        self.step(row["code"], pause=row.get("pause", 2))
        cap = getattr(self.args, "settle_cap", 0)
        cap = cap if full_settle else min(cap, RESET_CAP)
        self.last_settle = wait_settled(self.env, cap=cap) if cap and needs_settle(row["code"]) else None

    def reset_to_after(self, row, expect_windows: str = "", expect_digest=None, independent: bool = False) -> dict:
        """Fresh start plus the action.  With expect_windows (the recorded S' window list), the reset is checked
        against it and redone up to twice: a reset that comes back without the document (pilot2 0079 c01: only a
        file-manager "Home" window) otherwise rejects a correct undo.  With expect_digest (S' file digest), the
        files must match S' too (20 Oct, probe-0007: a redone reset passed the window check although its Delete had
        not trashed a.txt, and Escape twice then "restored" a file that had never left).  A mismatch saves a
        screenshot under <out>/reset_mismatch/."""
        from rig.mask import _fsig
        from rig.snapshot import WINDOWS_SCRIPT, _digest
        from rig.vm import vm_shell
        want = sorted(titles(expect_windows)) if expect_windows else None
        want_files = apply_file_mask(expect_digest, self.mask) if expect_digest else None
        why = ""
        # independent=True (confirming re-runs and replays): a fresh instance, as before VM snapshots, so a match that
        # held on one instance only is still caught; an agent row restored from its run's own VM has no fresh instance
        # that reaches its state (the replays diverged), so its re-runs restore that VM again
        agent_own = self.vmsnap is not None and row.get("vm_snapshot_before") in self.vmsnap.tags
        fresh = independent and not agent_own
        for attempt in range(3):
            dt = self._snap_load(row, "a") if attempt == 0 and not fresh else None
            if dt is not None:
                info = {"fresh_start": "vm-snapshot-after", "fresh_start_seconds": round(dt, 1), "setup_seconds": 0.0}
            else:
                try:
                    info = self.reset_to_before(row, fresh=fresh)
                except ResetFailed as e:
                    last_why = why = str(e)
                    print(f"  reset did not reproduce the after-state: {why[:120]}; again", flush=True)
                    why = ""
                    continue
                self.act(row)
            if want is None and want_files is None:
                return info
            if want is not None:
                # poll up to 20 s: right after Don't Save the list is empty until the Start Center is drawn
                for _ in range(8):
                    got = sorted(titles(vm_shell(self.env, WINDOWS_SCRIPT, timeout=20).get("output") or ""))
                    if got == want:
                        break
                    time.sleep(2.5)
                if got != want:
                    why = f"windows {got} vs {want}"
            if want_files is not None and not why:
                d, _ = _digest(self.env)
                have = apply_file_mask(d, self.mask)
                bad = sorted(p for p in set(have) | set(want_files) if _fsig(p, have.get(p)) != _fsig(p, want_files.get(p)))
                if bad:
                    why = f"files differ from S': {len(bad)} ({bad[0]})"
            if not why:
                return {**info, "reset_attempts": attempt + 1, "reset_checked": "windows+files" if want_files is not None else "windows"}
            print(f"  reset did not reproduce the after-state: {why}; again", flush=True)
            last_why = why
            try:
                shot = self.env.controller.get_screenshot()
                if shot:
                    d = self.out / "reset_mismatch"
                    d.mkdir(exist_ok=True)
                    (d / f"{row['row_id']}_{int(time.time())}.png").write_bytes(shot)
            except Exception:
                pass
            why = ""
        raise ResetFailed(f"after-state not reproduced in 3 resets: {last_why}")

    def snapshot(self, path, meta, expect_kind="calc", office_expected=True):
        """expect_kind: the spot's declared outcome for S' ('calc', 'dialog', 'start_center', 'second_window',
        'app_closed'); 'any' for undo candidates and replays, whose outcome is unknown: the tree is taken as it is
        (waiting for a LibreOffice window only when one is expected) and completeness is not a gate;
        'apps:<bus name>,...' for rows outside LibreOffice: those applications must be in the tree with a window."""
        t = time.time()
        if expect_kind in ("calc", "dialog", "start_center", "second_window"):
            self.settle_windows()
        # the size shortcut never applies to S or S' themselves: a half-filled S' the size of S would hide the action
        primed = (self.warm_accessibility(refs=meta.get("kind") not in ("before", "after"))
                  if getattr(self, "_warm_code", False) else None)
        if expect_kind == "none":                     # no readiness gate: an application whose bus name is not known yet
            snap = take_snapshot(self.env, path, meta, expect=None, require_office=False, primed=primed)
        elif expect_kind.startswith("apps:"):
            apps = [a for a in expect_kind[5:].split(",") if a]
            office = "soffice" in apps
            snap = take_snapshot(self.env, path, meta, expect="LibreOffice" if office else None, require_office=office,
                                 expect_apps=[a for a in apps if a != "soffice"], primed=primed)
        elif expect_kind == "any":
            snap = take_snapshot(self.env, path, meta, expect="LibreOffice" if office_expected else None, require_office=False,
                                 primed=primed)
        else:
            app_may_be_closed = expect_kind == "app_closed"
            snap = take_snapshot(self.env, path, meta, expect=None if app_may_be_closed else "LibreOffice",
                                 require_office=not app_may_be_closed)
        if expect_kind in ("calc", "dialog", "start_center", "second_window") \
                and not any("LibreOffice" in x for x in titles(snap.windows)):
            # the tree can catch LibreOffice while its window is still being replaced: probe-0005 S1 (20 Oct) was
            # recorded with an empty window list after Don't Save, and every correct reset to the Start Center then
            # failed the window check against it.  Not ok, so the caller retakes it.
            snap.meta["ok"] = False
            snap.meta["window_error"] = "window list lacks a LibreOffice window"
        self.timings["snapshot"].append(time.time() - t)
        if getattr(self, "_snap_after_walk", False) and self._cur_row is not None and snap.ok:
            # VS Code rows (30 Oct): the row's VM snapshots are saved after the state's tree was read, so every restore
            # comes back with VS Code's tree already exposed (a cold one needs three walks of about 40 s to fill in)
            kind = meta.get("kind")
            if kind == "before" and not str(meta.get("fresh_start", "")).startswith("vm-snapshot"):
                self._snap_save(self._cur_row, "b")
            elif kind == "after":
                self._snap_save(self._cur_row, "a")
        return snap

    def needs_warm(self, row) -> bool:
        if row.get("app") == "vs_code" or "code" in (str(row.get("expect_before", "")) + str(row.get("expect", ""))):
            return True
        task = self.task(row["task_id"])
        text = json.dumps(task.get("config", [])).lower() + " " + json.dumps(row.get("reopen_cmd") or []).lower() + " " + str(row.get("code", "")).lower()
        return any(k in text for k in ("vscode", "vs_code", "\"code\"", "code -g", ".pdf", "evince"))

    def warm_accessibility(self, reads: int = 3, tolerance: float = 0.02, refs: bool = False):
        """VS Code (Chromium) exposes its web content to the accessibility bus only once something has asked for it,
        and fills it in over a few seconds: v2-0040 (24 Oct, VS Code no-op) recorded 50 nodes in S and 340 in S', the
        editor absent from the first.  Walk the tree until two consecutive reads agree in size (at most `reads`).
        Returns the last read, (xml, stats), when it agreed with the one before: the snapshot uses it instead of a
        fourth walk (30 Oct: about 40 s each in VS Code).  None otherwise, and the snapshot walks again.
        With refs (candidates, confirmations, replays; never S or S'), a first read already within the same tolerance
        of a full tree this row recorded (S or S', self._warm_refs) is taken at once: a VS Code tree still filling in is far smaller (50 nodes of 586, 29 Oct), and restores of
        VS Code rows come back warm, so the second read only repeated the first (30 Oct check: two or three walks
        of 29-38 s per candidate)."""
        from rig.fasttree import fast_tree
        prev = None
        for i in range(reads):
            xml, stats = fast_tree(self.env)
            n = xml.count("<")
            near = lambda m: abs(n - m) <= max(5, tolerance * max(n, m))
            if refs and xml and i == 0 and any(near(m) for m in getattr(self, "_warm_refs", [])):
                return xml, {**stats, "warm_ref": True}
            if prev is not None and near(prev):
                return (xml, stats) if xml else None
            prev = n
            time.sleep(3)
        return None

    def settle_windows(self, timeout: float = 45) -> list:
        """Wait until a LibreOffice window is listed and the window list is the same on two reads 3 s apart, before
        the accessibility tree is walked.  Walking LibreOffice's tree while it swaps a closing document for the Start
        Center made it vanish (probe-0005 S1, 20 Oct, after Don't Save: the S1 snapshot and both retakes found no
        LibreOffice window, while every reset that read only the window list found the Start Center)."""
        from rig.snapshot import WINDOWS_SCRIPT
        from rig.vm import vm_shell
        deadline, prev = time.time() + timeout, None
        while time.time() < deadline:
            cur = titles(vm_shell(self.env, WINDOWS_SCRIPT, timeout=20).get("output") or "")
            if cur == prev and any("LibreOffice" in x for x in cur):
                return cur
            prev = cur
            time.sleep(3)
        return prev or []

    def quick_state(self):
        """Window titles and file digest only (about 6 s): enough to reject most failed undos without a tree."""
        from rig.snapshot import WINDOWS_SCRIPT, _digest
        from rig.vm import vm_shell
        windows = vm_shell(self.env, WINDOWS_SCRIPT, timeout=20).get("output") or ""
        if not titles(windows) and "@!" not in windows:
            # an empty list without even the desktop entry is wmctrl failing, not an empty desktop
            # (pilot-0210 c07): ask once more before judging
            time.sleep(3)
            windows = vm_shell(self.env, WINDOWS_SCRIPT, timeout=20).get("output") or windows
        digest, err = _digest(self.env)
        return windows, digest, err

    def quick_matches(self, S, windows, digest):
        reasons = []
        if titles(windows) != titles(S.windows):
            reasons.append(f"windows differ: {titles(windows)} vs {titles(S.windows)}")
        fa, fb = apply_file_mask(S.digest, self.mask), apply_file_mask(digest, self.mask)
        from rig.mask import _fsig
        fdiffs = sorted(p for p in set(fa) | set(fb) if _fsig(p, fa.get(p)) != _fsig(p, fb.get(p)))
        if fdiffs:
            reasons.append(f"files differ: {len(fdiffs)} ({fdiffs[0]}{' ...' if len(fdiffs) > 1 else ''})")
        return (not reasons), reasons, fdiffs

    # ------------------------------------------------------------------ one row
    def run_row(self, row) -> dict:
        t_row = time.time()
        rid = row["row_id"]
        # rows with VS Code or a PDF viewer on screen warm the accessibility tree before every snapshot
        # (warm_accessibility): both expose their content lazily (VS Code: v2-0040; evince's 97 page nodes appeared
        # after a click: step had walked the tree, v2-0084, 24 Oct); set before S is taken
        self._warm_code = self.needs_warm(row)
        # VS Code rows save their VM snapshots after the state's tree is read (snapshot()); LibreOffice rows keep
        # saving before any walk, since walking LibreOffice and then acting on it made it vanish (probe-0005)
        self._snap_after_walk = self.vmsnap is not None and row.get("app") == "vs_code"
        self._cur_row = row
        self._warm_refs = []             # sizes of this row's full trees (S, S'), for warm_accessibility
        spot = self.spots[row["spot_id"]]
        rdir = self.out / rid
        rdir.mkdir(parents=True, exist_ok=True)
        task = self.task(row["task_id"])
        env_how = self.ensure_task(row["task_id"])
        rec = {"row_id": rid, "app": row.get("app", "libreoffice-calc"), "task_id": row["task_id"], "workbook": row["workbook"],
               "spot_id": row["spot_id"], "band": row["band"], "on_task": row["on_task"], "on_task_reason": row["on_task_reason"],
               "seed": row["seed"], "sequence": row.get("sequence"), "step": row.get("step"), "twin_of": row.get("twin_of"),
               "target_cell": row.get("target_cell"), "target_in_set": row.get("target_in_set"),
               "action": {"type": "pyautogui", "desc": spot["desc"], "code": row["code"], "setup": row.get("setup") or "",
                          "prelude": row.get("prelude", PRELUDE), "pause": row.get("pause", 2), "expect": row.get("expect", "calc")},
               "known_answer": row.get("known_answer"),
               "mask_version": self.mask_version, "rules_version": self.rules_version, "candidates_version": self.candidates_version, "env": env_how,
               "started_at": time.time()}

        # ---- S
        signal.alarm(WATCHDOG_SECONDS)
        info = self.reset_to_before(row)
        S = self.snapshot(rdir / "S", {"row": rid, "kind": "before", **info}, expect_kind=row.get("expect_before", "calc"))
        if not S.ok:
            time.sleep(3)
            S = self.snapshot(rdir / "S", {"row": rid, "kind": "before", **info, "retake": True}, expect_kind=row.get("expect_before", "calc"))
        signal.alarm(0)
        if S.ok and S.tree_xml:
            self._warm_refs = [S.tree_xml.count("<")]
        rec["snapshot_before"] = str(S.path.relative_to(self.out))
        rec["before_ok"] = S.ok
        rec["tree_before"] = str((S.path / "tree.xml").relative_to(self.out))
        files_scope = "office" if rec["app"] == "libreoffice-calc" else "user"
        before_text = render(S.canon, S.digest, S.windows, files=files_scope)
        rec["state_before_compact"] = before_text
        rec["state_before_tokens_est"] = len(before_text) // 4

        # ---- agent rows: is S the screen the agent saw before this step?  (rig/agentrun/fidelity.py, 28 Oct)
        if row.get("band") == "agent" and row.get("recorded_before") and (BASE / row["recorded_before"] / "tree.xml").exists():
            # the agent's own state before this step was recorded during its run (OSWorld/lib_run_single.py,
            # RIG_RECORD_STATES, 29 Oct): S must equal it under the same rules as any reset, else the replay diverged
            R = load_snapshot(BASE / row["recorded_before"])

            def same(S_):
                # the recorded state comes from another VM instance: its housekeeping files (ibus' bus address,
                # evolution's contact DB, caches, browser profiles) differ between instances even with no action, and
                # the noise mask was built within one instance (29 Oct, agr-shell_script_permissions-02: 0 tree, 2
                # such files).  The gate compares the tree, the window titles and the user's files; labelling still
                # compares S and S' of one instance under the full mask.
                keep = lambda dg: {p: v for p, v in dg.items() if not p.startswith(GATE_IGNORED) or p.startswith("/home/user/.local/share/Trash/")}
                eq_, td, fd = states_equal(S_.canon, keep(S_.digest), R.canon, keep(R.digest), self.mask)
                return eq_ and titles(S_.windows) == titles(R.windows), len(td), len(fd)
            ok_, ntd, nfd = same(S)
            if not ok_:
                # one more replay: app launch and dialog timing vary between instances
                signal.alarm(WATCHDOG_SECONDS)
                self._snap_drop(row, ("b",))
                info = self.reset_to_before(row)
                S = self.snapshot(rdir / "S", {"row": rid, "kind": "before", **info, "retake": "fidelity"},
                                  expect_kind=row.get("expect_before", "calc"))
                signal.alarm(0)
                ok_, ntd, nfd = same(S)
            rec["replay_fidelity"] = {"recorded": row["recorded_before"], "equal": ok_, "tree_diffs": ntd, "file_diffs": nfd}
            if not ok_:
                print(f"  [{rid}] replay diverged from the agent's recorded state ({ntd} tree, {nfd} files): not labelled", flush=True)
                rec.update({"status": "replay_diverged", "executed_label": None, "shortest_undo": None, "undo_length": None,
                            "found_tier": None, "budget_used": 0, "guessed_label_verbatim": None, "guessed_label_defined": None,
                            "row_seconds": round(time.time() - rec["started_at"], 1)})
                return rec
        elif row.get("band") == "agent":
            from rig.agentrun.fidelity import agent_before_shot, screen_diff, DIVERGED
            shot = agent_before_shot(row)
            if shot and (S.path / "screenshot.png").exists():
                score = screen_diff(S.path / "screenshot.png", shot)
                if score > DIVERGED:
                    # one more replay: app launch and search timing vary between instances
                    signal.alarm(WATCHDOG_SECONDS)
                    self._snap_drop(row, ("b",))
                    info = self.reset_to_before(row)
                    S = self.snapshot(rdir / "S", {"row": rid, "kind": "before", **info, "retake": "fidelity"},
                                      expect_kind=row.get("expect_before", "calc"))
                    signal.alarm(0)
                    score = screen_diff(S.path / "screenshot.png", shot)
                rec["replay_fidelity"] = {"score": round(score, 1), "limit": DIVERGED, "agent_shot": str(shot.relative_to(BASE))}
                if score > DIVERGED:
                    print(f"  [{rid}] replay diverged from the agent's screen (score {score:.1f} > {DIVERGED}): not labelled", flush=True)
                    rec.update({"status": "replay_diverged", "executed_label": None, "shortest_undo": None, "undo_length": None,
                                "found_tier": None, "budget_used": 0, "guessed_label_verbatim": None, "guessed_label_defined": None,
                                "row_seconds": round(time.time() - rec["started_at"], 1)})
                    return rec

        # ---- teacher guesses, requested before the action runs
        guesses = {}
        trajectory = row.get("trajectory") or (["Ctrl+Home (cursor to A1)"] + ([f"setup keys: {row['setup']}"] if row.get("setup") else []))
        instruction = task["instruction"]

        def ask():
            from rig import teacher
            try:
                guesses["A"] = teacher.guess_a(instruction, before_text, trajectory, spot["desc"], row["code"])
            except Exception as e:
                guesses["A"] = {"reversible": None, "error": repr(e)[:300]}
            try:
                guesses["B"] = teacher.guess_b(instruction, before_text, trajectory, spot["desc"], row["code"])
            except Exception as e:
                guesses["B"] = {"reversible": None, "error": repr(e)[:300]}
        th = None
        rec["guess_requested_at"] = None
        if not self.args.no_teacher:
            rec["guess_requested_at"] = time.time()
            th = threading.Thread(target=ask, daemon=True)
            th.start()

        # ---- action and S'.  The action runs on a fresh instance that nobody has walked: after the S snapshot read
        # LibreOffice's accessibility tree, closing a document in the same instance made LibreOffice vanish
        # (probe-0005, 20 Oct: Don't Save left a bare desktop three times; resets that walked nothing showed the
        # Start Center).  S is the same state either way: every reset is checked against it below.
        # The action must do what the row says (20 Oct, probe-0007: the Delete key reached nothing on the action's
        # instance, S' showed a.txt still in place, and the search then measured nothing for 5.8 h).  A probe row
        # names the classes of change its action must produce in `expect_change` ("files", "windows", "tree"); the
        # action is retried on a fresh instance up to twice, and a row whose action never takes effect is broken,
        # not data.  Pilot rows name none and keep the old rule: any change counts, none is a broken key route.
        want_change = set(row.get("expect_change") or [])
        misfires = []
        for action_try in range(3):
            signal.alarm(WATCHDOG_SECONDS)
            rec["action_instance"] = self.reset_to_before(row)
            rec["action_executed_at"] = time.time()
            self.act(row, full_settle=True)
            if not self._snap_after_walk:
                self._snap_save(row, "a")
            rec["settle"] = self.last_settle
            S1 = self.snapshot(rdir / "S1", {"row": rid, "kind": "after"}, expect_kind=row.get("expect", "calc"))
            if self.last_settle:
                rec["after_late_changes"] = late_file_changes(self.env, S1.digest, self.mask)
            for wait in (3, 10):
                if S1.ok:
                    break
                time.sleep(wait)
                S1 = self.snapshot(rdir / "S1", {"row": rid, "kind": "after", "retake": True}, expect_kind=row.get("expect", "calc"))
            if S1.meta.get("window_error"):
                # an after-state recorded without the application it must show would misjudge every candidate: the row
                # is retried from a fresh sandbox instead (probe-0005, 20 Oct)
                signal.alarm(0)
                raise RuntimeError(f"after-state not recorded: {S1.meta['window_error']}")
            signal.alarm(0)
            eq, tdiffs, fdiffs = states_equal(S.canon, S.digest, S1.canon, S1.digest, self.mask)
            # a window the tree does not show (VS Code's GTK chooser and its replace question, v3-0072 on 27 Oct) is a
            # change too, as the candidate judge and the recompare already count it
            eq = eq and titles(S1.windows) == titles(S.windows)
            changed = set()
            if fdiffs:
                changed.add("files")
            if titles(S1.windows) != titles(S.windows):
                changed.add("windows")
            if tdiffs:
                changed.add("tree")
            if not want_change or changed & want_change:
                break
            misfires.append({"try": action_try + 1, "changed": sorted(changed), "instance": rec["action_instance"]})
            print(f"  [{rid}] the action changed {sorted(changed) or 'nothing'}, not {sorted(want_change)}: again on a fresh instance", flush=True)
            kept = rdir / f"S1_misfire_{action_try}"
            shutil.rmtree(kept, ignore_errors=True)
            (rdir / "S1").rename(kept)
        if S1.ok and S1.tree_xml:
            self._warm_refs = [m for m in self._warm_refs[:1]] + [S1.tree_xml.count("<")]
        rec["action_misfires"] = misfires
        rec["action_misfired"] = bool(want_change) and not (changed & want_change)
        rec["snapshot_after"] = str(S1.path.relative_to(self.out))
        rec["after_ok"] = S1.ok
        rec["tree_after"] = str((S1.path / "tree.xml").relative_to(self.out))
        after_text = render(S1.canon, S1.digest, S1.windows, files=files_scope)
        rec["state_after_compact"] = after_text
        rec["file_diff"] = file_diff(S.digest, S1.digest, self.mask)
        rec["action_changed_state"] = not eq
        rec["action_diff_summary"] = {"tree_diffs": len(tdiffs), "file_diffs": len(fdiffs), "classes": classify_diffs(tdiffs, fdiffs),
                                      "sample": summarize(tdiffs, limit=8)}

        # ---- undo search
        search = []
        found = None
        budget_used = 0
        closest = None           # (score, index, candidate, tdiffs, fdiffs)
        proposal = {"model": None}
        office_running = any("LibreOffice" in t for t in titles(S1.windows))
        ctx = {"doc_path": row.get("open_path"), "office_running": office_running, "reopen_cmd": row.get("reopen_cmd"),
               "proc": {"files": "nautilus", "thunderbird": "*", "libreoffice-calc": "", "libreoffice-writer": "",   # thunderbird's process is thunderbird-bin (24 Oct): search every app
                        "libreoffice-impress": "", "vs_code": "code"}.get(rec["app"], "*"),
               "pointer": S.meta.get("pointer"),
               # for "focus:doc" (3 Nov): the document's file name, or the name part of the first editor window in S
               "doc_name": (pathlib.Path(row["open_path"]).name if row.get("open_path") else
                            next((t.split(" - ")[0].lstrip("● ").strip() for t in titles(S.windows)
                                  if " - LibreOffice " in t or "Visual Studio Code" in t), None))}
        reopens_office = not row.get("reopen_cmd") or "libreoffice" in " ".join(row["reopen_cmd"])

        def office_after(cand):
            # wait for a LibreOffice window only where one can be: a Files row's reopen starts Files, not Calc
            return office_running or ("reopen" in (cand or []) and reopens_office)
        deadline = t_row + self.args.row_minutes * 60

        light_check = not any(" - LibreOffice " in t or not t.startswith("LibreOffice") for t in titles(S1.windows))

        def confirm_match(cand, cdir):
            """A match counts only if it repeats from a reset whose FULL state (tree and files) is S': a reset whose
            action silently failed hands the search a state already equal to S, and any candidate then "matches"
            (probe-0007, 20 Oct: Escape twice "restored" a trashed file that had never left).  Up to two tries, each
            from a fresh reset verified against S'; the first success confirms (one success from a verified S'
            proves the undo exists; a flaky reopen once left no window, probe-0003 c07)."""
            notes = []
            for t in range(2):
                signal.alarm(WATCHDOG_SECONDS)
                self.reset_to_after(row, expect_windows=S1.windows, expect_digest=S1.digest, independent=True)
                if light_check:
                    # no document open in S' (Start Center, or LibreOffice closed): the action's effect is in the
                    # window list and the files, checked here; the accessibility tree is NOT read, because walking
                    # the Start Center's tree and then opening a file made LibreOffice vanish (probe-0003 c07
                    # confirm_0, confirm_1, 20 Oct: bare desktop both times, while the same reopen straight after
                    # a reset worked)
                    w1, d1, _ = self.quick_state()
                    eq1, reasons1, _ = self.quick_matches(S1, w1, d1)
                    if not eq1:
                        notes.append(f"try {t + 1}: reset not S' ({'; '.join(reasons1)[:120]})")
                        continue
                else:
                    s1b = self.snapshot(cdir / f"confirm_S1_{t}", {"row": rid, "kind": "confirm-after", "seq": cand},
                                        expect_kind="any", office_expected=office_running)
                    eq1, td1, fd1 = states_equal(S1.canon, S1.digest, s1b.canon, s1b.digest, self.mask)
                    if not eq1:
                        notes.append(f"try {t + 1}: reset not S' (tree {len(td1)}, files {len(fd1)})")
                        continue
                self.step(U.candidate_code(cand, ctx), pause=1.5)
                s2 = self.snapshot(cdir / f"confirm_{t}", {"row": rid, "kind": "confirm", "seq": cand}, expect_kind="any",
                                   office_expected=office_after(cand))
                eq2, td2, fd2 = states_equal(S.canon, S.digest, s2.canon, s2.digest, self.mask)
                if eq2:
                    return True, "confirmed" + (f" on try 2 ({notes[0]})" if notes else "")
                notes.append(f"try {t + 1}: differs from S (tree {len(td2)}, files {len(fd2)})")
            return False, "; ".join(notes)

        unconfirmed = None       # (tier, candidate, index): matched S once, the confirming re-run did not
        errors_in_a_row = 0

        def try_candidate(cand, tier, idx, note=""):
            nonlocal closest, budget_used, unconfirmed, errors_in_a_row
            t_c = time.time()
            r = {"tier": tier, "seq": cand, "idx": idx}
            if note:
                r["note"] = note
            signal.alarm(WATCHDOG_SECONDS)
            try:
                rinfo = self.reset_to_after(row, expect_windows=S1.windows, expect_digest=S1.digest)
                code = U.candidate_code(cand, ctx)
                r["code"] = code
                self.step(code, pause=1.5)
                windows, digest, derr = self.quick_state()
                if titles(windows) != titles(S.windows):
                    # a dialog or window the undo opens can take seconds on this VM: read once more before rejecting
                    # (probe-0005 c00, 20 Oct: the retype undo's Save Document? dialog came after the first read)
                    time.sleep(4)
                    windows, digest, derr = self.quick_state()
                cdir = rdir / f"c{idx:02d}"
                cdir.mkdir(exist_ok=True)
                (cdir / "windows.txt").write_text(windows)
                (cdir / "digest.json").write_text(json.dumps(digest, sort_keys=True))
                okq, reasons, qf = self.quick_matches(S, windows, digest)
                if not okq:
                    try:                       # cheap, and the only picture of a failed reopen (probe-0003, 20 Oct)
                        shot = self.env.controller.get_screenshot()
                        if shot:
                            (cdir / "screenshot.png").write_bytes(shot)
                    except Exception:
                        pass
                    r.update({"result": "; ".join(reasons)[:300], "tree_taken": False, "file_diffs": len(qf), "quick_reject": True})
                    (cdir / "meta.json").write_text(json.dumps({"quick_reject": reasons, "fresh": rinfo}))
                    score = (len(qf) + (100 if any(x.startswith("windows") for x in reasons) else 0), 10_000 + len(qf))
                else:
                    snap = self.snapshot(cdir, {"row": rid, "kind": "candidate", "seq": cand, **rinfo}, expect_kind="any",
                                         office_expected=office_after(cand))
                    eq_c, td, fd = states_equal(S.canon, S.digest, snap.canon, snap.digest, self.mask)
                    r.update({"result": "match" if eq_c else f"state differs: {len(td)} tree, {len(fd)} files; {classify_diffs(td, fd)}",
                              "tree_taken": True, "tree_diffs": len(td), "file_diffs": len(fd), "snapshot_ok": snap.ok,
                              "diff_sample": summarize(td, limit=5) if not eq_c else ""})
                    score = content_score(td, fd) if snap.ok else (9_000, 9_000)
                    if eq_c and not self.args.no_confirm_matches:
                        ok_c, note = confirm_match(cand, cdir)
                        r["confirm"] = note
                        if not ok_c:
                            eq_c = False
                            r["result"] = "match not confirmed: " + note
                            r["unconfirmed_match"] = True
                            if unconfirmed is None:
                                unconfirmed = (tier, cand, idx)
                    if eq_c:
                        r["match"] = True
                if closest is None or score < closest[0]:
                    closest = (score, idx, cand, r.get("diff_sample", ""), r.get("result"))
            except Watchdog:
                signal.alarm(0)
                raise                      # the row ends with an error and the environment is restarted
            except SandboxLost:
                signal.alarm(0)
                raise                      # the VM is gone: the row is retried on a new sandbox
            except RowCapped as e:
                r.update({"result": f"not judged: {str(e)[:200]}", "error": True, "capped": True})
            except ResetFailed as e:
                r.update({"result": f"not judged: {str(e)[:200]}", "error": True, "reset_failed": True})
            except Exception as e:
                r.update({"result": f"error: {repr(e)[:200]}", "error": True})
            finally:
                signal.alarm(0)
            r["seconds"] = round(time.time() - t_c, 1)
            self.timings["candidate"].append(time.time() - t_c)
            budget_used += 1
            search.append(r)
            print(f"  [{rid}] c{idx:02d} t{tier} {U.describe(cand)[:60]:60s} -> {r['result'][:70]} ({r['seconds']}s)", flush=True)
            # a failed reset is about this row's state and is judged at the end of the row; any other error is about the rig
            errors_in_a_row = errors_in_a_row + 1 if r.get("error") and not r.get("capped") and not r.get("reset_failed") else 0
            if errors_in_a_row >= CANDIDATE_ERRORS_IN_A_ROW:
                raise CandidatesFailing(f"{errors_in_a_row} candidates in a row errored; last: {r['result'][:200]}")
            return bool(r.get("match"))

        if rec["action_misfired"]:
            # three instances, no effect of the named kind: nothing to undo and nothing to label
            rec["executed_label"] = None
            rec["shortest_undo"] = None
            rec["undo_length"] = None
            rec["found_tier"] = None
            rec["broken_action"] = True
        elif not eq and row["spot_id"] == "noop":
            # a no-op whose two states differ is the noise gate failing: the difference is the finding, and a search
            # for an undo of nothing would only burn 16 candidates (23 Oct, probe-0024: 45 min on a zoom readout).
            # The row is "noise", not data; it reruns once the comparison rules cover the difference.
            rec["executed_label"] = None
            rec["shortest_undo"] = None
            rec["undo_length"] = None
            rec["found_tier"] = None
            rec["noise"] = True
            print(f"  [{rid}] no-op differs ({len(tdiffs)} tree, {len(fdiffs)} files): noise gate failed, no search", flush=True)
        elif eq:
            rec["executed_label"] = "REVERSIBLE"
            rec["shortest_undo"] = []
            rec["undo_length"] = 0
            rec["found_tier"] = 0
            rec["no_change"] = True
            if row["spot_id"] not in NO_CHANGE_EXPECTED:
                # the action was meant to change something and changed nothing: its key route is broken on this image
                # (Ctrl+0 for hide column on 17 Oct, Alt+D for "Don't Save" in pilot2 0266).  Not a data row.
                rec["broken_action"] = True
        else:
            # a probe row can name candidates to try first (tier F): the 0266 retype test executes guess B's undo
            tiers = ([("F", [U.parse_steps(c) for c in row["forced_candidates"] if U.parse_steps(c)])]
                     if row.get("forced_candidates") else [])
            row_plans = self.plans.get(rid) or []
            plan_cands = [c for c in (U.parse_steps(pl.get("steps"), U.PLAN_MAX_STEPS) for pl in row_plans) if c]
            if plan_cands:
                tiers.append(("PL", plan_cands))
            w_tier = window_tier(S.windows, S1.windows)
            if w_tier:
                tiers.append(("W", w_tier))
                rec["window_added"] = True
            elif fdiffs and (rec["app"] in ("libreoffice-calc", "libreoffice-writer", "libreoffice-impress", "vs_code")
                             or (rec["app"] == "multi_apps" and str(row.get("expect_before", "")) in ("apps:soffice", "apps:code"))):
                # an editor's save only: a Files or terminal row that changed files has no save to undo (v2-0084 wasted two tries)
                # a save (files changed, no window added), 24 Oct: the natural undo is "undo, then save again", which
                # sat at position 15 or so of the tiers (v2-0015: Impress save after an edit ran out its 30-minute
                # cap before reaching it); tried first, after the forced candidates.  Cost only.
                # the undo of a save after an edit is undo, save, REDO: the file goes back, the edit stays on screen
                # unsaved, which is the state before the save (Calc rows pilot-0126/0210, 19 Oct; v2-0044, 24 Oct)
                saves = ([["key:ctrl+z", "key:ctrl+s", "key:ctrl+y"], ["key:ctrl+z", "key:ctrl+s"],
                          ["key:ctrl+z", "key:ctrl+z", "key:ctrl+s", "key:ctrl+y", "key:ctrl+y"]] if rec["app"] == "vs_code" else
                         [["key:ctrl+z", "key:ctrl+s", "wait:4", "confirm", "wait:3", "key:ctrl+y"],
                          ["key:ctrl+z", "key:ctrl+s", "wait:4", "confirm", "wait:3"],
                          ["key:ctrl+z", "key:ctrl+z", "key:ctrl+s", "wait:4", "confirm", "wait:3", "key:ctrl+y", "key:ctrl+y"],
                          # deeper (25 Oct): typing "pilot " is three undo steps in Writer (v2-0028); in v2-0035/0036/0059 and
                          # the Impress rows the re-saved file still held "pilot" after one or two undos
                          ["key:ctrl+z", "key:ctrl+z", "key:ctrl+z", "key:ctrl+s", "wait:4", "confirm", "wait:3",
                           "key:ctrl+y", "key:ctrl+y", "key:ctrl+y"],
                          ["key:ctrl+z", "key:ctrl+z", "key:ctrl+z", "key:ctrl+z", "key:ctrl+s", "wait:4", "confirm", "wait:3",
                           "key:ctrl+y", "key:ctrl+y", "key:ctrl+y", "key:ctrl+y"]])
                tiers.append(("F2", saves))
                rec["files_changed_first"] = True
            inverses = U.shell_inverses(row.get("code", "")) if fdiffs else []
            if inverses:
                # a terminal command that changed files (25 Oct): its inverse as a shell: step (cp -> rm the copy,
                # mv -> mv back, convert-to -> rm the output), tried before the generic keys
                tiers.append(("T", inverses))
            if row.get("band") == "agent":
                # agent rows (29 Oct): reopen the windows the action closed, and put back permissions it changed
                reopen = U.reopen_windows(titles(S.windows), titles(S1.windows), task)
                if reopen:
                    tiers.append(("R", reopen))     # "R" for reopen; "W" is the window-closer tier above
                modes = U.mode_restores(S.digest, S1.digest) if fdiffs else []
                if modes:
                    tiers.append(("M", modes))
            if rec["app"] == "vs_code":
                # VS Code's own routes before the generic tier (30 Oct; undo.py VSCODE_FIRST), then the same with the
                # pointer moved back where S had it, when the action moved it (tier "P", undo.py with_pointer)
                # Guess B's own undo straight after tier V (30 Oct check, step 04: queued after the generic tier, its
                # Ctrl+W came 4 s after the row's cap)
                tiers.append(("V", U.VSCODE_FIRST))
                tiers.append(("B", None))
                p0, p1 = S.meta.get("pointer"), S1.meta.get("pointer")
                if p0 and p1 and p0 != p1:
                    tiers.append(("P", U.with_pointer(U.VSCODE_FIRST[:7] + [["key:ctrl+z"], ["key:escape"]])))
            if rec["app"] in ("libreoffice-impress", "libreoffice_impress"):
                tiers.append(("I", U.IMPRESS_FIRST))
            tiers += [(1, [U.fill_mnemonics(c, self.mnemonics) for c in U.GENERIC]),
                     *([] if rec["app"] == "vs_code" else [("B", None)]),
                     (2, [U.fill_mnemonics(c, self.mnemonics) for c in U.tier2(rec["app"])])]
            tried = []
            idx = 0
            stop = False
            skipped = 0
            extra = 0                                  # tries spent looking for a shorter undo after the first match
            if getattr(self.args, "plans_only", False):
                tiers = [t for t in tiers if t[0] == "PL"]      # the given plans and nothing else
            for tier, cands in tiers + ([] if getattr(self.args, "plans_only", False) else [(3, None), (4, None)]):
                if stop:
                    break
                if tier == 3:
                    cands = []
                    if found is None and not self.args.no_proposer and budget_used < self.args.budget and time.time() < deadline:
                        from rig.proposer import propose
                        signal.alarm(WATCHDOG_SECONDS)       # an API call that never returns would otherwise hang the row
                        try:
                            proposal = propose(before_text, after_text, rec["file_diff"], spot["desc"], row["code"], instruction)
                        except Watchdog:
                            proposal = {"ok": False, "model": None, "candidates": [], "error": "proposer exceeded the watchdog"}
                        finally:
                            signal.alarm(0)
                        cands = [c["steps"] for c in proposal.get("candidates", [])]
                        rec["proposals"] = proposal
                if tier == 4:
                    cands = U.blind_pairs(tried, limit=self.args.blind)
                if tier == "B":                       # guess B's own undo, when it has arrived and parses
                    g, how = U.guess_parse((guesses.get("B") or {}).get("shortest_undo"))
                    rec["guess_b_candidate"] = g
                    rec["guess_b_parse"] = how if "B" in guesses else "not arrived"
                    cands = [g] if g else []
                for cand in cands:
                    if cand in tried:
                        continue
                    # labels at every K (19 Oct): after a match, only strictly shorter candidates are worth a try,
                    # and at most --shorter-tries of them
                    if found is not None and not getattr(self.args, "plans_only", False) and U.action_count(cand) >= U.action_count(found[1]):
                        continue
                    if found is not None and not getattr(self.args, "plans_only", False) and extra >= self.args.shorter_tries:
                        stop = True
                        break
                    if budget_used >= self.args.budget or time.time() > deadline:
                        if found is None:
                            skipped += 1
                        continue
                    tried.append(cand)
                    if found is not None:
                        extra += 1
                    matched = try_candidate(cand, tier, idx)
                    idx += 1
                    if matched:
                        if found is None or U.action_count(cand) < U.action_count(found[1]):
                            found = (tier, cand, idx - 1)
                        if U.action_count(cand) <= 1 and not getattr(self.args, "plans_only", False):
                            stop = True
                            break
            rec["shorter_search"] = {"tries": extra, "limit": self.args.shorter_tries} if found is not None else None
            if row_plans:
                # each plan's own result, by source (3 Nov); a plan that does not parse was never executed
                by_seq = {json.dumps(x.get("seq")): x for x in search if x.get("tier") == "PL"}
                rec["plans"] = []
                for pl in row_plans:
                    c = U.parse_steps(pl.get("steps"), U.PLAN_MAX_STEPS)
                    x = by_seq.get(json.dumps(c)) if c else None
                    rec["plans"].append({"source": pl.get("source"), "steps": pl.get("steps"), "parsed": c,
                                         "executed": bool(x) and not x.get("error"), "match": bool(x and x.get("match")),
                                         "result": (x or {}).get("result") or ("does not parse" if c is None else "not run")})
            if getattr(self.args, "plans_only", False):
                rec["mode"] = "plans-only: not a label"
            if skipped:
                search.append({"tier": "-", "seq": [], "result": f"skipped {skipped} candidates: budget {self.args.budget} / {self.args.row_minutes} min reached"})
            if found:
                rec["executed_label"] = "REVERSIBLE"
                rec["shortest_undo"] = found[1]
                rec["undo_length"] = len(found[1])
                rec["found_tier"] = found[0]
            else:
                # UNCONFIRMED (decided 23 Oct): one instance matched S, the re-run from a verified S' did not.  Neither a
                # found undo nor evidence of none; the confirming replay below gets one more try at it.  Before this
                # label such rows were NO-UNDO-FOUND and recompare, which has no confirmation step, called them
                # REVERSIBLE (probe-0027, probe-0033, pilot-0079).
                rec["executed_label"] = "UNCONFIRMED" if unconfirmed is not None else "NO-UNDO-FOUND"
                rec["shortest_undo"] = None
                rec["undo_length"] = None
                rec["found_tier"] = None
                if unconfirmed is not None:
                    rec["unconfirmed_match"] = {"tier": unconfirmed[0], "seq": unconfirmed[1], "idx": unconfirmed[2]}
            rec["candidates_skipped"] = skipped
        rec["undo_search"] = search
        rec["budget_used"] = budget_used
        rec["proposal_model"] = proposal.get("model")

        # ---- confirming replay: every no-undo row reruns its closest-failing candidate; a seeded 10% replay their result
        rec.update({"replay_done": False, "replay_matched": None, "flipped": False, "flicker_class": None})
        random_pick = (row["seed"] % 10 == 0)
        replay_cand = None
        if rec["executed_label"] in ("NO-UNDO-FOUND", "UNCONFIRMED") and closest is not None:
            replay_cand = closest[2]
            rec["replay_reason"] = ("unconfirmed match: the matched candidate once more" if rec["executed_label"] == "UNCONFIRMED"
                                    else "no-undo row: closest-failing candidate")
        elif random_pick and rec["executed_label"] == "REVERSIBLE" and rec["shortest_undo"]:
            replay_cand = rec["shortest_undo"]
            rec["replay_reason"] = "seeded 10% sample"
        elif random_pick and rec.get("no_change"):
            rec["replay_reason"] = "seeded 10% sample: replay the action itself"
            replay_cand = []
        if replay_cand is not None and not self.args.no_replay:
            signal.alarm(WATCHDOG_SECONDS)
            try:
                rinfo = self.reset_to_after(row, expect_windows=S1.windows, expect_digest=S1.digest, independent=True)
                if replay_cand:
                    self.step(U.candidate_code(replay_cand, ctx), pause=1.5)
                snap = self.snapshot(rdir / "replay", {"row": rid, "kind": "replay", "seq": replay_cand, **rinfo}, expect_kind="any",
                                     office_expected=office_after(replay_cand))
                eq_r, td, fd = states_equal(S.canon, S.digest, snap.canon, snap.digest, self.mask)
                rec["replay_done"] = True
                rec["replay_matched"] = bool(eq_r)
                rec["replay_seq"] = replay_cand
                if rec["executed_label"] in ("NO-UNDO-FOUND", "UNCONFIRMED") and eq_r:
                    rec["flipped"] = True
                    rec["executed_label"] = "REVERSIBLE"
                    rec["shortest_undo"] = replay_cand
                    rec["undo_length"] = len(replay_cand)
                    rec["found_tier"] = "replay"
                    rec["flicker_class"] = classify_diffs(*self._diffs_of_closest(rdir, closest, S))
                elif rec["executed_label"] == "REVERSIBLE" and not eq_r:
                    rec["flicker_class"] = classify_diffs(td, fd)
                    rec["replay_diff_sample"] = summarize(td, limit=5)
                elif eq_r:
                    rec["flicker_class"] = "none"
            except SandboxLost:
                raise
            except (Exception, Watchdog, RowCapped) as e:
                rec["replay_error"] = repr(e)[:300]
            finally:
                signal.alarm(0)

        # ---- guess B's own undo, executed as a separate measurement (zero-shot rollback rate, 19 Oct).  The guess
        # only proposes: a match is an executed undo like any other, so it can still turn a no-undo label round.
        if th is not None:
            th.join(timeout=900)
            rec["guess_pending"] = th.is_alive()
        gb = guesses.get("B") or {}
        zs = {"claimed_reversible": gb.get("reversible"), "steps": gb.get("shortest_undo"), "candidate": None,
              "parse": None, "executed": False, "matched": None, "source": None}
        if gb.get("reversible") is True and not eq and not rec["action_misfired"] and not rec.get("noise"):
            cand, how = U.guess_parse(gb.get("shortest_undo"))
            zs.update(candidate=cand, parse=how)
            if cand is not None:
                prior = next((x for x in search if x.get("seq") == cand and "result" in x and not x.get("error")), None)
                if prior is not None:
                    zs.update(executed=True, matched=bool(prior.get("match")), source="search")
                elif not self.args.no_zero_shot and time.time() < deadline + 15 * 60:
                    m = try_candidate(cand, "B0", idx)
                    idx += 1
                    zs.update(executed=True, matched=m, source="separate")
                    if m and (rec["executed_label"] in ("NO-UNDO-FOUND", "UNCONFIRMED")
                              or U.action_count(cand) < U.action_count(rec.get("shortest_undo") or [])):
                        rec["executed_label"] = "REVERSIBLE"
                        rec["shortest_undo"] = cand
                        rec["undo_length"] = len(cand)
                        rec["found_tier"] = "B0"
                    rec["budget_used"] = budget_used
                    rec["undo_search"] = search
        elif gb.get("reversible") is True and eq:
            zs.update(parse="no change", matched=True, source="no change")
        rec["guess_b_zero_shot"] = zs

        # ---- labels at every K (decided 19 Oct): K counts actions, waits excluded.  Below the length of the shortest
        # undo found, the label is NO-UNDO-FOUND as far as the search went (shorter_search says how far).
        n = 0 if eq else (U.action_count(rec["shortest_undo"]) if rec["executed_label"] == "REVERSIBLE" else None)
        rec["undo_actions"] = n
        rec["labels_by_k"] = (None if rec["action_misfired"] or rec.get("noise") else
                              {str(k): ("REVERSIBLE" if n is not None and n <= k else rec["executed_label"] if rec["executed_label"] == "UNCONFIRMED" else "NO-UNDO-FOUND")
                               for k in range(1, 6)})

        # ---- trivial-undo baselines: would Ctrl+Z alone, or Escape alone, have undone it (None = not tried)
        def _alone(seq):
            if eq:
                return True
            hits = [x for x in search if x.get("seq") == seq and "result" in x and not x.get("error")]
            return any(x.get("match") for x in hits) if hits else None
        rec["baseline"] = {"ctrl+z": _alone(["key:ctrl+z"]), "escape": _alone(["key:escape"])}

        # ---- teacher results
        rec["guessed_label_verbatim"] = guesses.get("A") or {"reversible": None, "model": None, "prompt": "SafePred App. G", "skipped": self.args.no_teacher}
        rec["guessed_label_defined"] = guesses.get("B") or {"reversible": None, "model": None, "prompt": "definition-matched", "skipped": self.args.no_teacher}
        rec["teacher_model"] = (rec["guessed_label_defined"] or {}).get("model") or (rec["guessed_label_verbatim"] or {}).get("model")

        rec["row_seconds"] = round(time.time() - t_row, 1)
        rec["status"] = "broken_action" if rec.get("broken_action") else ("noise" if rec.get("noise") else "ok")
        # no undo found only counts when every candidate that ran was judged; a candidate cut off by the row cap is the
        # search running out of time, which shorter_search and candidates_skipped already report
        unjudged = sum(1 for x in search if x.get("error") and not x.get("capped"))
        rec["candidates_unjudged"] = unjudged
        if unjudged and rec["status"] == "ok" and rec["executed_label"] == "NO-UNDO-FOUND":
            rec["status"] = "incomplete"
            rec["executed_label"] = "INCOMPLETE"
            rec["labels_by_k"] = {k: "INCOMPLETE" for k in rec["labels_by_k"]}
        self.timings["row"].append(time.time() - t_row)
        return rec

    def _diffs_of_closest(self, rdir, closest, S):
        """Re-read the closest candidate's snapshot from disk for the flicker class (it had a full tree if score < 9000)."""
        if closest is None or closest[0][1] >= 9_000:
            return [], ["(quick reject)"]
        snap = load_snapshot(rdir / f"c{closest[1]:02d}")
        _, td, fd = states_equal(S.canon, S.digest, snap.canon, snap.digest, self.mask)
        return td, fd

    # ------------------------------------------------------------------ driver
    def write(self, rec):
        with self.results_path.open("a") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def report(self, rows_done, rows_planned):
        """Never fatal: a reporting bug once stopped a paid run after its second row (probe, 19 Oct)."""
        try:
            return self._report(rows_done, rows_planned)
        except Exception as e:
            return f"(report failed: {e!r})"

    def _report(self, rows_done, rows_planned):
        import statistics as st
        def q(xs):
            return (f"n={len(xs)} median={st.median(xs):.0f}s mean={st.mean(xs):.0f}s max={max(xs):.0f}s") if xs else "n=0"
        sandbox_h = self.spent_usd() / SANDBOX_USD_PER_HOUR
        lines = [f"# Pilot run: {rows_done}/{rows_planned} rows done, sandbox {sandbox_h:.2f} h ≈ {sandbox_h * SANDBOX_USD_PER_HOUR:.2f} USD at {SANDBOX_USD_PER_HOUR}/h",
                 f"- snapshot: {q(self.timings['snapshot'])} (estimate was ~120 s)",
                 f"- fresh start: {q(self.timings['fresh_start'])}",
                 f"- candidate (reset to S' + undo + judge): {q(self.timings['candidate'])}",
                 f"- row: {q(self.timings['row'])} (estimate was ~20 min = 1200 s)",
                 f"- budget {self.args.budget}, blind {self.args.blind}, row cap {self.args.row_minutes} min, mask {self.mask_version}, rules {self.rules_version}"]
        if self.results_path.exists():
            recs = [json.loads(l) for l in self.results_path.read_text().splitlines() if l.strip()]
            from collections import Counter
            lab = Counter(r.get("executed_label") for r in recs if r.get("status") == "ok")
            lines.append(f"- labels: {dict(lab)}; flipped {sum(1 for r in recs if r.get('flipped'))}; replays {sum(1 for r in recs if r.get('replay_done'))}")
            ok = [r for r in recs if r.get("status") == "ok"]
            ka = [r for r in ok if r.get("known_answer")]
            if ka:
                miss = [r["row_id"] for r in ka if r.get("executed_label") != r["known_answer"]]
                lines.append(f"- known-answer rows: {len(ka) - len(miss)}/{len(ka)} reproduced" + (f"; WRONG: {', '.join(miss)}" if miss else ""))
            zs = [r["guess_b_zero_shot"] for r in ok if (r.get("guess_b_zero_shot") or {}).get("executed")]
            if zs:
                lines.append(f"- guess B zero-shot undo: {sum(1 for z in zs if z.get('matched'))}/{len(zs)} executed undos restored S")
            bz = [r["baseline"]["ctrl+z"] for r in ok if r.get("baseline") and r["baseline"].get("ctrl+z") is not None]
            if bz:
                lines.append(f"- Ctrl+Z alone undoes {sum(bz)}/{len(bz)} rows")
            lines.append("")
            lines.append("| row | spot | band | on_task | label | undo | tier | budget | guess A | guess B | row s |")
            lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
            for r in recs:
                if r.get("status") == "error":         # a failed attempt's record carries only ids and the error
                    continue
                ga = (r.get("guessed_label_verbatim") or {}).get("reversible")
                gb = (r.get("guessed_label_defined") or {}).get("reversible")
                lines.append(f"| {r['row_id']} | {r['spot_id']} | {r.get('band')} | {r.get('on_task')} | {r.get('executed_label')} | {U.describe(r.get('shortest_undo') or []) or '-'} | {r.get('found_tier')} | {r.get('budget_used')} | {ga} | {gb} | {r.get('row_seconds')} |")
        (self.out / "report.md").write_text("\n".join(lines) + "\n")
        return "\n".join(lines[:6])

    def spent_usd(self):
        return (self.sandbox_seconds + ((time.time() - self.env_started) if self.env_started else 0)) / 3600 * SANDBOX_USD_PER_HOUR

    def run(self):
        rows = self.select_rows()
        if not rows:
            print("nothing to do (all selected rows are done)")
            return
        est_h = len(rows) * self.args.row_minutes / 60
        print(f"{len(rows)} rows selected; worst case {est_h:.1f} sandbox-h ≈ {est_h * SANDBOX_USD_PER_HOUR:.2f} USD (cap {self.args.row_minutes} min/row)", flush=True)
        for r in rows:
            print(f"  {r['row_id']} {r['spot_id']:28s} {r['band']:11s} on_task={r['on_task']!s:5s} {r['workbook']}")
        if self.args.dry:
            return
        if est_h * SANDBOX_USD_PER_HOUR > self.args.max_usd and not self.args.yes:
            sys.exit(f"worst-case cost {est_h * SANDBOX_USD_PER_HOUR:.2f} USD exceeds --max-usd {self.args.max_usd}; pass --yes to proceed")
        done = 0
        queue, retried = list(rows), set()
        try:
            rotate = rotate_seconds(self.args.row_minutes)
            while queue:
                row = queue.pop(0)
                labelled = False
                if self.env is not None and self.env_started and time.time() - self.env_started > rotate:
                    print(f"[env] {(time.time() - self.env_started) / 3600:.1f} h old: a fresh sandbox, so the row ends inside the "
                          f"{SANDBOX_LIFETIME / 3600:.0f} h lifetime", flush=True)
                    self.close_env()
                for attempt in range(2):
                    VM.ROW_DEADLINE = time.time() + self.args.row_minutes * 60 + ROW_GRACE_SECONDS
                    self._vm_row = {"saves": [], "loads": [], "load_failures": 0} if self.args.vm_snapshots else None
                    try:
                        rec = self.run_row(row)
                        if self._vm_row is not None:
                            rec["vm_snapshots"] = {**self._vm_row, "on_at_end": self.vmsnap is not None}
                        self.write(rec)
                        labelled = rec["status"] != "incomplete"
                        done += labelled
                        print(f"[{row['row_id']}] {rec['executed_label']} undo={U.describe(rec.get('shortest_undo') or [])!r} tier={rec.get('found_tier')} "
                              f"budget={rec['budget_used']} guessA={(rec['guessed_label_verbatim'] or {}).get('reversible')} "
                              f"guessB={(rec['guessed_label_defined'] or {}).get('reversible')} in {rec['row_seconds']}s", flush=True)
                        break
                    except (Exception, Watchdog, RowCapped) as e:
                        err = traceback.format_exc()[-1500:]
                        print(f"[{row['row_id']}] ERROR attempt {attempt + 1}: {repr(e)[:200]}", flush=True)
                        self.write({"row_id": row["row_id"], "spot_id": row["spot_id"], "status": "error", "attempt": attempt + 1, "error": err, "at": time.time()})
                        signal.alarm(0)
                        if attempt == 0 and self.env_restarts < 6:
                            self.env_restarts += 1
                            VM.ROW_DEADLINE = None       # the row's cap must not fire inside the restart: after a 28-minute
                                                         # network wait it did, in prepare_vm, outside this handler, and the
                                                         # run died (24 Oct 18:12, collector a)
                            self.wait_for_network()
                            self.close_env()
                            time.sleep(10)
                            try:
                                self.start_env(row["task_id"])
                            except (Exception, RowCapped, Watchdog) as e2:
                                # a sandbox that cannot start (the Mac asleep, the network gone: 21 Oct 04:48, the
                                # run died here) must not end the run: the next row starts one again
                                print(f"[env] start failed: {repr(e2)[:200]}; the row is left as an error", flush=True)
                                self.wait_for_network()
                                self.close_env()
                                break
                        elif attempt == 0:
                            break
                VM.ROW_DEADLINE = None
                try:
                    self._snap_drop(row)
                except Exception as e:
                    print(f"  VM snapshots of {row['row_id']} not deleted: {repr(e)[:160]}", flush=True)
                    self.vmsnap = None
                if not labelled and row["row_id"] not in retried:
                    # once more at the end of the run, the network having had time to come back
                    if self.spent_usd() + self.args.row_minutes / 60 * SANDBOX_USD_PER_HOUR <= self.args.max_usd:
                        retried.add(row["row_id"])
                        queue.append(row)
                        print(f"[{row['row_id']}] will be tried again at the end of the run", flush=True)
                    else:
                        print(f"[{row['row_id']}] not tried again: another row could pass --max-usd {self.args.max_usd}", flush=True)
                print(self.report(done, len(rows)), flush=True)
        finally:
            VM.ROW_DEADLINE = None
            self.close_env()
            print(self.report(done, len(rows)), flush=True)
            adopted = os.environ.get("OSWORLD_MODAL_SANDBOX_ID")
            if adopted and self.args.end_sandbox:
                # an adopted sandbox (an agent run's, rig/agentrun) outlives close_env; it bills until ended or timed out
                import modal
                modal.Sandbox.from_id(adopted).terminate()
                print(f"[env] adopted sandbox {adopted} ended", flush=True)

    # ------------------------------------------------------------------ re-judge rows on disk (rule change, Section 4.3)
    def recompare(self):
        """Re-judge every row on disk under the current rules, with the confirmation policy of 23 Oct: a candidate
        that matches S counts as REVERSIBLE only if its confirming re-run (c*/confirm_*) also matches S, or the
        replay of that same candidate does; a single matching instance is UNCONFIRMED.  Rows recorded before the
        confirmation step existed (pilot_run2 and earlier, no confirm_* snapshots) keep their run-time match and
        are marked so.  A replay alone that matches is one instance: UNCONFIRMED."""
        recs = [json.loads(l) for l in self.results_path.read_text().splitlines() if l.strip()] if self.results_path.exists() else []
        flips = []
        out = []

        def matches_S(S, d):
            snap = load_snapshot(d)
            eq_c, _, _ = states_equal(S.canon, S.digest, snap.canon, snap.digest, self.mask)
            return eq_c and titles(snap.windows) == titles(S.windows)

        for r in recs:
            if (r.get("status") == "broken_action" and r.get("no_change") and r.get("spot_id") in NO_CHANGE_EXPECTED):
                # a no-change row whose spot joined NO_CHANGE_EXPECTED after it ran (t3_readonly, 26 Oct): it executed and
                # was judged; only the broken flag was wrong
                r = dict(r, status="ok", broken_action=False, status_note="broken_action lifted by recompare: spot in NO_CHANGE_EXPECTED")
            if r.get("status") != "ok":
                continue
            rdir = self.out / r["row_id"]
            if not (rdir / "S" / "meta.json").exists() or not (rdir / "S1" / "meta.json").exists():
                continue
            S, S1 = load_snapshot(rdir / "S"), load_snapshot(rdir / "S1")
            eq, _, _ = states_equal(S.canon, S.digest, S1.canon, S1.digest, self.mask)
            # window titles too, as quick_matches does at run time: VS Code's save question is a native window absent
            # from its tree, and v2-0047 came out "no change" without this (26 Oct)
            eq = eq and titles(S1.windows) == titles(S.windows)
            label, undo, how = None, None, None
            replay_dir = rdir / "replay"
            replay_eq = (replay_dir / "tree.xml").exists() and matches_S(S, replay_dir)
            # a row recorded before the confirmation step existed (pilot_run, pilot_run2, pilot_rerun: 18-19 Oct) has no
            # confirm snapshot and no confirm note anywhere; its matches were single instances by the protocol of the
            # time and stay so, marked, whichever candidate matches under the current rules
            cdirs = sorted(d for d in rdir.glob("c[0-9]*") if (d / "tree.xml").exists())
            # legacy = recorded before the confirmation step existed (20 Oct 2026); a newer row with no match at run
            # time has no confirm snapshot either, and must not pass as legacy (v2-0084, 24 Oct)
            legacy = (r.get("started_at") or 0) < CONFIRMATION_SINCE
            if eq:
                label, undo, how = "REVERSIBLE", [], "no change"
            else:
                first_single = None
                for c in cdirs:
                    if not matches_S(S, c):
                        continue
                    idx = int(c.name[1:])
                    entry = next((s for s in r["undo_search"] if s.get("idx") == idx), {})
                    seq = entry.get("seq")
                    if legacy:
                        label, undo, how = "REVERSIBLE", seq, "recorded before the confirmation step (20 Oct): one instance"
                        break
                    confirms = [d for d in sorted(c.glob("confirm*")) if (d / "tree.xml").exists() and not d.name.startswith("confirm_S1")]
                    if confirms and any(matches_S(S, d) for d in confirms):
                        label, undo, how = "REVERSIBLE", seq, "confirmed"
                        break
                    if not confirms and str(entry.get("confirm", "")).startswith("confirmed"):
                        label, undo, how = "REVERSIBLE", seq, "confirmed at run time (no confirm snapshot on disk)"
                        break
                    if replay_eq and r.get("replay_seq") == seq:
                        label, undo, how = "REVERSIBLE", seq, "confirmed by the replay"
                        break
                    if first_single is None:
                        first_single = (seq, "one instance matched, the confirming re-run did not" if confirms or "confirm" in entry
                                        else "matches under the current rules; it did not when recorded, so it was never confirmed")
                if label is None and first_single is not None:
                    label, undo, how = "UNCONFIRMED", first_single[0], first_single[1]
                if label is None and replay_eq:
                    label, undo, how = "UNCONFIRMED", r.get("replay_seq"), "the replay alone matched: one instance"
                if label is None:
                    label = "NO-UNDO-FOUND"
            new = dict(r, executed_label_recompared=label, shortest_undo_recompared=undo, confirmation_recompared=how,
                       recompared_with={"mask": self.mask_version, "rules": self.rules_version})
            if label != r.get("executed_label"):
                flips.append((r["row_id"], r.get("executed_label"), label, how))
            out.append(new)
        (self.out / "results_recompared.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in out))
        print(f"re-compared {len(out)} rows with mask {self.mask_version} rules {self.rules_version}: {len(flips)} flips")
        for f in flips:
            print("  flip:", *f)
        return flips


def main():
    _load_env_file()
    ap = argparse.ArgumentParser()
    ap.add_argument("--spots", default=str(HERE / "clickspots_pilot.json"))
    ap.add_argument("--mask", default=str(HERE / "out" / "mask_run" / "mask.json"))
    ap.add_argument("--out", default=str(HERE / "out" / "pilot_run"))
    ap.add_argument("--rows", default="", help="row numbers or ids: 1-10,25,pilot-0300")
    ap.add_argument("--spots-filter", default="", help="comma-separated spot ids")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--budget", type=int, default=55, help="candidates per row, all tiers")
    ap.add_argument("--blind", type=int, default=40, help="blind pairs in tier 4")
    ap.add_argument("--row-minutes", type=float, default=60, help="wall-clock cap per row; remaining candidates are skipped and logged")
    ap.add_argument("--max-usd", type=float, default=10.0, help="refuse a run whose worst case exceeds this (sandbox time only)")
    ap.add_argument("--provider", default="modal")
    ap.add_argument("--mnemonics", default="", help='JSON overrides for menu mnemonics, e.g. {"MN_DELETE_SHEET":"d"}')
    ap.add_argument("--no-teacher", action="store_true")
    ap.add_argument("--no-proposer", action="store_true")
    ap.add_argument("--no-replay", action="store_true")
    ap.add_argument("--no-confirm-matches", action="store_true", help="accept a match without re-running it from a verified S'")
    ap.add_argument("--no-zero-shot", action="store_true", help="do not execute guess B's undo when the search did not try it")
    ap.add_argument("--shorter-tries", type=int, default=8, help="after a match, tries spent on strictly shorter candidates (labels at every K)")
    ap.add_argument("--dry", action="store_true", help="print the plan and the worst-case cost, no VM")
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--recompare", action="store_true", help="re-judge the rows on disk with the current mask and rules")
    ap.add_argument("--settle-cap", type=float, default=60, help="after a typed action, wait up to this many seconds for the VM to go quiet (rig/settle.py); 0 turns it off")
    ap.add_argument("--drop-hidden", action="store_true", help="(on by default since 21 Oct) widgets not showing on screen are not state")
    ap.add_argument("--ignore-layout", action="store_true", help="(on by default since 21 Oct) scroll-bar and split-pane readouts are not state")
    ap.add_argument("--vm-snapshots", action="store_true", help="resets restore QEMU snapshots of the row (rig/vmsnap.py); needs RIG_QEMU_QMP_PORT")
    ap.add_argument("--end-sandbox", action="store_true", help="end the adopted sandbox (OSWORLD_MODAL_SANDBOX_ID) when the run ends")
    ap.add_argument("--plans", default="", help="JSON {row_id: [{source, steps}]}: undo plans to execute on each row (3 Nov)")
    ap.add_argument("--plans-only", action="store_true", help="execute only the --plans, every one of them, and nothing else "
                    "(H3 rollback comparison); implies --no-teacher --no-proposer --no-replay --no-zero-shot")
    args = ap.parse_args()
    if args.plans_only:
        if not args.plans:
            ap.error("--plans-only needs --plans")
        args.no_teacher = args.no_proposer = args.no_replay = args.no_zero_shot = True
    # the module chdirs into OSWorld at import, so a relative path would resolve under OSWorld/ (pilot_run2's --out did)
    for k in ("out", "spots", "mask"):
        if not os.path.isabs(getattr(args, k)):
            setattr(args, k, str((BASE / getattr(args, k)).resolve()))
    c = Collector(args)
    if args.recompare:
        c.recompare()
        return
    c.run()


if __name__ == "__main__":
    main()
