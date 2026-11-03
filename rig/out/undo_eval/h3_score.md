# H3 rollback comparison (107 of 125 rows scored)

| Source | Rolled back | no plan | rig's own undo | unconfirmed | files differ | window differs | screen differs |
|---|---|---|---|---|---|---|---|
| model | 58 of 107 (54%) | 1 | 9 | 2 | 16 | 10 | 11 |
| claude | 72 of 107 (67%) | 8 | 7 | 3 | 2 | 6 | 9 |
| ctrlz | 38 of 107 (36%) | 0 | 2 | 0 | 20 | 35 | 12 |

Model only 3, Claude only 17, both 55, neither 32; sign test p = 0.00.
No source rolled back 32 rows. Left out (rig could not rebuild the after-state, or the row cap stopped a plan; includes rows still running): 18 ['pilot-0271', 'probe-0001', 'probe-0003', 'probe-0005', 'probe-0007', 'probe-0008', 'probe-0010', 'probe-0012', 'probe-0014', 'probe-0015', 'probe-0017', 'probe-0025', 'probe-0029', 'probe-0031', 'v2-0038', 'v2-0099', 'v3-0043', 'v3-0064'].
Claude's plan when it gives one, else the model's: 75 of 107 (70%). Either one works (upper bound of any mix): 75 of 107 (70%).

| App | Rows | Model | Claude | Ctrl+Z |
|---|---|---|---|---|
| multi_apps | 34 | 16 | 23 | 11 |
| libreoffice-calc | 22 | 16 | 16 | 11 |
| libreoffice-impress | 21 | 12 | 13 | 9 |
| vs_code | 11 | 6 | 8 | 5 |
| libreoffice-writer | 10 | 3 | 6 | 2 |
| thunderbird | 6 | 5 | 3 | 0 |
| os | 3 | 0 | 3 | 0 |
