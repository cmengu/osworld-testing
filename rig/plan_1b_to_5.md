# Steps 1b–5: what each one fixes (6 Nov 2026)

**Goal:** before each agent step, predict what it will change. Stop the step if it can't be undone and isn't part of the task. If a step that ran turns out wrong, roll it back.

The diagram shows the loop. Each note on the right is a known gap and the step that addresses it.

```
  agent proposes a step
          │
          ▼
  ┌──────────────────┐   STEP 4 · we can't see web app data (mail, shop, booking)
  │ 0. READ STATE    │◄─ OSWorld 2.0 adds ~1.4 sends/submits/payments per task
  │ tree · windows · │   STEP 3 · blind spots: VS Code text, terminal effects
  │ file digests     │
  └────────┬─────────┘
           ▼
  ┌──────────────────┐   STEP 1 DONE · exact file set 85%, content 90%,
  │ 1. FORWARD       │                 no-change 97%
  │ predict change   │   STEP 3 · windows and dialogs weak (F1 0.51)
  └────────┬─────────┘
           ▼
  ┌──────────────────┐   STEP 1b · the change list doesn't say whether lost content
  │ 2. REVERSIBLE    │   survives somewhere (undo history, open editor, Trash, a move)
  │ undo in ≤ 3?     │   rule on the change 77–81% vs trained answer 92%
  └────────┬─────────┘
           ▼
  ┌──────────────────┐   STEP 3 · where Claude still wins: reversible saves in
  │ 3. GUARD         │   Impress/VS Code, rm of a file open in VS Code,
  │ block if one-way │   Thunderbird deletes and discards it lets through
  │ AND off-task     │   now 0.907 vs Claude 0.882 (a tie, p 0.70)
  └──┬────────────┬──┘
   allow        block ──► ask the user
     ▼
  step runs … and turns out wrong
     ▼
  ┌──────────────────┐   STEP 2 · the undo writer doesn't use the predicted change
  │ 4. UNDO          │   model 70/99 vs Claude 77/99 (86/99 with check-and-retry)
  │ write rollback   │
  └──────────────────┘

  STEP 5 · the whole loop on real agent mistakes (OSWorld 2.0 desktop tasks):
           are bad steps caught, are good steps rarely blocked, does the rollback work?
```

| Step | Link it fixes | It passes if | If it passes | If it fails | Cost |
|---|---|---|---|---|---|
| **1b** | FORWARD → REVERSIBLE | a rule on the predicted change (plus "content survives at X") reaches about 92% | every block comes with a reason: "the unsaved text is lost" | keep the trained answer for decisions; FORWARD only explains | ~4 USD |
| **2** | FORWARD → UNDO | feeding the predicted change to the undo writer gets ≥ 77/99 | the 8B model does all four jobs, no Claude call | Claude writes undos (86/99 with retry); our model is the guard | 5–10 USD |
| **3** | weak spots in READ, FORWARD, GUARD | targeted rows clearly beat Claude's 0.882 | a significant guard win over Claude | the limit is what the model can see: fix the reader, not the row count | 5–10 USD |
| **4** | READ for web apps | the rig reads web app data well enough to label | guard covers OSWorld 2.0 web actions | fixed rule: always ask before send, pay or submit | ~2 USD to try |
| **5** | the whole loop | catches bad steps, few false blocks, task success unchanged, rollback works | the paper's main result | too many blocks → train on-task judgement; misses → back to 1b or 3 | design first |

Every "fails" branch still tells us which part is the bottleneck: prediction, decision, undo or input.
