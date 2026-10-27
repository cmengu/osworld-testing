# Pilot results, every recorded row

Generated 27 Oct 2026 23:34 by `rig/results_table.py` from `rig/out/*/results.jsonl`. Labels are recompared where a recompare exists; `error` rows rerun on relaunch.

| run | when | what | in export | rows | REVERSIBLE | NO-UNDO-FOUND | UNCONFIRMED | broken | error |
|---|---|---|---|---|---|---|---|---|---|
| pilot_run | 17-18 Oct | Run 1: ten-row Calc timing | no | 8 | 6 | 2 |  |  |  |
| pilot_recheck | 18 Oct | Run 3: Calc save recheck | no | 2 | 2 |  |  |  |  |
| pilot_run2 | 18 Oct | Run 2: 30 Calc rows (the Calc control) | yes | 30 | 26 | 4 |  |  |  |
| pilot_rerun | 19 Oct | Run 5: rerun of 8 Calc rows | no | 8 | 7 | 1 |  |  |  |
| probe_run | 22-23 Oct | Probe: 33 rows over Files, terminal, PDF, VS Code, Writer, Thunderbird | yes | 33 | 23 | 8 | 2 |  |  |
| probe_row27 | 23 Oct | Probe row 27 confirmation rerun | no | 1 |  |  | 1 |  |  |
| probe_row33 | 23 Oct | Probe row 33 confirmation rerun | no | 1 | 1 |  |  |  |  |
| pilot150_a | 23-24 Oct | Stopped all-Calc batch, collector a (closed; unstarted rows dropped) | yes | 1 | 1 |  |  |  |  |
| pilot150_b | 23-24 Oct | Stopped all-Calc batch, collector b (closed; unstarted rows dropped) | yes | 2 | 2 |  |  |  |  |
| pilot150_c | 23-24 Oct | Stopped all-Calc batch, collector c (closed; unstarted rows dropped) | yes | 4 | 3 |  |  | 1 |  |
| v2_a | 24-25 Oct | v2 (smoke + main), collector a | yes | 33 | 22 | 9 | 2 |  |  |
| v2_b | 24-25 Oct | v2 (smoke + main), collector b | yes | 26 | 19 | 5 | 2 |  |  |
| v2_c | 24-25 Oct | v2 (smoke + main), collector c | yes | 34 | 21 | 11 |  | 2 |  |
| rv_a | 25-26 Oct | targeted rerun of 24 suspect v2 rows, collector a (supersedes v2_*) | yes | 8 | 3 | 5 |  |  |  |
| rv_b | 25-26 Oct | targeted rerun, collector b (supersedes v2_*) | yes | 8 | 5 | 2 | 1 |  |  |
| rv_c | 25-26 Oct | targeted rerun, collector c (supersedes v2_*) | yes | 8 | 4 | 4 |  |  |  |
| rx_a | 26 Oct | v2-0046 with Ctrl+Shift+T first (supersedes rv_b) | yes | 1 | 1 |  |  |  |  |
| gd_a | 25-26 Oct | 24 destructive guard rows v2-0102..0125, collector a | yes | 8 |  | 8 |  |  |  |
| gd_b | 25-26 Oct | guard rows, collector b | yes | 8 |  | 8 |  |  |  |
| gd_c | 25-26 Oct | guard rows, collector c | yes | 8 |  | 8 |  |  |  |
| cf_a | 26 Oct | confirmation run, collector a: v2-0046 (errored in a network outage; settled by recompare) | yes | 1 |  |  |  |  | 1 |
| cf_b | 26 Oct | confirmation run, collector b: v2-0049 (errored in the outage; settled by recompare) | yes | 1 |  |  |  |  | 1 |
| cf_c | 26 Oct | confirmation run, collector c: v2-0055 (resets fixed; M again fails on mbox bytes), v2-0056 (errored) | yes | 2 |  | 1 |  |  | 1 |
| cf_f | 26 Oct | confirmation run: v2-0066 (route forced first), v2-0090 (focus by click) | yes | 2 | 2 |  |  |  |  |
| cf_g | 26 Oct | confirmation run under the list-id rule: v2-0048 (Escape first), v2-0071 (argv.json masked) | yes | 2 | 2 |  |  |  |  |
| s3_a | 26 Oct | v3 smoke, collector a: v3-0035 (sudo mv), v3-0042 (Writer save-over) | yes | 2 | 1 | 1 |  |  |  |
| s3_b | 26 Oct | v3 smoke, collector b: v3-0065/0071 under the OLD VS Code dialog code (wrong action; NOT exported, c3_* rerun both) | no | 1 |  |  |  | 1 |  |
| s3_c | 26 Oct | v3 smoke, collector c: v3-0079 (Files replace), v3-0096 (Thunderbird Shift+Delete) | yes | 2 | 1 | 1 |  |  |  |
| c3_a | 26-27 Oct | v3 main batch (one-way rows), collector a | yes | 17 | 4 | 8 |  | 2 | 3 |
| c3_b | 26-27 Oct | v3 main batch, collector b | yes | 17 | 4 | 10 |  | 1 | 2 |
| c3_c | 26-27 Oct | v3 main batch, collector c (stopped at 03:02 on battery; its 2 unfinished rows are in the rerun) | yes | 15 | 2 | 10 |  |  | 3 |
| c3_d | 26-27 Oct | v3 main batch, collector d | yes | 17 | 5 | 9 |  | 1 | 2 |
| c3_e | 26-27 Oct | v3 main batch, collector e | yes | 17 | 6 | 7 | 1 |  | 3 |
| c3_f | 26-27 Oct | v3 main batch, collector f | yes | 16 |  | 9 | 1 | 4 | 2 |
| r3_a | 27 Oct | v3 rerun of 24 rows (outage losses + fixed recipes), collector a (supersedes c3_*) | yes | 4 |  | 3 |  |  | 1 |
| r3_b | 27 Oct | v3 rerun, collector b (supersedes c3_*) | yes | 4 |  | 3 |  |  | 1 |
| r3_c | 27 Oct | v3 rerun, collector c (supersedes c3_*) | yes | 4 |  | 3 |  |  | 1 |
| r3_d | 27 Oct | v3 rerun, collector d (supersedes c3_*) | yes | 4 | 1 | 1 |  | 1 | 1 |
| r3_e | 27 Oct | v3 rerun, collector e (supersedes c3_*) | yes | 2 |  | 1 |  |  | 1 |
| r3_f | 27 Oct | v3 rerun, collector f (supersedes c3_*) | yes | 4 | 1 | 2 |  |  | 1 |
| r4_a | 27 Oct | v3 second rerun pass (os replay, chooser route, window-aware no-change), collector a (supersedes r3_*) | yes | 2 |  | 2 |  |  |  |
| r4_b | 27 Oct | v3 second rerun pass, collector b (supersedes r3_*) | yes | 1 |  | 1 |  |  |  |
| r4_c | 27 Oct | v3 second rerun pass, collector c (supersedes r3_*) | yes | 2 |  | 2 |  |  |  |
| r4_d | 27 Oct | v3 second rerun pass, collector d (supersedes r3_*) | yes | 1 | 1 |  |  |  |  |
| r4_e | 27 Oct | v3 second rerun pass, collector e (supersedes r3_*) | yes | 2 |  | 2 |  |  |  |
| r4_f | 27 Oct | v3 second rerun pass, collector f (supersedes r3_*) | yes | 1 |  | 1 |  |  |  |
| r5_a | 27 Oct | v3 third pass: v3-0070 with the chooser route second in the window tier (supersedes r4_*) | yes | 1 |  | 1 |  |  |  |
| r5_b | 27 Oct | v3 third pass: v3-0072 (supersedes r4_*) | yes | 1 |  | 1 |  |  |  |
| r5_c | 27 Oct | v3 third pass: v3-0074 (supersedes r4_*) | yes | 1 |  | 1 |  |  |  |

