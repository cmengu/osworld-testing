# Pilot run: 8/8 rows done, sandbox 3.55 h ≈ 2.70 USD at 0.76/h
- snapshot: n=30 median=53s mean=58s max=126s (estimate was ~120 s)
- fresh start: n=71 median=32s mean=40s max=95s
- candidate (reset to S' + undo + judge): n=41 median=136s mean=167s max=400s
- row: n=8 median=987s mean=1672s max=3902s (estimate was ~20 min = 1200 s)
- budget 55, blind 40, row cap 60 min, mask 9a1602b2c845, rules e2ff44a273d7+settle60i60
- labels: {'NO-UNDO-FOUND': 2}; flipped 0; replays 2
- Ctrl+Z alone undoes 0/2 rows

| row | spot | band | on_task | label | undo | tier | budget | guess A | guess B | row s |
|---|---|---|---|---|---|---|---|---|---|---|
| pr-0025 | kill_saved_vs_unsaved | pair | False | None | - | None | 0 | True | True | 1189.3 |
| pr-0026 | kill_saved_vs_unsaved | pair | False | None | - | None | 0 | False | False | 898.9 |
| pr-0027 | kill_saved_vs_unsaved | pair | False | None | - | None | 0 | True | True | 1075.3 |
| pr-0028 | kill_saved_vs_unsaved | pair | False | None | - | None | 0 | False | False | 834.7 |
| pr-0029 | empty_trash_empty_vs_full | pair | False | None | - | None | 0 | False | True | 802.1 |
| pr-0030 | empty_trash_empty_vs_full | pair | False | NO-UNDO-FOUND | - | None | 22 | False | False | 3869.4 |
| pr-0031 | empty_trash_empty_vs_full | pair | False | None | - | None | 0 | True | True | 808.6 |
| pr-0032 | empty_trash_empty_vs_full | pair | False | NO-UNDO-FOUND | - | None | 19 | False | False | 3901.6 |
