"""The trained model's answers on the review-page agent steps (30 Oct 2026; TEST ONLY, no training here): the first
token's probability of yes/no (REVERSIBLE) and refuse/allow (GUARD), as evaluate.py scores them, from the five K=3
adapters of the v3 export (tag k3_v3, seed 2026).  One A100 and a 15-minute limit keep it under about 0.65 USD.

    OSWorld/.venv/bin/modal run rig/train/modal_predict_agent.py     # -> rig/out/model_on_agent/predictions.json
"""
import json
import os
import pathlib

import modal

HERE = pathlib.Path(__file__).parent
OUT = HERE.parent / "out" / "model_on_agent"
PROMPTS = os.environ.get("AGENT_PROMPTS", str(OUT / "prompts.jsonl"))   # 7 Nov: the intent probe passes its own file
app = modal.App("osguard-predict")
vol = modal.Volume.from_name("osguard-train")
image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install_from_requirements(str(HERE / "requirements.txt"))
         .env({"HF_HOME": "/vol/hf", "TOKENIZERS_PARALLELISM": "false"})
         .add_local_file(PROMPTS, remote_path="/data/prompts.jsonl")
         .add_local_file(str(HERE / "evaluate.py"), remote_path="/code/evaluate.py"))


@app.function(image=image, gpu="A100-80GB", timeout=15 * 60, volumes={"/vol": vol})
def predict(model_name: str = "Qwen/Qwen3-8B", tag: str = "k3_v3", max_len: int = 8192) -> dict:
    import sys
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer
    sys.path.insert(0, "/code")
    from evaluate import SYSTEM
    rows = [json.loads(l) for l in open("/data/prompts.jsonl")]
    tok = AutoTokenizer.from_pretrained(model_name)
    base = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.bfloat16, device_map="auto")
    model = PeftModel.from_pretrained(base, f"/vol/runs/{tag}/fold0/adapter", adapter_name="fold0")
    for f in range(1, 5):
        model.load_adapter(f"/vol/runs/{tag}/fold{f}/adapter", adapter_name=f"fold{f}")
    model.eval()

    def prob(prompt, pos, neg):
        msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]
        kw = {"enable_thinking": False} if "enable_thinking" in tok.apply_chat_template.__code__.co_varnames else {}
        enc = tok.apply_chat_template(msgs, add_generation_prompt=True, return_tensors="pt", **kw)
        ids = (enc if torch.is_tensor(enc) else enc["input_ids"]).to(model.device)[:, -max_len:]
        with torch.no_grad():
            p = torch.softmax(model(ids).logits[0, -1].float(), -1)
        a, b = (float(p[tok(o, add_special_tokens=False)["input_ids"][0]]) for o in (pos, neg))
        return round(a / max(1e-9, a + b), 4)

    out = {"tag": tag, "model": model_name, "rows": {}}
    for f in range(5):
        model.set_adapter(f"fold{f}")
        for r in rows:
            d = out["rows"].setdefault(r["row_id"], {"reversible_yes": [], "guard_refuse": []})
            if r.get("reversible"):
                d["reversible_yes"].append(prob(r["reversible"], "yes", "no"))
            d["guard_refuse"].append(prob(r["guard"], "refuse", "allow"))
        print(f"fold {f} done", flush=True)
    return out


@app.local_entrypoint()
def main(tag: str = "k3_v3", out: str = "predictions.json"):
    res = predict.remote(tag=tag)
    (OUT / out).write_text(json.dumps(res, indent=1))
    print(len(res["rows"]), "rows predicted")
