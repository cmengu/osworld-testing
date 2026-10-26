# Live evaluation: where the guard hooks into OSWorld (26 Oct 2026)

Read-only survey of the OSWorld checkout under `OSWorld/` for the paper's Section 6.5 (guard before every agent action). No code was changed.

## Hook point
- Generic loop: `OSWorld/lib_run_single.py:14-74` (`run_single_example`). Inside `for action in actions:` (line 36) the call `env.step(action, args.sleep_after_execution)` is at line 40. The guard goes between lines 39 and 40: `obs` still holds the pre-action observation; fresh copies via `env.controller.get_accessibility_tree()` / `get_screenshot()`.
- Observations: `desktop_env/desktop_env.py:337-345` `_get_obs()` returns screenshot PNG bytes and the raw a11y XML (`/accessibility`, `.json()["AT"]`) when `require_a11y_tree=True`. `get_accessibility_tree` (`controllers/python.py:129-149`) has no request timeout (the rig once hung 80 min on it).
- The Claude runner is `OSWorld/scripts/python/run_multienv_claude.py` (AnthropicAgent at 268-287; action space `claude_computer_use`; env hardwired to AWS image map; Modal not in its provider list although `desktop_env/providers/modal/` exists and the rig uses it).

## Returning a refusal to the Claude agent
- `OSWorld/mm_agents/anthropic/main.py` (locally modified; `.orig-20261016` backups). `predict()` returns `(reasonings, actions)`; each action is `{"name","input","id": tool_use_id,"action_type":"tool_use","command": <pyautogui code>,"raw_response"}` (lines 931-981); `parse_actions_from_tool_call` 286-511.
- Tool results are written lazily at the start of the NEXT `predict()` (575-656): line 644 hardcodes `self.add_tool_result(tool_block["id"], "Success", ...)`. `add_tool_result` (170-210) never sets `is_error`. The zoom-error path (606-612, 631-637) already returns an error string: copy that pattern.
- Plan: (1) `agent.pending_results: dict[tool_use_id -> str]` filled by the guard; (2) line 644 uses `pending_results.get(id, "Success")`, optionally `is_error: True`; (3) skip `env.step` for refused actions; (4) log the verdict beside the action in `traj.jsonl` (or `guard.jsonl`).
- AnthropicAgent uses only `obs["screenshot"]`; a tree-based guard must set `require_a11y_tree=True` or fetch the tree itself. Model ids in `mm_agents/anthropic/utils.py:68-97` include claude-sonnet-5-5 / claude-opus-5-5 / claude-haiku-5-5 (toolset `computer_toolset_20260801` for 5.5).
- `PromptAgent` (`mm_agents/agent.py`, claude branch 656-710) and the local `claude_sub_agent.py` have no tool results: a refusal goes into the next prompt's history instead.

## Execution and results
- Action space assert in `desktop_env.py:183-189`; `step()` 416-456: WAIT/FAIL/DONE handled locally, pyautogui-style commands go to `PythonController.execute_python_command` (`controllers/python.py:195-222`) which POSTs to `/execute` (server `desktop_env/server/main.py:76-118`, "without any safety checks").
- Evaluation `desktop_env.py:369-414, 458-524`: `evaluator.func` metrics under `desktop_env/evaluators/metrics/*`, getters under `getters/*`, `postconfig` run first; infeasible tasks score 1 only if the last action was FAIL.
- Output layout `result_dir/<action_space>/<obs_type>/<model>/<domain>/<example_id>/`: `step_{n}_{ts}.png`, `traj.jsonl` (step_num, action_timestamp, action, response, reward, done, info, screenshot_file), `result.txt`, `runtime.log`, `recording.mp4`; `lib_results_logger.py` for results.json. Resume logic deletes folders without `result.txt`.

## What the rig already shares with OSWorld
- The rig builds `DesktopEnv(provider_name="modal", action_space="pyautogui")` and uses the same port-5000 server: `/execute` (rig/vm.py:55 `vm_shell`), `/accessibility` (snapshot.py:181 fallback), `/file` (fasttree.py:250), `/screenshot` via the controller; `env.step` ~22 call sites, `env.reset` ~12. `/run_bash_script` is broken in this image.
- Closest existing pre-action model call: `rig/collect_pilot.py:558-575` (teacher guess before `env.step`), state text from `rig/compact.py`.
- No hook, callback or guard exists in OSWorld. Only `run_single_example_vlaa_gui` (lib_run_single.py:873+) has a second-model check (gates DONE, not each action): a template for reject-and-continue.

## Tasks
280 task JSONs in our domains: writer 23, impress 47, calc 47, vs_code 23, thunderbird 15, multi_apps 101, os 24. Config step types: download 249, open 154, launch 149, execute 132, activate_window 36, command 29. Top evaluators: compare_table 61, compare_pptx_files 49, check_include_exclude 21, compare_docx_files 16, infeasible 13, exact_match 13, compare_pdfs 11.
