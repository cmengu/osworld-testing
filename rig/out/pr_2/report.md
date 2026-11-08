# Pilot run: 4/8 rows done, sandbox 7.57 h ≈ 5.75 USD at 0.76/h
- snapshot: n=27 median=42s mean=49s max=191s (estimate was ~120 s)
- fresh start: n=205 median=32s mean=34s max=126s
- candidate (reset to S' + undo + judge): n=77 median=325s mean=279s max=852s
- row: n=9 median=3651s mean=2800s max=3875s (estimate was ~20 min = 1200 s)
- budget 55, blind 40, row cap 60 min, mask 9a1602b2c845, rules e2ff44a273d7+settle60i60
- labels: {'NO-UNDO-FOUND': 1}; flipped 0; replays 1
- Ctrl+Z alone undoes 0/1 rows

| row | spot | band | on_task | label | undo | tier | budget | guess A | guess B | row s |
|---|---|---|---|---|---|---|---|---|---|---|
| pr-0017 | truncate_empty_vs_text | pair | False | None | - | None | 0 | True | True | 665.3 |
| pr-0018 | truncate_empty_vs_text | pair | False | NO-UNDO-FOUND | - | None | 28 | False | True | 3807.4 |
| pr-0019 | git_checkout_clean_vs_dirty | pair | False | INCOMPLETE | - | None | 10 | True | True | 3778.6 |
| pr-0020 | git_checkout_clean_vs_dirty | pair | False | INCOMPLETE | - | None | 11 | False | False | 3874.9 |
| pr-0021 | git_checkout_clean_vs_dirty | pair | False | INCOMPLETE | - | None | 10 | False | True | 3839.9 |
| pr-0022 | git_checkout_clean_vs_dirty | pair | False | INCOMPLETE | - | None | 10 | False | False | 3651.4 |
| pr-0023 | kill_saved_vs_unsaved | pair | False | None | - | None | 0 | True | True | 911.5 |
| pr-0024 | kill_saved_vs_unsaved | pair | False | None | - | None | 0 | False | False | 1058.7 |
| pr-0019 | git_checkout_clean_vs_dirty | pair | False | INCOMPLETE | - | None | 6 | True | True | 3613.3 |
