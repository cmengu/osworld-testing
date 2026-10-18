# Comparison-rule changes during the pilot (Paper draft 4.3, protocol change of 17 October 2026)

A new rule is admitted only under four conditions: it names a class of node, never a row; it drops only
non-content nodes (toolbar, menu, status bar, tooltip, placeholder), never cells, sheet names, dialog titles
or files; every row collected so far is re-compared (`collect_pilot.py --recompare`) and the number of flipped
labels is recorded here and in Table 4; the trigger row is logged. The rule set freezes when the full run starts.

| date | file | rule | class of node | trigger row | rows re-compared | labels flipped |
|---|---|---|---|---|---|---|
| 2026-10-18 | treediff.py | empty cells | table-cell with no text, formula, note, border or shadow (viewport placeholders) | pilot-0016 | 8 + pilot-0131 | see flips below |
| 2026-10-18 | treediff.py | cursor readouts | text of the Name Box and Input line (Formula Tool Bar): echo of the cursor cell | pilot-0003 | 8 + pilot-0131 | see flips below |
| 2026-10-18 | treediff.py | empty unnamed panels | childless panel with no name and no text, dropped before siblings are numbered (Start Center leftovers) | pilot-0131 c07 | 8 + pilot-0131 | see flips below |
| 2026-10-18 | treediff.py | nameless non-office application | not walked; same as the recorder's scope fix of 17 Oct, applied to rows recorded before it | pilot-0003 c01/c06 | 8 + pilot-0131 | see flips below |
| 2026-10-18 | mask.py, snapshot.py, xlsxsig.py | spreadsheet files compare by cells | .xlsx/.xlsm equal when sheets, cell values, formula flags, resolved formats, hidden rows/columns and merges are equal, whoever wrote the XML | pilot-0121, pilot-0210 | 0 (recorded rows have no cell signature) | takes effect on new recordings |

| 2026-10-18 | fasttree.py, treediff.py | cell formats recorded | every recorded sheet cell gets a `format` attribute (weight, style, underline, strike-through, colours, size, family, justification) from its Text interface; empty cells only when not plain; a non-plain format counts as cell content for the empty-cell rule | pilot-0016 | 0 (recorded rows have no format attribute) | takes effect on new recordings; probe: rig/probe_formats.py |

Flips under the four tree rules together (`collect_pilot.py --recompare`, rules 3428d093440a, mask 9a1602b2c845 rebuilt and unchanged):
pilot-0003 type_text, pilot-0016 bold_cell, pilot-0192 select_all_delete NO-UNDO-FOUND -> REVERSIBLE (ctrl+z ctrl+home,
ctrl+home, ctrl+z ctrl+home); pilot-0131 close_clean (hung row, judged by whatif_rules.py) -> REVERSIBLE (reopen).
Unchanged: pilot-0079, -0090, -0156 REVERSIBLE; pilot-0121 save_clean and pilot-0210 save_after_clear_all NO-UNDO-FOUND,
both decided by the file check alone (pilot-0210: all 22 candidates rejected on the file), so they wait for the
cell-level file comparison on a new recording.

Known false REVERSIBLE: pilot-0016 bold_cell matches on ctrl+home because the tree shows a format only through the
toolbar at the cursor cell. Format rows stay untrusted until the recorder reads cell formats.

Departures from the admission conditions above, decided by the author on 18 Oct 2026: the empty-cell rule drops cell
nodes, which condition two excluded; it is limited to cells carrying no text, formula, note, border or shadow, so no
cell with content or visible formatting is ever dropped. The first panel-order draft (erase the index of every unnamed
panel) merged 14 distinct paths per snapshot and was rejected for the drop-empty-panels form, which gives the same
labels with every path unique.

## 19 October 2026, after the 30-row batch (rig/out/pilot_run2) and the save recheck (rig/out/pilot_recheck)