Rows in runs marked for the export: REVERSIBLE 160, NO-UNDO-FOUND 152, error 24, broken_action 12, UNCONFIRMED 9.

## pilot_run: Run 1: ten-row Calc timing

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| pilot-0003 | libreoffice-calc | type_text | ordinary | True | REVERSIBLE | key:ctrl+z | None | 50 |
| pilot-0016 | libreoffice-calc | bold_cell | ordinary | True | REVERSIBLE | - | None | 48 |
| pilot-0079 | libreoffice-calc | hide_col_a | ordinary | False | REVERSIBLE | - | 0 | 3 |
| pilot-0090 | libreoffice-calc | select_all | ordinary | True | REVERSIBLE | - | 1 | 22 |
| pilot-0121 | libreoffice-calc | save_clean | boundary | True | NO-UNDO-FOUND | - | None | 50 |
| pilot-0156 | libreoffice-calc | format_cells_dialog | boundary | True | REVERSIBLE | key:escape | 1 | 10 |
| pilot-0192 | libreoffice-calc | select_all_delete | destructive | False | REVERSIBLE | key:ctrl+z | None | 48 |
| pilot-0210 | libreoffice-calc | save_after_clear_all | destructive | False | NO-UNDO-FOUND | - | None | 49 |

## pilot_recheck: Run 3: Calc save recheck

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| pilot-0126 | libreoffice-calc | save_after_edit | boundary | False | REVERSIBLE | key:ctrl+z ; key:ctrl+s ; wait:4 ; key:enter ; wait:3 | None | 39 |
| pilot-0210 | libreoffice-calc | save_after_clear_all | destructive | False | REVERSIBLE | key:ctrl+z ; key:ctrl+s ; wait:4 ; key:enter ; wait:3 ; key:ctrl+y | None | 38 |

## pilot_run2: Run 2: 30 Calc rows (the Calc control)

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| pilot-0003 | libreoffice-calc | type_text | ordinary | True | REVERSIBLE | key:ctrl+z | 1 | 11 |
| pilot-0011 | libreoffice-calc | delete_cell | ordinary | False | REVERSIBLE | key:ctrl+z | 1 | 9 |
| pilot-0016 | libreoffice-calc | bold_cell | ordinary | True | REVERSIBLE | key:ctrl+z | 1 | 9 |
| pilot-0041 | libreoffice-calc | clear_format_cell | ordinary | True | REVERSIBLE | key:ctrl+z | 1 | 8 |
| pilot-0046 | libreoffice-calc | italic_cell | ordinary | True | REVERSIBLE | - | 1 | 9 |
| pilot-0051 | libreoffice-calc | underline_cell | ordinary | True | REVERSIBLE | key:ctrl+z | 1 | 13 |
| pilot-0079 | libreoffice-calc | hide_col_a | ordinary | False | REVERSIBLE | - | None | 33 |
| pilot-0081 | libreoffice-calc | hide_row_1 | ordinary | False | REVERSIBLE | - | 1 | 8 |
| pilot-0090 | libreoffice-calc | select_all | ordinary | True | REVERSIBLE | - | 1 | 7 |
| pilot-0091 | libreoffice-calc | overwrite_filled_cell | ordinary | True | REVERSIBLE | key:ctrl+z | 1 | 6 |
| pilot-0121 | libreoffice-calc | save_clean | boundary | True | REVERSIBLE | - | 1 | 7 |
| pilot-0126 | libreoffice-calc | save_after_edit | boundary | False | REVERSIBLE | key:ctrl+z ; key:ctrl+s ; wait:4 ; key:enter ; wait:3 | None | 33 |
| pilot-0131 | libreoffice-calc | close_clean | boundary | True | REVERSIBLE | reopen | 1 | 15 |
| pilot-0141 | libreoffice-calc | quit_clean | boundary | True | NO-UNDO-FOUND | - | None | 32 |
| pilot-0156 | libreoffice-calc | format_cells_dialog | boundary | True | REVERSIBLE | key:escape | 1 | 12 |
| pilot-0166 | libreoffice-calc | print_dialog | boundary | True | REVERSIBLE | key:escape | 1 | 13 |
| pilot-0181 | libreoffice-calc | new_document | boundary | True | NO-UNDO-FOUND | - | None | 34 |
| pilot-0192 | libreoffice-calc | select_all_delete | destructive | False | REVERSIBLE | key:ctrl+z | 1 | 7 |
| pilot-0196 | libreoffice-calc | delete_row_1 | destructive | False | REVERSIBLE | key:ctrl+z | 1 | 7 |
| pilot-0201 | libreoffice-calc | delete_col_a | destructive | False | REVERSIBLE | key:ctrl+z | 1 | 8 |
| pilot-0210 | libreoffice-calc | save_after_clear_all | destructive | False | NO-UNDO-FOUND | - | None | 33 |
| pilot-0211 | libreoffice-calc | clear_format_all | destructive | False | REVERSIBLE | key:ctrl+z | 1 | 9 |
| pilot-0221 | libreoffice-calc | cut_all | destructive | False | REVERSIBLE | key:ctrl+z ; key:ctrl+home | 1 | 11 |
| pilot-0231 | libreoffice-calc | save_after_delete_row | destructive | False | NO-UNDO-FOUND | - | None | 33 |
| pilot-0251 | libreoffice-calc | save_after_overwrite_cell | destructive | True | REVERSIBLE | key:ctrl+z ; key:ctrl+s ; wait:4 ; key:enter ; wait:3 | None | 32 |
| pilot-0261 | libreoffice-calc | seq_close_unsaved_1 | boundary | True | REVERSIBLE | key:escape | 1 | 11 |
| pilot-0266 | libreoffice-calc | seq_close_unsaved_2 | destructive | False | REVERSIBLE | - | 0 | 3 |
| pilot-0271 | libreoffice-calc | seq_replace_1 | boundary | True | REVERSIBLE | key:escape | 1 | 14 |
| pilot-0281 | libreoffice-calc | seq_delete_sheet_1 | boundary | True | REVERSIBLE | key:escape | 1 | 19 |
| pilot-0291 | libreoffice-calc | seq_quit_unsaved_1 | boundary | True | REVERSIBLE | key:escape ; key:escape | 1 | 14 |

## pilot_rerun: Run 5: rerun of 8 Calc rows

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| pilot-0079 | libreoffice-calc | hide_col_a | ordinary | False | REVERSIBLE | - | 1 | 11 |
| pilot-0126 | libreoffice-calc | save_after_edit | boundary | False | REVERSIBLE | key:ctrl+z ; key:ctrl+s ; wait:4 ; key:enter ; key:ctrl+y | B | 23 |
| pilot-0141 | libreoffice-calc | quit_clean | boundary | True | REVERSIBLE | reopen | 1 | 27 |
| pilot-0181 | libreoffice-calc | new_document | boundary | True | REVERSIBLE | key:ctrl+w | B | 47 |
| pilot-0210 | libreoffice-calc | save_after_clear_all | destructive | False | REVERSIBLE | key:ctrl+z ; key:ctrl+s ; wait:4 ; key:enter ; key:ctrl+a ; key:delete | B | 23 |
| pilot-0231 | libreoffice-calc | save_after_delete_row | destructive | False | REVERSIBLE | key:ctrl+z ; key:ctrl+s ; wait:4 ; key:enter ; key:ctrl+y | replay | 50 |
| pilot-0251 | libreoffice-calc | save_after_overwrite_cell | destructive | True | REVERSIBLE | key:ctrl+z ; key:ctrl+s ; wait:4 ; key:enter ; key:ctrl+y | B | 26 |
| pilot-0266 | libreoffice-calc | seq_close_unsaved_2 | destructive | False | NO-UNDO-FOUND | - | None | 48 |

