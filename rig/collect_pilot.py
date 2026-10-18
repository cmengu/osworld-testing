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
import sys
import threading
import time
import traceback

HERE = pathlib.Path(__file__).resolve().parent
BASE = HERE.parent
OSWORLD = BASE / "OSWorld"
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(OSWORLD))
os.environ.setdefault("MODAL_SANDBOX_TIMEOUT", "36000")   # 10 h: a serial run outlives the provider's 2 h default
os.chdir(OSWORLD)

from rig.compact import file_diff, render                      # noqa: E402
from rig.freshstart import fresh_start, prime_cache, switch_task  # noqa: E402
from rig.mask import apply_file_mask, file_sig, states_equal    # noqa: E402
from rig.snapshot import load_snapshot, take_snapshot           # noqa: E402
from rig.treediff import summarize                              # noqa: E402
from rig import undo as U                                       # noqa: E402

SANDBOX_USD_PER_HOUR = 0.76
WATCHDOG_SECONDS = 900        # no single candidate, snapshot or reset may take longer; a dead tunnel otherwise hangs forever


# spots whose action may legitimately leave no trace (saving an unchanged file); every other "no change" is a
# broken key route
NO_CHANGE_EXPECTED = frozenset({"save_clean", "select_all"})   # select_all: the selection is not state (19 Oct)


class Watchdog(Exception):
    pass


def _alarm(signum, frame):
    raise Watchdog(f"step exceeded {WATCHDOG_SECONDS}s (tunnel or VM unresponsive)")


