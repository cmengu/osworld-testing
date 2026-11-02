# The draft's hypotheses on recorded results, and the free checks (2 November 2026)

Read-only apart from the settling fix. Numbers: `rig/agentrun/hypotheses_20261102.json`, from `rig/train/score_hypotheses.py`. Built rows only (v3 export, K = 3). Earlier reports quoted F1 instead of these tests.

| Test | Threshold in the draft | Result | Reading |
|---|---|---|---|
| **H1** guessed vs executed labels | Agreement on the no-undo class below 90%, every frontier model, definition-matched prompt | 82.5% (85 of 103), Claude Opus 5.5 only | Met for the one model tested |
| **H2** executed labels train a better guard | Recall at least 10 points above Model-G at 5% false refusal | E 79.8%, G 64.9%: +14.9 points. Seed 7: +10.5. 95% interval by task, about -12 to +36 | Clears the margin as a point estimate; **not supported** under the draft's rule that a margin smaller than its interval is not support |
| **H3** trained undo beats zero-shot | Rollback at least 15 points above the best zero-shot | Not testable: model undos never executed. Exact match 60%; zero-shot rollback 44% (55 of 125, 37 not executed; 55 of 88 executed); Ctrl+Z 23% | Open; needs the model's undos run on the VM |
| **H4** live test | Fewer irreversible events | Not run | Open |

**Limits:**

- H1: a miss may partly reflect no-undo being a lower bound, though section 3 of `steps_1_to_3_20261102.md` found real file differences. 57 rows have no guess.
- H2: Model-G has one seed; Model-E two. The gap narrows at higher false-refusal rates (+3.5 points at 8%). Model-E without written descriptions gives +17.6.
- Thresholds were read on data already seen, as drafted before collection.

## Free checks

- **Editor text:** training VS Code rows do not have it. Their trees read "The editor is not accessible at this time": screen-reader mode was off then, and is on in agent rows. The fix needs rendering plus recollecting 19 VS Code rows, about 8.5 USD, not a cheap retrain as first hoped.
- **Settling wait:** threshold lowered from 70% to 60% idle, and replays used as resets now wait at most 15 seconds. Offline tests pass; still untested on a VM.
- **SafePred-8B: not run.** The weights are public, but it expects policies, a trajectory, the agent's reasoning and its own state format, and returns policy violations rather than a reversibility answer. A fair run is more work than expected: about 1 to 2 hours of setup and about 2 USD on an A100, by estimate. A rushed version could be unfair to it.
