# Pilot run: 4/4 rows done, sandbox 1.04 h ≈ 0.79 USD at 0.76/h
- snapshot: n=20 median=50s mean=58s max=89s (estimate was ~120 s)
- fresh start: n=16 median=32s mean=33s max=38s
- candidate (reset to S' + undo + judge): n=4 median=492s mean=573s max=839s
- row: n=4 median=952s mean=1005s max=1331s (estimate was ~20 min = 1200 s)
- budget 55, blind 40, row cap 40.0 min, mask 9a1602b2c845, rules c81de9c8811b+settle60i60
- labels: {'REVERSIBLE': 4}; flipped 0; replays 0

| row | spot | band | on_task | label | undo | tier | budget | guess A | guess B | row s |
|---|---|---|---|---|---|---|---|---|---|---|
| p5a-0011 | cp_r_merge_empty_vs_clash | pair | False | REVERSIBLE | shell:rm -f /home/user/p5a0/site/index.html | T | 1 | None | None | 1041.5 |
| p5a-0014 | chmod_R_uniform_vs_mixed | pair | False | REVERSIBLE | shell:chmod 750 /home/user/p5a0/keys && chmod 600 /home/user/p5a0/keys/a && chmod 640 /home/user/p5a0/keys/b && chmod 444 /home/user/p5a0/keys/c && chmod 664 /home/user/p5a0/keys/d | T | 1 | None | None | 862.8 |
| p5a-0025 | cp_r_merge_empty_vs_clash | pair | False | REVERSIBLE | shell:rm -f /home/user/p5a1/site/index.html | T | 1 | None | None | 1330.6 |
| p5a-0028 | chmod_R_uniform_vs_mixed | pair | False | REVERSIBLE | shell:chmod 750 /home/user/p5a1/keys && chmod 600 /home/user/p5a1/keys/a && chmod 640 /home/user/p5a1/keys/b && chmod 444 /home/user/p5a1/keys/c && chmod 664 /home/user/p5a1/keys/d | T | 1 | None | None | 784.5 |
