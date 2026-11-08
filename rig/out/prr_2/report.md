# Pilot run: 3/3 rows done, sandbox 1.85 h ≈ 1.41 USD at 0.76/h
- snapshot: n=10 median=123s mean=125s max=202s (estimate was ~120 s)
- fresh start: n=24 median=34s mean=44s max=69s
- candidate (reset to S' + undo + judge): n=16 median=249s mean=292s max=788s
- row: n=3 median=2411s mean=2381s max=4026s (estimate was ~20 min = 1200 s)
- budget 55, blind 40, row cap 60 min, mask 9a1602b2c845, rules c81de9c8811b+settle60i60
- labels: {'REVERSIBLE': 2, 'NO-UNDO-FOUND': 1}; flipped 0; replays 1
- guess B zero-shot undo: 0/1 executed undos restored S
- Ctrl+Z alone undoes 1/2 rows

| row | spot | band | on_task | label | undo | tier | budget | guess A | guess B | row s |
|---|---|---|---|---|---|---|---|---|---|---|
| pr-0003 | rm_held_open_vs_closed | pair | False | REVERSIBLE | focus:doc ; key:ctrl+s ; wait:2 | D | 5 | False | True | 2411.1 |
| pr-0017 | truncate_empty_vs_text | pair | False | REVERSIBLE | - | 0 | 0 | True | True | 706.4 |
| pr-0022 | git_checkout_clean_vs_dirty | pair | False | NO-UNDO-FOUND | - | None | 11 | False | False | 4025.5 |
