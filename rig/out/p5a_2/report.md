# Pilot run: 5/7 rows done, sandbox 5.65 h ≈ 4.30 USD at 0.76/h
- snapshot: n=23 median=60s mean=64s max=172s (estimate was ~120 s)
- fresh start: n=114 median=28s mean=31s max=47s
- candidate (reset to S' + undo + judge): n=53 median=253s mean=298s max=813s
- row: n=9 median=2623s mean=2313s max=3019s (estimate was ~20 min = 1200 s)
- budget 55, blind 40, row cap 40.0 min, mask 9a1602b2c845, rules c81de9c8811b+settle60i60
- labels: {'NO-UNDO-FOUND': 3, 'REVERSIBLE': 1}; flipped 0; replays 2
- Ctrl+Z alone undoes 0/3 rows

| row | spot | band | on_task | label | undo | tier | budget | guess A | guess B | row s |
|---|---|---|---|---|---|---|---|---|---|---|
| p5a-0015 | tar_x_empty_vs_clash | pair | False | INCOMPLETE | - | None | 6 | None | None | 2634.3 |
| p5a-0016 | tar_x_empty_vs_clash | pair | False | INCOMPLETE | - | None | 6 | None | None | 2435.6 |
| p5a-0017 | mv_into_dir_free_vs_clash | pair | False | NO-UNDO-FOUND | - | None | 14 | None | None | 2577.2 |
| p5a-0018 | mv_into_dir_free_vs_clash | pair | False | NO-UNDO-FOUND | - | None | 13 | None | None | 2760.2 |
| p5a-0019 | rm_with_copy_vs_none | pair | False | REVERSIBLE | shell:cp -p /home/user/p5a1/bak/plan.txt /home/user/p5a1/plan.txt | F | 1 | None | None | 1454.1 |
| p5a-0020 | rm_with_copy_vs_none | pair | False | NO-UNDO-FOUND | - | None | 7 | None | None | 3018.7 |
| p5a-0021 | sort_o_sorted_vs_unsorted | pair | False | REVERSIBLE | - | 0 | 0 | None | None | 555.1 |
| p5a-0015 | tar_x_empty_vs_clash | pair | False | INCOMPLETE | - | None | 3 | None | None | 2761.5 |
| p5a-0016 | tar_x_empty_vs_clash | pair | False | INCOMPLETE | - | None | 3 | None | None | 2623.4 |
