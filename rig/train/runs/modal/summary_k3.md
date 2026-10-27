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

## Learning curve (fold 0, same 37 test rows, 3 epochs, seed 2026 subsets by row id)

| Train rows | Lines | Steps | REVERSIBLE P / R / F1 | GUARD P / R / F1 | UNDO exact match | eval loss |
|---|---|---|---|---|---|---|
| 50 | 167 | 63 | 0.703 / 1.000 / **0.825** | 0.000 / 0.000 / **0.000** | 0.60 (n=20) | 0.454 |
| 100 | 333 | 126 | 0.839 / 1.000 / **0.912** | 0.583 / 0.636 / **0.609** | 0.70 (n=20) | 0.325 |
| 148 (all) | 507 | 192 | 0.867 / 1.000 / **0.929** | 0.750 / 0.818 / **0.783** | 0.65 (n=20) | 0.241 |

At 50 rows the model answers "yes" to every REVERSIBLE question (precision = the 70% base rate) and never refuses on GUARD: the classifier has not started. Between 50 and 100 rows it turns, and from 100 to 148 GUARD still gains 0.17 F1, so the curve has not flattened at the current data size. UNDO (the step-language undo sequence) is learned from 50 rows already. Files: `k3_rows50/fold0.json`, `k3_rows100/fold0.json`.

## Second seed (K=3, seed 7, same folds and settings)

| | REVERSIBLE pooled P / R / F1 | REVERSIBLE F1 mean ± sd | GUARD pooled P / R / F1 | GUARD F1 mean ± sd | UNDO exact match |
|---|---|---|---|---|---|
| seed 2026 | 0.916 / 0.952 / **0.934** | 0.929 ± 0.042 | 0.786 / 0.688 / **0.733** | 0.678 ± 0.198 | 55/101 = 0.545 |
| seed 7 | 0.891 / 0.968 / **0.928** | 0.922 ± 0.056 | 0.833 / 0.729 / **0.778** | 0.736 ± 0.158 | 62/101 = 0.614 |
| two seeds | **0.931 ± 0.003** | | **0.756 ± 0.023** | | 0.58 ± 0.03 |

Per fold (seed 7): REV F1 0.945 / 0.951 / 0.913 / 0.818 / 0.982; GUARD F1 0.600 / 0.500 / 0.815 / 0.857 / 0.909; UNDO 0.70 / 0.52 / 0.68 / 0.38 / 0.76. Seed-to-seed movement on GUARD (0.045 pooled, up to 0.18 on one fold) is of the same size as the fold spread: with 3 to 15 refuse rows per fold single-fold GUARD numbers are not stable, pooled ones are. Files `k3_seed7/fold*.json`, `compare_k3_seed7.json`.

## K=1 ablation (label = an undo of at most one action; same folds, seed 2026)

Targets change with K: yes 106 / no 70 (K=3: 126 / 50), refuse 66 / allow 110 (K=3: 48 / 128). The teacher is re-scored against the K=1 labels on the same covered rows.

| | REVERSIBLE pooled P / R / F1 | REVERSIBLE F1 mean ± sd | GUARD pooled P / R / F1 | GUARD F1 mean ± sd | UNDO exact match |
|---|---|---|---|---|---|
| Model, K=1 | 0.710 / 0.877 / **0.785** | 0.783 ± 0.117 | 0.857 / 0.364 / **0.511** | 0.469 ± 0.145 | 60/101 = 0.594 |
| Teacher A on K=1 labels | | 0.768 ± 0.106 | | 0.606 ± 0.199 | |
| Teacher B on K=1 labels | | 0.860 ± 0.068 | | 0.651 ± 0.214 | |
| Model, K=3 (reference) | 0.916 / 0.952 / 0.934 | 0.929 ± 0.042 | 0.786 / 0.688 / 0.733 | 0.678 ± 0.198 | 0.545 |

K=1 is a harder and noisier target for the model and for both teacher prompts alike (teacher B drops from 0.96 to 0.86 on REVERSIBLE and from 0.89 to 0.65 on GUARD): whether an undo takes one action or two (Ctrl+Z then Ctrl+Home; Escape then Escape) is a property of the application's key routes, not of the action's safety. Fold 3 (13 yes of 35) collapses to REV F1 0.553. K=3 stays the main label. Files `k1/fold*.json`, `compare_k1.json`.

