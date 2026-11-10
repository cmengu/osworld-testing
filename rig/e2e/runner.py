"""End-to-end pilot episode with a counterfactual branch (10 Nov 2026).  TEST ONLY.

Arm A (agent alone): the agent runs the task; the world-model guard (rig/guard_live.py, mode "world": world model first,
Claude for what it does not model, Claude says whether a one-way step is on-task, a simulated user may approve a block)
judges EVERY step in SHADOW: its decision is logged, never applied.
Branch: at the first step the shadow guard would have SKIPPED, the VM is snapshotted (QEMU, rig/vmsnap.py) and the
agent's history copied, before the step runs.  Arm A then goes on to the end and the task's checker scores it.
Arm B (agent + guard): the VM is restored to the branch, the agent's history restored, the step is skipped with the
guard's note, and the run goes on with the guard LIVE until the end; the checker scores it.  Both arms share every
step before the branch, so the comparison is paired at the decision itself.  No branch -> arm B is arm A.

Per episode: <result dir>/e2e.json {A: checker, B: checker, branch: {...}}, guard.jsonl (arm A shadow + arm B live),
states/ (arm A) and arm_b/states/ (arm B).  Called from OSWorld/lib_run_single.py when RIG_E2E=1.
"""
import datetime
import json
import logging
import os
import pathlib
import shutil
import sys
import time

BASE = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE))
from rig.e2e.tasks import TASKS                                    # noqa: E402
from rig.e2e.vmscripts import checker_script, parse_check, setup_script   # noqa: E402
from rig.vm import vm_shell                                        # noqa: E402

logger = logging.getLogger("desktopenv.experiment")
BY_ID = {t["id"]: t for t in TASKS}


def _check(env, task):
    r = vm_shell(env, checker_script(task), timeout=300)
    return parse_check(r.get("output") or "") or {"error": (r.get("error") or r.get("output") or "")[-400:]}


def _step(env, agent_dir, step_no, action, args, response):
    ts = datetime.datetime.now().strftime("%Y%m%d@%H%M%S%f")
    obs, reward, done, info = env.step(action, args.sleep_after_execution)
    with open(os.path.join(agent_dir, f"step_{step_no}_{ts}.png"), "wb") as f:
        f.write(obs["screenshot"])
    with open(os.path.join(agent_dir, "traj.jsonl"), "a") as f:
        f.write(json.dumps({"step_num": step_no, "action_timestamp": ts, "action": action, "response": response,
                            "done": done, "screenshot_file": f"step_{step_no}_{ts}.png"}) + "\n")
    return obs, done


def _last_acts(out_dir):
    """Did the guard's last decision ACT (block, or back up under the loss-aware backup policy)?  Read from guard.jsonl:
    in shadow (arm A) the backup policy cannot run (no env), so a loss-aware refusal shows as block=True there."""
    try:
        last = json.loads(open(os.path.join(out_dir, "guard.jsonl")).read().splitlines()[-1])
    except (OSError, IndexError, ValueError):
        return None
    if last.get("block") or last.get("backup"):
        return "block" if last.get("block") else "backup"
    return None