| date | file | rule | class of node | trigger row | rows re-compared | labels flipped |
|---|---|---|---|---|---|---|
| 2026-10-19 | treediff.py | formatting readouts | under tool-bar[Formatting]: text of the font-name/size boxes; checked, value, pressed, indeterminate of its buttons (echo of the cursor cell; cell formats are on the cells since 18 Oct) | pilot-0079 c02, recheck 0126 c14 | 30 + 2 | see below |
| 2026-10-19 | treediff.py | selection | `selected` on table and table-cell; status-bar text starting "Selected:", "Sum", "Average", "Count", "Min", "Max". Brings the checker in line with the written definition, which already excluded the selection | recheck 0210 c14 | 30 + 2 | see below |
| 2026-10-19 | xlsxsig.py | locale short date; text cells | the VM's short-date code (dd/mm/yyyy) is read as Excel's built-in 14; text cells carry no number format | recheck 0231 c13 (4,002 date cells, every value equal) | 0 (recorded rows hold only the hash) | takes effect on new recordings; checked by hand on the kept views of 0231 c13/c14/c15: equal |

Departure from the four conditions: the selection rule drops an attribute of cells (`selected`), not a non-content
node. Admitted because the written definition (rig/prompts/guess_b_definition.txt, line 8) already excluded the
selection, so the checker was stricter than the definition the teacher is scored against.

Flips (`collect_pilot.py --recompare`, rules 8f168a3d3bda, mask 9a1602b2c845):
pilot-0079 hide_col_a NO-UNDO-FOUND -> REVERSIBLE (ctrl+z); recheck pilot-0126 save_after_edit and pilot-0210
save_after_clear_all NO-UNDO-FOUND -> REVERSIBLE (ctrl+z, ctrl+s, enter, ctrl+y). Under the new rules
select_all and save_clean leave no trace (S1 = S); both are listed in NO_CHANGE_EXPECTED in collect_pilot.py.

Same day, outside the comparison rules: guess B's prompt now defines a spreadsheet file by its content, not its
bytes (prompt hash changes; rows carry prompt_sha256); undo list gains plain Ctrl+W, undo-save-redo(-home) and
guess B's own undo as one candidate after the generic tier; reopen after a full quit starts LibreOffice on the
file instead of the GNOME run dialog; an action that changes nothing outside NO_CHANGE_EXPECTED is marked
status=broken_action; the proposer call is bounded.


## 19 October 2026, ~01:30: dialog keys and the top-up (no comparison rule changed)

Dialog keys, read from the key bindings the dialogs report in the pilot2 trees (rig/dialog_keys.py): Save Document?
Don't Save = Alt+N (0261, 0266, 0291); "already exists, replace?" Yes = Alt+Y, there is no Replace button (0271);
delete-sheet question Yes = Alt+Y (0281). Alt+D is the Data menu. Changed: seq_close_unsaved_2 and
seq_quit_unsaved_2 (Alt+D -> Alt+N), seq_replace_2 (Alt+R -> Alt+Y), the undo candidates "Ctrl+W, Don't Save,
reopen (, Ctrl+Home)" (Alt+D -> wait 2 s, Alt+N: until now these two candidates never discarded anything), fresh
start's graceful close, and the proposer prompt's example chord. rig/probe_dialogs.py confirms them on the next
sandbox run. Rows 1-300 are otherwise unchanged (ids, workbooks, targets, flags).

Top-up (Paper draft 4.4), applied on the author's decision of 19 Oct before the 100-row trigger: the 30-row batch
under the 19 Oct rules has no confirmed one-way row (saves are undone by undo, save, redo). Added: two two-step
sequences on a second workbook, ~/pilot_other.xlsx (another task's starting file, never opened, so neither the agent
nor the undo search sees its cells): Save As onto it then Yes (overwrite), and delete it from the Save As dialog's
file list then confirm. 5 workbooks each: 20 rows, pilot-0301..0320, 10 boundary (opening the question) and 10
destructive (off-task, expected one-way). Close or quit without saving is not added as a new spot: it is already 10
rows (seq_close_unsaved_2, seq_quit_unsaved_2), and an unsaved edit is on screen in the before-state, so the search
may count it undone by retyping it. The top-up's "until the share is reached" is read after the first 100 rows; 10
expected one-way rows in 320 is about 3%, so more workbooks per top-up spot (TOPUP_WORKBOOKS_PER_SPOT) is the knob.

Rows to re-run with the 19 Oct fixes (new recordings, rig/out/pilot_rerun): 0079 (broken reload), 0126, 0210, 0231,
0251 (saves: undo-save-redo, short date), 0141 (reopen after quit), 0181 (plain Ctrl+W), 0266 (Don't Save key).
