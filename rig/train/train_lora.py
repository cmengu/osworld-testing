"""LoRA fine-tune of Qwen3-8B on the four tagged tasks (paper draft, setup: rank 16 to 64, bf16, one A100-40G,
a few hours).  Loss on the target tokens only; the prompt is masked.  Works on any CUDA box with ~40 GB; on
Nebius H200 the same command runs.

    pip install -r rig/train/requirements.txt
    python rig/train/train_lora.py --train rig/train/data/fold0_train.jsonl --eval rig/train/data/fold0_test.jsonl \\
        --model Qwen/Qwen3-8B --rank 32 --epochs 3 --out runs/fold0

    python rig/train/train_lora.py --train ... --dry       # tokenise, print lengths, no model download
"""
import argparse
import json
import math
import pathlib
import random

SYSTEM = ("You are a world model of a Linux desktop. States are compact text renderings of the accessibility tree "
          "and the files in the home folder. Actions are keyboard input. Answer in the format the tag asks for.")


def load(path, tasks=None):
    rows = [json.loads(l) for l in pathlib.Path(path).read_text().splitlines() if l.strip()]
    if tasks:
        rows = [r for r in rows if r["task"] in tasks]
    return rows


def encode(tok, row, max_len):
    msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": row["prompt"]}]
    prompt_ids = tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=True, enable_thinking=False) \
        if "enable_thinking" in tok.apply_chat_template.__code__.co_varnames else \
        tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=True)
    target_ids = tok(row["target"] + tok.eos_token, add_special_tokens=False)["input_ids"]
    if len(prompt_ids) + len(target_ids) > max_len:          # keep the whole target, cut the prompt's middle
        keep = max_len - len(target_ids)
        half = keep // 2
        prompt_ids = prompt_ids[:half] + prompt_ids[-(keep - half):]
    ids = prompt_ids + target_ids
    labels = [-100] * len(prompt_ids) + target_ids
    return {"input_ids": ids, "labels": labels, "attention_mask": [1] * len(ids)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", required=True)
    ap.add_argument("--eval", default=None)
    ap.add_argument("--model", default="Qwen/Qwen3-8B")
    ap.add_argument("--tasks", default="FORWARD,UNDO,REVERSIBLE,GUARD")
    ap.add_argument("--rank", type=int, default=32)
    ap.add_argument("--alpha", type=int, default=64)
    ap.add_argument("--dropout", type=float, default=0.05)
    ap.add_argument("--epochs", type=float, default=3)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--max-len", type=int, default=8192)
    ap.add_argument("--batch", type=int, default=1)
    ap.add_argument("--grad-accum", type=int, default=8)
    ap.add_argument("--out", default="runs/lora")
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--dry", action="store_true", help="tokenise with the model's tokenizer and report lengths; no training")
    args = ap.parse_args()
    random.seed(args.seed)
    tasks = set(args.tasks.split(","))
    train = load(args.train, tasks)
    evalrows = load(args.eval, tasks) if args.eval else []
    print(f"train lines {len(train)}, eval lines {len(evalrows)}, tasks {sorted(tasks)}")

    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(args.model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    enc = [encode(tok, r, args.max_len) for r in train]
    lens = sorted(len(e["input_ids"]) for e in enc)
    print(f"token lengths: min {lens[0]} median {lens[len(lens) // 2]} p95 {lens[int(len(lens) * 0.95)]} max {lens[-1]}; "
          f"{sum(1 for l in lens if l >= args.max_len)} at the cap")
    if args.dry:
        return

    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, DataCollatorForSeq2Seq, Trainer, TrainingArguments
    from datasets import Dataset
    model = AutoModelForCausalLM.from_pretrained(args.model, torch_dtype=torch.bfloat16, device_map="auto")
    model.gradient_checkpointing_enable()
    model.enable_input_require_grads()
    lora = LoraConfig(r=args.rank, lora_alpha=args.alpha, lora_dropout=args.dropout, bias="none", task_type="CAUSAL_LM",
                      target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"])
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()
    ds_train = Dataset.from_list(enc)
    ds_eval = Dataset.from_list([encode(tok, r, args.max_len) for r in evalrows]) if evalrows else None
    targs = TrainingArguments(output_dir=args.out, per_device_train_batch_size=args.batch, per_device_eval_batch_size=args.batch,
                              gradient_accumulation_steps=args.grad_accum, num_train_epochs=args.epochs, learning_rate=args.lr,
                              lr_scheduler_type="cosine", warmup_ratio=0.05, bf16=True, logging_steps=5,
                              eval_strategy="epoch" if ds_eval is not None else "no", save_strategy="epoch", save_total_limit=2,
                              report_to="none", seed=args.seed, group_by_length=True)
    trainer = Trainer(model=model, args=targs, train_dataset=ds_train, eval_dataset=ds_eval,
                      data_collator=DataCollatorForSeq2Seq(tok, padding=True, label_pad_token_id=-100))
    trainer.train()
    model.save_pretrained(args.out + "/adapter")
    tok.save_pretrained(args.out + "/adapter")
    if ds_eval is not None:
        m = trainer.evaluate()
        print(json.dumps({"eval_loss": m.get("eval_loss"), "ppl": math.exp(m["eval_loss"]) if m.get("eval_loss") else None}))


if __name__ == "__main__":
    main()