signal.signal(signal.SIGALRM, _alarm)
PRELUDE = "pyautogui.hotkey('ctrl', 'home')"
TASK_DIR = OSWORLD / "evaluation_examples" / "examples" / "libreoffice_calc"


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
        self.rules_version = hashlib.sha256((HERE / "treediff.py").read_bytes() + (HERE / "mask.py").read_bytes() + (HERE / "xlsxsig.py").read_bytes()).hexdigest()[:12]
        data = json.load(open(args.spots))
        self.spots = {s["id"]: s for s in data["spots"]}
        self.rows_all = data["rows"]
        self.mnemonics = dict(data["meta"].get("mnemonic_placeholders", {}))
        if args.mnemonics:
            self.mnemonics.update(json.loads(args.mnemonics))
        self.results_path = self.out / "results.jsonl"
        self.done = set()
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

    # ------------------------------------------------------------------ selection
    def select_rows(self):
        rows = self.rows_all
        if self.args.rows:
            wanted = set()
            for part in self.args.rows.split(","):
                part = part.strip()
                if "-" in part and not part.startswith("pilot"):
                    a, b = part.split("-")
                    wanted.update(range(int(a), int(b) + 1))
                elif part.startswith("pilot-"):
                    wanted.add(int(part.split("-")[1]))
                elif part:
                    wanted.add(int(part))
            rows = [r for r in rows if int(r["row_id"].split("-")[1]) in wanted]
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
            self.tasks[task_id] = json.loads((TASK_DIR / f"{task_id}.json").read_text())
        return self.tasks[task_id]

    # ------------------------------------------------------------------ environment
    def start_env(self, task_id):
        from desktop_env.desktop_env import DesktopEnv
        from rig.vmprep import prepare_vm
        t0 = time.time()
        self.env = DesktopEnv(provider_name=self.args.provider, action_space="pyautogui", headless=True,
                              require_a11y_tree=False, os_type="Ubuntu")
        self.env_started = time.time()
        task = self.task(task_id)
        self.env.reset(task_config=task)
        print(f"[env] task {task_id[:8]} ready after {time.time() - t0:.0f}s; prep: {prepare_vm(self.env)}; cache: {prime_cache(self.env, task)}", flush=True)
        self.current_task_id = task_id

    def close_env(self):
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

    def reset_to_before(self, row) -> dict:
        """Fresh start, Ctrl+Home, setup.  Returns timings."""
        t = time.time()
        how = fresh_start(self.env, self.task(row["task_id"]))
        t_fs = time.time() - t
        self.timings["fresh_start"].append(t_fs)
        self.step(PRELUDE, pause=1.0)
        if row.get("setup"):
            self.step(row["setup"], pause=2.0)
        return {"fresh_start": how, "fresh_start_seconds": round(t_fs, 1), "setup_seconds": round(time.time() - t - t_fs, 1)}

    def act(self, row):
        self.step(row["code"], pause=row.get("pause", 2))

    def reset_to_after(self, row) -> dict:
        info = self.reset_to_before(row)
        self.act(row)
        return info

    def snapshot(self, path, meta, expect_kind="calc", office_expected=True):
        """expect_kind: the spot's declared outcome for S' ('calc', 'dialog', 'start_center', 'second_window',
        'app_closed'); 'any' for undo candidates and replays, whose outcome is unknown: the tree is taken as it is
        (waiting for a LibreOffice window only when one is expected) and completeness is not a gate."""
        t = time.time()
        if expect_kind == "any":
            snap = take_snapshot(self.env, path, meta, expect="LibreOffice" if office_expected else None, require_office=False)
        else:
            app_may_be_closed = expect_kind == "app_closed"
            snap = take_snapshot(self.env, path, meta, expect=None if app_may_be_closed else "LibreOffice",
                                 require_office=not app_may_be_closed)
        self.timings["snapshot"].append(time.time() - t)
        return snap

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
        spot = self.spots[row["spot_id"]]
        rdir = self.out / rid
        rdir.mkdir(parents=True, exist_ok=True)
        task = self.task(row["task_id"])
        env_how = self.ensure_task(row["task_id"])
        rec = {"row_id": rid, "app": "libreoffice-calc", "task_id": row["task_id"], "workbook": row["workbook"],
               "spot_id": row["spot_id"], "band": row["band"], "on_task": row["on_task"], "on_task_reason": row["on_task_reason"],
               "seed": row["seed"], "sequence": row.get("sequence"), "step": row.get("step"), "twin_of": row.get("twin_of"),
               "target_cell": row.get("target_cell"), "target_in_set": row.get("target_in_set"),
               "action": {"type": "pyautogui", "desc": spot["desc"], "code": row["code"], "setup": row.get("setup") or "",
                          "prelude": PRELUDE, "pause": row.get("pause", 2), "expect": row.get("expect", "calc")},
               "mask_version": self.mask_version, "rules_version": self.rules_version, "env": env_how,
               "started_at": time.time()}

        # ---- S
        signal.alarm(WATCHDOG_SECONDS)
        info = self.reset_to_before(row)
        S = self.snapshot(rdir / "S", {"row": rid, "kind": "before", **info})
        if not S.ok:
            time.sleep(3)
            S = self.snapshot(rdir / "S", {"row": rid, "kind": "before", **info, "retake": True})
        signal.alarm(0)
        rec["snapshot_before"] = str(S.path.relative_to(self.out))
        rec["before_ok"] = S.ok
        rec["tree_before"] = str((S.path / "tree.xml").relative_to(self.out))
        before_text = render(S.canon, S.digest, S.windows)
        rec["state_before_compact"] = before_text
        rec["state_before_tokens_est"] = len(before_text) // 4

        # ---- teacher guesses, requested before the action runs
        guesses = {}
        trajectory = ["Ctrl+Home (cursor to A1)"] + ([f"setup keys: {row['setup']}"] if row.get("setup") else [])
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

        # ---- action and S'
        rec["action_executed_at"] = time.time()
        signal.alarm(WATCHDOG_SECONDS)
        self.act(row)
        S1 = self.snapshot(rdir / "S1", {"row": rid, "kind": "after"}, expect_kind=row.get("expect", "calc"))
        if not S1.ok:
            time.sleep(3)
            S1 = self.snapshot(rdir / "S1", {"row": rid, "kind": "after", "retake": True}, expect_kind=row.get("expect", "calc"))
        signal.alarm(0)
        rec["snapshot_after"] = str(S1.path.relative_to(self.out))
        rec["after_ok"] = S1.ok
        rec["tree_after"] = str((S1.path / "tree.xml").relative_to(self.out))
        after_text = render(S1.canon, S1.digest, S1.windows)
        rec["state_after_compact"] = after_text
        rec["file_diff"] = file_diff(S.digest, S1.digest, self.mask)
        eq, tdiffs, fdiffs = states_equal(S.canon, S.digest, S1.canon, S1.digest, self.mask)
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
        ctx = {"doc_path": row["open_path"], "office_running": office_running}
        deadline = t_row + self.args.row_minutes * 60

        def try_candidate(cand, tier, idx, note=""):
            nonlocal closest, budget_used
            t_c = time.time()
            r = {"tier": tier, "seq": cand, "idx": idx}
            if note:
                r["note"] = note
            signal.alarm(WATCHDOG_SECONDS)
            try:
                rinfo = self.reset_to_after(row)
                code = U.candidate_code(cand, ctx)
                r["code"] = code
                self.step(code, pause=1.5)
                windows, digest, derr = self.quick_state()
                cdir = rdir / f"c{idx:02d}"
                cdir.mkdir(exist_ok=True)
                (cdir / "windows.txt").write_text(windows)
                (cdir / "digest.json").write_text(json.dumps(digest, sort_keys=True))
                okq, reasons, qf = self.quick_matches(S, windows, digest)
                if not okq:
                    r.update({"result": "; ".join(reasons)[:300], "tree_taken": False, "file_diffs": len(qf), "quick_reject": True})
                    (cdir / "meta.json").write_text(json.dumps({"quick_reject": reasons, "fresh": rinfo}))
                    score = (len(qf) + (100 if any(x.startswith("windows") for x in reasons) else 0), 10_000 + len(qf))
                else:
                    snap = self.snapshot(cdir, {"row": rid, "kind": "candidate", "seq": cand, **rinfo}, expect_kind="any",
                                         office_expected=office_running or "reopen" in cand)
                    eq_c, td, fd = states_equal(S.canon, S.digest, snap.canon, snap.digest, self.mask)
                    r.update({"result": "match" if eq_c else f"state differs: {len(td)} tree, {len(fd)} files; {classify_diffs(td, fd)}",
                              "tree_taken": True, "tree_diffs": len(td), "file_diffs": len(fd), "snapshot_ok": snap.ok,
                              "diff_sample": summarize(td, limit=5) if not eq_c else ""})
                    score = content_score(td, fd) if snap.ok else (9_000, 9_000)
                    if eq_c:
                        r["match"] = True
                if closest is None or score < closest[0]:
                    closest = (score, idx, cand, r.get("diff_sample", ""), r.get("result"))
            except Watchdog:
                signal.alarm(0)
                raise                      # the row ends with an error and the environment is restarted
            except Exception as e:
                r.update({"result": f"error: {repr(e)[:200]}", "error": True})
            finally:
                signal.alarm(0)
            r["seconds"] = round(time.time() - t_c, 1)
            self.timings["candidate"].append(time.time() - t_c)
            budget_used += 1
            search.append(r)
            print(f"  [{rid}] c{idx:02d} t{tier} {U.describe(cand)[:60]:60s} -> {r['result'][:70]} ({r['seconds']}s)", flush=True)
            return bool(r.get("match"))

        if eq:
            rec["executed_label"] = "REVERSIBLE"
            rec["shortest_undo"] = []
            rec["undo_length"] = 0
            rec["found_tier"] = 0
            rec["no_change"] = True
            if spot["spot_id"] not in NO_CHANGE_EXPECTED:
                # the action was meant to change something and changed nothing: its key route is broken on this image
                # (Ctrl+0 for hide column on 17 Oct, Alt+D for "Don't Save" in pilot2 0266).  Not a data row.
                rec["broken_action"] = True
        else:
            tiers = [(1, [U.fill_mnemonics(c, self.mnemonics) for c in U.GENERIC]),
                     ("B", None),
                     (2, [U.fill_mnemonics(c, self.mnemonics) for c in U.CALC])]
            tried = []
            idx = 0
            stop = False
            skipped = 0
            for tier, cands in tiers + [(3, None), (4, None)]:
                if stop:
                    break
                if tier == 3:
                    cands = []
                    if not self.args.no_proposer and budget_used < self.args.budget and time.time() < deadline:
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
                    g = U.from_guess((guesses.get("B") or {}).get("shortest_undo"))
                    rec["guess_b_candidate"] = g
                    cands = [g] if g else []
                for cand in cands:
                    if cand in tried:
                        continue
                    if budget_used >= self.args.budget:
                        skipped += 1
                        continue
                    if time.time() > deadline:
                        skipped += 1
                        continue
                    tried.append(cand)
                    if try_candidate(cand, tier, idx):
                        found = (tier, cand, idx)
                        stop = True
                        break
                    idx += 1
            if skipped:
                search.append({"tier": "-", "seq": [], "result": f"skipped {skipped} candidates: budget {self.args.budget} / {self.args.row_minutes} min reached"})
            if found:
                rec["executed_label"] = "REVERSIBLE"
                rec["shortest_undo"] = found[1]
                rec["undo_length"] = len(found[1])
                rec["found_tier"] = found[0]
            else:
                rec["executed_label"] = "NO-UNDO-FOUND"
                rec["shortest_undo"] = None
                rec["undo_length"] = None
                rec["found_tier"] = None
            rec["candidates_skipped"] = skipped
        rec["undo_search"] = search
        rec["budget_used"] = budget_used
        rec["proposal_model"] = proposal.get("model")

        # ---- confirming replay: every no-undo row reruns its closest-failing candidate; a seeded 10% replay their result
        rec.update({"replay_done": False, "replay_matched": None, "flipped": False, "flicker_class": None})
        random_pick = (row["seed"] % 10 == 0)
        replay_cand = None
        if rec["executed_label"] == "NO-UNDO-FOUND" and closest is not None:
            replay_cand = closest[2]
            rec["replay_reason"] = "no-undo row: closest-failing candidate"
        elif random_pick and rec["executed_label"] == "REVERSIBLE" and rec["shortest_undo"]:
            replay_cand = rec["shortest_undo"]
            rec["replay_reason"] = "seeded 10% sample"
        elif random_pick and rec.get("no_change"):
            rec["replay_reason"] = "seeded 10% sample: replay the action itself"
            replay_cand = []
        if replay_cand is not None and not self.args.no_replay:
            signal.alarm(WATCHDOG_SECONDS)
            try:
                rinfo = self.reset_to_after(row)
                if replay_cand:
                    self.step(U.candidate_code(replay_cand, ctx), pause=1.5)
                snap = self.snapshot(rdir / "replay", {"row": rid, "kind": "replay", "seq": replay_cand, **rinfo}, expect_kind="any",
                                     office_expected=office_running or "reopen" in (replay_cand or []))
                eq_r, td, fd = states_equal(S.canon, S.digest, snap.canon, snap.digest, self.mask)
                rec["replay_done"] = True
                rec["replay_matched"] = bool(eq_r)
                rec["replay_seq"] = replay_cand
                if rec["executed_label"] == "NO-UNDO-FOUND" and eq_r:
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
            except Exception as e:
                rec["replay_error"] = repr(e)[:300]
            finally:
                signal.alarm(0)

        # ---- teacher results
        if th is not None:
            th.join(timeout=900)
            rec["guess_pending"] = th.is_alive()
        rec["guessed_label_verbatim"] = guesses.get("A") or {"reversible": None, "model": None, "prompt": "SafePred App. G", "skipped": self.args.no_teacher}
        rec["guessed_label_defined"] = guesses.get("B") or {"reversible": None, "model": None, "prompt": "definition-matched", "skipped": self.args.no_teacher}
        rec["teacher_model"] = (rec["guessed_label_defined"] or {}).get("model") or (rec["guessed_label_verbatim"] or {}).get("model")

        rec["row_seconds"] = round(time.time() - t_row, 1)
        rec["status"] = "broken_action" if rec.get("broken_action") else "ok"
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
        import statistics as st
        def q(xs):
            return (f"n={len(xs)} median={st.median(xs):.0f}s mean={st.mean(xs):.0f}s max={max(xs):.0f}s") if xs else "n=0"
        sandbox_h = (self.sandbox_seconds + ((time.time() - self.env_started) if self.env_started else 0)) / 3600
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
            lines.append("")
            lines.append("| row | spot | band | on_task | label | undo | tier | budget | guess A | guess B | row s |")
            lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
            for r in recs:
                ga = (r.get("guessed_label_verbatim") or {}).get("reversible")
                gb = (r.get("guessed_label_defined") or {}).get("reversible")
                lines.append(f"| {r['row_id']} | {r['spot_id']} | {r['band']} | {r['on_task']} | {r.get('executed_label')} | {U.describe(r.get('shortest_undo') or []) or '-'} | {r.get('found_tier')} | {r.get('budget_used')} | {ga} | {gb} | {r.get('row_seconds')} |")
        (self.out / "report.md").write_text("\n".join(lines) + "\n")
        return "\n".join(lines[:6])

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
        try:
            for row in rows:
                for attempt in range(2):
                    try:
                        rec = self.run_row(row)
                        self.write(rec)
                        done += 1
                        print(f"[{row['row_id']}] {rec['executed_label']} undo={U.describe(rec.get('shortest_undo') or [])!r} tier={rec.get('found_tier')} "
                              f"budget={rec['budget_used']} guessA={(rec['guessed_label_verbatim'] or {}).get('reversible')} "
                              f"guessB={(rec['guessed_label_defined'] or {}).get('reversible')} in {rec['row_seconds']}s", flush=True)
                        break
                    except Exception as e:
                        err = traceback.format_exc()[-1500:]
                        print(f"[{row['row_id']}] ERROR attempt {attempt + 1}: {repr(e)[:200]}", flush=True)
                        self.write({"row_id": row["row_id"], "spot_id": row["spot_id"], "status": "error", "attempt": attempt + 1, "error": err, "at": time.time()})
                        signal.alarm(0)
                        if attempt == 0 and self.env_restarts < 3:
                            self.env_restarts += 1
                            self.close_env()
                            time.sleep(10)
                            self.start_env(row["task_id"])
                        elif attempt == 0:
                            break
                print(self.report(done, len(rows)), flush=True)
        finally:
            self.close_env()
            print(self.report(done, len(rows)), flush=True)

    # ------------------------------------------------------------------ re-judge rows on disk (rule change, Section 4.3)
    def recompare(self):
        recs = [json.loads(l) for l in self.results_path.read_text().splitlines() if l.strip()] if self.results_path.exists() else []
        flips = []
        out = []
        for r in recs:
            if r.get("status") != "ok":
                continue
            rdir = self.out / r["row_id"]
            if not (rdir / "S" / "meta.json").exists() or not (rdir / "S1" / "meta.json").exists():
                continue
            S, S1 = load_snapshot(rdir / "S"), load_snapshot(rdir / "S1")
            eq, _, _ = states_equal(S.canon, S.digest, S1.canon, S1.digest, self.mask)
            label, undo = None, None
            if eq:
                label, undo = "REVERSIBLE", []
            else:
                for c in sorted(rdir.glob("c*")):
                    if not (c / "tree.xml").exists():
                        continue
                    snap = load_snapshot(c)
                    eq_c, _, _ = states_equal(S.canon, S.digest, snap.canon, snap.digest, self.mask)
                    if eq_c:
                        idx = int(c.name[1:])
                        seq = next((s["seq"] for s in r["undo_search"] if s.get("idx") == idx), None)
                        label, undo = "REVERSIBLE", seq
                        break
                if label is None and (rdir / "replay" / "tree.xml").exists():
                    snap = load_snapshot(rdir / "replay")
                    eq_c, _, _ = states_equal(S.canon, S.digest, snap.canon, snap.digest, self.mask)
                    if eq_c:
                        label, undo = "REVERSIBLE", r.get("replay_seq")
                if label is None:
                    label = "NO-UNDO-FOUND"
            new = dict(r, executed_label_recompared=label, shortest_undo_recompared=undo, recompared_with={"mask": self.mask_version, "rules": self.rules_version})
            if label != r.get("executed_label"):
                flips.append((r["row_id"], r.get("executed_label"), label))
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
    ap.add_argument("--dry", action="store_true", help="print the plan and the worst-case cost, no VM")
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--recompare", action="store_true", help="re-judge the rows on disk with the current mask and rules")
    args = ap.parse_args()
    if not os.path.isabs(args.out):
        # the module chdirs into OSWorld at import, so a relative --out would land under OSWorld/ (pilot_run2 did)
        args.out = str((BASE / args.out).resolve())
    c = Collector(args)
    if args.recompare:
        c.recompare()
        return
    c.run()


if __name__ == "__main__":
    main()
