# Training bundle: Qwen3-8B LoRA on the executed-reversibility rows

What the paper's setup section fixes: Qwen3-8B, LoRA rank 16 to 64, bf16, one A100-40G (or Nebius H200), text only,
inputs capped near 8K tokens; four tagged tasks over one set of weights (FORWARD, UNDO, REVERSIBLE, GUARD); the guard
target is one-way AND off-task.

## 1. Export the rows (no GPU)

    OSWorld/.venv/bin/python -I rig/train/export.py --k 3 --out rig/train/data \
        rig/out/pilot_run2 rig/out/pilot150_a rig/out/pilot150_b rig/out/pilot150_c rig/out/probe_run rig/out/v2_a rig/out/v2_b rig/out/v2_c

    # 27 Oct: data_k3 (186 rows, sha 1760d60ea62e) = the 20 directories pilot_run2 pilot150_a..c probe_run v2_a..c rv_a..c rx_a
    # gd_a..c cf_a cf_b cf_c cf_f cf_g in that order; data_k3_v3 (269 rows, sha 870d9cefd208) adds s3_a s3_c c3_a..f after them
    # (s3_b stays out: wrong VS Code dialog code); the r3_a..f rerun directories go last once the rerun is over.

Writes `all.jsonl` (one line per row and task), `fold{0..4}_{train,test}.jsonl` (grouped by OSWorld task, so a
workbook never straddles the split) and `summary.json`.  Rows labelled UNCONFIRMED or unlabelled are left out of
REVERSIBLE and GUARD.  `--k` sets the main label: the paper pre-registers K = 2 or 3; Part 5 of the pilot tab says
K = 1.  Export both and report both.

## 2. Zero-shot baseline from the recorded teacher guesses (no GPU)

    OSWorld/.venv/bin/python -I rig/train/evaluate.py --test rig/train/data/fold0_test.jsonl \
        --teacher rig/out/pilot_run2 rig/out/pilot150_a rig/out/pilot150_b rig/out/pilot150_c rig/out/probe_run rig/out/v2_a rig/out/v2_b rig/out/v2_c

Guess A is the SafePred prompt, guess B the definition-matched prompt, both Claude Opus 5.5 answers recorded with
each row before the action ran.  This is the "guessed labels" side of the paper's comparison.

## 3. Train (GPU box)

    pip install -r rig/train/requirements.txt
    for f in 0 1 2 3 4; do
      python rig/train/train_lora.py --train rig/train/data/fold${f}_train.jsonl --eval rig/train/data/fold${f}_test.jsonl \
          --model Qwen/Qwen3-8B --rank 32 --epochs 3 --out runs/fold${f}
      python rig/train/evaluate.py --test rig/train/data/fold${f}_test.jsonl --adapter runs/fold${f}/adapter --out runs/fold${f}/scores.json
    done

`--dry` on the training script tokenises with the model's tokenizer and prints the length distribution without
downloading weights beyond the tokenizer.  Five folds of about 150 rows each take a few hours on one A100.
With ~150 rows the result is a trend with cross-validation intervals, not a tight number; say so in the write-up.

## 4. What to report

Per fold and pooled: REVERSIBLE and GUARD precision, recall, F1 and the precision-recall curve (from `_curves`),
against the two teacher baselines on the same rows; UNDO exact match, and the rollback rate once the predicted undos
are executed by the collector (`forced_candidates` on a rerun of the test rows).
