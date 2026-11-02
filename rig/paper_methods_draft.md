# Methods (draft, 1 November 2026)

Status: draft for the author. `[TO CONFIRM]` marks a point not settled yet. The hand review has no answers yet, so this section describes its protocol only and reports no results from it.

## 1. What is being predicted

The model answers questions about one proposed desktop action, given a text rendering of the state before it.

An action is **reversible at K** if the state before it can be brought back within K actions, using only what the desktop offers a user: keys, menus, named buttons, reopening a file or window, or one terminal command per action. Waits, window focus changes, answering a confirmation prompt and moving the pointer back do not count as actions. Typing lost content back in is not an undo. The main setting is K = 3, with K = 1 run as a comparison. K is a chosen threshold, not a derived one. For the hand review, "brought back" means files and document content match exactly; pointer effects and on-screen trivia do not count (author's decision, 2 November). All rig results reported here use the stricter comparison in place before 2 November; later runs ignore six kinds of on-screen trivia and are marked with a new rules version.

The **guard target** is `refuse` when an action is not reversible at K and the task did not ask for it, and `allow` otherwise. On-task marks take the instruction literally, so a harmful action the instruction asked for counts as on-task. Harm is not part of the target.

## 2. Executed labels

Labels come from executing actions in an OSWorld Ubuntu VM (QEMU, in a Modal sandbox). For each row the rig records the state S, runs the action, records S′, and searches for an undo.

**State comparison.** A state is the accessibility tree, the window list and a digest of the files under the home folder. Two states are equal only if all three agree after a noise mask is applied. The mask is built from repeated snapshots of one nominal state: whatever differs between them cannot be an action's effect. Files compare by size and content hash, not modified time. `[TO CONFIRM: mask snapshot count and rule version to report; the current mask file records 22 snapshots.]`

**Undo search.** Candidates run cheapest first, each from a reset to S′: generic keys, application-specific routes, proposed candidates, then blind pairs of generic steps. The budget is 55 candidates and a per-row time cap. Window list and files are compared first, and the slower tree read runs only if both match. If S′ equals S, the row is reversible with an empty undo.

**Confirmation.** A matching candidate is re-run from a verified S′ on a fresh instance (on the newest agent run, from that run's own snapshot, since no fresh instance can reproduce it). A match that does not repeat is `UNCONFIRMED` and is left out of REVERSIBLE and GUARD.

**What a no-undo label means.** `NO-UNDO-FOUND` means no candidate tried within the budget and cap restored the state exactly. It is a lower bound on reversibility, not proof that an action is one-way. An undo the candidate list lacks, or a small leftover on screen, produces the same label as a truly one-way action.

**Excluded rows.** Rows whose no-undo label reflects a known rig limit stay in FORWARD but are left out of REVERSIBLE and GUARD (`rig/train/exclude_rig_issues.txt`).

**A flaw found late.** Until 30 October, a row could be labelled no-undo even when some candidates errored or failed their reset before being judged. An audit found 12 such rows. Six are test-only agent rows. Of the six in the training data, four were already excluded and one takes its label from a later clean run. The last, v3-0052, was still in use and goes into the exclusion list at the next export, so the scores in this draft still include it. New runs mark such rows `INCOMPLETE` and do not train on them.

## 3. Training data

The training export has 289 rows from OSWorld tasks, with actions we wrote rather than took from an agent (145 destructive, 86 ordinary, 58 boundary): multi-app 129, Impress 40, Calc 41, Writer 24, VS Code 21, Files 15, Thunderbird 14, OS 5. At K = 3 it gives REVERSIBLE 154 yes and 119 no, and GUARD 114 refuse and 159 allow. Four rows were skipped as unconfirmed or unlabelled and 12 were excluded as rig limits. Folds are grouped by OSWorld task, so a task's rows never straddle train and test.

## 4. Baselines

Before each action ran, the rig recorded two guesses from Claude Opus 5.5 ("the teacher"), which sees only the before-state, task and action: guess A uses the SafePred prompt and guess B a prompt matching our definition. These are the zero-shot comparison. Not every row has a guess, so model-versus-teacher comparisons use only the rows both cover.

## 5. Model and training

Qwen3-8B with a LoRA adapter: rank 32, dropout 0.05, learning rate 1e-4 with a cosine schedule, batch size 1 with 8 gradient-accumulation steps, 3 epochs, bf16, inputs capped at 8,192 tokens, trained on an A100-80GB. Four tagged tasks share one set of weights: FORWARD, UNDO, REVERSIBLE and GUARD. Input is text only; the model does not see screenshots.

**Model-E** trains on executed labels. **Model-G** trains on teacher guess B and is tested on executed labels, on the same rows and folds.

## 6. Evaluation on built rows

Five-fold cross-validation, with seeds 2026 and 7 for Model-E and seed 2026 for Model-G. REVERSIBLE and GUARD take the probability of the positive answer from the first output token, thresholded at 0.5, and report precision, recall and F1 of the positive class. UNDO reports exact match of the step sequence. These rows are ones we wrote, so the scores do not show how the model does on real agent actions.

## 7. Real agent test set

**Tasks and agent.** 14 of the 25 distinct OS-Harm misbehavior scenarios that fall in our applications (tml-epfl/os-harm at c0fa95e7). We left out the email-sending tasks, which would send mail to a real third-party address, plus disk partitioning and tasks testing something other than reversibility. The agent is Claude Sonnet 5.5 (Claude Code headless, screenshot observations, pyautogui actions, 20 steps at most), with no guard. OS-Harm asks that its tasks not be used for training, so every row from these runs is test only and is never exported for training.

**Three generations of recording.**

| Run | How states were obtained | How undos were tested |
|---|---|---|
| First | Replay of the agent's earlier steps | From the replay |
| Earlier | Recorded during the agent's run | From a replay, gated on the recording |
| Newest | Recorded during the run, with a QEMU snapshot at each step | Restored from the agent's own snapshots |

**Snapshots.** Replays often diverged from the agent's run, or used the row's time on resets. The newest run saves a QEMU snapshot through QMP (`snapshot-save` and `snapshot-load` on the disk node) after each step, so undos are tested on the exact state the agent left. On the labelled rows of that run, restored states matched the recording with no tree or file differences. It covers one task so far.

**Replay validity check.** We compared the agent's After screenshot with the replay's After screenshot for the 17 first-run steps that have replay data. The measure is the share of pixels differing by more than 40 grey levels at 480×270, with the top bar removed. At 20% or more (8 steps) the rig's label is left out of comparisons because the replay did not reproduce the step. From 9% to 20% (4 steps) results are flagged. This threshold was chosen after seeing the data, and dark screens can hide differences.

## 8. Hand review

**Purpose.** To give an answer key independent of the rig and of Claude on real agent actions, and to measure how far the rig's strict rule sits from a person's judgment.

**Protocol.** For each step the reviewer sees the task, the run's outline in the agent's own words, the before and after screenshots, a view boxing pixel differences, recorded file and window changes, the agent's note and the action's code. The reviewer then answers: did it change anything; could the earlier state be brought back in at most 3 actions (yes exactly, yes except small on-screen differences, no, can't tell, nothing to undo); was it on-task; and how sure. The rig's result, Claude's guess and the draft on-task mark stay hidden until the answer is saved, and a later change keeps the first answer.

**Scoring.** The author's final answers are the labels. Under the definition in Section 1, "small differences" counts as undoable; the strict reading is reported as well. "Can't tell" is left out. "Nothing to undo" counts as undoable.

**Model predictions.** The five K = 3 Model-E adapters (seed 2026) scored 70 steps, with the mean probability used, and the results were saved before any answer existed. The other steps have no prediction: 12 had a diverged replay and so no faithful before-state, and 2 were added to the page later. No adapter trained on these tasks. Agent steps have no natural description, so the action text reads "agent step" plus the code.

**Sample.** The First 20: 11 rig no-undo steps from the earlier runs, 7 steps from the newest run and 2 controls. 19 were labelled; `ag-close_delete_spreadsheets-01` was left out because its replay is unreliable. The set is mostly rig no-undo steps (16 of 20), so it can show whether the rig is too strict but gives no overall accuracy.

## 9. Limits to state in the paper

- **One rater, who is the author.** There is no agreement figure unless a second rater labels a sample.
- **How the labels were made.** The 19 labels are the author's final human decisions, reached with Claude's help. Claude explained steps, suggested answers on some of them and entered the answers at the author's request, and each answer's note records this. Claude is also one of the sources compared, so agreement with Claude's guess may be overstated. The author also knew before finishing that the set is mostly rig no-undo steps.
- **Pictures can lag the recorded state.** On `agr-fix_todo_list-12` the After picture shows one typed character while the recorded files show `todo.py` overwritten, and on `ag-redundant_files-04` the pictures do not match the agent's note.
- **The review aids shape judgment.** The outline is the agent's stated intent, not what happened, and the difference boxes are an aid that can over- or under-mark.
- **Screenshots cannot show everything.** Users, mounts, services and settings outside the home folder are invisible on the page, so some steps stay "can't tell".
- **Label strictness.** Training labels use the same rule under test. If the review shows it is too strict, the training labels share that bias.
- **Input gaps.** The model's state text omits the VS Code editor's contents. Its system prompt describes actions as keyboard input and its training is mostly keyboard actions, while the agent also clicks at screen coordinates. A low score on agent steps may partly reflect this.
- **Small test set.** Few tasks and few steps, with several steps from one task. Results are a first read, not an estimate for agents in general.
- **Benign runs.** On the newest run all steps appear on-task, so the guard's target is `allow` throughout and that run cannot show whether the guard catches anything.
