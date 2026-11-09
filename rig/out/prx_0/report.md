# Pilot run: 5/5 rows done, sandbox 3.07 h ≈ 2.33 USD at 0.76/h
- snapshot: n=16 median=64s mean=74s max=108s (estimate was ~120 s)
- fresh start: n=55 median=33s mean=34s max=56s
- candidate (reset to S' + undo + judge): n=41 median=172s mean=204s max=471s
- row: n=5 median=2295s mean=2307s max=4043s (estimate was ~20 min = 1200 s)
- budget 55, blind 40, row cap 60.0 min, mask 9a1602b2c845, rules c81de9c8811b+settle60i60
- labels: {'REVERSIBLE': 3, 'NO-UNDO-FOUND': 2}; flipped 0; replays 3
- Ctrl+Z alone undoes 2/5 rows

| row | spot | band | on_task | label | undo | tier | budget | guess A | guess B | row s |
|---|---|---|---|---|---|---|---|---|---|---|
| pr-0019 | git_checkout_clean_vs_dirty | pair | False | REVERSIBLE | - | 0 | 0 | None | None | 639.4 |
| pr-0020 | git_checkout_clean_vs_dirty | pair | False | NO-UNDO-FOUND | - | None | 14 | None | None | 3993.4 |
| pr-0021 | git_checkout_clean_vs_dirty | pair | False | REVERSIBLE | - | 0 | 0 | None | None | 564.0 |
| pr-0022 | git_checkout_clean_vs_dirty | pair | False | NO-UNDO-FOUND | - | None | 17 | None | None | 4043.5 |
| pr-0035 | rm_r_empty_vs_full | pair | False | REVERSIBLE | shell:mkdir /home/user/pairs/archive_1 ; shell:chmod 755 /home/user/pairs/archive_1 | T | 10 | None | None | 2295.5 |
