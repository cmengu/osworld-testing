# Pilot run: 8/8 rows done, sandbox 5.20 h ≈ 3.95 USD at 0.76/h
- snapshot: n=34 median=36s mean=41s max=74s (estimate was ~120 s)
- fresh start: n=104 median=32s mean=33s max=53s
- candidate (reset to S' + undo + judge): n=78 median=166s mean=193s max=571s
- row: n=8 median=2506s mean=2393s max=3918s (estimate was ~20 min = 1200 s)
- budget 55, blind 40, row cap 60 min, mask 9a1602b2c845, rules e2ff44a273d7+settle60i60
- labels: {'REVERSIBLE': 3, 'NO-UNDO-FOUND': 4}; flipped 0; replays 4
- guess B zero-shot undo: 3/3 executed undos restored S
- Ctrl+Z alone undoes 0/4 rows

| row | spot | band | on_task | label | undo | tier | budget | guess A | guess B | row s |
|---|---|---|---|---|---|---|---|---|---|---|
| pr-0009 | mv_new_vs_existing | pair | False | REVERSIBLE | shell:mv /home/user/Desktop/final_2.txt /home/user/Desktop/draft_2.txt | T | 1 | True | True | 1012.4 |
| pr-0010 | mv_new_vs_existing | pair | False | NO-UNDO-FOUND | - | None | 20 | False | False | 3909.5 |
| pr-0013 | cp_new_vs_existing | pair | False | REVERSIBLE | shell:rm /home/user/pairs/report_1.txt | T | 1 | True | True | 600.5 |
| pr-0014 | cp_new_vs_existing | pair | False | NO-UNDO-FOUND | - | None | 22 | False | False | 3877.1 |
| pr-0011 | cp_new_vs_existing | pair | False | REVERSIBLE | shell:rm /home/user/pairs/report_0.txt | T | 2 | True | True | 1218.3 |
| pr-0012 | cp_new_vs_existing | pair | False | NO-UNDO-FOUND | - | None | 17 | False | False | 3918.0 |
| pr-0015 | truncate_empty_vs_text | pair | False | None | - | None | 0 | True | True | 811.5 |
| pr-0016 | truncate_empty_vs_text | pair | False | NO-UNDO-FOUND | - | None | 15 | False | True | 3793.2 |
