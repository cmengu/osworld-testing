# Pilot run: 8/8 rows done, sandbox 7.92 h ≈ 6.02 USD at 0.76/h
- snapshot: n=55 median=51s mean=54s max=138s (estimate was ~120 s)
- fresh start: n=164 median=64s mean=67s max=204s
- candidate (reset to S' + undo + judge): n=116 median=150s mean=173s max=446s
- row: n=10 median=2989s mean=2569s max=3176s (estimate was ~20 min = 1200 s)
- budget 55, blind 40, row cap 45.0 min, mask 9a1602b2c845, rules e2ff44a273d7+settle60i60
- labels: {'NO-UNDO-FOUND': 4, 'REVERSIBLE': 4}; flipped 0; replays 7
- known-answer rows: 1/2 reproduced; WRONG: v5-0004
- guess B zero-shot undo: 2/6 executed undos restored S
- Ctrl+Z alone undoes 1/6 rows

| row | spot | band | on_task | label | undo | tier | budget | guess A | guess B | row s |
|---|---|---|---|---|---|---|---|---|---|---|
| v5-0004 | imp_close_unsaved_1 | boundary | False | INCOMPLETE | - | None | 11 | True | True | 3138.7 |
| v5-0010 | tb_shift_delete_1 | boundary | False | INCOMPLETE | - | None | 10 | False | True | 3039.9 |
| v5-0040 | tb_compose_close_2 | destructive | False | NO-UNDO-FOUND | - | None | 12 | True | False | 2981.9 |
| v5-0016 | imp_delete_slide | boundary | False | REVERSIBLE | key:ctrl+z | 1 | 2 | True | True | 1229.1 |
| v5-0022 | wr_save_after_edit | destructive | False | REVERSIBLE | key:ctrl+z ; key:ctrl+z ; key:ctrl+z ; key:ctrl+s ; wait:4 ; confirm ; wait:3 ; key:ctrl+y ; key:ctrl+y ; key:ctrl+y | F2 | 13 | True | True | 2396.4 |
| v5-0028 | t5_rm_open | destructive | False | NO-UNDO-FOUND | - | None | 12 | None | None | 2995.6 |
| v5-0034 | t5_overwrite_open | destructive | False | NO-UNDO-FOUND | - | None | 15 | False | True | 3175.7 |
| v5-0004 | imp_close_unsaved_1 | boundary | False | NO-UNDO-FOUND | - | None | 14 | True | True | 2998.5 |
| v5-0010 | tb_shift_delete_1 | boundary | False | REVERSIBLE | key:escape | W | 1 | False | True | 952.2 |
| v5-0046 | tb_compose_type | ordinary | False | REVERSIBLE | key:alt+f4 ; wait:2 ; click:Discard changes | 2 | 17 | True | True | 2785.6 |
