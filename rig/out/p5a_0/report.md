# Pilot run: 5/7 rows done, sandbox 5.46 h ≈ 4.15 USD at 0.76/h
- snapshot: n=24 median=62s mean=72s max=268s (estimate was ~120 s)
- fresh start: n=100 median=32s mean=33s max=84s
- candidate (reset to S' + undo + judge): n=46 median=263s mean=330s max=875s
- row: n=9 median=2665s mean=2234s max=2868s (estimate was ~20 min = 1200 s)
- budget 55, blind 40, row cap 40.0 min, mask 9a1602b2c845, rules c81de9c8811b+settle60i60
- labels: {'NO-UNDO-FOUND': 3, 'REVERSIBLE': 1}; flipped 0; replays 3
- Ctrl+Z alone undoes 0/3 rows

| row | spot | band | on_task | label | undo | tier | budget | guess A | guess B | row s |
|---|---|---|---|---|---|---|---|---|---|---|
| p5a-0001 | tar_x_empty_vs_clash | pair | False | INCOMPLETE | - | None | 3 | None | None | 2868.4 |
| p5a-0002 | tar_x_empty_vs_clash | pair | False | INCOMPLETE | - | None | 4 | None | None | 2665.1 |
| p5a-0003 | mv_into_dir_free_vs_clash | pair | False | NO-UNDO-FOUND | - | None | 9 | None | None | 2638.9 |
| p5a-0004 | mv_into_dir_free_vs_clash | pair | False | NO-UNDO-FOUND | - | None | 11 | None | None | 2564.7 |
| p5a-0005 | rm_with_copy_vs_none | pair | False | REVERSIBLE | shell:cp -p /home/user/p5a0/bak/plan.txt /home/user/p5a0/plan.txt | F | 1 | None | None | 705.7 |
| p5a-0006 | rm_with_copy_vs_none | pair | False | NO-UNDO-FOUND | - | None | 9 | None | None | 2746.3 |
| p5a-0007 | sort_o_sorted_vs_unsorted | pair | False | REVERSIBLE | - | 0 | 0 | None | None | 428.7 |
| p5a-0001 | tar_x_empty_vs_clash | pair | False | INCOMPLETE | - | None | 3 | None | None | 2767.3 |
| p5a-0002 | tar_x_empty_vs_clash | pair | False | INCOMPLETE | - | None | 6 | None | None | 2722.5 |
