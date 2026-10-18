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
