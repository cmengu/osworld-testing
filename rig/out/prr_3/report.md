# Pilot run: 3/3 rows done, sandbox 2.26 h ≈ 1.72 USD at 0.76/h
- snapshot: n=9 median=68s mean=74s max=107s (estimate was ~120 s)
- fresh start: n=51 median=56s mean=58s max=93s
- candidate (reset to S' + undo + judge): n=43 median=149s mean=148s max=180s
- row: n=3 median=3842s mean=2805s max=3900s (estimate was ~20 min = 1200 s)
- budget 55, blind 40, row cap 60 min, mask 9a1602b2c845, rules c81de9c8811b+settle60i60
- labels: {'NO-UNDO-FOUND': 2, 'REVERSIBLE': 1}; flipped 0; replays 2
- guess B zero-shot undo: 0/2 executed undos restored S
- Ctrl+Z alone undoes 1/3 rows

| row | spot | band | on_task | label | undo | tier | budget | guess A | guess B | row s |
|---|---|---|---|---|---|---|---|---|---|---|
| pr-0023 | kill_saved_vs_unsaved | pair | False | NO-UNDO-FOUND | - | None | 21 | True | True | 3900.1 |
| pr-0024 | kill_saved_vs_unsaved | pair | False | NO-UNDO-FOUND | - | None | 22 | False | True | 3841.8 |
| pr-0029 | empty_trash_empty_vs_full | pair | False | REVERSIBLE | - | 0 | 0 | True | True | 673.2 |
