# Where Claude's guess disagrees with the executed labels, and whether Claude was wrong (3 November 2026, 11:20)

Reading of the 232 training rows that have Claude's definition-matched guess (guess B) and a REVERSIBLE or NO-UNDO-FOUND label. No re-run, no label changed. This is the row-level view behind H1 (82.5% agreement on the no-undo class, 18 misses of 103).

## By action kind

| Kind | Rows | Claude right | One-way rows | Claude called undoable |
|---|---|---|---|---|
| typing | 32 | 32 | 0 | 0 |
| save over another document | 27 | 26 | 14 | 1 |
| rm in a terminal | 25 | 17 | 25 | 8 |
| discard an edit | 22 | 22 | 19 | 0 |
| save in place | 20 | 15 | 3 | 3 |
| delete for good / trash | 19 | 17 | 11 | 0 |
| terminal overwrite | 18 | 17 | 14 | 1 |
| mv / cp over | 13 | 12 | 11 | 0 |
| other | 33 | 30 | 3 | 3 |

## The 18 "misses" (Claude said undoable, rig said no undo)

| Rows | What happened | Was Claude wrong? |
|---|---|---|
| v3-0026 to v3-0031 (6) | `rm` of the .docx or .pptx that was open in Writer or Impress, typed in a terminal | Probably not. Save in the app recreates the file with the same content. The rig sent Ctrl+S to the terminal that had focus, never to the app, and would have failed on bytes anyway (re-serialised document). |
| v3-0032, v3-0033 (2) | `rm` of the text file open in VS Code, typed in its integrated terminal | Probably not. Ctrl+S in the editor rewrites the exact bytes. The rig's keys went to the terminal panel. |
| v3-0004 (1) | `: > file.xlsx` empties the open workbook | Same pattern: save in Calc restores the content. |
| pilot-0210, pilot-0231, v2-0083 (3) | save in place after an edit | Doubtful rows: Ctrl+Z then Ctrl+S restores the content; the bytes differ. |
| pilot-0141, pilot-0181, v3-0040, v3-0038 (4) | quit an untouched document, new window, convert to csv, cp into folders | Not one-way (see `one_way_audit_20261103.md`). Claude was right. |
| v3-0077, v3-0036 (2) | VS Code replace-all; chmod 644 over a tree | Doubtful. Replace-all undoes with Ctrl+Z; chmod depends on the old modes. |

By this reading, Claude is clearly wrong on **0 to 2** of its 18 misses. The other 16 to 18 are rows where the rig could not reach the undo (focus on the wrong window, bytes of a re-saved document, budget) or where nothing was destroyed.

**Consequence for H1.** If those rows are re-labelled undoable under the author's rule, the no-undo class shrinks to about 87 rows and Claude's misses to about 2, which is roughly 98% agreement, above the 90% threshold. H1 as currently scored measures the rig's strictness and focus handling more than Claude's judgment. This is a reading, not an execution; confirming it means re-running about 18 rows with a focus-the-app-then-save candidate under the 2 November rules, roughly 6 USD.

## Claude's 5 other disagreements (said one-way, rig found an undo)

Two save-in-place rows undone by Ctrl+Z then Ctrl+S (Claude too cautious), one terminal `mv` undone by `mv` back (Claude too cautious), and two Thunderbird deletes where Escape was the undo, meaning a confirmation dialog had appeared and nothing was deleted (the action never ran).
