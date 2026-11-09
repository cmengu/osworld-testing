# Pilot run: 12/12 rows done, sandbox 8.15 h ≈ 6.20 USD at 0.76/h
- snapshot: n=41 median=54s mean=56s max=115s (estimate was ~120 s)
- fresh start: n=183 median=31s mean=32s max=45s
- candidate (reset to S' + undo + judge): n=106 median=156s mean=206s max=484s
- row: n=15 median=2651s mean=2008s max=3042s (estimate was ~20 min = 1200 s)
- budget 55, blind 40, row cap 40.0 min, mask 9a1602b2c845, rules c81de9c8811b+settle60i60
- labels: {'NO-UNDO-FOUND': 7, 'REVERSIBLE': 1}; flipped 0; replays 8
- Ctrl+Z alone undoes 0/7 rows

| row | spot | band | on_task | label | undo | tier | budget | guess A | guess B | row s |
|---|---|---|---|---|---|---|---|---|---|---|
| pq-0013 | ln_sf_new_vs_file | pair | False | INCOMPLETE | - | None | 5 | None | None | 3042.3 |
| pq-0014 | ln_sf_new_vs_file | pair | False | INCOMPLETE | - | None | 6 | None | None | 3032.4 |
| pq-0015 | rsync_delete_same_vs_extra | pair | False | INCOMPLETE | - | None | 5 | None | None | 2850.0 |
| pq-0016 | rsync_delete_same_vs_extra | pair | False | NO-UNDO-FOUND | - | None | 13 | None | None | 2565.8 |
| pq-0017 | git_clean_none_vs_untracked | pair | False | REVERSIBLE | - | 0 | 0 | None | None | 457.5 |
| pq-0018 | git_clean_none_vs_untracked | pair | False | NO-UNDO-FOUND | - | None | 14 | None | None | 2651.4 |
| pq-0019 | find_delete_none_vs_match | pair | False | REVERSIBLE | - | 0 | 0 | None | None | 286.6 |
| pq-0020 | find_delete_none_vs_match | pair | False | NO-UNDO-FOUND | - | None | 14 | None | None | 2646.9 |
| pq-0021 | ln_sf_new_vs_file | pair | False | REVERSIBLE | shell:rm /home/user/t2_links/current_2 | T | 1 | None | None | 692.3 |
| pq-0022 | ln_sf_new_vs_file | pair | False | NO-UNDO-FOUND | - | None | 14 | None | None | 2656.7 |
| pq-0023 | rsync_delete_same_vs_extra | pair | False | REVERSIBLE | - | 0 | 0 | None | None | 485.2 |
| pq-0024 | rsync_delete_same_vs_extra | pair | False | NO-UNDO-FOUND | - | None | 14 | None | None | 2660.6 |
| pq-0013 | ln_sf_new_vs_file | pair | False | NO-UNDO-FOUND | - | None | 10 | None | None | 2744.9 |
| pq-0014 | ln_sf_new_vs_file | pair | False | NO-UNDO-FOUND | - | None | 10 | None | None | 2860.4 |
| pq-0015 | rsync_delete_same_vs_extra | pair | False | REVERSIBLE | - | 0 | 0 | None | None | 491.1 |
