# OSWorld rig — start here (written 16 Oct 2026)

Paper: Claude Doc "World Models for OS-Agent Safety", tab "Paper draft" (Appendix A = open items).
Memory note: ~/.claude/projects/-Users-ngchenmeng/memory/reference_gui_world_models_scan_2026_10_13.md

## State on 16 Oct
- App decided: LibreOffice Calc. 47 OSWorld Calc tasks; 44 graded by compare_table against an expected
  workbook, so the on-task flag is derivable from expected-vs-initial diff.
- Rig: OSWorld/ (clone of xlang-ai/OSWorld, Aug 2026) with the Modal provider. Modal workspace ngchenmeng1,
  app `osworld`, volume `osworld-vm-images` (Ubuntu.qcow2). One sandbox = 4 cores, 8 GiB, about $0.76/h,
  2 h lifetime by default (env MODAL_SANDBOX_TIMEOUT). No snapshot revert on Modal: a clean state means
  re-running task setup (env.reset) or a new sandbox. Boot to desktop 163 s, task setup done 281 s.
- Calc a11y tree (task 357ef137): raw ~270K tokens; OSWorld-filtered ~17.7K tokens; 726 of 820 lines are
  table cells. Decision: tree supplies window chrome, sheet enters as a compact dump of non-empty cells.
  Probe: calc_tree_probe.py, outputs in calc-tree/.
- Two agent paths: `--model claude-sub` (your Claude Code subscription wrapper, used in Sep, untouched) and
  mm_agents/anthropic (direct API). The API scaffold was patched on 16 Oct for computer_toolset_20260801
  (needed by Sonnet/Opus 5.5 on the Claude API); diff in toolset-patch.diff, offline test toolset_test.py,
  backups *.orig-20261016. Not yet run live: needs ANTHROPIC_API_KEY.
- tmux session `rig` exists (detached, cwd OSWorld/) for long runs.
- OSGuard data request drafted: osguard-data-request.md (not sent).

## Next
1. Recorder: after every action capture a11y tree (controller.get_accessibility_tree), screenshot, file
   digest (hash/size/mtime under home + LibreOffice profile, saved bytes of the open doc) and window list,
   via the VM's command endpoint. Write one JSON per snapshot.
2. Mask: 20 idle snapshots + 20 no-op replays on the same state; diff trees and digests; mask = everything
   that changes without an action (clocks, selection/focus attrs, LibreOffice registry/cache files).
3. Smoke test: 20 Calc click-spots x 3 replays; each replay = env.reset(task) + action + snapshot; pass if
   masked states agree in >= 90% of click-spots. Run in tmux `rig` across several sandboxes; log JSONL, resumable.
4. Then click-spot generator + undo tiers, 20-row dry run, 300-row pilot, H1 readout, HPC training bundle
   before ~31 Oct.
