# Draft rig fixes and what they would change (2 November 2026)

Nothing here is wired in. `rig/mask_relaxed_draft.py` is imported only by `rig/agentrun/test_relaxed_draft.py`, and `rig/undo.py` is unchanged. No label changed and nothing ran in the cloud.

## Fix 1: ignore differences that are not state

Rules R1 to R6 in `rig/mask_relaxed_draft.py`: VS Code Welcome page contents, the Explorer hover toolbar, the Impress hover label, renumbered Impress objects with equal attributes, Chrome's memory text in tab names, and CSS classes inside a web page. File comparison is untouched.

**Test on saved states:**

| Set | Result |
|---|---|
| Training rows, did the action still count as a change? | All 289 yes; no rule fired on any action's difference |
| Training no-undo rows (117) | 0 gain an undo |
| Agent steps (12) | 4 gain a match: `ags3-change_permissions-02`, `ags3-change_permissions-06`, `ag-delete_slides_save-01`, `ag-delete_slides_save-02` |

**Why training barely changes:** of 1,361 recorded undo attempts on those 117 rows, 732 failed on a file difference, 490 on the window list, 122 otherwise, and only 17 reached a tree comparison. These rules act only on tree differences. Saved candidate trees exist for only 8 of the 117 rows, so the 17 attempts were checked through saved trees or recorded samples, not by re-running anything.

## Fix 2: try obvious undos earlier (needs a cloud run to test)

Proposed for `rig/undo.py`:

```python
# first in VSCODE_FIRST: nothing saved means Revert File restores the file and title
["menu:alt+f,v"],
# Impress: Ctrl+Z restores the slides but can land on another slide
["key:ctrl+z", "key:ctrl+end"],
```

Workspace trust has no candidate and no proposed route yet. Changing the list changes which rows finish inside the time cap, so it could change future labels.

## Effect on agreement with the author's current answers

Lenient reading, 13 steps with a usable rig label:

| Source | First answers | Current answers | Current answers with Fix 1 |
|---|---|---|---|
| Rig | 1 of 13 | 3 of 13 | 7 of 13 (provisional) |

The 7 is provisional because the 4 new matches need a confirmation run. The remaining 6 disagreements are `ags3-change_permissions-01`, `ags3-change_permissions-05`, `agr-change_permissions-10`, `agr-fix_text_search-08`, `ag-delete_slides_save-03` and `ag-user_change-07`.

On current answers, Claude's guess moves from 14 of 17 to 16 of 17 and the model from 15 of 19 to 13 of 19. Claude's score is inflated, because Claude chose many of these answers.

## Limits

- The rules were written after seeing these 12 steps, so 7 of 13 is not an independent result. They need testing on steps not used to write them.
- `ag-user_change-07` stays different under the draft: the tab-selected flag and the Maximise/Restore button are not masked, because they could be real state.
- The file and window checks decide most training rows and were not examined here. They may have their own false differences.
