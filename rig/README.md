# rig — recorder, mask, smoke test

Deterministic plumbing, no model involved. Run everything from `~/ai-research/osworld-testing`
with the OSWorld virtualenv, long runs inside `tmux attach -t rig`.

| Piece | File | What it does |
|---|---|---|
| VM access | `vm.py` | run a shell script inside the VM through the server's `/execute` route (`/run_bash_script` is broken in this image) |
| Fast tree | `fasttree.py` | the server's own node builder, run inside the VM in parallel over LibreOffice's top-level parts; desktop-shell internals skipped; failing nodes dropped and counted |
| Recorder | `snapshot.py` | after an action: tree (fast, server walk as fallback), file digest of `$HOME` (size, raw hash, metadata-free content hash for office files), window list, screenshot → one directory |
| Tree diff | `treediff.py` | tree → `path -> {attr: value}` with geometry and focus flags dropped; exact differences between two trees |
| Mask | `mask.py` | union of everything that differs between snapshots of one unchanged state (attribute flicker, come-and-go subtrees, churn sites, flickering files); apply + compare |
| Fresh start | `freshstart.py` | close LibreOffice, clean locks/recovery, restore cached task files, relaunch, wait, maximise (~30 s); falls back to `env.reset` |
| VM quieting | `vmprep.py` | gsettings: no banners, no screen lock, no auto-updates |
| Mask run | `collect_mask.py` | one sandbox: idle snapshots, no-op inputs, fresh restarts → `out/mask_run/mask.json` |
| Smoke test | `smoke.py` | 20 Calc click-spots × 3 fresh-start replays; pass if ≥ 90% agree after masking; resumable |
| Click-spots | `clickspots_calc.json` | keyboard-only Calc actions (no coordinates, so they replay exactly) |
| Offline test | `test_offline.py` | parser, differ and mask on the real Calc tree in `../calc-tree/` |
| Dev probes | `dev_probe.py`, `debug_fasttree.py` | spare-sandbox checks of timing, fresh start and the fast tree |
| Pilot recipe | `make_clickspots.py` → `clickspots_pilot.json` | 24/14/14 single-step spots + 4 two-step sequences × 5 workbooks = 300 rows; on-task flag from the expected-vs-initial workbook diff (3.4); seed from the row id |
| Pilot collector | `collect_pilot.py` | per row: fresh start, S, action, S', four-tier undo search (budget ~55, first match on masked tree + file digest), confirming replays, JSONL rows (4.7); `--recompare` re-judges rows on disk after a rule change |
| Undo tiers | `undo.py` | generic, Calc-specific, blind pairs; the step language (`key:`, `type:`, `wait:`, `reopen`, `menu:`) shared with the proposer |
| Proposer (tier 3) | `proposer.py`, `prompts/proposer.txt` | GPT-6.1 Sol via the OpenAI API (fallback GPT-5.6 Sol), key from `.env` |
| Teacher guesses | `teacher.py`, `prompts/` | Guess A = SafePred App. G verbatim (`safepred_appendix_g_template.txt` + `safepred_fill.json`), Guess B = five-part definition prompt; headless `claude -p`, Opus 5.5, model id logged; both asked before the action runs |
| Compact state | `compact.py` | window chrome + non-empty cells + home files, for the teacher and the proposer |
| Menu probe | `probe_menus.py` | screenshots of the menus/dialogs the spots use; confirms mnemonics before the pilot |

```bash
cd ~/ai-research/osworld-testing
OSWorld/.venv/bin/python -I rig/test_offline.py                                   # no VM, seconds
OSWorld/.venv/bin/python -I rig/collect_mask.py --idle 10 --noop 10 --restarts 5  # one sandbox
OSWorld/.venv/bin/python -I rig/smoke.py --replays 3                              # one sandbox, resumable
OSWorld/.venv/bin/python -I rig/smoke.py --compare-only                           # re-judge what is on disk
OSWorld/.venv/bin/python -I rig/rebuild_mask.py                                   # rebuild mask.json after a mask.py change
OSWorld/.venv/bin/python -I rig/make_clickspots.py                                # regenerate clickspots_pilot.json (prints the tallies)
OSWorld/.venv/bin/python -I rig/probe_menus.py                                    # one sandbox, ~10 min: menu/dialog screenshots
OSWorld/.venv/bin/python -I rig/collect_pilot.py --rows 90,79,121 --dry           # plan + worst-case cost, no VM
OSWorld/.venv/bin/python -I rig/collect_pilot.py --rows 90,79,121 --row-minutes 45 # one sandbox; resumable; results in rig/out/pilot_run/
OSWorld/.venv/bin/python -I rig/collect_pilot.py --recompare                      # re-judge rows on disk after a treediff/mask rule change
```

Comparison rules (`treediff.py`, `mask.py`) change only under the four conditions of Paper draft 4.3 (a class of
node, never a row; non-content nodes only; every row re-compared and flips reported; logged with the trigger
row). Log every such change in `rig/out/pilot_run/rules_log.md` and run `--recompare`.

Every live script closes its sandbox in a `finally`; if a run is killed, check `modal container list`.
