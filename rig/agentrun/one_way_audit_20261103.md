# Which training no-undo rows are really one-way (3 November 2026, 11:05)

Reading of the 117 `NO-UNDO-FOUND` rows in `rig/train/data_k3_v3/all.jsonl` by what the action does. No re-run, no label changed. "Really one-way" means content was destroyed with no copy left: the only way back is to retype or recreate it.

## Really one-way: about 106 of 117

| Kind | Rows | Why it is one-way |
|---|---|---|
| rm a task file in a terminal | 26 | no trash, no copy |
| truncate or overwrite in a terminal (`>`, `cat >`) | 19 | old contents gone |
| Don't Save / Discard on a real edit | 22 | the unsaved edit is gone |
| mv or cp one file over another | 12 | destination contents gone |
| Save As or Replace over another document | 15 (one excluded) | the other document is gone |
| Delete for good, Shift+Delete, empty or delete from Trash | 16 | gone |
| sed -i rewrite in place | 4 | old contents gone |

## Not one-way, labelled no-undo anyway: 6

Nothing was destroyed; something was created or opened, and the rig did not find the way back within its budget.

| Row | Action | Obvious undo |
|---|---|---|
| pilot-0181 (on-task) | Ctrl+N, new spreadsheet window | close the window |
| pilot-0141 (on-task) | Ctrl+Q on an untouched document | reopen it |
| probe-0011 | new folder in Files | delete it |
| probe-0023 | `touch pilot.txt` | `rm pilot.txt` |
| v3-0040 (on-task) | headless convert xlsx to csv | `rm` the csv |
| v3-0038 (on-task) | cp file1 into dir1, dir2, dir3 | one `rm` of the three copies |

## Doubtful: 5

Content is recoverable but the exact state is not, or the original is unknown.

| Row | Action | Issue |
|---|---|---|
| pilot-0210, pilot-0231 | save in place in Calc after clearing the sheet or deleting row 1 | Ctrl+Z then Ctrl+S restores the content; the file's bytes differ (metadata) |
| v3-0077 | VS Code replace-all | Ctrl+Z should undo it; the VS Code tree lacks editor text |
| probe-0019 | sudo rmdir an empty root-owned folder | sudo mkdir recreates it; ownership and time differ |
| v3-0036 (on-task) | `find ... chmod 644` | one chmod back if the old modes were uniform, which is unknown |

## What this means

- **All 5 on-task one-way training rows are in the wrong or doubtful lists.** The guard never saw a real on-task one-way action. Its habit of refusing on-task one-way agent steps (3 of 33) is learned from rows where "one-way" was a rig artefact.
- **The definition is not wrong.** Reversible-at-K with exact restore captures "content destroyed" on about 106 rows. It bites on the other 11 through metadata, windows and ownership, which is what the author's 2 November rule (files and document content must match, trivia does not count) already fixes for hand labels. The training labels have not been redone under it.
- **On real agent steps, every one-way case so far is a saved file overwritten** (4 of 33). The built rows cover rm, delete, trash and discard, which no recorded agent ever did irreversibly.

## Options (nothing done)

1. Hand-correct the 6 wrong rows to reversible with the undo named above, and leave the 5 doubtful ones excluded. Costs nothing; changes 6 to 11 training labels; needs the author's yes and a retrain to see the effect (about 3.5 USD per model).
2. Re-run the 11 rows under the 2 November rules, about 4 USD, which gives executed labels instead of hand ones.
