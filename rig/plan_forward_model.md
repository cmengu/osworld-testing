# Plan: a symbolic FORWARD world model (9 Nov 2026)

Author's ask (9 Nov): "how can we make this symbolic world model stronger ... it should predict the future state, not
[just] undo it ... elaborate and really plan it out".

## 1. Goal in one paragraph

Today `rig/symbolic.py` + `rig/symbolic_gui.py` jump from (state, action) straight to a verdict (no-op / undoable /
one-way). The stronger model predicts the **next state**: `T(s, a) -> s'`. Everything the guard needs is then derived
from the prediction, not hand-written: **harm** (content in `s` that exists nowhere in `s'`), **reversibility** (a
sequence of at most K = 3 actions that maps `s'` back to `s`, found by searching the model itself), and the **revert
plan** (that sequence, or a backup taken before the step when no sequence exists). The model stays symbolic and
inspectable, and it grows from data: where a prediction misses a recorded transition, a new rule is proposed and kept
only if the recorded data confirms it.

## 2. Where we start (facts, 9 Nov)

| Item | Number |
|---|---|
| Pair test (32 rig-checked pairs) | hybrid 30/32, Claude 28/32, learned model 11/32 |
| Verdict accuracy on 346 rig-labelled rows | 97% when deciding, decides 66% |
| Coverage of 209 real agent steps | decides 78% |
| Learned FORWARD head (6 Nov) | file effects 85% exact, windows weak |
| Recorded row transitions (before-state S, action, after-state S1) | **974** |
| Undo candidates tried by the rig (reset to S', undo, judged) | **5,781** (910 with a saved state) |
| Recorded agent states (consecutive pairs = real transitions, unlabelled) | **363** (TEST ONLY: OS-Harm) |

## 3. The model

### 3.1 State `s`
| Part | Content | Source in the recording |
|---|---|---|
| Files | path -> content hash, size, mode, owner; folders; links | `digest.json` |
| Trash | files in `~/.local/share/Trash/files` + their original paths (`info/*.trashinfo`) | `digest.json` |
| System | users, groups, auto-login, mounts, packages hash, crontab, sudoers.d hashes, hosts | `system.json` |
| Windows | open windows: app, title, the document each holds | `windows.txt`, tree frames |
| Documents | per open document: path, unsaved-changes flag (VS Code `●`, LibreOffice modified indicator), buffer symbol | tree |
| Dialogs | the open question (save changes / delete / empty Trash / replace / other) and its buttons | tree alerts |
| Focus | the window and control that receive keys | tree `focused` |
| Symbols | values the state cannot know, written as names: `BUF(doc)`, `OUT(cmd)`, `NEW` | none |

### 3.2 Action `a`
Parsed once into a small action language (already half there in `symbolic_gui.events`): `shell(cmd)`, `key(k)`,
`hotkey(k)`, `type(text)`, `click(element)` with the element resolved from the tree, `wait`.

### 3.3 Transition `T(s, a) -> s'`
A list of **rules**. Each rule has a guard (when it applies) and an effect (a state delta), e.g.

```
rule rm_file:      shell("rm F")      if F is a file      -> files - {F}
rule mv_rename:    shell("mv A B")    if B free           -> files[B] = files[A]; files - {A}
rule save_doc:     hotkey(ctrl+s)     if focus doc D dirty -> files[path(D)] = BUF(D); D.dirty = False
rule close_dirty:  hotkey(ctrl+w)     if focus doc D dirty -> dialog = save-changes(D)
rule dont_save:    key(alt+n)         if dialog save-changes(D) -> windows - {D}; BUF(D) lost
rule files_delete: key(delete)        if Files, selection X -> trash += X with origin; files - {X}
```
A step whose action no rule covers yields `s' = UNKNOWN`. The guard then hands it to Claude, as today.

### 3.4 What is derived from `T`
| Question | Derivation |
|---|---|
| What changes? | `delta(s, s')` |
| Harm (content destroyed) | any hash or symbol in `s` (files, Trash, `BUF`) present nowhere in `s'` |
| Reversible within K? | breadth-first search over candidate inverse actions (from the same rule set: inverse rules, Ctrl+Z, Escape, reopen, restore from Trash, re-save), applying `T` symbolically, until a state equal to `s` (same equality as `rig/mask.py`) |
| Revert plan | the sequence the search found; if none, a **backup action** before the step (copy the files whose content would be destroyed, `crontab -l > f`, `cp /etc/x`) that makes the step undoable |

## 4. Data and splits (fixed before any scoring)

| Split | What | Used for |
|---|---|---|
| **DEV** | rig rows from runs before 8 Nov (pilot, v2-v5, probe, step 3; about 900 transitions) + training pairs `pt_*` | writing and inducing rules |
| **TEST-RIG** | pair rows `pr_*`, `prr_*`, `prx_*`, `pq_*` (TEST ONLY) | scoring only |
| **TEST-AGENT** | OS-Harm agent states (TEST ONLY, canary) | scoring only (coverage, agreement with Claude) |
| **TEST-FRESH** | a new labelled run of families written after the rules freeze (step P5) | the honest generalisation number |

No rule may be written or induced while looking at TEST rows. A rule-induction run reads DEV only, and its prompt and
the accepted rules are logged.

## 5. Phases

### P1. Forward model and its score (free, offline, about 1 day)
- Refactor the current rules into `rig/world/` (`state.py`, `actions.py`, `rules/*.py`, `T.py`).
- `rig/world/score_forward.py`: for every recorded transition, predict `s'` and compare it with the recorded S1 using
  the rig's own equality (masked files, window titles, dialogs).
- Metrics, per family and overall: **coverage** (share not UNKNOWN), **file-delta exact** (the predicted set of changed
  paths and their new hashes or symbols equals the recorded one), **path F1**, **window-set exact**, **dialog exact**,
  **system exact**.
- Baselines on the same transitions: "nothing changes"; the learned FORWARD head (k3_v6w); Claude asked to predict the
  change set (same text state, structured answer).
- **Pass line (pre-registered):** on DEV, file-delta exact >= 90% where it decides, and higher than the learned head's
  85%; coverage >= 70%.

### P2. Derived reversibility and revert plans (free, offline, about 1 day)
- `rig/world/undo_search.py`: BFS over inverse candidates using `T` only.
- Score the verdicts against rig labels (346 rows + the pair test). Score the plans against the 5,781 recorded
  candidates: does the model predict which candidates restored S, and which failed?
- Replace the hand-written verdicts in `symbolic.py` with the derived ones once they match or beat them.
- **Pass lines:** verdict accuracy >= the current 97% at no lower coverage; candidate outcome (restores S or not)
  predicted right on >= 90% of recorded candidates it covers.

### P3. Rule induction (subscription only, about 1-2 days)
- Loop on DEV misses: cluster the transitions the model gets wrong or calls UNKNOWN; for each cluster, Claude
  receives (state excerpt, action, recorded delta) and writes one rule in the rule format; the rule is **accepted only
  if** on DEV it fixes at least N transitions and breaks none (regression check over all DEV transitions).
- Keep a ledger: rule, who proposed it, the transitions it explains, date.
- Report learning curves: coverage and exactness on TEST-RIG after each accepted batch (TEST is read only for the
  curve, never by the inducer).
- **Pass line:** TEST-RIG coverage +10 points with exactness unchanged or better.

### P4. Multi-step rollouts and the revert guard (free to build; live pilot about 5 USD, needs a yes)
- Rollouts: apply `T` along an agent's planned sequence (or the next step plus the guard's assumptions) and report the
  first step at which content is destroyed.
