"""The trained model's undo plan for every UNDO row of the v3 export (3 November 2026), each from the adapter whose
fold held that row out, so no plan comes from a model that saw the row.  Greedy decoding, 64 new tokens, as
evaluate.py scores exact match.  The plans are executed by the rig in --plans-only mode (H3 rollback comparison).

    OSWorld/.venv/bin/modal run rig/train/modal_predict_undo.py      # -> rig/out/undo_eval/model_plans.json
"""
import json
import pathlib

import modal

HERE = pathlib.Path(__file__).parent
OUT = HERE.parent / "out" / "undo_eval"
DATA = HERE / "data_k3_v3"
app = modal.App("osguard-predict-undo")
vol = modal.Volume.from_name("osguard-train")
image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install_from_requirements(str(HERE / "requirements.txt"))
         .env({"HF_HOME": "/vol/hf", "TOKENIZERS_PARALLELISM": "false"})
         .add_local_dir(str(DATA), remote_path="/data")
         .add_local_file(str(HERE / "evaluate.py"), remote_path="/code/evaluate.py"))


@app.function(image=image, gpu="A100-80GB", timeout=30 * 60, volumes={"/vol": vol})
def predict(model_name: str = "Qwen/Qwen3-8B", tag: str = "k3_v3", max_len: int = 8192) -> dict:
    import sys
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer
    sys.path.insert(0, "/code")
    from evaluate import SYSTEM
    tok = AutoTokenizer.from_pretrained(model_name)
    base = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.bfloat16, device_map="auto")
    model = PeftModel.from_pretrained(base, f"/vol/runs/{tag}/fold0/adapter", adapter_name="fold0")
    for f in range(1, 5):
        model.load_adapter(f"/vol/runs/{tag}/fold{f}/adapter", adapter_name=f"fold{f}")
    model.eval()
    kw = {"enable_thinking": False} if "enable_thinking" in tok.apply_chat_template.__code__.co_varnames else {}
    out = {"tag": tag, "model": model_name, "rows": {}}
    for f in range(5):
        model.set_adapter(f"fold{f}")
        rows = [json.loads(l) for l in open(f"/data/fold{f}_test.jsonl")]
        for r in rows:
            if r["task"] != "UNDO":
                continue
            msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": r["prompt"]}]
            enc = tok.apply_chat_template(msgs, add_generation_prompt=True, return_tensors="pt", **kw)
            ids = (enc if torch.is_tensor(enc) else enc["input_ids"]).to(model.device)[:, -max_len:]
            with torch.no_grad():
                gen = model.generate(ids, max_new_tokens=64, do_sample=False)
            text = tok.decode(gen[0, ids.shape[1]:], skip_special_tokens=True).strip()
            out["rows"][r["row_id"]] = {"fold": f, "text": text, "target": r["target"]}
        print(f"fold {f}: {sum(1 for v in out['rows'].values() if v['fold'] == f)} rows", flush=True)
    return out


@app.local_entrypoint()
def main(tag: str = "k3_v3"):
    OUT.mkdir(parents=True, exist_ok=True)
    res = predict.remote(tag=tag)
    (OUT / "model_plans.json").write_text(json.dumps(res, indent=1))
    n = len(res["rows"])
    em = sum(v["text"] == v["target"] for v in res["rows"].values())
    print(f"{n} rows; exact match with the rig's undo {em} of {n}")
