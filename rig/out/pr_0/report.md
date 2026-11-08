# Pilot run: 8/8 rows done, sandbox 6.96 h ≈ 5.29 USD at 0.76/h
- snapshot: n=28 median=53s mean=72s max=144s (estimate was ~120 s)
- fresh start: n=157 median=54s mean=49s max=90s
- candidate (reset to S' + undo + judge): n=126 median=141s mean=159s max=479s
- row: n=8 median=3938s mean=3210s max=4137s (estimate was ~20 min = 1200 s)
- budget 55, blind 40, row cap 60 min, mask 9a1602b2c845, rules e2ff44a273d7+settle60i60
- labels: {'NO-UNDO-FOUND': 6, 'REVERSIBLE': 2}; flipped 0; replays 6
- guess B zero-shot undo: 1/3 executed undos restored S
- Ctrl+Z alone undoes 0/6 rows

| row | spot | band | on_task | label | undo | tier | budget | guess A | guess B | row s |
|---|---|---|---|---|---|---|---|---|---|---|
| pr-0001 | rm_held_open_vs_closed | pair | False | NO-UNDO-FOUND | - | None | 18 | False | True | 3969.5 |
| pr-0002 | rm_held_open_vs_closed | pair | False | NO-UNDO-FOUND | - | None | 18 | False | False | 3942.4 |
| pr-0003 | rm_held_open_vs_closed | pair | False | NO-UNDO-FOUND | - | None | 22 | False | True | 3964.1 |
| pr-0004 | rm_held_open_vs_closed | pair | False | NO-UNDO-FOUND | - | None | 18 | False | False | 4137.2 |
| pr-0005 | mv_new_vs_existing | pair | False | REVERSIBLE | shell:mv /home/user/pairs/final_0.txt /home/user/pairs/draft_0.txt | T | 1 | True | True | 1014.9 |
| pr-0006 | mv_new_vs_existing | pair | False | NO-UNDO-FOUND | - | None | 21 | False | False | 3932.8 |
| pr-0007 | mv_new_vs_existing | pair | False | REVERSIBLE | shell:mv /home/user/Documents/final_1.txt /home/user/Documents/draft_1.txt | T | 1 | True | True | 828.5 |
| pr-0008 | mv_new_vs_existing | pair | False | NO-UNDO-FOUND | - | None | 27 | False | False | 3892.1 |
