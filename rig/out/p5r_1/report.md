# Pilot run: 4/4 rows done, sandbox 1.42 h ≈ 1.08 USD at 0.76/h
- snapshot: n=18 median=48s mean=54s max=90s (estimate was ~120 s)
- fresh start: n=27 median=30s mean=32s max=45s
- candidate (reset to S' + undo + judge): n=15 median=187s mean=237s max=465s
- row: n=4 median=905s mean=1318s max=2671s (estimate was ~20 min = 1200 s)
- budget 55, blind 40, row cap 40.0 min, mask 9a1602b2c845, rules c81de9c8811b+settle60i60
- labels: {'REVERSIBLE': 3, 'NO-UNDO-FOUND': 1}; flipped 0; replays 1
- Ctrl+Z alone undoes 0/1 rows

| row | spot | band | on_task | label | undo | tier | budget | guess A | guess B | row s |
|---|---|---|---|---|---|---|---|---|---|---|
| p5a-0015 | tar_x_empty_vs_clash | pair | False | REVERSIBLE | shell:rm -f /home/user/p5a1/out/notes.txt | T | 1 | None | None | 1014.1 |
| p5a-0016 | tar_x_empty_vs_clash | pair | False | NO-UNDO-FOUND | - | None | 12 | None | None | 2670.7 |
| p5a-0017 | mv_into_dir_free_vs_clash | pair | False | REVERSIBLE | shell:mv /home/user/p5a1/archive/report.txt /home/user/p5a1/report.txt | T | 1 | None | None | 796.8 |
| p5a-0027 | chmod_R_uniform_vs_mixed | pair | False | REVERSIBLE | shell:chmod 755 /home/user/p5a1/keys && chmod 644 /home/user/p5a1/keys/a && chmod 644 /home/user/p5a1/keys/b && chmod 644 /home/user/p5a1/keys/c && chmod 644 /home/user/p5a1/keys/d | T | 1 | None | None | 789.5 |
