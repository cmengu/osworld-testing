"""Live guard for the step 5 pilot (7 Nov 2026, author: "step 1-3 then"): the trained Model-E (k3_v6w, five fold
adapters, mean of the five as in the offline agent-step scores) answers GUARD and REVERSIBLE for one agent step.
Deployed once, called per step from rig/guard_live.py; one L4 GPU (~0.8 USD/h), kept warm 10 min after the last
call, nothing billed when idle.  TEST ONLY use: the pilot's tasks are OS-Harm tasks; nothing here trains.

    OSWorld/.venv/bin/modal deploy rig/train/modal_guard_serve.py
    OSWorld/.venv/bin/modal app stop osguard-guard          # when the pilot is over
"""
import pathlib

import modal

HERE = pathlib.Path(__file__).parent
TAG = "k3_v6w"
app = modal.App("osguard-guard")
vol = modal.Volume.from_name("osguard-train")
image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install_from_requirements(str(HERE / "requirements.txt"))
         .env({"HF_HOME": "/vol/hf", "TOKENIZERS_PARALLELISM": "false"})
         .add_local_file(str(HERE / "evaluate.py"), remote_path="/code/evaluate.py"))


@app.cls(image=image, gpu="L4", timeout=20 * 60, volumes={"/vol": vol}, scaledown_window=600, max_containers=1)
class Guard:
    @modal.enter()
    def load(self):
        import sys
        import torch
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer
        sys.path.insert(0, "/code")
        from evaluate import SYSTEM
        self.torch, self.SYSTEM = torch, SYSTEM
        self.tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-8B")
        base = AutoModelForCausalLM.from_pretrained("Qwen/Qwen3-8B", torch_dtype=torch.bfloat16, device_map="auto")
        self.model = PeftModel.from_pretrained(base, f"/vol/runs/{TAG}/fold0/adapter", adapter_name="fold0")
        for f in range(1, 5):
            self.model.load_adapter(f"/vol/runs/{TAG}/fold{f}/adapter", adapter_name=f"fold{f}")
        self.model.eval()

    def _prob(self, prompt, pos, neg, max_len=8192):
        torch, tok = self.torch, self.tok
        msgs = [{"role": "system", "content": self.SYSTEM}, {"role": "user", "content": prompt}]
        kw = {"enable_thinking": False} if "enable_thinking" in tok.apply_chat_template.__code__.co_varnames else {}
        enc = tok.apply_chat_template(msgs, add_generation_prompt=True, return_tensors="pt", **kw)
        ids = (enc if torch.is_tensor(enc) else enc["input_ids"]).to(self.model.device)[:, -max_len:]
        with torch.no_grad():
            p = torch.softmax(self.model(ids).logits[0, -1].float(), -1)
        a, b = (float(p[tok(o, add_special_tokens=False)["input_ids"][0]]) for o in (pos, neg))
        return round(a / max(1e-9, a + b), 4)

    @modal.method()
    def score(self, guard_prompt: str, reversible_prompt: str) -> dict:
        out = {"tag": TAG, "guard_refuse": [], "reversible_yes": []}
        for f in range(5):
            self.model.set_adapter(f"fold{f}")
            out["guard_refuse"].append(self._prob(guard_prompt, "refuse", "allow"))
            out["reversible_yes"].append(self._prob(reversible_prompt, "yes", "no"))
        return out
