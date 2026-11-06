"""FORWARD predictions (6 Nov 2026, author's go: "sure run that"): the retrained Model-E (_v5w) predicts the change for
every FORWARD row of the v5 export, each from the adapter whose fold held that row out.  Greedy decoding, batched with
left padding, up to 1536 new tokens (the longest target is about 1,600 tokens).  One A100-80GB per fold, 5 at once
(the 5-GPU limit).  Scored offline by rig/train/score_forward.py against the rig's recorded change.

    OSWorld/.venv/bin/modal run rig/train/modal_predict_forward.py   # -> rig/out/forward/model_forward_k3_v5w.json
"""
import json
import pathlib

import modal

HERE = pathlib.Path(__file__).parent
OUT = HERE.parent / "out" / "forward"
DATA = HERE / "data_k3_v5"
app = modal.App("osguard-predict-forward")
vol = modal.Volume.from_name("osguard-train")
image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install_from_requirements(str(HERE / "requirements.txt"))
         .env({"HF_HOME": "/vol/hf", "TOKENIZERS_PARALLELISM": "false"})
         .add_local_dir(str(DATA), remote_path="/data")
         .add_local_file(str(HERE / "evaluate.py"), remote_path="/code/evaluate.py"))


@app.function(image=image, gpu="A100-80GB", timeout=60 * 60, volumes={"/vol": vol})
def predict(fold: int, tag: str = "k3_v5w", model_name: str = "Qwen/Qwen3-8B", max_len: int = 8192,
            max_new: int = 1536, batch: int = 8) -> dict:
    import sys
    import time
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer
    sys.path.insert(0, "/code")
    from evaluate import SYSTEM
    t0 = time.time()
    tok = AutoTokenizer.from_pretrained(model_name)
    tok.padding_side = "left"
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    base = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.bfloat16, device_map="auto")
    model = PeftModel.from_pretrained(base, f"/vol/runs/{tag}/fold{fold}/adapter")
    model.eval()
    kw = {"enable_thinking": False} if "enable_thinking" in tok.apply_chat_template.__code__.co_varnames else {}
    rows = [json.loads(l) for l in open(f"/data/fold{fold}_test.jsonl")]
    rows = [r for r in rows if r["task"] == "FORWARD"]
    texts = [tok.apply_chat_template([{"role": "system", "content": SYSTEM}, {"role": "user", "content": r["prompt"]}],
                                     add_generation_prompt=True, tokenize=False, **kw) for r in rows]
    lens = [len(tok(t)["input_ids"]) for t in texts]
    order = sorted(range(len(rows)), key=lambda i: lens[i])
    out = {}
    for s in range(0, len(order), batch):
        idx = order[s:s + batch]
        enc = tok([texts[i] for i in idx], return_tensors="pt", padding=True, truncation=True, max_length=max_len).to(model.device)
        with torch.no_grad():
            gen = model.generate(**enc, max_new_tokens=max_new, do_sample=False, pad_token_id=tok.pad_token_id)
        for j, i in enumerate(idx):
            text = tok.decode(gen[j, enc["input_ids"].shape[1]:], skip_special_tokens=True).strip()
            out[rows[i]["row_id"]] = {"fold": fold, "text": text, "target": rows[i]["target"], "prompt_tokens": lens[i],
                                      "hit_max": int((gen[j, enc["input_ids"].shape[1]:] != tok.pad_token_id).sum()) >= max_new}
        print(f"fold {fold}: {min(s + batch, len(order))}/{len(order)} at {time.time() - t0:.0f}s", flush=True)
    return out


@app.local_entrypoint()
def main(tag: str = "k3_v5w"):
    OUT.mkdir(parents=True, exist_ok=True)
    res = {"tag": tag, "rows": {}}
    for part in predict.map(range(5), kwargs={"tag": tag}):
        res["rows"].update(part)
    (OUT / f"model_forward_{tag}.json").write_text(json.dumps(res, indent=1))
    n = len(res["rows"])
    print(f"{n} rows; exact {sum(v['text'] == v['target'] for v in res['rows'].values())}; hit max {sum(v['hit_max'] for v in res['rows'].values())}")
