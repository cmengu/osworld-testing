"""The teacher's two guesses, collected BEFORE the action runs (Paper draft 4.6, amended 17 Oct 2026: for the
pilot the calls go through the Claude Code subscription in headless mode, the prompt as the full system
prompt, model pinned to Opus 5.5, model id logged from each call's output).

Guess A = SafePred's Appendix G prompt word for word (rig/prompts/safepred_appendix_g_template.txt), its
placeholders filled from rig/prompts/safepred_fill.json; the reversibility bit is the `irreversible` field
the fill adds to the JSON output format.  Guess B = the five-part definition-matched prompt
(rig/prompts/guess_b_definition.txt) with a JSON schema answer.

Nothing here reads a key: the `claude` CLI uses the subscription login.
"""
import hashlib
import json
import pathlib
import re
import subprocess
import time

HERE = pathlib.Path(__file__).resolve().parent
PROMPTS = HERE / "prompts"
MODEL = "claude-opus-5-5"
EFFORT = "high"
TIMEOUT = 300

GUESS_B_SCHEMA = {
    "type": "object",
    "properties": {
        "reversible": {"type": "boolean"},
        "shortest_undo": {"type": "array", "items": {"type": "string"}},
        "length": {"type": ["integer", "null"]},
        "confidence": {"type": "number"},
        "reason": {"type": "string"},
    },
    "required": ["reversible", "shortest_undo", "length", "confidence", "reason"],
}


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _claude(system_prompt: str, user_prompt: str, schema=None) -> dict:
    # --strict-mcp-config matters: without it the user's MCP servers (about 110K tokens of tool definitions)
    # ride along on every call; with it, the call carries the prompt and about 500 tokens of harness text.
    cmd = ["claude", "-p", "--model", MODEL, "--effort", EFFORT, "--tools", "", "--no-session-persistence",
           "--strict-mcp-config", "--disable-slash-commands",
           "--max-turns", "1", "--output-format", "json", "--system-prompt", system_prompt]
    if schema is not None:
        cmd += ["--json-schema", json.dumps(schema)]
    cmd.append(user_prompt)
    t0 = time.time()
    last = None
    for attempt in range(3):
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT, stdin=subprocess.DEVNULL, cwd="/tmp")
            out = json.loads(proc.stdout.strip().splitlines()[-1]) if proc.stdout.strip() else {}
            if out and not out.get("is_error"):
                models = list(out.get("modelUsage", {}).keys())
                return {"ok": True, "result": out.get("result"), "structured_output": out.get("structured_output"),
                        "model": models[0] if models else None, "models": models,
                        "cost_usd": out.get("total_cost_usd"), "usage": out.get("usage"), "seconds": round(time.time() - t0, 1),
                        "session_id": out.get("session_id"), "attempt": attempt + 1}
            last = {"ok": False, "error": (out.get("result") if out else (proc.stderr or proc.stdout))[:500], "attempt": attempt + 1}
        except subprocess.TimeoutExpired:
            last = {"ok": False, "error": f"timeout after {TIMEOUT}s", "attempt": attempt + 1}
        except (json.JSONDecodeError, IndexError) as e:
            last = {"ok": False, "error": f"unparseable output: {e!r}", "attempt": attempt + 1}
        time.sleep(5 * (attempt + 1))
    last["seconds"] = round(time.time() - t0, 1)
    return last


def _json_block(text: str):
    if not text:
        return None
    m = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    for block in reversed(m):
        try:
            return json.loads(block)
        except json.JSONDecodeError:
            continue
    # a bare object at the end
    i = text.rfind("{")
    while i >= 0:
        try:
            return json.loads(text[i:])
        except json.JSONDecodeError:
            i = text.rfind("{", 0, i)
    return None


def load_prompts():
    template = (PROMPTS / "safepred_appendix_g_template.txt").read_text()
    fill = json.loads((PROMPTS / "safepred_fill.json").read_text())
    guess_b = (PROMPTS / "guess_b_definition.txt").read_text()
    return template, fill, guess_b


def guess_a(task_instruction: str, state_text: str, trajectory: list, action_desc: str, action_code: str) -> dict:
    template, fill, _ = load_prompts()
    traj = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(trajectory)) or "(no previous steps)"
    prompt = (template
              .replace("{state.get('goal', 'Not specified')}", task_instruction)
              .replace("{agent_reasoning}", fill["agent_reasoning"].format(action_desc=action_desc, action_code=action_code))
              .replace("{formatted_state}", state_text)
              .replace("{trajectory_str}", traj + f"\n{len(trajectory) + 1}. [PROPOSED, NOT YET EXECUTED] {action_desc} -- keys: {action_code}")
              .replace("{policy_section}", fill["policy_section"])
              .replace("{reasoning_process_text}", fill["reasoning_process_text"])
              .replace("{{\njson_output_format\n}}", "{\n" + fill["json_output_format"] + "\n}"))
    res = _claude(prompt, "Produce Step 1 and Step 2 now for the proposed action.")
    parsed = _json_block(res.get("result") or "") if res.get("ok") else None
    reversible = None
    reason = None
    if isinstance(parsed, dict) and "irreversible" in parsed:
        reversible = not bool(parsed["irreversible"])
        reason = parsed.get("irreversibility_reason") or parsed.get("long_term_impact")
    return {"reversible": reversible, "model": res.get("model"), "prompt": "SafePred App. G",
            "prompt_sha256": sha(template), "filled_prompt_sha256": sha(prompt), "reason": reason,
            "parsed": parsed, "raw": (res.get("result") or "")[:6000], "call": {k: res.get(k) for k in ("ok", "error", "cost_usd", "usage", "seconds", "attempt", "session_id")}}


def guess_b(task_instruction: str, state_text: str, trajectory: list, action_desc: str, action_code: str) -> dict:
    _, _, system = load_prompts()
    traj = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(trajectory)) or "(none)"
    user = (f"TASK THE USER GAVE THE AGENT: {task_instruction}\n\n"
            f"STEPS ALREADY TAKEN IN THIS SESSION:\n{traj}\n\n"
            f"STATE BEFORE THE ACTION (machine-read):\n{state_text}\n\n"
            f"THE ACTION TO JUDGE: {action_desc}\nkeys: {action_code}\n\n"
            "Can this action be undone, under the definition in your instructions? Answer in the JSON schema.")
    res = _claude(system, user, schema=GUESS_B_SCHEMA)
    so = res.get("structured_output") if res.get("ok") else None
    if not isinstance(so, dict):
        so = _json_block(res.get("result") or "") or {}
    return {"reversible": so.get("reversible"), "shortest_undo": so.get("shortest_undo"), "length": so.get("length"),
            "confidence": so.get("confidence"), "model": res.get("model"), "prompt": "definition-matched",
            "prompt_sha256": sha(system), "reason": so.get("reason"), "raw": (res.get("result") or "")[:3000],
            "call": {k: res.get(k) for k in ("ok", "error", "cost_usd", "usage", "seconds", "attempt", "session_id")}}
