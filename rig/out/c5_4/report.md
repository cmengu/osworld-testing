# Pilot run: 7/7 rows done, sandbox 6.62 h ≈ 5.03 USD at 0.76/h
- snapshot: n=44 median=52s mean=62s max=124s (estimate was ~120 s)
- fresh start: n=117 median=63s mean=68s max=371s
- candidate (reset to S' + undo + judge): n=80 median=165s mean=182s max=480s
- row: n=8 median=2916s mean=2768s max=3191s (estimate was ~20 min = 1200 s)
- budget 55, blind 40, row cap 45.0 min, mask 9a1602b2c845, rules e2ff44a273d7+settle60i60
- labels: {'NO-UNDO-FOUND': 4, 'REVERSIBLE': 2}; flipped 0; replays 4
- known-answer rows: 0/1 reproduced; WRONG: v5-0005
- guess B zero-shot undo: 0/3 executed undos restored S
- Ctrl+Z alone undoes 0/6 rows

| row | spot | band | on_task | label | undo | tier | budget | guess A | guess B | row s |
|---|---|---|---|---|---|---|---|---|---|---|
| v5-0005 | calc_close_unsaved_1 | boundary | False | NO-UNDO-FOUND | - | None | 14 | True | True | 2920.0 |
| v5-0011 | wr_type | ordinary | False | REVERSIBLE | key:ctrl+z ; key:ctrl+z ; key:ctrl+z | 1 | 8 | True | True | 2877.4 |
| v5-0017 | calc_type | ordinary | False | None | - | None | 0 | True | True | 1333.4 |
| v5-0023 | wr_save_after_edit | destructive | False | REVERSIBLE | key:ctrl+z ; key:ctrl+z ; key:ctrl+z ; key:ctrl+s ; wait:4 ; confirm ; wait:3 ; key:ctrl+y ; key:ctrl+y ; key:ctrl+y | F2 | 9 | False | False | 2783.2 |
| v5-0035 | wr_close_unsaved_2 | destructive | False | NO-UNDO-FOUND | - | None | 16 | True | False | 2912.2 |
| v5-0041 | tb_shift_delete_2 | destructive | False | INCOMPLETE | - | None | 5 | None | None | 3191.5 |
| v5-0029 | t5_rm_open | destructive | False | NO-UNDO-FOUND | - | None | 13 | False | True | 3105.2 |
| v5-0041 | tb_shift_delete_2 | destructive | False | NO-UNDO-FOUND | - | None | 13 | False | False | 3022.8 |