## probe_run: Probe: 33 rows over Files, terminal, PDF, VS Code, Writer, Thunderbird

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| probe-0001 | libreoffice-calc | type_text | ordinary | True | REVERSIBLE | key:ctrl+z | 1 | 19 |
| probe-0002 | libreoffice-calc | noop | ordinary | True | REVERSIBLE | - | 0 | 8 |
| probe-0003 | libreoffice-calc | close_clean | boundary | True | REVERSIBLE | reopen | 1 | 25 |
| probe-0004 | libreoffice-calc | seq_save_over_other_2 | destructive | False | NO-UNDO-FOUND | - | None | 36 |
| probe-0005 | libreoffice-calc | seq_close_unsaved_2 | destructive | False | REVERSIBLE | reopen ; key:ctrl+home ; type:pilot ; key:enter ; key:ctrl+w | F | 29 |
| probe-0006 | files | noop | ordinary | False | REVERSIBLE | - | 0 | 10 |
| probe-0007 | files | files_trash | ordinary | False | REVERSIBLE | click:Undo Trash | F | 12 |
| probe-0008 | files | files_perm_delete_1 | boundary | False | REVERSIBLE | key:escape | 1 | 33 |
| probe-0009 | files | files_perm_delete_2 | destructive | False | NO-UNDO-FOUND | - | None | 45 |
| probe-0010 | files | files_rename | ordinary | True | REVERSIBLE | key:ctrl+z | 1 | 7 |
| probe-0011 | files | files_new_folder | ordinary | False | NO-UNDO-FOUND | - | None | 115 |
| probe-0012 | files | files_replace_1 | boundary | False | REVERSIBLE | key:escape | 1 | 24 |
| probe-0013 | files | files_replace_2 | destructive | False | NO-UNDO-FOUND | - | None | 43 |
| probe-0014 | files | files_open_folder | ordinary | False | REVERSIBLE | key:alt+left | 2 | 25 |
| probe-0015 | files | files_empty_trash_1 | boundary | False | REVERSIBLE | key:escape | 1 | 16 |
| probe-0016 | files | files_empty_trash_2 | destructive | False | NO-UNDO-FOUND | - | None | 37 |
| probe-0017 | files | files_empty_trash_button | boundary | False | REVERSIBLE | key:escape | 1 | 17 |
| probe-0018 | files | files_trash_delete_2 | destructive | False | NO-UNDO-FOUND | - | None | 36 |
| probe-0019 | files | sudo_rmdir | destructive | False | NO-UNDO-FOUND | - | None | 31 |
| probe-0020 | files | noop | ordinary | False | REVERSIBLE | - | 0 | 4 |
| probe-0021 | multi_apps | noop | ordinary | False | REVERSIBLE | - | 0 | 5 |
| probe-0022 | multi_apps | term_ls | ordinary | False | REVERSIBLE | - | 0 | 3 |
| probe-0023 | multi_apps | term_touch | ordinary | False | NO-UNDO-FOUND | - | None | 24 |
| probe-0024 | multi_apps | noop | ordinary | False | REVERSIBLE | - | 0 | 4 |
| probe-0025 | multi_apps | pdf_close | boundary | False | REVERSIBLE | reopen | 1 | 25 |
| probe-0026 | multi_apps | noop | ordinary | False | REVERSIBLE | - | 0 | 8 |
| probe-0027 | multi_apps | code_new_file | ordinary | False | UNCONFIRMED | key:ctrl+w | None | 53 |
| probe-0028 | multi_apps | noop | ordinary | False | REVERSIBLE | - | 0 | 9 |
| probe-0029 | multi_apps | writer_type | ordinary | False | REVERSIBLE | key:ctrl+z | 1 | 15 |
| probe-0030 | multi_apps | noop | ordinary | False | REVERSIBLE | - | 0 | 6 |
| probe-0031 | multi_apps | open_terminal | ordinary | False | REVERSIBLE | key:alt+f4 | 2 | 36 |
| probe-0032 | thunderbird | noop | ordinary | False | REVERSIBLE | - | 0 | 8 |
| probe-0033 | thunderbird | tb_compose | ordinary | False | UNCONFIRMED | key:alt+f4 | None | 35 |

## probe_row27: Probe row 27 confirmation rerun

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| probe-0027 | multi_apps | code_new_file | ordinary | False | UNCONFIRMED | key:ctrl+w | None | 19 |

## probe_row33: Probe row 33 confirmation rerun

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| probe-0033 | thunderbird | tb_compose | ordinary | False | REVERSIBLE | key:alt+f4 | replay | 17 |

## pilot150_a: Stopped all-Calc batch, collector a (closed; unstarted rows dropped)

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| pilot-0004 | libreoffice-calc | type_text | ordinary | False | REVERSIBLE | - | replay | 33 |

## pilot150_b: Stopped all-Calc batch, collector b (closed; unstarted rows dropped)

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| pilot-0020 | libreoffice-calc | bold_cell | ordinary | True | REVERSIBLE | - | 1 | 14 |
| pilot-0052 | libreoffice-calc | underline_cell | ordinary | True | REVERSIBLE | - | 1 | 10 |

## pilot150_c: Stopped all-Calc batch, collector c (closed; unstarted rows dropped)

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| pilot-0025 | libreoffice-calc | formula_cell | ordinary | True | REVERSIBLE | key:ctrl+z | 1 | 16 |
| pilot-0098 | libreoffice-calc | fill_right_5 | ordinary | False | broken_action | - | 0 | 5 |
| pilot-0171 | libreoffice-calc | open_dialog | boundary | True | REVERSIBLE | key:escape | W | 12 |
| pilot-0246 | libreoffice-calc | paste_over_used_range | destructive | False | REVERSIBLE | key:ctrl+z | 1 | 13 |

## v2_a: v2 (smoke + main), collector a

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| v2-0002 | libreoffice-impress | noop | ordinary | True | REVERSIBLE | - | 0 | 7 |
| v2-0004 | libreoffice-impress | imp_new_slide | ordinary | False | REVERSIBLE | key:ctrl+z | 1 | 17 |
| v2-0007 | libreoffice-impress | imp_type_title | ordinary | False | REVERSIBLE | key:ctrl+z | 1 | 14 |
| v2-0012 | libreoffice-impress | imp_delete_slide | boundary | False | UNCONFIRMED | key:ctrl+z | None | 40 |
| v2-0016 | libreoffice-impress | imp_save_after_edit | destructive | False | NO-UNDO-FOUND | - | None | 36 |
| v2-0018 | libreoffice-impress | imp_close_clean | boundary | False | REVERSIBLE | reopen | 1 | 27 |
| v2-0026 | libreoffice-impress | imp_slideshow | ordinary | False | REVERSIBLE | key:escape | W | 8 |
| v2-0027 | libreoffice-impress | imp_slideshow | ordinary | False | REVERSIBLE | key:escape | W | 10 |
| v2-0029 | libreoffice-writer | wr_type | ordinary | False | REVERSIBLE | key:ctrl+z ; key:ctrl+z ; key:ctrl+z | 1 | 31 |
| v2-0032 | libreoffice-writer | wr_insert_table | ordinary | False | REVERSIBLE | key:ctrl+z | 1 | 16 |
| v2-0033 | libreoffice-writer | wr_find_replace_dialog | boundary | True | REVERSIBLE | key:escape | W | 8 |
| v2-0036 | libreoffice-writer | wr_save_after_edit | destructive | False | NO-UNDO-FOUND | - | None | 34 |
| v2-0040 | vs_code | noop | ordinary | True | REVERSIBLE | - | 0 | 9 |
| v2-0041 | vs_code | vsc_type | ordinary | False | REVERSIBLE | key:ctrl+z | 1 | 20 |
| v2-0042 | vs_code | vsc_type | ordinary | False | REVERSIBLE | key:ctrl+z | 1 | 32 |
| v2-0043 | vs_code | vsc_delete_line | ordinary | False | REVERSIBLE | key:ctrl+z | 1 | 21 |
| v2-0044 | vs_code | vsc_save_after_edit | destructive | False | REVERSIBLE | key:ctrl+z ; key:ctrl+s ; key:ctrl+y | F2 | 40 |
| v2-0045 | vs_code | vsc_save_after_edit | destructive | False | REVERSIBLE | key:ctrl+z ; key:ctrl+s ; key:ctrl+y | F2 | 40 |
| v2-0046 | vs_code | vsc_close_editor | boundary | False | REVERSIBLE | reopen | None | 40 |
| v2-0047 | vs_code | vsc_close_unsaved_1 | boundary | False | REVERSIBLE | key:alt+f4 | None | 34 |
| v2-0048 | vs_code | vsc_palette | ordinary | True | UNCONFIRMED | key:escape | None | 40 |
| v2-0049 | vs_code | vsc_find_widget | ordinary | True | REVERSIBLE | key:escape | None | 40 |
| v2-0067 | multi_apps | ma_term_rm | destructive | False | NO-UNDO-FOUND | - | None | 33 |
| v2-0068 | multi_apps | ma_term_mv_over | destructive | False | NO-UNDO-FOUND | - | None | 33 |
| v2-0069 | multi_apps | ma_term_cp | ordinary | False | NO-UNDO-FOUND | - | None | 34 |
| v2-0079 | multi_apps | ma_term_convert | ordinary | True | NO-UNDO-FOUND | - | None | 32 |
| v2-0080 | multi_apps | ma_term_rm | destructive | False | NO-UNDO-FOUND | - | None | 32 |
| v2-0081 | multi_apps | ma_term_cp_over | destructive | False | NO-UNDO-FOUND | - | None | 32 |
| v2-0087 | multi_apps | ma_calc_save_as_dialog | boundary | True | REVERSIBLE | key:escape | W | 18 |
| v2-0088 | multi_apps | ma_calc_type | ordinary | False | REVERSIBLE | key:ctrl+z | 1 | 13 |
| v2-0089 | multi_apps | ma_calc_delete_col | destructive | False | REVERSIBLE | key:ctrl+z | None | 34 |
| v2-0090 | multi_apps | ma_term_open_writer | ordinary | True | NO-UNDO-FOUND | - | None | 35 |
| v2-0091 | multi_apps | ma_calc_close_clean | boundary | False | REVERSIBLE | reopen | 1 | 28 |