def run_e2e(agent, env, example, max_steps, instruction, args, out_dir, scores, lib):
    from rig.guard_live import LiveGuard
    task = BY_ID[example["id"]]
    env.reset(task_config=example)
    try:
        agent.reset(None, vm_ip=env.vm_ip)
    except Exception:
        agent.reset(vm_ip=env.vm_ip)
    lib._rig_prepare(env)
    r = vm_shell(env, setup_script(task), timeout=300)
    if "SETUP OK" not in (r.get("output") or ""):
        raise RuntimeError(f"e2e setup failed: {(r.get('output') or r.get('error') or '')[-300:]}")
    time.sleep(20)
    branch_on = os.environ.get("RIG_E2E_BRANCH", "1") == "1"
    snap = lib._rig_vmsnap(env) if branch_on else None
    guard = LiveGuard("world", out_dir, example)
    guard.env = None                 # shadow: no backup may run in arm A (the guard decides, nothing is applied)
    guard.arm = "A-shadow"
    k, step, done, branch = 0, 0, False, None
    lib._rig_record(env, out_dir, 0)
    obs = env._get_obs()
    t0 = time.time()
    # ---------------------------------------------------------------------------------------------- arm A
    while not done and step < max_steps:
        response, actions = agent.predict(instruction, obs)
        for i, action in enumerate(actions):
            note = guard.check(instruction, os.path.join(out_dir, "states", f"s{k:02d}"), k + 1, action)
            acts = _last_acts(out_dir)
            if acts and branch is None and branch_on:
                ts = time.time()
                try:
                    snap.save("e2e_branch")
                    branch = {"k": k, "step": step, "action": action, "note": note, "snapshot_s": round(time.time() - ts, 1),
                              "pending": actions[i:], "response": response, "why": acts,
                              "thoughts": list(agent.thoughts), "actions": list(agent.actions),
                              "observations": list(agent.observations)}
                    logger.info("e2e: branch at step %d (state s%02d), snapshot in %.0fs", step + 1, k, time.time() - ts)
                except Exception as e:  # noqa: BLE001  no snapshot: no arm B for this episode (logged)
                    branch = {"k": k, "step": step, "action": action, "note": note, "error": repr(e)[:300], "why": acts}
                    logger.warning("e2e: branch snapshot failed: %r", e)
            obs, done = _step(env, out_dir, step + 1, action, args, response)
            k += 1
            lib._rig_record(env, out_dir, k)
            if done:
                break
        obs = env._get_obs()
        step += 1
    res = {"task": task["id"], "A": _check(env, task), "A_steps": step, "A_seconds": round(time.time() - t0)}
    # ---------------------------------------------------------------------------------------------- arm B
    if branch and "error" not in branch:
        t1 = time.time()
        snap.load("e2e_branch")
        agent.thoughts, agent.actions, agent.observations = branch["thoughts"], branch["actions"], branch["observations"]
        b_dir = os.path.join(out_dir, "arm_b")
        os.makedirs(os.path.join(b_dir, "states"), exist_ok=True)
        shutil.copytree(os.path.join(out_dir, "states", f"s{branch['k']:02d}"), os.path.join(b_dir, "states", f"s{branch['k']:02d}"),
                        dirs_exist_ok=True)
        guard.arm = "B-live"
        guard.env = env
        k, step, done, note = branch["k"], branch["step"], False, ""
        for action in branch["pending"]:        # the flagged response, now through the live guard
            skipped = guard.check(instruction, os.path.join(b_dir, "states", f"s{k:02d}"), k + 1, action)
            if skipped:
                note = skipped
                break
            obs, done = _step(env, b_dir, step + 1, action, args, branch["response"])
            k += 1
            lib._rig_record(env, b_dir, k)
            if done:
                break
        step += 1
        obs = env._get_obs()
        while not done and step < max_steps:
            response, actions = agent.predict(instruction + note, obs)
            note = ""
            for action in actions:
                skipped = guard.check(instruction, os.path.join(b_dir, "states", f"s{k:02d}"), k + 1, action)
                if skipped:
                    note = skipped
                    break
                obs, done = _step(env, b_dir, step + 1, action, args, response)
                k += 1
                lib._rig_record(env, b_dir, k)
                if done:
                    break
            obs = env._get_obs()
            step += 1
        res.update(B=_check(env, task), B_steps=step, B_seconds=round(time.time() - t1))
    else:
        res.update(B=res["A"], B_same_as_A=True)
    res["branch"] = {k_: v for k_, v in (branch or {}).items() if k_ not in ("thoughts", "actions", "observations")} or None
    (pathlib.Path(out_dir) / "e2e.json").write_text(json.dumps(res, indent=1))
    logger.info("e2e %s: A lost=%s done=%s | B lost=%s done=%s | branch=%s", task["id"], res["A"].get("lost"), res["A"].get("success"),
                res["B"].get("lost"), res["B"].get("success"), bool(branch))
    scores.append(1.0 if res["A"].get("success") else 0.0)
    with open(os.path.join(out_dir, "result.txt"), "w") as f:
        f.write(f"{scores[-1]}\n")
