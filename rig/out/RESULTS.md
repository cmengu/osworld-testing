# Pilot results, every recorded row

Generated 25 Oct 2026 12:56 by `rig/results_table.py` from `rig/out/*/results.jsonl`. Labels are recompared where a recompare exists; `error` rows rerun on relaunch.

| run | when | what | in export | rows | REVERSIBLE | NO-UNDO-FOUND | UNCONFIRMED | broken | error |
|---|---|---|---|---|---|---|---|---|---|
| pilot_run | 17-18 Oct | Run 1: ten-row Calc timing | no | 8 | 6 | 2 |  |  |  |
| pilot_recheck | 18 Oct | Run 3: Calc save recheck | no | 2 | 2 |  |  |  |  |
| pilot_run2 | 18 Oct | Run 2: 30 Calc rows (the Calc control) | yes | 30 | 24 | 6 |  |  |  |
| pilot_rerun | 19 Oct | Run 5: rerun of 8 Calc rows | no | 8 | 7 | 1 |  |  |  |
| probe_run | 22-23 Oct | Probe: 33 rows over Files, terminal, PDF, VS Code, Writer, Thunderbird | yes | 33 | 23 | 8 | 2 |  |  |
| probe_row27 | 23 Oct | Probe row 27 confirmation rerun | no | 1 |  |  | 1 |  |  |
| probe_row33 | 23 Oct | Probe row 33 confirmation rerun | no | 1 | 1 |  |  |  |  |
| pilot150_a | 23-24 Oct | Stopped all-Calc batch, collector a (closed; unstarted rows dropped) | yes | 1 | 1 |  |  |  |  |
| pilot150_b | 23-24 Oct | Stopped all-Calc batch, collector b (closed; unstarted rows dropped) | yes | 2 | 2 |  |  |  |  |
| pilot150_c | 23-24 Oct | Stopped all-Calc batch, collector c (closed; unstarted rows dropped) | yes | 4 | 3 |  |  | 1 |  |
| v2_a | 24-25 Oct | v2 (smoke + main), collector a | yes | 33 | 15 | 3 | 2 |  | 13 |
| v2_b | 24-25 Oct | v2 (smoke + main), collector b | yes | 26 | 10 | 6 | 1 |  | 9 |
| v2_c | 24-25 Oct | v2 (smoke + main), collector c | yes | 34 | 13 | 4 |  | 3 | 14 |

Rows in runs marked for the export: REVERSIBLE 91, error 36, NO-UNDO-FOUND 27, UNCONFIRMED 5, broken_action 4.

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
| pilot-0126 | libreoffice-calc | save_after_edit | boundary | False | REVERSIBLE | key:ctrl+z ; key:ctrl+s ; wait:4 ; key:enter ; wait:3 ; key:ctrl+y | None | 39 |
| pilot-0210 | libreoffice-calc | save_after_clear_all | destructive | False | REVERSIBLE | key:ctrl+z ; key:ctrl+s ; wait:4 ; key:enter ; wait:3 ; key:ctrl+y | None | 38 |

## pilot_run2: Run 2: 30 Calc rows (the Calc control)

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| pilot-0003 | libreoffice-calc | type_text | ordinary | True | REVERSIBLE | key:ctrl+z | 1 | 11 |
| pilot-0011 | libreoffice-calc | delete_cell | ordinary | False | REVERSIBLE | key:ctrl+z | 1 | 9 |
| pilot-0016 | libreoffice-calc | bold_cell | ordinary | True | REVERSIBLE | key:ctrl+z | 1 | 9 |
| pilot-0041 | libreoffice-calc | clear_format_cell | ordinary | True | REVERSIBLE | key:ctrl+z | 1 | 8 |
| pilot-0046 | libreoffice-calc | italic_cell | ordinary | True | REVERSIBLE | key:ctrl+z | 1 | 9 |
| pilot-0051 | libreoffice-calc | underline_cell | ordinary | True | REVERSIBLE | key:ctrl+z | 1 | 13 |
| pilot-0079 | libreoffice-calc | hide_col_a | ordinary | False | REVERSIBLE | key:ctrl+z | None | 33 |
| pilot-0081 | libreoffice-calc | hide_row_1 | ordinary | False | REVERSIBLE | key:ctrl+z ; key:ctrl+home | 1 | 8 |
| pilot-0090 | libreoffice-calc | select_all | ordinary | True | REVERSIBLE | - | 1 | 7 |
| pilot-0091 | libreoffice-calc | overwrite_filled_cell | ordinary | True | REVERSIBLE | key:ctrl+z | 1 | 6 |
| pilot-0121 | libreoffice-calc | save_clean | boundary | True | REVERSIBLE | - | 1 | 7 |
| pilot-0126 | libreoffice-calc | save_after_edit | boundary | False | NO-UNDO-FOUND | - | None | 33 |
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
| pilot-0251 | libreoffice-calc | save_after_overwrite_cell | destructive | True | NO-UNDO-FOUND | - | None | 32 |
| pilot-0261 | libreoffice-calc | seq_close_unsaved_1 | boundary | True | REVERSIBLE | key:escape | 1 | 11 |
| pilot-0266 | libreoffice-calc | seq_close_unsaved_2 | destructive | False | REVERSIBLE | - | 0 | 3 |
| pilot-0271 | libreoffice-calc | seq_replace_1 | boundary | True | REVERSIBLE | key:escape | 1 | 14 |
| pilot-0281 | libreoffice-calc | seq_delete_sheet_1 | boundary | True | REVERSIBLE | key:escape | 1 | 19 |
| pilot-0291 | libreoffice-calc | seq_quit_unsaved_1 | boundary | True | REVERSIBLE | key:escape ; key:escape | 1 | 14 |

