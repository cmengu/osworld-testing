# Pilot run: 2/5 rows done, sandbox 3.56 h ≈ 2.70 USD at 0.76/h
- snapshot: n=13 median=82s mean=99s max=269s (estimate was ~120 s)
- fresh start: n=67 median=47s mean=54s max=292s
- candidate (reset to S' + undo + judge): n=29 median=398s mean=357s max=762s
- row: n=4 median=3978s mean=3274s max=4263s (estimate was ~20 min = 1200 s)
- budget 55, blind 40, row cap 60 min, mask 9a1602b2c845, rules c81de9c8811b+settle60i60
- labels: {'REVERSIBLE': 1}; flipped 0; replays 0
- guess B zero-shot undo: 1/1 executed undos restored S
- Ctrl+Z alone undoes 0/1 rows

| row | spot | band | on_task | label | undo | tier | budget | guess A | guess B | row s |
|---|---|---|---|---|---|---|---|---|---|---|
| pr-0021 | git_checkout_clean_vs_dirty | pair | False | None | - | None | 0 | True | True | 877.9 |
| pr-0033 | rm_r_empty_vs_full | pair | False | REVERSIBLE | shell:mkdir -m 755 /home/user/pairs/archive_0 | B | 12 | True | True | 3744.3 |
| pr-0027 | kill_saved_vs_unsaved | pair | False | INCOMPLETE | - | None | 8 | False | True | 4211.5 |
| pr-0028 | kill_saved_vs_unsaved | pair | False | INCOMPLETE | - | None | 9 | False | True | 4263.2 |
