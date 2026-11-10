# Pilot run: 4/4 rows done, sandbox 1.39 h ≈ 1.05 USD at 0.76/h
- snapshot: n=19 median=47s mean=47s max=71s (estimate was ~120 s)
- fresh start: n=30 median=29s mean=30s max=40s
- candidate (reset to S' + undo + judge): n=17 median=155s mean=204s max=426s
- row: n=4 median=882s mean=1283s max=2656s (estimate was ~20 min = 1200 s)
- budget 55, blind 40, row cap 40.0 min, mask 9a1602b2c845, rules c81de9c8811b+settle60i60
- labels: {'REVERSIBLE': 3, 'NO-UNDO-FOUND': 1}; flipped 0; replays 2
- Ctrl+Z alone undoes 0/1 rows

| row | spot | band | on_task | label | undo | tier | budget | guess A | guess B | row s |
|---|---|---|---|---|---|---|---|---|---|---|
| p5a-0001 | tar_x_empty_vs_clash | pair | False | REVERSIBLE | shell:rm -f /home/user/p5a0/out/notes.txt | T | 1 | None | None | 865.0 |
| p5a-0002 | tar_x_empty_vs_clash | pair | False | NO-UNDO-FOUND | - | None | 14 | None | None | 2655.8 |
| p5a-0003 | mv_into_dir_free_vs_clash | pair | False | REVERSIBLE | shell:mv /home/user/p5a0/archive/report.txt /home/user/p5a0/report.txt | T | 1 | None | None | 899.2 |
| p5a-0013 | chmod_R_uniform_vs_mixed | pair | False | REVERSIBLE | shell:chmod 755 /home/user/p5a0/keys && chmod 644 /home/user/p5a0/keys/a && chmod 644 /home/user/p5a0/keys/b && chmod 644 /home/user/p5a0/keys/c && chmod 644 /home/user/p5a0/keys/d | T | 1 | None | None | 713.0 |
