"""Boot one OSWorld Calc task on Modal, fetch the accessibility tree, count its size.

Answers Appendix A item: "Token length of a Calc accessibility tree. If it exceeds 8K after pruning,
the input format changes."  Writes raw tree, linearized tree, screenshot and result.json to OUT.
"""
import json
import os
import pathlib
import sys
import time

REPO = "/Users/ngchenmeng/ai-research/osworld-testing/OSWorld"
OUT = pathlib.Path("/Users/ngchenmeng/ai-research/osworld-testing/calc-tree")
TASK = "evaluation_examples/examples/libreoffice_calc/357ef137-7eeb-4c80-a3bb-0951f26a8aff.json"

sys.path.insert(0, REPO)
os.chdir(REPO)
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
OUT.mkdir(parents=True, exist_ok=True)

from desktop_env.desktop_env import DesktopEnv  # noqa: E402

task = json.load(open(TASK))
t0 = time.time()
stamp = lambda: round(time.time() - t0, 1)  # noqa: E731

env = DesktopEnv(
    provider_name="modal",
    action_space="pyautogui",
    headless=True,
    require_a11y_tree=True,
    os_type="Ubuntu",
)
print("env constructed", stamp(), flush=True)
try:
    obs = env.reset(task_config=task)
    print("reset done", stamp(), flush=True)
    tree = obs.get("accessibility_tree") or ""
    (OUT / "tree_raw.xml").write_text(tree)
    (OUT / "screenshot.png").write_bytes(obs["screenshot"])
    print("raw tree chars", len(tree), flush=True)

    # Pruned / linearized form, the way OSWorld's own a11y_tree agents see it.
    lin = ""
    try:
        from mm_agents.agent import linearize_accessibility_tree
        lin = linearize_accessibility_tree(tree, platform="ubuntu")
    except Exception as e:  # fall back to the filter alone
        print("linearize via mm_agents.agent failed:", repr(e)[:200], flush=True)
        try:
            import xml.etree.ElementTree as ET
            from mm_agents.accessibility_tree_wrap.heuristic_retrieve import filter_nodes
            nodes = filter_nodes(ET.fromstring(tree), platform="ubuntu")
            lin = "\n".join(
                f"{n.tag}\t{n.get('name','')}\t{n.text or ''}" for n in nodes
            )
        except Exception as e2:
            print("filter_nodes fallback failed:", repr(e2)[:200], flush=True)
    (OUT / "tree_linear.txt").write_text(lin)
    print("linearized chars", len(lin), flush=True)

    import tiktoken
    enc = tiktoken.get_encoding("o200k_base")
    qwen = None
    try:
        from transformers import AutoTokenizer
        qwen = AutoTokenizer.from_pretrained("Qwen/Qwen3-8B")
    except Exception as e:
        print("qwen tokenizer unavailable:", repr(e)[:200], flush=True)

    def counts(s):
        d = {"chars": len(s), "o200k_tokens": len(enc.encode(s))}
        if qwen is not None:
            d["qwen3_tokens"] = len(qwen.encode(s))
        return d

    res = {
        "task": task["id"],
        "instruction": task["instruction"],
        "raw_xml": counts(tree),
        "linearized": counts(lin),
        "seconds_to_reset": stamp(),
    }
    print(json.dumps(res, indent=1), flush=True)
    (OUT / "result.json").write_text(json.dumps(res, indent=1))
finally:
    try:
        env.close()
        print("env closed", stamp(), flush=True)
    except Exception as e:
        print("close error:", repr(e)[:200], flush=True)
