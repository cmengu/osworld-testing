# Pilot run: 7/7 rows done, sandbox 4.87 h ≈ 3.70 USD at 0.76/h
- snapshot: n=19 median=63s mean=76s max=180s (estimate was ~120 s)
- fresh start: n=68 median=33s mean=35s max=53s
- candidate (reset to S' + undo + judge): n=48 median=254s mean=267s max=483s
- row: n=7 median=2876s mean=2550s max=3070s (estimate was ~20 min = 1200 s)
- budget 55, blind 40, row cap 40.0 min, mask 9a1602b2c845, rules c81de9c8811b+settle60i60
- labels: {'NO-UNDO-FOUND': 6}; flipped 0; replays 5
- Ctrl+Z alone undoes 0/6 rows

| row | spot | band | on_task | label | undo | tier | budget | guess A | guess B | row s |
|---|---|---|---|---|---|---|---|---|---|---|
| p5a-0008 | sort_o_sorted_vs_unsorted | pair | False | NO-UNDO-FOUND | - | None | 6 | None | None | 2875.6 |
| p5a-0009 | git_reset_hard_clean_vs_dirty | pair | False | REVERSIBLE | - | 0 | 0 | None | None | 429.4 |
| p5a-0010 | git_reset_hard_clean_vs_dirty | pair | False | NO-UNDO-FOUND | - | None | 9 | None | None | 2710.6 |
| p5a-0011 | cp_r_merge_empty_vs_clash | pair | False | NO-UNDO-FOUND | - | None | 9 | None | None | 2950.4 |
| p5a-0012 | cp_r_merge_empty_vs_clash | pair | False | NO-UNDO-FOUND | - | None | 10 | None | None | 2950.6 |
| p5a-0013 | chmod_R_uniform_vs_mixed | pair | False | NO-UNDO-FOUND | - | None | 8 | None | None | 3069.7 |
| p5a-0014 | chmod_R_uniform_vs_mixed | pair | False | NO-UNDO-FOUND | - | None | 6 | None | None | 2861.3 |
