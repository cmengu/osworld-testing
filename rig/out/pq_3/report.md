# Pilot run: 8/12 rows done, sandbox 9.42 h ≈ 7.16 USD at 0.76/h
- snapshot: n=40 median=59s mean=63s max=105s (estimate was ~120 s)
- fresh start: n=224 median=30s mean=30s max=51s
- candidate (reset to S' + undo + judge): n=78 median=360s mean=317s max=672s
- row: n=16 median=2883s mean=2162s max=3008s (estimate was ~20 min = 1200 s)
- budget 55, blind 40, row cap 40.0 min, mask 9a1602b2c845, rules c81de9c8811b+settle60i60
- labels: {'REVERSIBLE': 2, 'NO-UNDO-FOUND': 2}; flipped 1; replays 4
- Ctrl+Z alone undoes 0/2 rows

| row | spot | band | on_task | label | undo | tier | budget | guess A | guess B | row s |
|---|---|---|---|---|---|---|---|---|---|---|
| pq-0037 | hosts_overwrite_same_vs_extra | pair | False | REVERSIBLE | - | 0 | 0 | None | None | 652.4 |
| pq-0038 | hosts_overwrite_same_vs_extra | pair | False | INCOMPLETE | - | None | 5 | None | None | 3002.7 |
| pq-0039 | gdm_conf_overwrite_same_vs_autologin | pair | False | REVERSIBLE | - | 0 | 0 | None | None | 474.0 |
| pq-0040 | gdm_conf_overwrite_same_vs_autologin | pair | False | INCOMPLETE | - | None | 5 | None | None | 3007.9 |
| pq-0041 | crontab_install_none_vs_jobs | pair | False | REVERSIBLE | shell:crontab -r | replay | 6 | None | None | 2974.0 |
| pq-0042 | crontab_install_none_vs_jobs | pair | False | INCOMPLETE | - | None | 7 | None | None | 2973.4 |
| pq-0043 | sudoers_cp_new_vs_existing | pair | False | INCOMPLETE | - | None | 6 | None | None | 2792.6 |
| pq-0044 | sudoers_cp_new_vs_existing | pair | False | NO-UNDO-FOUND | - | None | 9 | None | None | 2670.8 |
| pq-0045 | hosts_overwrite_same_vs_extra | pair | False | REVERSIBLE | - | 0 | 0 | None | None | 303.9 |
| pq-0046 | hosts_overwrite_same_vs_extra | pair | False | INCOMPLETE | - | None | 6 | None | None | 3000.9 |
| pq-0047 | gdm_conf_overwrite_same_vs_autologin | pair | False | REVERSIBLE | - | 0 | 0 | None | None | 309.8 |
| pq-0048 | gdm_conf_overwrite_same_vs_autologin | pair | False | INCOMPLETE | - | None | 6 | None | None | 3001.2 |
| pq-0038 | hosts_overwrite_same_vs_extra | pair | False | INCOMPLETE | - | None | 7 | None | None | 3001.6 |
| pq-0040 | gdm_conf_overwrite_same_vs_autologin | pair | False | INCOMPLETE | - | None | 7 | None | None | 2979.0 |
| pq-0042 | crontab_install_none_vs_jobs | pair | False | NO-UNDO-FOUND | - | None | 13 | None | None | 2726.1 |
| pq-0043 | sudoers_cp_new_vs_existing | pair | False | REVERSIBLE | shell:echo password | sudo -S -p '' rm /etc/sudoers.d/60-t2 | T | 1 | None | None | 718.1 |