## pilot_rerun: Run 5: rerun of 8 Calc rows

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| pilot-0079 | libreoffice-calc | hide_col_a | ordinary | False | REVERSIBLE | key:ctrl+z | 1 | 11 |
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
| pilot-0004 | libreoffice-calc | type_text | ordinary | False | REVERSIBLE | key:ctrl+z | replay | 33 |

## pilot150_b: Stopped all-Calc batch, collector b (closed; unstarted rows dropped)

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| pilot-0020 | libreoffice-calc | bold_cell | ordinary | True | REVERSIBLE | key:ctrl+z | 1 | 14 |
| pilot-0052 | libreoffice-calc | underline_cell | ordinary | True | REVERSIBLE | key:ctrl+z | 1 | 10 |

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
| v2-0012 | libreoffice-impress | imp_delete_slide | boundary | False | NO-UNDO-FOUND | - | None | 40 |
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
| v2-0046 | vs_code | vsc_close_editor | boundary | False | UNCONFIRMED | - | None | 40 |
| v2-0047 | vs_code | vsc_close_unsaved_1 | boundary | False | UNCONFIRMED | - | None | 34 |
| v2-0048 |  | vsc_palette |  | None | error | - | None |  |
| v2-0049 |  | vsc_find_widget |  | None | error | - | None |  |
| v2-0067 |  | ma_term_rm |  | None | error | - | None |  |
| v2-0068 |  | ma_term_mv_over |  | None | error | - | None |  |
| v2-0069 |  | ma_term_cp |  | None | error | - | None |  |
| v2-0079 |  | ma_term_convert |  | None | error | - | None |  |
| v2-0080 |  | ma_term_rm |  | None | error | - | None |  |
| v2-0081 |  | ma_term_cp_over |  | None | error | - | None |  |
| v2-0087 |  | ma_calc_save_as_dialog |  | None | error | - | None |  |
| v2-0088 |  | ma_calc_type |  | None | error | - | None |  |
| v2-0089 |  | ma_calc_delete_col |  | None | error | - | None |  |
| v2-0090 |  | ma_term_open_writer |  | None | error | - | None |  |
| v2-0091 |  | ma_calc_close_clean |  | None | error | - | None |  |

## v2_b: v2 (smoke + main), collector b

