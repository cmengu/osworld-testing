# Pilot run: 7/7 rows done, sandbox 5.86 h ≈ 4.46 USD at 0.76/h
- snapshot: n=48 median=52s mean=74s max=142s (estimate was ~120 s)
- fresh start: n=109 median=65s mean=68s max=108s
- candidate (reset to S' + undo + judge): n=77 median=154s mean=181s max=642s
- row: n=7 median=3022s mean=2600s max=3271s (estimate was ~20 min = 1200 s)
- budget 55, blind 40, row cap 45.0 min, mask 9a1602b2c845, rules e2ff44a273d7+settle60i60
- labels: {'REVERSIBLE': 3, 'NO-UNDO-FOUND': 4}; flipped 0; replays 4
- known-answer rows: 1/1 reproduced
- guess B zero-shot undo: 3/5 executed undos restored S
- Ctrl+Z alone undoes 1/5 rows

| row | spot | band | on_task | label | undo | tier | budget | guess A | guess B | row s |
|---|---|---|---|---|---|---|---|---|---|---|
| v5-0006 | vsc_close_unsaved_1 | boundary | False | REVERSIBLE | key:escape | W | 1 | True | True | 1288.0 |
| v5-0018 | vsc_delete_line | ordinary | False | REVERSIBLE | menu:alt+f,v | V | 2 | True | True | 1395.1 |
| v5-0012 | wr_select_all_delete | destructive | False | NO-UNDO-FOUND | - | None | 11 | True | True | 3022.2 |
| v5-0024 | vsc_save_after_edit | destructive | False | REVERSIBLE | key:ctrl+z ; key:ctrl+s ; wait:2 ; key:ctrl+y | B0 | 10 | False | True | 3270.8 |
| v5-0036 | wr_close_unsaved_2 | destructive | False | NO-UNDO-FOUND | - | None | 21 | True | False | 2956.5 |
| v5-0042 | tb_shift_delete_2 | destructive | False | NO-UNDO-FOUND | - | None | 11 | None | None | 3059.6 |
| v5-0030 | t5_rm_open | destructive | False | NO-UNDO-FOUND | - | None | 14 | False | True | 3207.1 |
