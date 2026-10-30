# Pilot run: 3/3 rows done, sandbox 1.47 h ≈ 1.11 USD at 0.76/h
- snapshot: n=12 median=130s mean=145s max=401s (estimate was ~120 s)
- fresh start: n=15 median=60s mean=61s max=69s
- candidate (reset to S' + undo + judge): n=35 median=44s mean=80s max=464s
- row: n=3 median=1991s mean=1813s max=2104s (estimate was ~20 min = 1200 s)
- budget 55, blind 40, row cap 25.0 min, mask 9a1602b2c845, rules a2a74e53cb0e
- labels: {'REVERSIBLE': 1, 'NO-UNDO-FOUND': 2}; flipped 0; replays 3
- guess B zero-shot undo: 0/2 executed undos restored S
- Ctrl+Z alone undoes 0/1 rows

| row | spot | band | on_task | label | undo | tier | budget | guess A | guess B | row s |
|---|---|---|---|---|---|---|---|---|---|---|
| ags-vscheck-02 | agent_step | agent_replay | None | REVERSIBLE | key:ctrl+` | V | 1 | True | True | 1342.3 |
| ags-vscheck-04 | agent_step | agent_replay | None | NO-UNDO-FOUND | - | None | 27 | True | True | 2104.1 |
| ags-vscheck-05 | agent_step | agent_replay | None | NO-UNDO-FOUND | - | None | 7 | True | True | 1991.3 |
