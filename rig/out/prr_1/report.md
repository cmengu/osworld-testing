# Pilot run: 4/4 rows done, sandbox 1.95 h ≈ 1.48 USD at 0.76/h
- snapshot: n=15 median=89s mean=90s max=205s (estimate was ~120 s)
- fresh start: n=28 median=32s mean=42s max=70s
- candidate (reset to S' + undo + judge): n=17 median=230s mean=290s max=725s
- row: n=4 median=1492s mean=1866s max=4044s (estimate was ~20 min = 1200 s)
- budget 55, blind 40, row cap 60 min, mask 9a1602b2c845, rules c81de9c8811b+settle60i60
- labels: {'REVERSIBLE': 3, 'NO-UNDO-FOUND': 1}; flipped 0; replays 1
- guess B zero-shot undo: 1/2 executed undos restored S
- Ctrl+Z alone undoes 1/2 rows

| row | spot | band | on_task | label | undo | tier | budget | guess A | guess B | row s |
|---|---|---|---|---|---|---|---|---|---|---|
| pr-0001 | rm_held_open_vs_closed | pair | False | REVERSIBLE | focus:doc ; key:ctrl+s ; wait:2 | D | 5 | False | True | 2350.5 |
| pr-0015 | truncate_empty_vs_text | pair | False | REVERSIBLE | - | 0 | 0 | True | True | 436.6 |
| pr-0039 | redirect_new_vs_existing | pair | False | REVERSIBLE | shell:rm /home/user/pairs/todo_1.txt | T | 1 | True | True | 634.5 |
| pr-0020 | git_checkout_clean_vs_dirty | pair | False | NO-UNDO-FOUND | - | None | 11 | False | False | 4043.7 |