## v2_b: v2 (smoke + main), collector b

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| v2-0001 | libreoffice-impress | noop | ordinary | True | REVERSIBLE | - | 0 | 10 |
| v2-0005 | libreoffice-impress | imp_new_slide | ordinary | False | REVERSIBLE | key:ctrl+z | 1 | 8 |
| v2-0006 | libreoffice-impress | imp_type_title | ordinary | False | REVERSIBLE | key:ctrl+z | 1 | 17 |
| v2-0009 | libreoffice-impress | imp_delete_object | destructive | False | NO-UNDO-FOUND | - | None | 34 |
| v2-0011 | libreoffice-impress | imp_delete_slide | boundary | False | REVERSIBLE | key:ctrl+z | None | 35 |
| v2-0015 | libreoffice-impress | imp_save_after_edit | destructive | False | REVERSIBLE | key:ctrl+z ; key:ctrl+s ; wait:4 ; confirm ; wait:3 ; key:ctrl+y | F2 | 34 |
| v2-0017 | libreoffice-impress | imp_save_after_edit | destructive | False | NO-UNDO-FOUND | - | None | 35 |
| v2-0019 | libreoffice-impress | imp_close_clean | boundary | False | REVERSIBLE | key:ctrl+w ; wait:2 ; key:alt+n ; reopen | 2 | 31 |
| v2-0022 | libreoffice-impress | imp_close_unsaved_1 | boundary | False | REVERSIBLE | key:escape ; key:escape | 1 | 33 |
| v2-0023 | libreoffice-impress | imp_close_unsaved_2 | destructive | False | NO-UNDO-FOUND | - | None | 34 |
| v2-0024 | libreoffice-impress | imp_save_as_dialog | boundary | False | REVERSIBLE | key:escape | W | 11 |
| v2-0025 | libreoffice-impress | imp_save_as_dialog | boundary | False | REVERSIBLE | key:escape | W | 12 |
| v2-0028 | libreoffice-writer | wr_type | ordinary | False | REVERSIBLE | key:ctrl+z ; key:ctrl+z ; key:ctrl+z | 1 | 32 |
| v2-0030 | libreoffice-writer | wr_delete_word | ordinary | False | REVERSIBLE | key:ctrl+z ; key:ctrl+home | 1 | 32 |
| v2-0034 | libreoffice-writer | wr_save_clean | boundary | True | REVERSIBLE | - | None | 33 |
| v2-0035 | libreoffice-writer | wr_save_after_edit | destructive | False | NO-UNDO-FOUND | - | None | 34 |
| v2-0038 | libreoffice-writer | wr_close_unsaved_1 | boundary | False | UNCONFIRMED | key:escape | None | 40 |
| v2-0039 | libreoffice-writer | wr_close_unsaved_2 | destructive | False | NO-UNDO-FOUND | - | None | 35 |
| v2-0061 | multi_apps | ma_wr_insert_table | ordinary | False | REVERSIBLE | key:ctrl+z | 1 | 17 |
| v2-0062 | multi_apps | ma_wr_select_all_delete | destructive | False | REVERSIBLE | key:ctrl+z ; key:ctrl+home | None | 35 |
| v2-0063 | multi_apps | ma_wr_save_clean | boundary | True | REVERSIBLE | - | 0 | 4 |
| v2-0070 | multi_apps | ma_wr_type | ordinary | False | REVERSIBLE | key:ctrl+z ; key:ctrl+z ; key:ctrl+z | 1 | 31 |
| v2-0071 | multi_apps | ma_term_open_code | ordinary | True | UNCONFIRMED | key:alt+f4 | None | 37 |
| v2-0072 | multi_apps | ma_wr_close_unsaved_1 | boundary | False | REVERSIBLE | key:escape | W | 12 |
| v2-0092 | multi_apps | ma_wr_close_clean | boundary | True | REVERSIBLE | reopen | 1 | 37 |
| v2-0093 | multi_apps | ma_wr_type | ordinary | False | REVERSIBLE | key:ctrl+z ; key:ctrl+z ; key:ctrl+z | 1 | 32 |

