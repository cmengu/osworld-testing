"""Tier 3 of the undo search: undo sequences proposed by a model of a different family from the teacher
(Paper draft 4.5, protocol change 17 Oct 2026: GPT-6.1 Sol through the OpenAI API, GPT-5.6 Sol as fallback).
The proposer proposes and the machine decides; a wrong proposal is discarded and never becomes a label.

The key comes from OPENAI_API_KEY in the environment, loaded from the git-ignored .env by the collector;
it is never printed or stored in a row.
"""
import json
import pathlib
import re
import time

PROMPT = (pathlib.Path(__file__).resolve().parent / "prompts" / "proposer.txt").read_text()
MODELS = ["gpt-6.1-sol", "gpt-5.6-sol"]
SCHEMA = {
    "type": "object",
    "properties": {
        "candidates": {"type": "array", "items": {"type": "object", "properties": {
            "steps": {"type": "array", "items": {"type": "string"}}, "why": {"type": "string"}},
            "required": ["steps", "why"], "additionalProperties": False}},
        "note": {"type": "string"},
    },
    "required": ["candidates", "note"],
    "additionalProperties": False,
}
STEP_RE = re.compile(r"^(key:[a-z0-9+_]+|type:.+|wait:\d+(\.\d+)?|reopen|menu:alt\+[a-z],[a-z]{1,4})$", re.I)


def propose(before_text: str, after_text: str, file_diff: list, action_desc: str, action_code: str,
            task_instruction: str, max_candidates: int = 5, max_len: int = 5) -> dict:
    from openai import OpenAI
    client = OpenAI()
    user = (f"TASK THE USER GAVE THE AGENT: {task_instruction}\n\n"
            f"ACTION: {action_desc}\nkeys: {action_code}\n\n"
            f"STATE BEFORE:\n{before_text}\n\n"
            f"STATE AFTER:\n{after_text}\n\n"
            f"FILE DIFFERENCES (masked):\n{json.dumps(file_diff, indent=0)[:4000]}\n\n"
            f"Propose up to {max_candidates} undo sequences of at most {max_len} steps each.")
    last_err = None
    for model in MODELS:
        t0 = time.time()
        try:
            r = client.responses.create(
                model=model,
                input=[{"role": "system", "content": PROMPT}, {"role": "user", "content": user}],
                text={"format": {"type": "json_schema", "name": "undo_proposals", "schema": SCHEMA, "strict": True}},
                max_output_tokens=1500,
            )
            data = json.loads(r.output_text)
            cands = []
            for c in data.get("candidates", []):
                steps = [s.strip() for s in c.get("steps", []) if isinstance(s, str) and s.strip()]
                if not steps or len(steps) > max_len or not all(STEP_RE.match(s) for s in steps):
                    continue
                cands.append({"steps": steps, "why": c.get("why", "")[:300]})
                if len(cands) >= max_candidates:
                    break
            return {"ok": True, "model": r.model, "candidates": cands, "note": data.get("note", "")[:500],
                    "usage": {"input": r.usage.input_tokens, "output": r.usage.output_tokens},
                    "seconds": round(time.time() - t0, 1), "rejected": len(data.get("candidates", [])) - len(cands)}
        except Exception as e:  # model unavailable, schema refusal, network
            last_err = f"{model}: {repr(e)[:300]}"
            time.sleep(3)
    return {"ok": False, "model": None, "candidates": [], "error": last_err}
