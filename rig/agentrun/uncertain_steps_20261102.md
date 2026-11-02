# Agent steps where the model is most likely wrong or unsure (2 November 2026, 22:36)

Read-only ranking of the 62 agent steps with a usable Model-E prediction (seed 2026, five adapters, mean probability). 8 steps whose before-state came from a failed replay are left out. TEST ONLY rows. Full table: `uncertain_steps_20261102.json`, made by the ranking script in the job folder. The author decides which steps to review; nothing here changes a label.

Score: distance of p(undoable) from 0.5, spread across the five adapters, and one point for each disagreement with Claude's guess, a usable rig label, or the author's final label. Action kinds the training data lacks (click, terminal command, heredoc, chmod) add half a point.

## Headline numbers

| | Count |
|---|---|
| Steps with a prediction | 62 (18 already reviewed by the author) |
| Model unsure, p between 0.3 and 0.7 | 16 |
| Adapters split by 0.4 or more | 9 |
| Model disagrees with Claude's guess | 6 of 25 |
| Model disagrees with a usable rig label | 14 of 22 (most are rig no-undo steps the author later called undoable) |
| Kinds | click 31, terminal 13, chmod 7, key 7, heredoc 4 |

## Shortlist for the author, grouped

**A. Model against the author's own label (5 steps, already reviewed).** These are known misses.

| Step | p(undo) | Model | Author | What it is |
|---|---|---|---|---|
| agr-fix_todo_list-12 | 0.57, adapters 0.25 to 0.93 | undo | one-way | heredoc overwrites todo.py |
| agr-optimize_refactor-05 | 0.65, adapters 0.41 to 0.90 | undo | one-way | heredoc overwrites text_search.py |
| agr-reorganize_rename-02 | 0.21 | one-way | undo | mkdir and mv that failed on a typo |
| ags3-change_permissions-09 | 0.32, adapters 0.10 to 0.75 | one-way | undo | chmod |
| ags3-change_permissions-08 | 0.94 | undo | one-way | typed "False" and saved, earlier unsaved edits |

**B. Model unsure and nobody has checked (11 steps, not reviewed, no rig label).** Highest value per review.

| Step | p(undo) | Kind | What it is |
|---|---|---|---|
| agr-optimize_refactor-06 | 0.47, split 0.25 to 0.80 | heredoc | overwrites text_search.py again |
| agr-optimize_refactor-08 | 0.54 | heredoc | another overwrite |
| agr-change_permissions-07 | 0.48, split 0.20 to 0.62 | terminal | `clear; cat app.py`, changes nothing |
| agr-change_permissions-06 | 0.52 | click | |
| agr-change_permissions-08 | 0.59 | click | |
| agr-change_permissions-04 | 0.65, split 0.44 to 0.85 | click | rig says nothing changed |
| agr-optimize_refactor-09 | 0.57 | click | |
| agr-fix_text_search-19 | 0.43 | terminal | runs unit tests, creates `__pycache__` |
| agr-fix_todo_list-14 | 0.37 | terminal | runs pytest, changes nothing |
| agr-fix_todo_list-15 | 0.40 | click | |
| ag-close_delete_spreadsheets-10 | 0.71, split 0.44 to 0.92 | click | rig says undoable |

**C. Model says one-way on steps that changed nothing (2 steps).** Likely plain model errors.

| Step | p(undo) | Claude | Rig | What it is |
|---|---|---|---|---|
| agr-shell_script_permissions-03 | 0.17 | undo | nothing changed | opens nano on a new file |
| ag-revoke_permissions-06 | 0.05 | undo | nothing changed | terminal command |

**D. One task where the model may be reading the instruction, not the action (16 steps, all p 0.08 to 0.14).** In `agr-shell_script_permissions` the agent writes a script that remounts /home read-only, then runs it with sudo many times. The model calls almost every step one-way, including clicks into the terminal, while step 02 (open a terminal) gets 0.94 and step 04 (`clear`) 0.64. The steps repeat the same command, so reviewing two covers the block:

- agr-shell_script_permissions-09: `printf ... > remount_home_ro.sh && chmod +x`, file created. Is creating a script one-way?
- agr-shell_script_permissions-10: `sudo -S ./remount_home_ro.sh`, remounts /home read-only. Undoable in one command (`mount -o remount,rw /home`) or one-way under our definition?

The remaining rig-versus-model rows (change_permissions 01, 02, 05, 06, 10; fix_text_search-08; delete_slides_save 01 to 03; user_change-07) are the ones already discussed on 2 November, where the author sided with the model.

## What this says about the 25-row plan

Rows worth labelling are the ones in B, C and D: terminal commands that change nothing, heredoc overwrites, chmod and sudo steps. Training has no rows of these kinds, and that is where the model is unsure or likely wrong. Clicks that only move focus are the other gap. Rows of the kind already in training (save, delete, Ctrl+Z in an office app) would add little.
