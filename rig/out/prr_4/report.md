# Pilot run: 4/4 rows done, sandbox 2.40 h ≈ 1.82 USD at 0.76/h
- snapshot: n=12 median=72s mean=63s max=88s (estimate was ~120 s)
- fresh start: n=49 median=66s mean=64s max=108s
- candidate (reset to S' + undo + judge): n=36 median=166s mean=174s max=351s
- row: n=4 median=2338s mean=2229s max=3955s (estimate was ~20 min = 1200 s)
- budget 55, blind 40, row cap 60 min, mask 9a1602b2c845, rules c81de9c8811b+settle60i60
- labels: {'REVERSIBLE': 1, 'NO-UNDO-FOUND': 2}; flipped 0; replays 2
- guess B zero-shot undo: 0/2 executed undos restored S
- Ctrl+Z alone undoes 1/3 rows

| row | spot | band | on_task | label | undo | tier | budget | guess A | guess B | row s |
|---|---|---|---|---|---|---|---|---|---|---|
| pr-0019 | git_checkout_clean_vs_dirty | pair | False | None | - | None | 0 | True | True | 779.4 |
| pr-0031 | empty_trash_empty_vs_full | pair | False | REVERSIBLE | - | 0 | 0 | True | True | 285.4 |
| pr-0025 | kill_saved_vs_unsaved | pair | False | NO-UNDO-FOUND | - | None | 18 | True | True | 3897.1 |
| pr-0026 | kill_saved_vs_unsaved | pair | False | NO-UNDO-FOUND | - | None | 18 | False | True | 3955.2 |
