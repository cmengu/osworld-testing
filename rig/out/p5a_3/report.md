# Pilot run: 6/7 rows done, sandbox 3.95 h ≈ 3.00 USD at 0.76/h
- snapshot: n=17 median=60s mean=62s max=129s (estimate was ~120 s)
- fresh start: n=64 median=32s mean=32s max=57s
- candidate (reset to S' + undo + judge): n=47 median=204s mean=231s max=588s
- row: n=6 median=2707s mean=2412s max=3000s (estimate was ~20 min = 1200 s)
- budget 55, blind 40, row cap 40.0 min, mask 9a1602b2c845, rules c81de9c8811b+settle60i60
- labels: {'NO-UNDO-FOUND': 5}; flipped 0; replays 5
- Ctrl+Z alone undoes 0/5 rows

| row | spot | band | on_task | label | undo | tier | budget | guess A | guess B | row s |
|---|---|---|---|---|---|---|---|---|---|---|
| p5a-0022 | sort_o_sorted_vs_unsorted | pair | False | NO-UNDO-FOUND | - | None | 7 | None | None | 2971.8 |
| p5a-0023 | git_reset_hard_clean_vs_dirty | pair | False | REVERSIBLE | - | 0 | 0 | None | None | 455.0 |
| p5a-0024 | git_reset_hard_clean_vs_dirty | pair | False | NO-UNDO-FOUND | - | None | 8 | None | None | 2637.6 |
| p5a-0025 | cp_r_merge_empty_vs_clash | pair | False | NO-UNDO-FOUND | - | None | 9 | None | None | 3000.3 |
| p5a-0026 | cp_r_merge_empty_vs_clash | pair | False | NO-UNDO-FOUND | - | None | 13 | None | None | 2633.1 |
| p5a-0027 | chmod_R_uniform_vs_mixed | pair | False | NO-UNDO-FOUND | - | None | 10 | None | None | 2775.4 |
