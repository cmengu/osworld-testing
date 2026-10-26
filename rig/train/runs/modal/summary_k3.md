# Qwen3-8B LoRA, K=3, five grouped folds (26 Oct 2026)

Model Qwen/Qwen3-8B, LoRA rank 32, 3 epochs, bf16, one A100-80GB per fold on Modal (`rig/train/modal_train.py`, commit 83e8bc4). Data `rig/train/data_k3` (186 rows, 639 lines, export sha256 1760d60ea62e), folds grouped by OSWorld task id. Scores from `evaluate.py`: REVERSIBLE and GUARD by the first-token probability of the positive answer at threshold 0.5, UNDO by exact match of the generated sequence. Teacher = Claude Opus 5.5 zero-shot at collection time: guess A (SafePred App. G prompt), guess B (definition-matched prompt). The teacher guessed only rows collected with the teacher on (probe rows never were), so model and teacher are also compared on the identical covered rows (`compare_teacher.py`, earliest guess per row).

Wall time per fold 812-1014 s training (192-195 steps, 4-5 s/step) plus ~3 min image/model/eval; folds 1-4 ran in parallel; about 0.7 USD per fold.

## Per fold (model on all rows of the fold)

| Fold | Rows | REVERSIBLE P / R / F1 | GUARD P / R / F1 | UNDO exact match |
|---|---|---|---|---|---|
| 0 | 37 (26 yes, 11 refuse) | 0.867 / 1.000 / **0.929** | 0.750 / 0.818 / **0.783** | 0.65 (n=20) |
| 1 | 33 (30 yes, 3 refuse) | 0.938 / 1.000 / **0.968** | 0.250 / 0.333 / **0.286** | 0.48 (n=25) |
| 2 | 36 (23 yes, 13 refuse) | 1.000 / 0.913 / **0.955** | 0.833 / 0.769 / **0.800** | 0.58 (n=19) |
| 3 | 35 (18 yes, 15 refuse) | 0.773 / 0.944 / **0.850** | 0.900 / 0.600 / **0.720** | 0.38 (n=16) |
| 4 | 35 (29 yes, 6 refuse) | 1.000 / 0.897 / **0.945** | 1.000 / 0.667 / **0.800** | 0.62 (n=21) |

## Model vs teacher on identical rows (rows with a recorded teacher guess)

| Fold | Covered / rows | Model REV F1 | Teacher A REV F1 | Teacher B REV F1 | Model GUARD F1 | Teacher A GUARD F1 | Teacher B GUARD F1 |
|---|---|---|---|---|---|---|---|
| 0 | 20 / 37 | 0.909 | 0.759 | 0.968 | 0.889 | 0.400 | 0.889 |
| 1 | 29 / 33 | 0.964 | 0.902 | 0.963 | 0.000 | 0.500 | 0.667 |
| 2 | 29 / 36 | 0.950 | 0.878 | 0.976 | 0.824 | 0.800 | 0.941 |
| 3 | 31 / 35 | 0.857 | 0.857 | 0.914 | 0.727 | 0.917 | 0.960 |
| 4 | 29 / 35 | 0.958 | 0.857 | 1.000 | 0.667 | 0.545 | 1.000 |

## Pooled over the five folds

Mean and standard deviation of the per-fold F1 (macro), and precision / recall / F1 over all pooled predictions (micro).

| | Rows | REVERSIBLE F1 mean ± sd | REVERSIBLE pooled P / R / F1 | GUARD F1 mean ± sd | GUARD pooled P / R / F1 |
|---|---|---|---|---|---|
| Model, all rows | 176 | 0.929 ± 0.042 | 0.916 / 0.952 / **0.934** | 0.678 ± 0.198 | 0.786 / 0.688 / **0.733** |
| Model, covered rows | 138 | 0.928 ± 0.040 | 0.917 / 0.952 / **0.934** | 0.621 ± 0.320 | 0.778 / 0.656 / **0.712** |
| Teacher A (SafePred prompt) | 136 | 0.851 ± 0.049 | 0.885 / 0.833 / **0.859** | 0.632 ± 0.194 | 0.719 / 0.719 / **0.719** |
| Teacher B (definition prompt) | 138 | 0.964 ± 0.028 | 0.953 / 0.981 / **0.967** | 0.891 ± 0.118 | 0.967 / 0.906 / **0.935** |

UNDO exact match: 55/101 = 0.545 pooled; per fold mean 0.541 ± 0.101.

## Reading

- REVERSIBLE: the 8B student is at 0.93 F1 pooled, between the two teacher prompts (A 0.85, B 0.96); recall is high (it rarely calls a reversible action one-way), precision is where it loses (false 'reversible' on one-way rows: 0.87 and 0.77 in folds 0 and 3).
- GUARD: 0.68 F1 mean, 0.73 pooled, with large fold-to-fold spread driven by the small number of refuse rows per fold (3 to 15). Fold 1 has 3 refuse rows and the model found 1. Teacher B at 0.89 is clearly better on GUARD; teacher A is at the model's level. 48 refuse rows in total is the limiting factor: GUARD is the task that needs more one-way data.
- UNDO: 0.54 exact match on the reversible rows; the model reproduces the collector's shortest undo about half the time (no credit for an equivalent but different undo; a functional check would need the VM).
- The teacher comparison is on identical rows; the model additionally covers the probe rows (terminal and file actions) where no teacher guess exists.
- Caveats: 186 rows; thresholds not tuned (0.5); one seed; 3 epochs with no early stopping (eval loss 0.24-0.31). Learning-curve runs (fold 0 train at 50 and 100 rows) follow in `k3_rows50`, `k3_rows100`.
