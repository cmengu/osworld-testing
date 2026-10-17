"""Boot a sandbox, open the Calc task, run the scoped tree dump several times and report
time, node counts, dropped counts and whether consecutive runs agree."""
import json
import os
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
BASE = HERE.parent
OSWORLD = BASE / "OSWorld"
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(OSWORLD))
os.chdir(OSWORLD)

from desktop_env.desktop_env import DesktopEnv       # noqa: E402
from rig.fasttree import fast_tree                   # noqa: E402
from rig.treediff import canonicalize, diff          # noqa: E402

TASK = "evaluation_examples/examples/libreoffice_calc/357ef137-7eeb-4c80-a3bb-0951f26a8aff.json"
SOFFICE = "/desktop-frame/application[soffice]"


def main() -> None:
    task = json.load(open(TASK))
    t0 = time.time()
    env = DesktopEnv(provider_name="modal", action_space="pyautogui", headless=True,
                     require_a11y_tree=False, os_type="Ubuntu")
    try:
        env.reset(task_config=task)
        print(f"task ready at {time.time() - t0:.0f}s", flush=True)
        time.sleep(5)
        prev = None
        for i in range(4):
            t = time.time()
            xml, info = fast_tree(env)
            print(f"run {i + 1}: {time.time() - t:.1f}s chars={len(xml)} info={json.dumps(info)[:600]}", flush=True)
            if not xml:
                continue
            canon = canonicalize(xml)
            soff = {p: v for p, v in canon.items() if p.startswith(SOFFICE)}
            line = f"        nodes={len(canon)} soffice={len(soff)}"
            if prev is not None:
                d = diff(prev, soff)
                line += f" | vs previous run: {len(d)} differences"
                for x in d[:5]:
                    line += f"\n            {x['path'][-80:]} {x['attr']} {repr(x['old'])[:25]} -> {repr(x['new'])[:25]}"
            print(line, flush=True)
            prev = soff
    finally:
        try:
            env.close()
            print("env closed", flush=True)
        except Exception as e:  # pragma: no cover
            print("close error:", repr(e)[:200], flush=True)


if __name__ == "__main__":
    main()
