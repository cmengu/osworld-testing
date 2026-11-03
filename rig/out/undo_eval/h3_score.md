# H3 rollback comparison (104 of 125 rows scored)

| Source | Rolled back | no plan | rig's own undo | unconfirmed | files differ | window differs | screen differs |
|---|---|---|---|---|---|---|---|
| model | 56 of 104 (54%) | 1 | 9 | 2 | 15 | 10 | 11 |
| claude | 69 of 104 (66%) | 8 | 7 | 3 | 2 | 6 | 9 |
| ctrlz | 36 of 104 (35%) | 0 | 2 | 0 | 20 | 34 | 12 |

Model only 3, Claude only 16, both 53, neither 32; sign test p = 0.00.
No source rolled back 32 rows. Left out (rig could not rebuild the after-state, or the row cap stopped a plan; includes rows still running): 21 ['pilot-0271', 'probe-0001', 'probe-0003', 'probe-0005', 'probe-0007', 'probe-0008', 'probe-0010', 'probe-0012', 'probe-0014', 'probe-0015', 'probe-0017', 'probe-0025', 'probe-0029', 'probe-0031', 'v2-0038', 'v2-0077', 'v2-0084', 'v2-0094', 'v2-0099', 'v3-0043', 'v3-0064'].
Claude's plan when it gives one, else the model's: 72 of 104 (69%). Either one works (upper bound of any mix): 72 of 104 (69%).

| App | Rows | Model | Claude | Ctrl+Z |
|---|---|---|---|---|
| multi_apps | 31 | 14 | 20 | 9 |
| libreoffice-calc | 22 | 16 | 16 | 11 |
| libreoffice-impress | 21 | 12 | 13 | 9 |
| vs_code | 11 | 6 | 8 | 5 |
| libreoffice-writer | 10 | 3 | 6 | 2 |
| thunderbird | 6 | 5 | 3 | 0 |
| os | 3 | 0 | 3 | 0 |
