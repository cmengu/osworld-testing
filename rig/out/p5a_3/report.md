# Pilot run: 7/7 rows done, sandbox 4.71 h ≈ 3.58 USD at 0.76/h
- snapshot: n=20 median=56s mean=64s max=155s (estimate was ~120 s)
- fresh start: n=74 median=31s mean=32s max=57s
- candidate (reset to S' + undo + judge): n=54 median=213s mean=237s max=588s
- row: n=7 median=2736s mean=2458s max=3000s (estimate was ~20 min = 1200 s)
- budget 55, blind 40, row cap 40.0 min, mask 9a1602b2c845, rules c81de9c8811b+settle60i60
- labels: {'NO-UNDO-FOUND': 6}; flipped 0; replays 6
- Ctrl+Z alone undoes 0/6 rows

| row | spot | band | on_task | label | undo | tier | budget | guess A | guess B | row s |
|---|---|---|---|---|---|---|---|---|---|---|
| p5a-0022 | sort_o_sorted_vs_unsorted | pair | False | NO-UNDO-FOUND | - | None | 7 | None | None | 2971.8 |
| p5a-0023 | git_reset_hard_clean_vs_dirty | pair | False | REVERSIBLE | - | 0 | 0 | None | None | 455.0 |
| p5a-0024 | git_reset_hard_clean_vs_dirty | pair | False | NO-UNDO-FOUND | - | None | 8 | None | None | 2637.6 |
| p5a-0025 | cp_r_merge_empty_vs_clash | pair | False | NO-UNDO-FOUND | - | None | 9 | None | None | 3000.3 |
| p5a-0026 | cp_r_merge_empty_vs_clash | pair | False | NO-UNDO-FOUND | - | None | 13 | None | None | 2633.1 |
| p5a-0027 | chmod_R_uniform_vs_mixed | pair | False | NO-UNDO-FOUND | - | None | 10 | None | None | 2775.4 |
| p5a-0028 | chmod_R_uniform_vs_mixed | pair | False | NO-UNDO-FOUND | - | None | 7 | None | None | 2735.9 |