## Decision threshold

Leave-one-fold-out tuning of the first-token threshold on the K=3 seed-2026 curves (grid 0.05 to 0.95): REVERSIBLE picks 0.25 to 0.60 by fold and scores 0.919 pooled, below the 0.934 at the default 0.5; GUARD picks 0.20 to 0.35 and scores 0.755 pooled (precision 0.69, recall 0.83) against 0.733 at 0.5. The paper keeps 0.5 and footnotes the tuned GUARD number; the operating point of a deployed guard is a recall-vs-false-refusal choice that the live evaluation, not this table, should set.

## More one-way rows (v3 export, 27 Oct; K=3, seed 2026, five folds)

The v3 batch of 26-27 Oct added one-way rows (shell overwrites, Save As over another document, VS Code Don't Save and Save As replace, Files replace and empty trash, Thunderbird permanent delete) to the training set: 269 rows against 186, refuse rows 102 against 48 (`data_k3_v3`, sha 870d9cefd208; 24 of its rows were still rerunning when this was trained, and the task-grouped folds were drawn afresh, so the test sets differ from the 26 Oct ones). Per fold:

| Fold | Rows | REVERSIBLE P / R / F1 | Refuse rows | GUARD P / R / F1 | UNDO exact match |
|---|---|---|---|---|---|
| 0 | 53 | 0.967 / 0.906 / 0.935 | 21 | 0.952 / 0.952 / 0.952 | 0.692 (n=26) |
| 1 | 52 | 0.906 / 1.000 / 0.951 | 23 | 0.909 / 0.870 / 0.889 | 0.652 (n=23) |
| 2 | 46 | 0.897 / 0.897 / 0.897 | 16 | 0.875 / 0.875 / 0.875 | 0.593 (n=27) |
| 3 | 53 | 0.912 / 0.969 / 0.939 | 20 | 0.783 / 0.900 / 0.837 | 0.520 (n=25) |
| 4 | 53 | 0.935 / 0.967 / 0.951 | 22 | 0.905 / 0.864 / 0.884 | 0.739 (n=23) |

Pooled, and split by whether a row was already in the 26 Oct export (`compare_subsets.py`, since the fold mix changed):

| Rows scored | n | REVERSIBLE P / R / F1 | Refuse rows | GUARD P / R / F1 |
|---|---|---|---|---|
| all (new folds) | 257 | 0.923 / 0.947 / **0.935** | 102 | 0.883 / 0.892 / **0.888** |
| the 176 rows of the 26 Oct export (like for like) | 176 | 0.932 / 0.976 / **0.953** | 48 | 0.872 / 0.854 / **0.863** |
| the 81 new v3 rows | 81 | 0.875 / 0.808 / 0.840 | 54 | 0.893 / 0.926 / 0.909 |
| 26 Oct model on the same 176 rows (reference) | 176 | 0.916 / 0.952 / 0.934 | 48 | 0.786 / 0.688 / 0.733 |

Means over folds: REVERSIBLE 0.935 ± 0.020, GUARD 0.887 ± 0.037, UNDO 0.639 ± 0.076 (pooled 79/124 = 0.637). Against the teacher on the covered rows (`compare_k3_v3pre.json`): model GUARD 0.893 ± 0.043, teacher B 0.896 ± 0.020, teacher A 0.771 ± 0.088; model REVERSIBLE 0.929 ± 0.025, teacher B 0.922 ± 0.017, teacher A 0.793 ± 0.053.

Reading: doubling the refuse rows lifted GUARD from 0.733 to 0.863 on the very rows it was scored on before (+0.13; the two-seed reference was 0.756 ± 0.023), and to 0.888 pooled over the larger set, with REVERSIBLE unchanged; the 8B student now matches the Claude teacher (guess B) on both questions. GUARD was limited by the number of one-way examples, as the learning curve suggested, which is the case for the 3,000-row collection. One seed so far; the post-rerun export gets a second seed. Files `k3_v3pre/fold*.json`, `subsets_k3_v3pre.json`, `compare_k3_v3pre.json`.
