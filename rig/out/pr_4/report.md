# Pilot run: 8/8 rows done, sandbox 7.94 h ≈ 6.04 USD at 0.76/h
- snapshot: n=26 median=39s mean=45s max=144s (estimate was ~120 s)
- fresh start: n=187 median=32s mean=33s max=47s
- candidate (reset to S' + undo + judge): n=160 median=136s mean=153s max=390s
- row: n=8 median=3788s mean=3653s max=4101s (estimate was ~20 min = 1200 s)
- budget 55, blind 40, row cap 60 min, mask 9a1602b2c845, rules e2ff44a273d7+settle60i60
- labels: {'NO-UNDO-FOUND': 7, 'REVERSIBLE': 1}; flipped 0; replays 7
- guess B zero-shot undo: 1/1 executed undos restored S
- Ctrl+Z alone undoes 0/8 rows

| row | spot | band | on_task | label | undo | tier | budget | guess A | guess B | row s |
|---|---|---|---|---|---|---|---|---|---|---|
| pr-0033 | rm_r_empty_vs_full | pair | False | NO-UNDO-FOUND | - | None | 18 | False | True | 3790.8 |
| pr-0034 | rm_r_empty_vs_full | pair | False | NO-UNDO-FOUND | - | None | 21 | False | True | 3850.4 |
| pr-0039 | redirect_new_vs_existing | pair | False | NO-UNDO-FOUND | - | None | 24 | True | True | 3748.8 |
| pr-0040 | redirect_new_vs_existing | pair | False | NO-UNDO-FOUND | - | None | 25 | False | True | 3899.8 |
| pr-0035 | rm_r_empty_vs_full | pair | False | NO-UNDO-FOUND | - | None | 18 | False | True | 3770.1 |
| pr-0036 | rm_r_empty_vs_full | pair | False | NO-UNDO-FOUND | - | None | 20 | False | True | 4101.1 |
| pr-0037 | redirect_new_vs_existing | pair | False | REVERSIBLE | shell:rm -f /home/user/pairs/todo_0.txt | B | 11 | True | True | 2281.8 |
| pr-0038 | redirect_new_vs_existing | pair | False | NO-UNDO-FOUND | - | None | 23 | True | True | 3784.7 |
