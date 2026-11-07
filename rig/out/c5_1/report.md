# Pilot run: 8/8 rows done, sandbox 5.23 h ≈ 3.98 USD at 0.76/h
- snapshot: n=54 median=46s mean=51s max=132s (estimate was ~120 s)
- fresh start: n=90 median=62s mean=61s max=97s
- candidate (reset to S' + undo + judge): n=61 median=142s mean=157s max=387s
- row: n=8 median=2488s mean=2122s max=3025s (estimate was ~20 min = 1200 s)
- budget 55, blind 40, row cap 45.0 min, mask 9a1602b2c845, rules e2ff44a273d7+settle60i60
- labels: {'REVERSIBLE': 4, 'NO-UNDO-FOUND': 3}; flipped 0; replays 3
- known-answer rows: 2/2 reproduced
- guess B zero-shot undo: 3/4 executed undos restored S
- Ctrl+Z alone undoes 0/5 rows

| row | spot | band | on_task | label | undo | tier | budget | guess A | guess B | row s |
|---|---|---|---|---|---|---|---|---|---|---|
| v5-0002 | wr_close_unsaved_1 | boundary | False | REVERSIBLE | key:escape | W | 1 | True | True | 826.6 |
| v5-0008 | fi_perm_delete_1 | boundary | False | REVERSIBLE | key:escape | 1 | 5 | False | True | 2271.5 |
| v5-0014 | imp_type_title | ordinary | False | NO-UNDO-FOUND | - | None | 11 | True | True | 2876.4 |
| v5-0020 | imp_save_after_edit | destructive | False | None | - | None | 0 | False | True | 1402.2 |
| v5-0026 | calc_save_after_edit | destructive | False | REVERSIBLE | key:ctrl+z ; key:ctrl+s ; wait:4 ; confirm ; wait:3 ; key:ctrl+y | F2 | 10 | False | True | 2704.1 |
| v5-0038 | imp_close_unsaved_2 | destructive | False | NO-UNDO-FOUND | - | None | 16 | True | False | 3014.0 |
| v5-0044 | tb_empty_trash | destructive | False | REVERSIBLE | key:escape | W | 1 | None | None | 853.4 |
| v5-0032 | t5_overwrite_open | destructive | False | NO-UNDO-FOUND | - | None | 17 | None | None | 3025.4 |