- Guard in `rig/guard_live.py`: `T` first; one-way and off-task -> block, or **back up then allow** (the backup action
  from 3.4) and log the revert plan; UNKNOWN -> Claude as today.
- Live pilot: 2 OS-Harm tasks x 2 arms (hybrid-revert guard vs Claude guard) plus the planted bad steps
  (`rig/planted_catch.py`). Measure catch, false blocks, Claude calls avoided, latency, and **revert success** (after a
  planted bad step was allowed with a backup, does the revert plan restore S, checked by the rig).

### P5. Fresh test for the write-up (about 15 USD, needs a yes)
- 20-30 new pairs and 40 GUI rows from families written after the rules freeze. Score `T` exactness, verdicts, revert
  success; compare hybrid vs Claude with the pre-registered pair rule.

## 6. Risks and how we handle them

| Risk | Handling |
|---|---|
| Overfitting rules to the families we test on | DEV/TEST split by run; TEST-FRESH written after freeze; the inducer never sees TEST |
| Rig labels are themselves wrong (seen 9 Nov: the systemctl bug) | the forward model flags disagreements; each one is checked by hand before it counts against the model |
| Window and app state is noisy (LibreOffice recovery, VS Code reloads) | separate metrics for files, system, windows; rules may predict "window changes, details UNKNOWN" |
| Symbols leak (a `BUF` with unknown content) | harm and equality treat symbols as opaque but trackable; a symbol destroyed is harm |
| Coverage stalls on long-tail GUI | that tail stays with Claude; we report the split honestly |
| Cost | P1-P3 offline and free (P3 uses the subscription); P4/P5 need explicit yes |

## 7. Deliverables and order

| Order | Deliverable | Cost | Needs |
|---|---|---|---|
| 1 | P1 forward model + `score_forward.py` + numbers vs learned head and Claude | free | go |
| 2 | P2 derived reversibility + revert plans, scored on labels and candidates | free | - |
| 3 | P3 rule-induction loop + ledger + learning curve | subscription | - |
| 4 | P4 revert guard + live pilot | ~5 USD | yes |
| 5 | P5 fresh test | ~15 USD | yes |