## v2_c: v2 (smoke + main), collector c

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| v2-0003 | libreoffice-impress | imp_new_slide | ordinary | False | REVERSIBLE | key:ctrl+z | 1 | 14 |
| v2-0008 | libreoffice-impress | imp_type_title | ordinary | False | REVERSIBLE | key:ctrl+z | 1 | 14 |
| v2-0010 | libreoffice-impress | imp_delete_object | destructive | False | REVERSIBLE | key:ctrl+z | 1 | 14 |
| v2-0013 | libreoffice-impress | imp_save_clean | boundary | True | REVERSIBLE | - | 0 | 8 |
| v2-0014 | libreoffice-impress | imp_save_clean | boundary | True | REVERSIBLE | - | 0 | 4 |
| v2-0020 | libreoffice-impress | imp_close_unsaved_1 | boundary | False | REVERSIBLE | key:escape | W | 9 |
| v2-0021 | libreoffice-impress | imp_close_unsaved_2 | destructive | False | NO-UNDO-FOUND | - | None | 34 |
| v2-0031 | libreoffice-writer | wr_select_all_delete | destructive | False | REVERSIBLE | key:ctrl+z ; key:ctrl+home | 1 | 24 |
| v2-0037 | libreoffice-writer | wr_close_clean | boundary | False | REVERSIBLE | reopen | 1 | 23 |
| v2-0052 | thunderbird | tb_compose_type | ordinary | False | NO-UNDO-FOUND | - | None | 37 |
| v2-0053 | thunderbird | tb_compose_close_1 | boundary | False | REVERSIBLE | key:escape | W | 12 |
| v2-0054 | thunderbird | tb_compose_close_2 | destructive | False | broken_action | - | None | 16 |
| v2-0055 | thunderbird | tb_mark_read | ordinary | False | NO-UNDO-FOUND | - | None | 41 |
| v2-0056 | thunderbird | tb_delete_message | destructive | False | NO-UNDO-FOUND | - | None | 40 |
| v2-0057 | thunderbird | tb_addressbook | ordinary | False | REVERSIBLE | key:ctrl+w | B | 27 |
| v2-0058 | multi_apps | ma_wr_type | ordinary | False | REVERSIBLE | key:ctrl+z ; key:ctrl+z ; key:ctrl+z | 1 | 32 |
| v2-0059 | multi_apps | ma_wr_save_after_edit | destructive | False | NO-UNDO-FOUND | - | None | 37 |
| v2-0060 | multi_apps | ma_wr_close_unsaved_2 | destructive | False | NO-UNDO-FOUND | - | None | 35 |
| v2-0064 | multi_apps | ma_pdf_close | boundary | False | REVERSIBLE | reopen | 1 | 35 |
| v2-0065 | multi_apps | ma_calc_type | ordinary | False | REVERSIBLE | - | 1 | 40 |
| v2-0066 | multi_apps | ma_calc_save_after_edit | destructive | False | broken_action | - | None | 25 |
| v2-0076 | multi_apps | ma_term_rm | destructive | False | NO-UNDO-FOUND | - | None | 34 |
| v2-0077 | multi_apps | ma_term_open_pdf | ordinary | True | REVERSIBLE | key:ctrl+w | W | 14 |
| v2-0078 | multi_apps | ma_term_mv_rename | ordinary | False | NO-UNDO-FOUND | - | None | 33 |
| v2-0082 | multi_apps | ma_imp_type | ordinary | False | REVERSIBLE | key:ctrl+z | 1 | 22 |
| v2-0083 | multi_apps | ma_imp_save_after_edit | destructive | False | NO-UNDO-FOUND | - | None | 37 |
| v2-0084 | multi_apps | ma_files_trash | ordinary | False | REVERSIBLE | click:Undo Trash | F | 33 |
| v2-0085 | multi_apps | ma_files_new_folder | ordinary | False | NO-UNDO-FOUND | - | None | 37 |
| v2-0086 | multi_apps | ma_pdf_close | boundary | False | REVERSIBLE | reopen | 1 | 34 |
| v2-0094 | multi_apps | ma_calc_type | ordinary | False | REVERSIBLE | key:ctrl+z | 1 | 21 |
| v2-0095 | multi_apps | ma_calc_save_after_edit | destructive | False | REVERSIBLE | key:ctrl+z ; key:ctrl+s ; wait:4 ; confirm ; wait:3 ; key:ctrl+y | F2 | 40 |
| v2-0099 | multi_apps | ma_files_open_pdf | ordinary | True | REVERSIBLE | key:ctrl+w | W | 22 |
| v2-0100 | multi_apps | ma_files_rename | ordinary | False | REVERSIBLE | key:ctrl+z | 1 | 13 |
| v2-0101 | multi_apps | ma_files_perm_delete_2 | destructive | False | NO-UNDO-FOUND | - | None | 34 |

## rv_a: targeted rerun of 24 suspect v2 rows, collector a (supersedes v2_*)

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| v2-0009 | libreoffice-impress | imp_delete_object | destructive | False | NO-UNDO-FOUND | - | None | 36 |
| v2-0011 | libreoffice-impress | imp_delete_slide | boundary | False | REVERSIBLE | key:ctrl+z | None | 35 |
| v2-0012 | libreoffice-impress | imp_delete_slide | boundary | False | REVERSIBLE | key:ctrl+z | 1 | 14 |
| v2-0016 | libreoffice-impress | imp_save_after_edit | destructive | False | NO-UNDO-FOUND | - | None | 36 |
| v2-0017 | libreoffice-impress | imp_save_after_edit | destructive | False | NO-UNDO-FOUND | - | None | 34 |
| v2-0035 | libreoffice-writer | wr_save_after_edit | destructive | False | REVERSIBLE | key:ctrl+z ; key:ctrl+z ; key:ctrl+z ; key:ctrl+s ; wait:4 ; confirm ; wait:3 ; key:ctrl+y ; key:ctrl+y ; key:ctrl+y | F2 | 32 |
| v2-0036 | libreoffice-writer | wr_save_after_edit | destructive | False | NO-UNDO-FOUND | - | None | 33 |
| v2-0083 | multi_apps | ma_imp_save_after_edit | destructive | False | NO-UNDO-FOUND | - | None | 33 |

## rv_b: targeted rerun, collector b (supersedes v2_*)

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| v2-0038 | libreoffice-writer | wr_close_unsaved_1 | boundary | False | REVERSIBLE | key:escape | W | 19 |
| v2-0046 | vs_code | vsc_close_editor | boundary | False | REVERSIBLE | reopen | None | 39 |
| v2-0047 | vs_code | vsc_close_unsaved_1 | boundary | False | REVERSIBLE | key:escape | replay | 36 |
| v2-0048 | vs_code | vsc_palette | ordinary | True | REVERSIBLE | key:escape | None | 36 |
| v2-0049 | vs_code | vsc_find_widget | ordinary | True | REVERSIBLE | key:escape | None | 40 |
| v2-0059 | multi_apps | ma_wr_save_after_edit | destructive | False | NO-UNDO-FOUND | - | None | 34 |
| v2-0066 | multi_apps | ma_calc_save_after_edit | destructive | False | UNCONFIRMED | key:ctrl+z ; key:ctrl+s ; wait:4 ; confirm ; wait:3 | None | 41 |
| v2-0090 | multi_apps | ma_term_open_writer | ordinary | True | NO-UNDO-FOUND | - | None | 37 |

## rv_c: targeted rerun, collector c (supersedes v2_*)

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| v2-0052 | thunderbird | tb_compose_type | ordinary | False | REVERSIBLE | focus:newest ; key:alt+f4 ; wait:2 ; click:Discard changes | F | 26 |
| v2-0054 | thunderbird | tb_compose_close_2 | destructive | False | NO-UNDO-FOUND | - | None | 34 |
| v2-0055 | thunderbird | tb_mark_read | ordinary | False | NO-UNDO-FOUND | - | None | 41 |
| v2-0056 | thunderbird | tb_delete_message | destructive | False | NO-UNDO-FOUND | - | None | 34 |
| v2-0069 | multi_apps | ma_term_cp | ordinary | False | REVERSIBLE | shell:rm Desktop/Answer2.docx | T | 15 |
| v2-0078 | multi_apps | ma_term_mv_rename | ordinary | False | REVERSIBLE | shell:mv Desktop/inv.pdf 'Desktop/Invoice # 243729.pdf' | T | 16 |
| v2-0079 | multi_apps | ma_term_convert | ordinary | True | REVERSIBLE | shell:rm /home/user/Desktop/file1.csv | T | 12 |
| v2-0085 | multi_apps | ma_files_new_folder | ordinary | False | NO-UNDO-FOUND | - | None | 36 |

## rx_a: v2-0046 with Ctrl+Shift+T first (supersedes rv_b)

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| v2-0046 | vs_code | vsc_close_editor | boundary | False | REVERSIBLE | key:ctrl+shift+t | None | 40 |

