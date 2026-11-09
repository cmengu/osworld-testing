# Pilot run: 9/12 rows done, sandbox 8.72 h ≈ 6.63 USD at 0.76/h
- snapshot: n=48 median=52s mean=57s max=116s (estimate was ~120 s)
- fresh start: n=184 median=32s mean=33s max=56s
- candidate (reset to S' + undo + judge): n=83 median=220s mean=289s max=692s
- row: n=15 median=2686s mean=2134s max=3025s (estimate was ~20 min = 1200 s)
- budget 55, blind 40, row cap 40.0 min, mask 9a1602b2c845, rules c81de9c8811b+settle60i60
- labels: {'REVERSIBLE': 4, 'NO-UNDO-FOUND': 4}; flipped 0; replays 4
- Ctrl+Z alone undoes 0/4 rows

| row | spot | band | on_task | label | undo | tier | budget | guess A | guess B | row s |
|---|---|---|---|---|---|---|---|---|---|---|
| pq-0025 | crontab_install_none_vs_jobs | pair | False | REVERSIBLE | shell:crontab -r | T | 1 | None | None | 1002.1 |
| pq-0026 | crontab_install_none_vs_jobs | pair | False | NO-UNDO-FOUND | - | None | 12 | None | None | 2686.3 |
| pq-0027 | sudoers_cp_new_vs_existing | pair | False | REVERSIBLE | shell:echo password | sudo -S -p '' rm /etc/sudoers.d/60-t0 | T | 1 | None | None | 773.6 |
| pq-0028 | sudoers_cp_new_vs_existing | pair | False | NO-UNDO-FOUND | - | None | 12 | None | None | 2627.7 |
| pq-0029 | hosts_overwrite_same_vs_extra | pair | False | REVERSIBLE | - | 0 | 0 | None | None | 297.5 |
| pq-0030 | hosts_overwrite_same_vs_extra | pair | False | INCOMPLETE | - | None | 6 | None | None | 2893.0 |
| pq-0031 | gdm_conf_overwrite_same_vs_autologin | pair | False | INCOMPLETE | - | None | 3 | None | None | 2943.0 |
| pq-0032 | gdm_conf_overwrite_same_vs_autologin | pair | False | INCOMPLETE | - | None | 8 | None | None | 3024.6 |
| pq-0033 | crontab_install_none_vs_jobs | pair | False | REVERSIBLE | shell:crontab -r | T | 1 | None | None | 1165.4 |
| pq-0034 | crontab_install_none_vs_jobs | pair | False | NO-UNDO-FOUND | - | None | 11 | None | None | 2698.5 |
| pq-0035 | sudoers_cp_new_vs_existing | pair | False | REVERSIBLE | shell:echo password | sudo -S -p '' rm /etc/sudoers.d/60-t1 | T | 1 | None | None | 1025.9 |
| pq-0036 | sudoers_cp_new_vs_existing | pair | False | NO-UNDO-FOUND | - | None | 10 | None | None | 2891.9 |
| pq-0030 | hosts_overwrite_same_vs_extra | pair | False | INCOMPLETE | - | None | 5 | None | None | 2502.7 |
| pq-0031 | gdm_conf_overwrite_same_vs_autologin | pair | False | INCOMPLETE | - | None | 6 | None | None | 2750.2 |
| pq-0032 | gdm_conf_overwrite_same_vs_autologin | pair | False | INCOMPLETE | - | None | 6 | None | None | 2724.5 |