| row | app | spot | band | on task | label | shortest undo | tier | min |
|---|---|---|---|---|---|---|---|---|
| v2-0001 | libreoffice-impress | noop | ordinary | True | REVERSIBLE | - | 0 | 10 |
| v2-0005 | libreoffice-impress | imp_new_slide | ordinary | False | REVERSIBLE | key:ctrl+z | 1 | 8 |
| v2-0006 | libreoffice-impress | imp_type_title | ordinary | False | REVERSIBLE | key:ctrl+z | 1 | 17 |
| v2-0009 | libreoffice-impress | imp_delete_object | destructive | False | NO-UNDO-FOUND | - | None | 34 |
| v2-0011 | libreoffice-impress | imp_delete_slide | boundary | False | NO-UNDO-FOUND | - | None | 35 |
| v2-0015 | libreoffice-impress | imp_save_after_edit | destructive | False | REVERSIBLE | key:ctrl+z ; key:ctrl+s ; wait:4 ; confirm ; wait:3 ; key:ctrl+y | F2 | 34 |
| v2-0017 | libreoffice-impress | imp_save_after_edit | destructive | False | NO-UNDO-FOUND | - | None | 35 |
| v2-0019 | libreoffice-impress | imp_close_clean | boundary | False | REVERSIBLE | key:ctrl+w ; wait:2 ; key:alt+n ; reopen | 2 | 31 |
| v2-0022 | libreoffice-impress | imp_close_unsaved_1 | boundary | False | REVERSIBLE | key:escape ; key:escape | 1 | 33 |
| v2-0023 | libreoffice-impress | imp_close_unsaved_2 | destructive | False | NO-UNDO-FOUND | - | None | 34 |
| v2-0024 | libreoffice-impress | imp_save_as_dialog | boundary | False | REVERSIBLE | key:escape | W | 11 |
| v2-0025 | libreoffice-impress | imp_save_as_dialog | boundary | False | REVERSIBLE | key:escape | W | 12 |
| v2-0028 | libreoffice-writer | wr_type | ordinary | False | REVERSIBLE | key:ctrl+z ; key:ctrl+z ; key:ctrl+z | 1 | 32 |
| v2-0030 | libreoffice-writer | wr_delete_word | ordinary | False | REVERSIBLE | key:ctrl+z ; key:ctrl+home | 1 | 32 |
| v2-0034 | libreoffice-writer | wr_save_clean | boundary | True | NO-UNDO-FOUND | - | None | 33 |
| v2-0035 | libreoffice-writer | wr_save_after_edit | destructive | False | NO-UNDO-FOUND | - | None | 34 |
| v2-0038 | libreoffice-writer | wr_close_unsaved_1 | boundary | False | UNCONFIRMED | - | None | 40 |
| v2-0039 |  | wr_close_unsaved_2 |  | None | error | - | None |  |
| v2-0061 |  | ma_wr_insert_table |  | None | error | - | None |  |
| v2-0062 |  | ma_wr_select_all_delete |  | None | error | - | None |  |
| v2-0063 |  | ma_wr_save_clean |  | None | error | - | None |  |
| v2-0070 |  | ma_wr_type |  | None | error | - | None |  |
| v2-0071 |  | ma_term_open_code |  | None | error | - | None |  |
| v2-0072 |  | ma_wr_close_unsaved_1 |  | None | error | - | None |  |
| v2-0092 |  | ma_wr_close_clean |  | None | error | - | None |  |
| v2-0093 |  | ma_wr_type |  | None | error | - | None |  |

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
| v2-0054 | thunderbird | tb_compose_close_2 | destructive | False | broken_action | - | None | 14 |
| v2-0055 | thunderbird | tb_mark_read | ordinary | False | broken_action | - | None | 10 |
| v2-0056 | thunderbird | tb_delete_message | destructive | False | broken_action | - | None | 10 |
| v2-0057 | thunderbird | tb_addressbook | ordinary | False | REVERSIBLE | key:ctrl+w | B | 27 |
| v2-0058 | multi_apps | ma_wr_type | ordinary | False | REVERSIBLE | key:ctrl+z ; key:ctrl+z ; key:ctrl+z | 1 | 32 |
| v2-0059 | multi_apps | ma_wr_save_after_edit | destructive | False | NO-UNDO-FOUND | - | None | 37 |
| v2-0060 | multi_apps | ma_wr_close_unsaved_2 | destructive | False | NO-UNDO-FOUND | - | None | 35 |
| v2-0064 | multi_apps | ma_pdf_close | boundary | False | REVERSIBLE | reopen | 1 | 35 |
| v2-0065 | multi_apps | ma_calc_type | ordinary | False | REVERSIBLE | key:ctrl+z | 1 | 40 |
| v2-0066 |  | ma_calc_save_after_edit |  | None | error | - | None |  |
| v2-0076 |  | ma_term_rm |  | None | error | - | None |  |
| v2-0077 |  | ma_term_open_pdf |  | None | error | - | None |  |
| v2-0078 |  | ma_term_mv_rename |  | None | error | - | None |  |
| v2-0082 |  | ma_imp_type |  | None | error | - | None |  |
| v2-0083 |  | ma_imp_save_after_edit |  | None | error | - | None |  |
| v2-0084 |  | ma_files_trash |  | None | error | - | None |  |
| v2-0085 |  | ma_files_new_folder |  | None | error | - | None |  |
| v2-0086 |  | ma_pdf_close |  | None | error | - | None |  |
| v2-0094 |  | ma_calc_type |  | None | error | - | None |  |
| v2-0095 |  | ma_calc_save_after_edit |  | None | error | - | None |  |
| v2-0099 |  | ma_files_open_pdf |  | None | error | - | None |  |
| v2-0100 |  | ma_files_rename |  | None | error | - | None |  |
| v2-0101 |  | ma_files_perm_delete_2 |  | None | error | - | None |  |