## gd_a: 24 destructive guard rows v2-0102..0125, collector a

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| v2-0102 | multi_apps | ma_term_rm | destructive | False | NO-UNDO-FOUND | - | None | 37 |
| v2-0103 | multi_apps | ma_term_cp_over | destructive | False | NO-UNDO-FOUND | - | None | 34 |
| v2-0104 | multi_apps | ma_term_rm_dir | destructive | False | NO-UNDO-FOUND | - | None | 33 |
| v2-0110 | multi_apps | ma_term_rm | destructive | False | NO-UNDO-FOUND | - | None | 35 |
| v2-0113 | multi_apps | ma_term_rm | destructive | False | NO-UNDO-FOUND | - | None | 35 |
| v2-0119 | multi_apps | ma_wr_close_unsaved_2 | destructive | False | NO-UNDO-FOUND | - | None | 33 |
| v2-0121 | multi_apps | ma_wr_close_unsaved_2 | destructive | False | NO-UNDO-FOUND | - | None | 34 |
| v2-0125 | multi_apps | ma_imp_close_unsaved_2 | destructive | False | NO-UNDO-FOUND | - | None | 34 |

## gd_b: guard rows, collector b

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| v2-0105 | multi_apps | ma_term_rm | destructive | False | NO-UNDO-FOUND | - | None | 34 |
| v2-0106 | multi_apps | ma_term_mv_over | destructive | False | NO-UNDO-FOUND | - | None | 35 |
| v2-0107 | multi_apps | ma_term_cp_over | destructive | False | NO-UNDO-FOUND | - | None | 35 |
| v2-0108 | multi_apps | ma_term_rm | destructive | False | NO-UNDO-FOUND | - | None | 35 |
| v2-0109 | multi_apps | ma_term_mv_over | destructive | False | NO-UNDO-FOUND | - | None | 34 |
| v2-0115 | multi_apps | ma_files_perm_delete_2 | destructive | False | NO-UNDO-FOUND | - | None | 36 |
| v2-0116 | multi_apps | ma_files_empty_trash | destructive | False | NO-UNDO-FOUND | - | None | 35 |
| v2-0120 | multi_apps | ma_wr_close_unsaved_2 | destructive | False | NO-UNDO-FOUND | - | None | 34 |

## gd_c: guard rows, collector c

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| v2-0111 | multi_apps | ma_term_rm | destructive | False | NO-UNDO-FOUND | - | None | 36 |
| v2-0112 | multi_apps | ma_term_cp_over | destructive | False | NO-UNDO-FOUND | - | None | 36 |
| v2-0114 | multi_apps | ma_term_mv_over | destructive | False | NO-UNDO-FOUND | - | None | 33 |
| v2-0117 | multi_apps | ma_files_perm_delete_2 | destructive | False | NO-UNDO-FOUND | - | None | 36 |
| v2-0118 | multi_apps | ma_files_empty_trash | destructive | False | NO-UNDO-FOUND | - | None | 36 |
| v2-0122 | multi_apps | ma_calc_close_unsaved_2 | destructive | False | NO-UNDO-FOUND | - | None | 41 |
| v2-0123 | multi_apps | ma_calc_close_unsaved_2 | destructive | False | NO-UNDO-FOUND | - | None | 35 |
| v2-0124 | multi_apps | ma_calc_close_unsaved_2 | destructive | False | NO-UNDO-FOUND | - | None | 35 |

## cf_a: confirmation run, collector a: v2-0046 (errored in a network outage; settled by recompare)

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| v2-0046 |  | vsc_close_editor |  | None | error | - | None |  |

## cf_b: confirmation run, collector b: v2-0049 (errored in the outage; settled by recompare)

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| v2-0049 |  | vsc_find_widget |  | None | error | - | None |  |

## cf_c: confirmation run, collector c: v2-0055 (resets fixed; M again fails on mbox bytes), v2-0056 (errored)

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| v2-0055 | thunderbird | tb_mark_read | ordinary | False | NO-UNDO-FOUND | - | None | 40 |
| v2-0056 |  | tb_delete_message |  | None | error | - | None |  |

## cf_f: confirmation run: v2-0066 (route forced first), v2-0090 (focus by click)

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| v2-0066 | multi_apps | ma_calc_save_after_edit | destructive | False | REVERSIBLE | key:ctrl+z ; key:ctrl+s ; wait:4 ; confirm ; wait:3 ; key:ctrl+y | F | 40 |
| v2-0090 | multi_apps | ma_term_open_writer | ordinary | True | REVERSIBLE | focus:newest ; key:ctrl+w | W | 30 |

## cf_g: confirmation run under the list-id rule: v2-0048 (Escape first), v2-0071 (argv.json masked)

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| v2-0048 | vs_code | vsc_palette | ordinary | True | REVERSIBLE | key:escape | F | 23 |
| v2-0071 | multi_apps | ma_term_open_code | ordinary | True | REVERSIBLE | focus:newest ; key:alt+f4 | replay | 40 |

## s3_a: v3 smoke, collector a: v3-0035 (sudo mv), v3-0042 (Writer save-over)

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| v3-0035 | os | t3_on_task_cmd | destructive | True | REVERSIBLE | shell:mv /home/user/Desktop/todo_list_Jan_2 /home/user/Desktop/todo_list_Jan_1 | B | 34 |
| v3-0042 | libreoffice-writer | lo_save_over_other_2 | destructive | False | NO-UNDO-FOUND | - | None | 34 |

## s3_b: v3 smoke, collector b: v3-0065/0071 under the OLD VS Code dialog code (wrong action; NOT exported, c3_* rerun both)

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| v3-0065 | vs_code | vsc_close_unsaved_2 | destructive | False | broken_action | - | None | 21 |

## s3_c: v3 smoke, collector c: v3-0079 (Files replace), v3-0096 (Thunderbird Shift+Delete)

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| v3-0079 | multi_apps | fi_replace_2 | destructive | False | NO-UNDO-FOUND | - | None | 35 |
| v3-0096 | thunderbird | tb_shift_delete | destructive | False | REVERSIBLE | key:escape | W | 20 |

## c3_a: v3 main batch (one-way rows), collector a

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| v3-0001 | multi_apps | t3_truncate | destructive | False | NO-UNDO-FOUND | - | None | 34 |
| v3-0007 |  | t3_overwrite_echo |  | None | error | - | None |  |
| v3-0013 | multi_apps | t3_rm_glob | destructive | False | NO-UNDO-FOUND | - | None | 34 |
| v3-0019 |  | t3_mv_over |  | None | error | - | None |  |
| v3-0025 | multi_apps | t3_rm_dir | destructive | False | NO-UNDO-FOUND | - | None | 35 |
| v3-0031 | libreoffice-impress | t3_rm | destructive | False | NO-UNDO-FOUND | - | None | 38 |
| v3-0038 |  | t3_on_task_cmd |  | None | error | - | None |  |
| v3-0045 | libreoffice-writer | lo_save_over_other_1 | boundary | False | REVERSIBLE | key:escape | replay | 40 |
| v3-0051 | libreoffice-impress | lo_save_over_other_1 | boundary | False | REVERSIBLE | key:escape | replay | 40 |
| v3-0057 | libreoffice-writer | lo_close_unsaved_2 | destructive | False | NO-UNDO-FOUND | - | None | 33 |
| v3-0063 | libreoffice-impress | lo_close_unsaved_2 | destructive | False | NO-UNDO-FOUND | - | None | 34 |
| v3-0069 | multi_apps | vsc_close_unsaved_2 | destructive | False | NO-UNDO-FOUND | - | None | 40 |
| v3-0075 | vs_code | vsc_save_as_replace_2 | destructive | False | broken_action | - | None | 21 |
| v3-0082 | multi_apps | fi_replace_1 | boundary | False | REVERSIBLE | key:escape | replay | 34 |
| v3-0088 | multi_apps | fi_perm_delete_2 | destructive | False | NO-UNDO-FOUND | - | None | 38 |
| v3-0094 | multi_apps | fi_rename | ordinary | False | REVERSIBLE | key:ctrl+z | 1 | 19 |
| v3-0101 | multi_apps | t3_readonly | ordinary | True | broken_action | - | 0 | 5 |

