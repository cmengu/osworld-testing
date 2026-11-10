"""Run a task in the throwaway Docker sandbox (rig/e2e/sandbox/Dockerfile): setup, then a bash script, then the checker.
No network; the container is removed afterwards.  Used by the free pre-screen and the offline checks."""
import json
import subprocess

from rig.e2e.vmscripts import checker_script, parse_check, setup_script

IMAGE = "e2e-sandbox"
MARK = "E2E-SOLUTION-OUTPUT"


def run_task(task, solution, timeout=90):
    sol = (solution or "true").replace("\r", "")
    script = (setup_script(task) + "\n"
              + f"echo {MARK}-BEGIN\n( cd ~ && timeout 60 bash <<'E2ESOL'\n{sol}\nE2ESOL\n) 2>&1 | tail -c 3000\necho {MARK}-END\n"
              + checker_script(task) + "\n")
    try:
        r = subprocess.run(["docker", "run", "--rm", "-i", "--network", "none", "--memory", "1g", "--cpus", "1", IMAGE, "bash"],
                           input=script, capture_output=True, text=True, timeout=timeout + 60)
    except subprocess.TimeoutExpired:
        return {"error": "sandbox timeout"}
    out = r.stdout
    if "SETUP OK" not in out:
        return {"error": "setup failed: " + (out + r.stderr)[-400:]}
    res = parse_check(out) or {"error": "no check: " + (out + r.stderr)[-400:]}
    if MARK + "-BEGIN" in out:
        res["solution_output"] = out.split(MARK + "-BEGIN", 1)[1].split(MARK + "-END", 1)[0][-1500:]
    return res