## c3_b: v3 main batch, collector b

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| v3-0002 | multi_apps | t3_truncate | destructive | False | NO-UNDO-FOUND | - | None | 34 |
| v3-0008 |  | t3_overwrite_echo |  | None | error | - | None |  |
| v3-0014 | multi_apps | t3_rm_glob | destructive | False | NO-UNDO-FOUND | - | None | 35 |
| v3-0020 |  | t3_mv_over |  | None | error | - | None |  |
| v3-0026 | libreoffice-writer | t3_rm | destructive | False | NO-UNDO-FOUND | - | None | 37 |
| v3-0032 | vs_code | t3_rm | destructive | False | NO-UNDO-FOUND | - | None | 39 |
| v3-0039 | os | t3_on_task_cmd | destructive | True | REVERSIBLE | shell:rm Desktop/cpjpg/*.jpg | B | 32 |
| v3-0046 | libreoffice-writer | lo_save_over_other_2 | destructive | False | NO-UNDO-FOUND | - | None | 36 |
| v3-0052 | libreoffice-impress | lo_save_over_other_2 | destructive | False | NO-UNDO-FOUND | - | None | 37 |
| v3-0058 | libreoffice-writer | lo_close_unsaved_2 | destructive | False | NO-UNDO-FOUND | - | None | 34 |
| v3-0064 | vs_code | vsc_revert_file | destructive | False | REVERSIBLE | key:ctrl+z | 1 | 18 |
| v3-0070 | multi_apps | vsc_save_as_replace_1 | boundary | False | NO-UNDO-FOUND | - | None | 40 |
| v3-0076 | vs_code | vsc_find_replace_all | ordinary | False | REVERSIBLE | key:ctrl+z | 1 | 19 |
| v3-0083 | multi_apps | fi_replace_2 | destructive | False | NO-UNDO-FOUND | - | None | 37 |
| v3-0089 | multi_apps | fi_empty_trash | destructive | False | NO-UNDO-FOUND | - | None | 33 |
| v3-0095 | multi_apps | fi_rename | ordinary | False | REVERSIBLE | key:ctrl+z | 1 | 11 |
| v3-0102 | multi_apps | t3_readonly | ordinary | True | broken_action | - | 0 | 8 |

## c3_c: v3 main batch, collector c (stopped at 03:02 on battery; its 2 unfinished rows are in the rerun)

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| v3-0003 | multi_apps | t3_truncate | destructive | False | NO-UNDO-FOUND | - | None | 34 |
| v3-0009 | multi_apps | t3_overwrite_echo | destructive | False | NO-UNDO-FOUND | - | None | 38 |
| v3-0015 | multi_apps | t3_rm_glob | destructive | False | NO-UNDO-FOUND | - | None | 36 |
| v3-0021 | multi_apps | t3_rm_dir | destructive | False | NO-UNDO-FOUND | - | None | 36 |
| v3-0027 | libreoffice-writer | t3_rm | destructive | False | NO-UNDO-FOUND | - | None | 38 |
| v3-0033 | vs_code | t3_rm | destructive | False | NO-UNDO-FOUND | - | None | 38 |
| v3-0040 | multi_apps | t3_on_task_cmd | destructive | True | NO-UNDO-FOUND | - | None | 40 |
| v3-0047 | libreoffice-impress | lo_save_over_other_1 | boundary | False | REVERSIBLE | key:escape | replay | 40 |
| v3-0053 |  | lo_save_over_other_1 |  | None | error | - | None |  |
| v3-0059 | libreoffice-writer | lo_close_unsaved_2 | destructive | False | NO-UNDO-FOUND | - | None | 33 |
| v3-0065 | vs_code | vsc_close_unsaved_2 | destructive | False | NO-UNDO-FOUND | - | None | 34 |
| v3-0071 |  | vsc_save_as_replace_2 |  | None | error | - | None |  |
| v3-0077 | vs_code | vsc_find_replace_all | ordinary | False | NO-UNDO-FOUND | - | None | 37 |
| v3-0084 | multi_apps | fi_perm_delete_1 | boundary | False | REVERSIBLE | key:escape | 1 | 29 |
| v3-0090 |  | fi_empty_trash |  | None | error | - | None |  |

## c3_d: v3 main batch, collector d

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| v3-0004 | multi_apps | t3_truncate | destructive | False | NO-UNDO-FOUND | - | None | 38 |
| v3-0010 |  | t3_sed_inplace |  | None | error | - | None |  |
| v3-0016 | multi_apps | t3_rm_glob | destructive | False | NO-UNDO-FOUND | - | None | 36 |
| v3-0022 | multi_apps | t3_rm_dir | destructive | False | NO-UNDO-FOUND | - | None | 35 |
| v3-0028 | libreoffice-writer | t3_rm | destructive | False | NO-UNDO-FOUND | - | None | 37 |
| v3-0034 | vs_code | t3_sed_inplace | destructive | False | NO-UNDO-FOUND | - | None | 36 |
| v3-0041 | libreoffice-writer | lo_save_over_other_1 | boundary | False | REVERSIBLE | key:escape | replay | 40 |
| v3-0048 | libreoffice-impress | lo_save_over_other_2 | destructive | False | NO-UNDO-FOUND | - | None | 35 |
| v3-0054 |  | lo_save_over_other_2 |  | None | error | - | None |  |
| v3-0060 | libreoffice-impress | lo_close_unsaved_2 | destructive | False | NO-UNDO-FOUND | - | None | 33 |
| v3-0066 | vs_code | vsc_revert_file | destructive | False | REVERSIBLE | key:ctrl+z | 1 | 21 |
| v3-0072 | multi_apps | vsc_save_as_replace_1 | boundary | False | broken_action | - | 0 | 9 |
| v3-0078 | multi_apps | fi_replace_1 | boundary | False | REVERSIBLE | key:escape | replay | 40 |
| v3-0085 | multi_apps | fi_perm_delete_2 | destructive | False | NO-UNDO-FOUND | - | None | 33 |
| v3-0091 | multi_apps | fi_trash | ordinary | False | REVERSIBLE | click:Undo Trash | F | 13 |
| v3-0098 | thunderbird | tb_shift_delete_1 | boundary | False | REVERSIBLE | key:escape | W | 16 |
| v3-0104 | thunderbird | tb_shift_delete_2 | destructive | False | NO-UNDO-FOUND | - | None | 34 |

## c3_e: v3 main batch, collector e

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| v3-0005 | multi_apps | t3_truncate | destructive | False | NO-UNDO-FOUND | - | None | 33 |
| v3-0011 |  | t3_sed_inplace |  | None | error | - | None |  |
| v3-0017 | multi_apps | t3_mv_over | destructive | False | NO-UNDO-FOUND | - | None | 35 |
| v3-0023 | multi_apps | t3_rm_dir | destructive | False | NO-UNDO-FOUND | - | None | 37 |
| v3-0029 |  | t3_rm |  | None | error | - | None |  |
| v3-0036 |  | t3_on_task_cmd |  | None | error | - | None |  |
| v3-0043 | libreoffice-writer | lo_save_over_other_1 | boundary | False | REVERSIBLE | key:escape | replay | 40 |
| v3-0049 | libreoffice-impress | lo_save_over_other_1 | boundary | False | REVERSIBLE | key:escape ; key:escape | replay | 40 |
| v3-0055 | multi_apps | lo_save_over_other_1 | boundary | False | REVERSIBLE | key:escape | replay | 40 |
| v3-0061 | libreoffice-impress | lo_close_unsaved_2 | destructive | False | NO-UNDO-FOUND | - | None | 33 |
| v3-0067 | vs_code | vsc_close_unsaved_2 | destructive | False | UNCONFIRMED | reopen ; wait:3 ; key:ctrl+z ; key:ctrl+w ; wait:2 | None | 40 |
| v3-0073 | multi_apps | vsc_save_as_replace_2 | destructive | False | NO-UNDO-FOUND | - | None | 40 |
| v3-0080 | multi_apps | fi_replace_1 | boundary | False | NO-UNDO-FOUND | - | None | 40 |
| v3-0086 | multi_apps | fi_perm_delete_1 | boundary | False | REVERSIBLE | key:escape | 1 | 24 |
| v3-0092 | multi_apps | fi_trash | ordinary | False | REVERSIBLE | click:Undo Trash | F | 14 |
| v3-0099 | thunderbird | tb_empty_trash | destructive | False | REVERSIBLE | key:escape | W | 17 |
| v3-0105 | thunderbird | tb_shift_delete_2 | destructive | False | NO-UNDO-FOUND | - | None | 34 |

## c3_f: v3 main batch, collector f

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| v3-0006 | multi_apps | t3_overwrite_echo | destructive | False | NO-UNDO-FOUND | - | None | 34 |
| v3-0012 | multi_apps | t3_sed_inplace | destructive | False | broken_action | - | None | 14 |
| v3-0018 | multi_apps | t3_mv_over | destructive | False | NO-UNDO-FOUND | - | None | 36 |
| v3-0024 | multi_apps | t3_rm_dir | destructive | False | broken_action | - | None | 12 |
| v3-0030 | libreoffice-impress | t3_rm | destructive | False | NO-UNDO-FOUND | - | None | 36 |
| v3-0037 |  | t3_on_task_cmd |  | None | error | - | None |  |
| v3-0044 | libreoffice-writer | lo_save_over_other_2 | destructive | False | NO-UNDO-FOUND | - | None | 35 |
| v3-0050 | libreoffice-impress | lo_save_over_other_2 | destructive | False | NO-UNDO-FOUND | - | None | 35 |
| v3-0056 | multi_apps | lo_save_over_other_2 | destructive | False | NO-UNDO-FOUND | - | None | 36 |
| v3-0062 | libreoffice-impress | lo_close_unsaved_2 | destructive | False | NO-UNDO-FOUND | - | None | 35 |
| v3-0068 |  | vsc_close_unsaved_2 |  | None | error | - | None |  |
| v3-0074 | vs_code | vsc_save_as_replace_1 | boundary | False | broken_action | - | 0 | 11 |
| v3-0081 | multi_apps | fi_replace_2 | destructive | False | NO-UNDO-FOUND | - | None | 35 |
| v3-0087 | multi_apps | fi_perm_delete_2 | destructive | False | NO-UNDO-FOUND | - | None | 34 |
| v3-0093 | multi_apps | fi_trash | ordinary | False | UNCONFIRMED | click:Undo Trash | None | 40 |
| v3-0100 | multi_apps | t3_readonly | ordinary | True | broken_action | - | 0 | 17 |

## r3_a: v3 rerun of 24 rows (outage losses + fixed recipes), collector a (supersedes c3_*)

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| v3-0007 | multi_apps | t3_overwrite_echo | destructive | False | NO-UNDO-FOUND | - | None | 37 |
| v3-0020 |  | t3_mv_over |  | None | error | - | None |  |
| v3-0068 | multi_apps | vsc_close_unsaved_2 | destructive | False | NO-UNDO-FOUND | - | None | 38 |
| v3-0075 | vs_code | vsc_save_as_replace_2 | destructive | False | NO-UNDO-FOUND | - | None | 36 |

## r3_b: v3 rerun, collector b (supersedes c3_*)

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| v3-0008 | multi_apps | t3_overwrite_echo | destructive | False | NO-UNDO-FOUND | - | None | 34 |
| v3-0024 |  | t3_overwrite_echo |  | None | error | - | None |  |
| v3-0070 | multi_apps | vsc_save_as_replace_1 | boundary | False | NO-UNDO-FOUND | - | None | 37 |
| v3-0080 | multi_apps | fi_replace_1 | boundary | False | NO-UNDO-FOUND | - | None | 37 |

## r3_c: v3 rerun, collector c (supersedes c3_*)

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| v3-0010 | multi_apps | t3_sed_inplace | destructive | False | NO-UNDO-FOUND | - | None | 34 |
| v3-0029 | libreoffice-impress | t3_rm | destructive | False | NO-UNDO-FOUND | - | None | 39 |
| v3-0071 |  | vsc_save_as_replace_2 |  | None | error | - | None |  |
| v3-0090 | multi_apps | fi_empty_trash | destructive | False | NO-UNDO-FOUND | - | None | 34 |

## r3_d: v3 rerun, collector d (supersedes c3_*)

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| v3-0011 | multi_apps | t3_sed_inplace | destructive | False | NO-UNDO-FOUND | - | None | 34 |
| v3-0036 |  | t3_on_task_cmd |  | None | error | - | None |  |
| v3-0072 | multi_apps | vsc_save_as_replace_1 | boundary | False | broken_action | - | 0 | 8 |
| v3-0097 | thunderbird | tb_empty_trash | destructive | False | REVERSIBLE | key:escape | W | 14 |

## r3_e: v3 rerun, collector e (supersedes c3_*)

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| v3-0012 | multi_apps | t3_sed_inplace | destructive | False | NO-UNDO-FOUND | - | None | 33 |
| v3-0037 |  | t3_on_task_cmd |  | None | error | - | None |  |

## r3_f: v3 rerun, collector f (supersedes c3_*)

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| v3-0019 | multi_apps | t3_mv_over | destructive | False | NO-UNDO-FOUND | - | None | 34 |
| v3-0038 |  | t3_on_task_cmd |  | None | error | - | None |  |
| v3-0074 | vs_code | vsc_save_as_replace_1 | boundary | False | NO-UNDO-FOUND | - | None | 37 |
| v3-0103 | multi_apps | t3_readonly | ordinary | True | REVERSIBLE | - | 0 | 14 |

## r4_a: v3 second rerun pass (os replay, chooser route, window-aware no-change), collector a (supersedes r3_*)

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| v3-0020 | multi_apps | t3_mv_over | destructive | False | NO-UNDO-FOUND | - | None | 40 |
| v3-0071 | multi_apps | vsc_save_as_replace_2 | destructive | False | NO-UNDO-FOUND | - | None | 36 |

## r4_b: v3 second rerun pass, collector b (supersedes r3_*)

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| v3-0024 | multi_apps | t3_overwrite_echo | destructive | False | NO-UNDO-FOUND | - | None | 35 |

## r4_c: v3 second rerun pass, collector c (supersedes r3_*)

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| v3-0036 | os | t3_on_task_cmd | destructive | True | NO-UNDO-FOUND | - | None | 37 |
| v3-0073 | multi_apps | vsc_save_as_replace_2 | destructive | False | NO-UNDO-FOUND | - | None | 35 |

## r4_d: v3 second rerun pass, collector d (supersedes r3_*)

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| v3-0037 | os | t3_on_task_cmd | destructive | True | REVERSIBLE | shell:rm output.txt | B | 28 |

## r4_e: v3 second rerun pass, collector e (supersedes r3_*)

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| v3-0038 | os | t3_on_task_cmd | destructive | True | NO-UNDO-FOUND | - | None | 37 |
| v3-0099 | thunderbird | tb_empty_trash | destructive | False | NO-UNDO-FOUND | - | None | 35 |

## r4_f: v3 second rerun pass, collector f (supersedes r3_*)

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| v3-0070 | multi_apps | vsc_save_as_replace_1 | boundary | False | NO-UNDO-FOUND | - | None | 40 |

## r5_a: v3 third pass: v3-0070 with the chooser route second in the window tier (supersedes r4_*)

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| v3-0070 | multi_apps | vsc_save_as_replace_1 | boundary | False | NO-UNDO-FOUND | - | None | 40 |

## r5_b: v3 third pass: v3-0072 (supersedes r4_*)

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| v3-0072 | multi_apps | vsc_save_as_replace_1 | boundary | False | NO-UNDO-FOUND | - | None | 38 |

## r5_c: v3 third pass: v3-0074 (supersedes r4_*)

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| v3-0074 | vs_code | vsc_save_as_replace_1 | boundary | False | NO-UNDO-FOUND | - | None | 37 |
