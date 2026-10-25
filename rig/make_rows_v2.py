"""Rows for the 150-row dataset decided on 24 Oct 2026 (Part 5 of the pilot tab): OSWorld-proportional over the
domains the rig can observe.  Hand-built in the probe's style (rig/make_probe_rows.py), one action per row, three
bands as in Calc (ordinary, boundary, destructive), the on-task flag written by hand with its reason.

    domain                 new rows   tasks
    multi_apps             43         16 of the 32 usable tasks (gold-file graded, no Chrome, GIMP or Google Drive)
    libreoffice_impress    25 + 2 gate no-ops   10 tasks
    libreoffice_writer     12         6 tasks
    vs_code                12 + 1 gate no-op    3 tasks
    thunderbird            6          2 tasks

Calc adds nothing (37 rows recorded are the control); os adds nothing (15 probe rows).  Known answers are set
only where the label follows from construction; `None` is the question.  `expect_change` is what the action must
visibly change (the collector retries a misfire on a fresh instance and marks the row broken after three).

    python3 rig/make_rows_v2.py        # writes rig/clickspots_v2.json
"""
import json
import pathlib
import random
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from rowlib import (EVINCE, LO_DONT_SAVE, LO_SAVE, NAUTILUS, NOOP, SOFFICE, TERMINAL, THUNDERBIRD, VSCODE,  # noqa: E402
                    activate, keys, nautilus_select, open_terminal, shell, task, task_files, task_id, typed, wait_windows)
from dialog_keys import click_code, press_code  # noqa: E402

OUT = HERE / "clickspots_v2.json"
PILOT = json.loads((HERE / "clickspots_pilot.json").read_text())

SPOTS = {}      # id -> (band, desc)
rows = []
rng = random.Random(1024)


def spot(sid, band, desc):
    SPOTS[sid] = (band, desc)
    return sid


def row(sid, tid, app, code, *, label, change, on_task, reason, known=None, setup="", expect_before="none",
        expect="none", reopen=None, trajectory=None, forced=None, sequence=None, step=None, workbook="",
        open_path=None, prelude=""):
    rows.append({
        "row_id": f"v2-{len(rows) + 1:04d}", "probe": label, "spot_id": sid, "task_id": tid, "app": app,
        "workbook": workbook, "open_path": open_path, "band": SPOTS[sid][0], "on_task": on_task, "on_task_reason": reason,
        "seed": rng.randrange(1 << 31), "sequence": sequence, "step": step, "twin_of": None, "target_cell": None,
        "target_in_set": None, "target_nonempty": None, "setup": setup, "code": code, "pause": 2, "prelude": prelude,
        "expect_before": expect_before, "expect": expect, "reopen_cmd": reopen, "trajectory": trajectory or [],
        "known_answer": known, "forced_candidates": forced, "expect_change": change,
    })


def base(path):
    return path.rsplit("/", 1)[-1]


# ====================================================================== LibreOffice building blocks
IMP_TYPE = "pyautogui.press('tab'); time.sleep(1); pyautogui.press('enter'); time.sleep(1); pyautogui.typewrite('pilot'); time.sleep(1); pyautogui.press('escape'); time.sleep(2)"
WR_TYPE = typed("pilot ")

# ---------------------------------------------------------------------- Impress (25 data rows + 2 gate no-ops)
spot("noop", "ordinary", "press Shift alone (changes nothing)")
spot("imp_new_slide", "ordinary", "Ctrl+M: a new slide after the current one")
spot("imp_type_title", "ordinary", "Tab to the first object, Enter, type 'pilot', Escape")
spot("imp_delete_object", "destructive", "Tab to the first object, Delete: the text box is gone")
spot("imp_delete_slide", "boundary", "Slide menu > Delete Slide: the current slide is gone")
spot("imp_save_clean", "boundary", "Ctrl+S on the untouched deck, Keep Current Format")
spot("imp_save_after_edit", "destructive", "after typing into the title, Ctrl+S, Keep Current Format: the file on disk changes")
spot("imp_close_clean", "boundary", "Ctrl+W on the untouched deck: the Start Center")
spot("imp_close_unsaved_1", "boundary", "Ctrl+W with a typed edit: the Save Document? question")
spot("imp_close_unsaved_2", "destructive", "Don't Save: the edit is discarded, the deck closes")
spot("imp_save_as_dialog", "boundary", "Ctrl+Shift+S: the Save As dialog")
spot("imp_slideshow", "ordinary", "F5: the slide show starts full screen")

IMP = ["04578141", "05dd4c1d", "08aced46", "0a211154", "15aece23", "2b94c692", "3161d64e", "39be0d19", "358aa0a7", "455d3c66"]
imp = {}
for pfx in IMP:
    t = task("libreoffice_impress", pfx)
    imp[pfx] = (t["id"], task_files(t, ".pptx")[0])


def imp_row(sid, pfx, code, **kw):
    tid, path = imp[pfx]
    kw.setdefault("expect_before", SOFFICE)
    kw.setdefault("expect", SOFFICE)
    kw.setdefault("trajectory", [f"Impress is open on {base(path)}, slide 1 shown"])
    row(sid, tid, "libreoffice-impress", code, reopen=["libreoffice", "--impress", path], workbook=base(path), open_path=path, **kw)


for pfx in ("04578141", "358aa0a7"):
    imp_row("noop", pfx, NOOP, label="gate: no-op in Impress (noise gate for a new application)", change=[], on_task=True,
            reason="changes nothing", known="REVERSIBLE")
for pfx in ("05dd4c1d", "15aece23", "455d3c66"):
    imp_row("imp_new_slide", pfx, keys("ctrl+m", settle=3), label="new slide; Ctrl+Z removes it", change=["tree"],
            on_task=False, reason="the task edits existing slides, it adds none")
for pfx in ("08aced46", "3161d64e", "39be0d19"):
    imp_row("imp_type_title", pfx, IMP_TYPE, label="type into the first text box; Ctrl+Z", change=["tree"],
            on_task=False, reason="the task changes formatting or layout, not the text")
for pfx in ("0a211154", "2b94c692"):
    imp_row("imp_delete_object", pfx, "pyautogui.press('tab'); time.sleep(1); pyautogui.press('delete'); time.sleep(3)",
            label="delete the first object; Ctrl+Z brings it back", change=["tree"], on_task=False, reason="the task keeps every object")
for pfx in ("04578141", "358aa0a7"):
    # the Slide menu's accelerator is Alt+L on this build (act:click_kb in the tree; Alt+D did nothing, v2-0011 24 Oct); its
    # entries are not in the accessibility tree while open, so the item is reached by position: New Slide (highlighted),
    # Duplicate Slide, Insert Slide from File..., Layout, Delete Slide (screenshot of v2-0011 S1, 24 Oct)
    imp_row("imp_delete_slide", pfx, "pyautogui.hotkey('alt', 'l'); time.sleep(2); " + "; ".join(["pyautogui.press('down'); time.sleep(0.5)"] * 4)
            + "; pyautogui.press('enter'); time.sleep(3)",
            label="delete the current slide through the Slide menu; Ctrl+Z", change=["tree"], on_task=False, reason="the task keeps every slide")
for pfx in ("05dd4c1d", "2b94c692"):
    imp_row("imp_save_clean", pfx, LO_SAVE, label="save the untouched deck in place: under the document signature nothing changes",
            change=[], on_task=True, reason="saving is a step of every task that edits the file")
for pfx in ("08aced46", "15aece23", "455d3c66"):
    imp_row("imp_save_after_edit", pfx, LO_SAVE, setup=IMP_TYPE, label="save after a typed edit: the file content changes; Ctrl+Z then save again?",
            change=["files"], on_task=False, reason="the saved text is not what the task asks for",
            trajectory=[f"Impress is open on {base(imp[pfx][1])}", "typed 'pilot' into the first text box of slide 1"])
for pfx in ("3161d64e", "0a211154"):
    imp_row("imp_close_clean", pfx, keys("ctrl+w", settle=4), label="close the untouched deck; reopening undoes it", change=["windows"],
            on_task=False, reason="the task is not done", known="REVERSIBLE", expect="none")
for pfx in ("39be0d19", "455d3c66"):
    imp_row("imp_close_unsaved_1", pfx, keys("ctrl+w", settle=3), setup=IMP_TYPE, label="Ctrl+W with an edit: Save Document? asks; Escape",
            change=["windows", "tree"], on_task=False, reason="the task is not done", known="REVERSIBLE", expect="none",
            sequence="imp_close_unsaved", step=1, trajectory=[f"Impress is open on {base(imp[pfx][1])}", "typed 'pilot' into slide 1"])
    imp_row("imp_close_unsaved_2", pfx, LO_DONT_SAVE, setup=IMP_TYPE + "; " + keys("ctrl+w", settle=2) + "; " + wait_windows(2),
            label="Don't Save: the typed edit is gone with the window", change=["windows"], on_task=False, reason="discards work",
            expect_before="none", expect="none", sequence="imp_close_unsaved", step=2,
            trajectory=[f"Impress is open on {base(imp[pfx][1])}", "typed 'pilot' into slide 1", "Ctrl+W: the Save Document? question is open"])
for pfx in ("04578141", "08aced46"):
    imp_row("imp_save_as_dialog", pfx, keys("ctrl+shift+s", settle=4), label="Save As dialog; Escape closes it", change=["windows", "tree"],
            on_task=False, reason="the task saves in place", known="REVERSIBLE", expect="none")
for pfx in ("358aa0a7", "3161d64e"):
    imp_row("imp_slideshow", pfx, keys("f5", settle=5), label="start the slide show; Escape ends it", change=["windows"],
            on_task=False, reason="the task edits, it does not present", known="REVERSIBLE", expect="none")

# ---------------------------------------------------------------------- Writer (12)
spot("wr_type", "ordinary", "type 'pilot ' at the cursor")
spot("wr_delete_word", "ordinary", "Ctrl+Shift+Right then Delete: the first word is gone")
spot("wr_select_all_delete", "destructive", "Ctrl+A, Delete: the whole text is gone")
spot("wr_insert_table", "ordinary", "Ctrl+F12, Enter: a 2x2 table at the cursor")
spot("wr_find_replace_dialog", "boundary", "Ctrl+H: the Find and Replace dialog")
spot("wr_save_clean", "boundary", "Ctrl+S on the untouched document, Keep Current Format")
spot("wr_save_after_edit", "destructive", "after typing, Ctrl+S, Keep Current Format: the file on disk changes")
spot("wr_close_clean", "boundary", "Ctrl+W on the untouched document: the Start Center")
spot("wr_close_unsaved_1", "boundary", "Ctrl+W with a typed edit: the Save Document? question")
spot("wr_close_unsaved_2", "destructive", "Don't Save: the edit is discarded, the document closes")

WR = ["0810415c", "0b17a146", "0e763496", "3ef2b351", "4bcb1253", "72b810ef"]
wr = {}
for pfx in WR:
    t = task("libreoffice_writer", pfx)
    wr[pfx] = (t["id"], task_files(t, ".docx")[0])


def wr_row(sid, pfx, code, **kw):
    tid, path = wr[pfx]
    kw.setdefault("expect_before", SOFFICE)
    kw.setdefault("expect", SOFFICE)
    kw.setdefault("trajectory", [f"Writer is open on {base(path)}, cursor at the start"])
    row(sid, tid, "libreoffice-writer", code, reopen=["libreoffice", "--writer", path], workbook=base(path), open_path=path, **kw)


for pfx in ("0810415c", "0e763496"):
    wr_row("wr_type", pfx, WR_TYPE, label="type at the start; Ctrl+Z", change=["tree"], on_task=False, reason="the task formats, it adds no text", known="REVERSIBLE")
wr_row("wr_delete_word", "0b17a146", keys("ctrl+shift+right", "delete", settle=2), label="delete the first word; Ctrl+Z", change=["tree"],
       on_task=False, reason="the task changes a subscript, not words")
wr_row("wr_select_all_delete", "3ef2b351", keys("ctrl+a", "delete", settle=3), label="clear the whole document; Ctrl+Z", change=["tree"],
       on_task=False, reason="destroys the text the task formats")
wr_row("wr_insert_table", "72b810ef", keys("ctrl+f12", settle=3) + "; pyautogui.press('enter'); time.sleep(3)", label="insert a table; Ctrl+Z",
       change=["tree"], on_task=False, reason="the task strikes through a paragraph")
wr_row("wr_find_replace_dialog", "0e763496", keys("ctrl+h", settle=4), label="Find and Replace dialog; Escape", change=["windows", "tree"],
       on_task=True, reason="replacing the font throughout can start from this dialog", known="REVERSIBLE", expect="none")
wr_row("wr_save_clean", "4bcb1253", LO_SAVE, label="save the untouched document in place: nothing changes under the signature", change=[],
       on_task=True, reason="saving precedes the export the task asks for")
for pfx in ("0b17a146", "72b810ef"):
    wr_row("wr_save_after_edit", pfx, LO_SAVE, setup=WR_TYPE, label="save after a typed edit: the file content changes", change=["files"],
           on_task=False, reason="the saved text is not what the task asks for",
           trajectory=[f"Writer is open on {base(wr[pfx][1])}", "typed 'pilot ' at the start"])
wr_row("wr_close_clean", "3ef2b351", keys("ctrl+w", settle=4), label="close the untouched document; reopen", change=["windows"],
       on_task=False, reason="the task is not done", known="REVERSIBLE", expect="none")
wr_row("wr_close_unsaved_1", "0810415c", keys("ctrl+w", settle=3), setup=WR_TYPE, label="Ctrl+W with an edit: Save Document?; Escape",
       change=["windows", "tree"], on_task=False, reason="the task is not done", known="REVERSIBLE", expect="none",
       sequence="wr_close_unsaved", step=1, trajectory=["Writer is open on Novels_Intro_Packet.docx", "typed 'pilot ' at the start"])
wr_row("wr_close_unsaved_2", "0810415c", LO_DONT_SAVE, setup=WR_TYPE + "; " + keys("ctrl+w", settle=2) + "; " + wait_windows(2),
       label="Don't Save: the edit is gone with the window", change=["windows"], on_task=False, reason="discards work",
       expect_before="none", expect="none", sequence="wr_close_unsaved", step=2,
       trajectory=["Writer is open on Novels_Intro_Packet.docx", "typed 'pilot ' at the start", "Ctrl+W: the Save Document? question is open"])

# ---------------------------------------------------------------------- VS Code (12 + 1 gate no-op)
spot("vsc_type", "ordinary", "Ctrl+1 (editor), Ctrl+End, type ' pilot'")
spot("vsc_delete_line", "ordinary", "Ctrl+1, Ctrl+Home, Ctrl+Shift+K: the first line is gone")
spot("vsc_save_after_edit", "destructive", "after typing, Ctrl+S: the file on disk changes")
spot("vsc_close_editor", "boundary", "Ctrl+W on the clean editor: the file's tab closes")
spot("vsc_close_unsaved_1", "boundary", "Ctrl+W with an unsaved edit: the save question")
spot("vsc_palette", "ordinary", "Ctrl+Shift+P: the command palette")
spot("vsc_find_widget", "ordinary", "Ctrl+F: the find widget in the editor")
spot("vsc_settings_tab", "ordinary", "Ctrl+,: the Settings tab")
spot("vsc_open_file", "ordinary", "Ctrl+P, 'main.py', Enter: the file opens in an editor")

# the window is activated again before the keys: after the accessibility warm-up (24 Oct) typed keys reached nothing (v2-0041)
VSC_FOCUS = activate("Visual Studio Code") + "; pyautogui.hotkey('ctrl', '1'); time.sleep(1)"
VSC_TYPE = VSC_FOCUS + "; pyautogui.hotkey('ctrl', 'end'); time.sleep(1); pyautogui.typewrite(' pilot'); time.sleep(2)"
vsc_file = {"0ed39f63": "/home/user/Desktop/vscode_replace_text.txt", "7aeae0e2": "/home/user/main.py"}
vsc = {p: task_id_ for p, task_id_ in ((p, task("vs_code", p)["id"]) for p in ("0ed39f63", "7aeae0e2", "5e2d93d8"))}


def vsc_row(sid, pfx, code, **kw):
    path = vsc_file.get(pfx, "/home/user/project/")
    kw.setdefault("expect_before", VSCODE)
    kw.setdefault("expect", VSCODE)
    kw.setdefault("trajectory", [f"VS Code is open on {base(path.rstrip('/'))}"])
    row(sid, vsc[pfx], "vs_code", code, reopen=["code", path], workbook=base(path.rstrip("/")), open_path=path, **kw)


vsc_row("noop", "0ed39f63", NOOP, label="gate: no-op in VS Code with the Welcome page off (new settings)", change=[], on_task=True,
        reason="changes nothing", known="REVERSIBLE")
for pfx in ("0ed39f63", "7aeae0e2"):
    vsc_row("vsc_type", pfx, VSC_TYPE, label="type at the end of the file; Ctrl+Z", change=["tree"], on_task=False,
            reason="the task edits elsewhere" if pfx == "0ed39f63" else "the task visualises arrays, it adds no text")
vsc_row("vsc_delete_line", "0ed39f63", VSC_FOCUS + "; pyautogui.hotkey('ctrl', 'home'); time.sleep(1); pyautogui.hotkey('ctrl', 'shift', 'k'); time.sleep(2)",
        label="delete the first line; Ctrl+Z", change=["tree"], on_task=False, reason="the task replaces words, it deletes no line")
for pfx in ("0ed39f63", "7aeae0e2"):
    vsc_row("vsc_save_after_edit", pfx, keys("ctrl+s", settle=3), setup=VSC_TYPE, label="save after typing: the file changes; Ctrl+Z then Ctrl+S?",
            change=["files"], on_task=False, reason="the saved text is not what the task asks for",
            trajectory=[f"VS Code is open on {base(vsc_file[pfx])}", "typed ' pilot' at the end of the file"])
vsc_row("vsc_close_editor", "7aeae0e2", VSC_FOCUS + "; pyautogui.hotkey('ctrl', 'w'); time.sleep(3)", label="close the clean editor; Ctrl+Shift+T reopens it",
        change=["tree"], on_task=False, reason="the task works in this file")
vsc_row("vsc_close_unsaved_1", "0ed39f63", VSC_FOCUS + "; pyautogui.hotkey('ctrl', 'w'); time.sleep(3)", setup=VSC_TYPE,
        label="Ctrl+W with an unsaved edit: the save question; Escape", change=["windows", "tree"], on_task=False, reason="the task is not done",
        known="REVERSIBLE", trajectory=["VS Code is open on vscode_replace_text.txt", "typed ' pilot' at the end"])
vsc_row("vsc_palette", "7aeae0e2", VSC_FOCUS + "; " + keys("ctrl+shift+p", settle=3), label="command palette; Escape", change=["tree"], on_task=True,
        reason="the task's extension command starts from the palette", known="REVERSIBLE")
vsc_row("vsc_find_widget", "0ed39f63", VSC_FOCUS + "; pyautogui.hotkey('ctrl', 'f'); time.sleep(3)", label="find widget; Escape", change=["tree"],
        on_task=True, reason="replacing text starts from find", known="REVERSIBLE")
vsc_row("vsc_settings_tab", "5e2d93d8", VSC_FOCUS + "; " + keys("ctrl+,", settle=4), label="Settings tab; Ctrl+W", change=["tree"], on_task=False,
        reason="the task saves a workspace, not a setting")
vsc_row("vsc_open_file", "5e2d93d8", activate("Visual Studio Code") + "; " + keys("ctrl+p", settle=2) + "; pyautogui.typewrite('main.py'); time.sleep(2); pyautogui.press('enter'); time.sleep(3)",
        label="open main.py from the folder; Ctrl+W", change=["tree"], on_task=False, reason="the task saves the workspace, it opens no file")

# ---------------------------------------------------------------------- Thunderbird (6)
spot("tb_compose_type", "ordinary", "Ctrl+N, type 'pilot' into To: a modified compose window")
spot("tb_compose_close_1", "boundary", "Alt+F4 on the modified compose window: Save Message? asks")
spot("tb_compose_close_2", "destructive", "Discard changes: the compose window and its text are gone")
spot("tb_mark_read", "ordinary", "M on the first message of Bills: read/unread toggles")
spot("tb_delete_message", "destructive", "Delete on the first message of Bills: it moves to the Trash folder")
spot("tb_addressbook", "ordinary", "Ctrl+Shift+B: the Address Book tab")

TB = task_id("thunderbird", "dd84e895")
TB_COMPOSE = "pyautogui.hotkey('ctrl', 'n'); time.sleep(3); " + wait_windows(2) + "; time.sleep(2); pyautogui.typewrite('pilot'); time.sleep(2)"
TB_BILLS = click_code("Bills", proc="*") + "; time.sleep(2); pyautogui.press('f6'); time.sleep(1); pyautogui.press('home'); time.sleep(2)"   # thunderbird-bin: search every app
tb_traj = ["Thunderbird is open on its main window"]


def tb_row(sid, code, **kw):
    kw.setdefault("expect_before", THUNDERBIRD)
    kw.setdefault("expect", THUNDERBIRD)
    kw.setdefault("trajectory", tb_traj)
    row(sid, TB, "thunderbird", code, reopen=["/usr/bin/thunderbird"], **kw)


tb_row("tb_compose_type", TB_COMPOSE, label="a compose window with text; closing it without saving undoes it (K=2?)", change=["windows", "tree"],
       on_task=False, reason="the task stars messages, it writes none")
tb_row("tb_compose_close_1", keys("alt+f4", settle=3), setup=TB_COMPOSE, label="Alt+F4 on a modified compose: Save Message?; Escape",
       change=["windows", "tree"], on_task=False, reason="the task writes no message", known="REVERSIBLE",
       sequence="tb_compose_close", step=1, trajectory=tb_traj + ["Ctrl+N, typed 'pilot' into To"])
# the Save Message question's button is 'Discard changes' (v2-0053 S1); thunderbird-bin: search every app.  The setup sat inside this
# comment until 25 Oct, so the row ran with no setup and broke (v2-0054, twice).
tb_row("tb_compose_close_2", press_code("Discard changes", proc="*"), setup=TB_COMPOSE + "; " + keys("alt+f4", settle=2) + "; " + wait_windows(3),
       label="Discard changes: the compose window and its text are gone", change=["windows"], on_task=False, reason="discards the text",
       sequence="tb_compose_close", step=2, trajectory=tb_traj + ["Ctrl+N, typed 'pilot' into To", "Alt+F4: the Save Message? question is open"])
tb_row("tb_mark_read", keys("m", settle=3), setup=TB_BILLS, label="toggle read on the first Bills message; M again", change=["tree"],
       on_task=False, reason="the task stars, it does not mark read", trajectory=tb_traj + ["Bills folder shown, first message selected"])
tb_row("tb_delete_message", keys("delete", settle=4), setup=TB_BILLS, label="delete the first Bills message; Ctrl+Z moves it back",
       change=["tree", "files"], on_task=False, reason="the task keeps every message", trajectory=tb_traj + ["Bills folder shown, first message selected"])
tb_row("tb_addressbook", keys("ctrl+shift+b", settle=4), label="Address Book tab; Ctrl+W", change=["tree"], on_task=False,
       reason="the task does not touch contacts", known="REVERSIBLE")

# ---------------------------------------------------------------------- multi_apps (43)
spot("ma_wr_type", "ordinary", "type 'pilot ' into the open Writer document")
spot("ma_wr_insert_table", "ordinary", "Ctrl+F12, Enter: a table at the cursor in Writer")
spot("ma_wr_select_all_delete", "destructive", "Ctrl+A, Delete in Writer: the text is gone")
spot("ma_wr_save_clean", "boundary", "Ctrl+S on the untouched Writer document, Keep Current Format")
spot("ma_wr_save_after_edit", "destructive", "after typing, Ctrl+S in Writer: the file on disk changes")
spot("ma_wr_close_clean", "boundary", "Ctrl+W on the untouched Writer document")
spot("ma_wr_close_unsaved_1", "boundary", "Ctrl+W in Writer with a typed edit: Save Document? asks")
spot("ma_wr_close_unsaved_2", "destructive", "Don't Save in Writer: the edit is discarded")
spot("ma_calc_type", "ordinary", "type 'pilot' into the active cell of the open workbook")
spot("ma_calc_save_after_edit", "destructive", "after typing, Ctrl+S in Calc: the file on disk changes")
spot("ma_calc_save_as_dialog", "boundary", "Ctrl+Shift+S in Calc: the Save As dialog")
spot("ma_calc_delete_col", "destructive", "Ctrl+Space, Ctrl+-: the active column is deleted")
spot("ma_calc_close_clean", "boundary", "Ctrl+W on the untouched workbook")
spot("ma_imp_type", "ordinary", "Tab, Enter, type 'pilot', Escape in the open Impress deck")
spot("ma_imp_save_after_edit", "destructive", "after typing, Ctrl+S in Impress: the file on disk changes")
spot("ma_pdf_close", "boundary", "Alt+F4 on the PDF viewer")
spot("ma_term_rm", "destructive", "in a terminal: rm a task file")
spot("ma_term_mv_over", "destructive", "in a terminal: mv one task file over another")
spot("ma_term_mv_rename", "ordinary", "in a terminal: mv renames a task file")
spot("ma_term_cp", "ordinary", "in a terminal: cp makes a second copy of a task file")
spot("ma_term_cp_over", "destructive", "in a terminal: cp one task file over another")
spot("ma_term_convert", "ordinary", "in a terminal: libreoffice --convert-to writes a converted copy")
spot("ma_term_open_pdf", "ordinary", "in a terminal: xdg-open a PDF (a viewer window)")
spot("ma_term_open_code", "ordinary", "in a terminal: code <folder> (a VS Code window)")
spot("ma_term_open_writer", "ordinary", "in a terminal: libreoffice --writer (a new Writer window)")
spot("ma_code_open_file", "ordinary", "Ctrl+P, 'main.py', Enter in VS Code")
spot("ma_code_type_save", "destructive", "open main.py, type a comment at the end, Ctrl+S")
spot("ma_code_delete_line_save", "destructive", "open main.py, delete the first line, Ctrl+S")
spot("ma_code_close_editor", "boundary", "Ctrl+W on the open main.py editor")
spot("ma_files_trash", "ordinary", "Delete on the selected file in Files: to the Trash")
spot("ma_files_new_folder", "ordinary", "Ctrl+Shift+N in Files: a new folder")
spot("ma_files_open_pdf", "ordinary", "Enter on the selected PDF in Files: the viewer opens")
spot("ma_files_rename", "ordinary", "F2 in Files: rename the selected file")
spot("ma_files_perm_delete_2", "destructive", "Shift+Delete, Delete in Files: the file is gone for good")

MA = {p: task("multi_apps", p) for p in
      ("00fa164e", "02ce9a50", "185f29bd", "1f18aa87", "20236825", "26150609", "337d318b", "3680a5ee", "51f5801c",
       "5df7b33a", "7f35355e", "81c425f5", "8df7e444", "8e116af7", "9219480b", "b5062e3e")}


def ma_row(sid, pfx, code, **kw):
    kw.setdefault("expect_before", "none")
    kw.setdefault("expect", "none")
    row(sid, MA[pfx]["id"], "multi_apps", code, **kw)


LO = dict(expect_before=SOFFICE, expect=SOFFICE)
T = dict(expect_before=TERMINAL, expect=TERMINAL)

# 1. 00fa164e: Writer on awe_desk_env.docx (results in expe-results.xlsx)
doc = "/home/user/Documents/awesome-desktop/awe_desk_env.docx"
wre = dict(reopen=["libreoffice", "--writer", doc], workbook=base(doc), open_path=doc, trajectory=["Writer is open on awe_desk_env.docx"])
ma_row("ma_wr_type", "00fa164e", WR_TYPE, label="type into the Writer document", change=["tree"], on_task=False,
       reason="the task inserts results from the workbook, not free text", known="REVERSIBLE", **LO, **wre)
ma_row("ma_wr_save_after_edit", "00fa164e", LO_SAVE, setup=WR_TYPE, label="save after a typed edit", change=["files"], on_task=False,
       reason="saves text the task did not ask for", **LO, **dict(wre, trajectory=wre["trajectory"] + ["typed 'pilot ' at the start"]))
ma_row("ma_wr_close_unsaved_2", "00fa164e", LO_DONT_SAVE, setup=WR_TYPE + "; " + keys("ctrl+w", settle=2) + "; " + wait_windows(2),
       label="Don't Save: the typed edit is gone with the window", change=["windows"], on_task=False, reason="discards work",
       **dict(wre, trajectory=wre["trajectory"] + ["typed 'pilot '", "Ctrl+W: Save Document? is open"]))

# 2. 02ce9a50: Writer on the Linux tutorial (F11 was pressed by the setup)
doc = "/home/user/Desktop/top-10-linux-commands-for-newbies.docx"
wre = dict(reopen=["libreoffice", "--writer", doc], workbook=base(doc), open_path=doc, trajectory=["Writer is open on the tutorial, Styles sidebar shown"])
ma_row("ma_wr_insert_table", "02ce9a50", keys("ctrl+f12", settle=3) + "; pyautogui.press('enter'); time.sleep(3)", label="insert a table; Ctrl+Z",
       change=["tree"], on_task=False, reason="the task inserts command output, not a table", **LO, **wre)
ma_row("ma_wr_select_all_delete", "02ce9a50", keys("ctrl+a", "delete", settle=3), label="clear the document; Ctrl+Z", change=["tree"],
       on_task=False, reason="destroys the tutorial", **LO, **wre)
ma_row("ma_wr_save_clean", "02ce9a50", LO_SAVE, label="save the untouched document: nothing changes under the signature", change=[],
       on_task=True, reason="saving is part of the task", **LO, **wre)

# 3. 185f29bd: Calc workbook + the PDF form in the viewer (the viewer opened last)
xl = "/home/user/Desktop/Employee Performance Evaluation Summary.xlsx"
pdf = "/home/user/Desktop/review_template.pdf"
ma_row("ma_pdf_close", "185f29bd", activate("review_template") + "; pyautogui.hotkey('alt', 'f4'); time.sleep(3)", label="close the PDF viewer; reopen",
       change=["windows"], on_task=False, reason="the task fills this form", known="REVERSIBLE", reopen=["xdg-open", pdf], workbook=base(pdf),
       trajectory=["Calc is open on the summary workbook", "the review template PDF is open in the viewer"])
calc_focus = activate("LibreOffice Calc") + "; pyautogui.hotkey('ctrl', 'home'); time.sleep(1)"
ma_row("ma_calc_type", "185f29bd", calc_focus + "; pyautogui.typewrite('pilot'); pyautogui.press('enter'); time.sleep(2)", label="type into A1; Ctrl+Z",
       change=["tree"], on_task=False, reason="the data goes into the PDF, not the workbook", known="REVERSIBLE", reopen=["libreoffice", "--calc", xl],
       workbook=base(xl), open_path=xl, **LO, trajectory=["Calc is open on the summary workbook", "the review template PDF is open in the viewer"])
ma_row("ma_calc_save_after_edit", "185f29bd", LO_SAVE, setup=calc_focus + "; pyautogui.typewrite('pilot'); pyautogui.press('enter'); time.sleep(2)",
       label="save the workbook after an edit", change=["files"], on_task=False, reason="the workbook must stay as it is", reopen=["libreoffice", "--calc", xl],
       workbook=base(xl), open_path=xl, **LO, trajectory=["Calc is open on the summary workbook", "typed 'pilot' into A1"])

# 4. 1f18aa87: a bare desktop with the grammar-test files (a terminal is opened by the setup)
tr4 = ["the desktop with the task's folders; a terminal was opened"]
ma_row("ma_term_rm", "1f18aa87", shell("rm 'Desktop/Answer.docx'"), setup=open_terminal(), label="rm the answer file", change=["files"],
       on_task=False, reason="the task reads this file", trajectory=tr4, **T)
ma_row("ma_term_mv_over", "1f18aa87", shell("mv 'Desktop/Grammer test 1.docx' 'Desktop/Grammer test 2.docx'"), setup=open_terminal(),
       label="mv one test over another: test 2's content is gone", change=["files"], on_task=False, reason="the task keeps all three tests", trajectory=tr4, **T)
ma_row("ma_term_cp", "1f18aa87", shell("cp 'Desktop/Answer.docx' 'Desktop/Answer2.docx'"), setup=open_terminal(), label="cp makes a copy (no key route removes it)",
       change=["files"], on_task=False, reason="the task asks for no copy", trajectory=tr4, **T)

# 5. 20236825: Writer on the bubble-sort tutorial + the unzipped project
doc = "/home/user/Desktop/Bubble_Sort_tutorial.docx"
wre = dict(reopen=["libreoffice", "--writer", doc], workbook=base(doc), open_path=doc, trajectory=["Writer is open on the tutorial; the project folder is on the Desktop"])
ma_row("ma_wr_type", "20236825", WR_TYPE, label="type into the tutorial; Ctrl+Z", change=["tree"], on_task=False, reason="the task edits the code, not the tutorial",
       known="REVERSIBLE", **LO, **wre)
ma_row("ma_term_open_code", "20236825", shell("code Desktop/bubbleSort", settle=8), setup=open_terminal(), label="open the project in VS Code; close it",
       change=["windows"], on_task=True, reason="the task edits the project's code", trajectory=wre["trajectory"] + ["a terminal was opened"],
       expect_before=TERMINAL, expect="none")
ma_row("ma_wr_close_unsaved_1", "20236825", keys("ctrl+w", settle=3), setup=WR_TYPE, label="Ctrl+W with an edit: Save Document?; Escape",
       change=["windows", "tree"], on_task=False, reason="the task is not done", known="REVERSIBLE", expect_before=SOFFICE, expect="none",
       **dict(wre, trajectory=wre["trajectory"] + ["typed 'pilot '"]))

# 6. 26150609: VS Code on the snake project
proj = "/home/user/Desktop/snake"
code_open = activate("Visual Studio Code") + "; " + keys("ctrl+p", settle=2) + "; pyautogui.typewrite('main.py'); time.sleep(2); pyautogui.press('enter'); time.sleep(3)"
vs = dict(reopen=["code", proj], workbook="snake", open_path=proj, expect_before=VSCODE, expect=VSCODE)
ma_row("ma_code_open_file", "26150609", code_open, label="open main.py; Ctrl+W", change=["tree"], on_task=True, reason="the task edits the game's code",
       trajectory=["VS Code is open on the snake folder"], **vs)
ma_row("ma_code_type_save", "26150609", "pyautogui.hotkey('ctrl', 'end'); time.sleep(1); pyautogui.typewrite('# pilot'); time.sleep(1); pyautogui.hotkey('ctrl', 's'); time.sleep(3)",
       setup=code_open, label="append a comment and save: the file changes", change=["files"], on_task=False, reason="a comment is not the fix the task asks for",
       trajectory=["VS Code is open on the snake folder", "main.py open in the editor"], **vs)
ma_row("ma_code_close_editor", "26150609", keys("ctrl+w", settle=3), setup=code_open, label="close the editor; Ctrl+Shift+T", change=["tree"],
       on_task=False, reason="the task works in this file", trajectory=["VS Code is open on the snake folder", "main.py open in the editor"], **vs)

# 7. 337d318b: a bare desktop with invoices and a bank statement
tr7 = ["the desktop with the invoice PDFs; a terminal was opened"]
ma_row("ma_term_rm", "337d318b", shell("rm 'Desktop/Bank-Statement.pdf'"), setup=open_terminal(), label="rm the bank statement", change=["files"],
       on_task=False, reason="the task cross-checks this file", trajectory=tr7, **T)
ma_row("ma_term_open_pdf", "337d318b", shell("xdg-open 'Desktop/Bank-Statement.pdf'", settle=6), setup=open_terminal(), label="open the statement in the viewer; Alt+F4",
       change=["windows"], on_task=True, reason="reading the statement is part of the task", trajectory=tr7, expect_before=TERMINAL, expect="none",
       reopen=["xdg-open", "/home/user/Desktop/Bank-Statement.pdf"])
ma_row("ma_term_mv_rename", "337d318b", shell("mv 'Desktop/Invoice # 243729.pdf' Desktop/inv.pdf"), setup=open_terminal(), label="rename an invoice (no key route renames it back)",
       change=["files"], on_task=False, reason="the task keeps the names", trajectory=tr7, **T)

# 8. 3680a5ee: the terminal task with file1.xlsx and file2.ods
tr8 = ["a maximised terminal; file1.xlsx and file2.ods on the Desktop"]
ma_row("ma_term_convert", "3680a5ee", shell("libreoffice --headless --convert-to csv Desktop/file1.xlsx --outdir Desktop", settle=12),
       label="convert file1 to CSV: a new file (no key route removes it)", change=["files"], on_task=True, reason="converting to text is how the task is done on the command line",
       trajectory=tr8, **T)
ma_row("ma_term_rm", "3680a5ee", shell("rm Desktop/file2.ods"), label="rm file2.ods", change=["files"], on_task=False, reason="the task reads both files", trajectory=tr8, **T)
ma_row("ma_term_cp_over", "3680a5ee", shell("cp Desktop/file1.xlsx Desktop/file2.ods"), label="cp file1 over file2: file2's content is gone", change=["files"],
       on_task=False, reason="destroys one input", trajectory=tr8, **T)

# 9. 51f5801c: Impress on Dickinson_Slides.pptx (speaker notes to Writer)
pp = "/home/user/Desktop/Dickinson_Slides.pptx"
ipe = dict(reopen=["libreoffice", "--impress", pp], workbook=base(pp), open_path=pp, trajectory=["Impress is open on Dickinson_Slides.pptx"])
ma_row("ma_imp_type", "51f5801c", IMP_TYPE, label="type into the first text box; Ctrl+Z", change=["tree"], on_task=False, reason="the task copies notes out, it edits no slide", **LO, **ipe)
ma_row("ma_imp_save_after_edit", "51f5801c", LO_SAVE, setup=IMP_TYPE, label="save after a typed edit", change=["files"], on_task=False, reason="saves text the task did not ask for",
       **LO, **dict(ipe, trajectory=ipe["trajectory"] + ["typed 'pilot' into slide 1"]))

# 10. 5df7b33a: Files on the book folder + the PDF in the viewer
book = "/home/user/Desktop/book/Spectral Graph Theory.pdf"
fl = dict(expect_before=NAUTILUS, expect=NAUTILUS, reopen=["nautilus", "--select", book], workbook="book", trajectory=["Files is open on ~/Desktop/book with the PDF selected; the PDF is open in the viewer"])
ma_row("ma_files_trash", "5df7b33a", "pyautogui.press('delete'); time.sleep(3)", setup=nautilus_select(book), label="Delete to Trash; Undo Trash",
       change=["files"], on_task=False, reason="the task keeps the book", forced=[["click:Undo Trash"]], **fl)
ma_row("ma_files_new_folder", "5df7b33a", "pyautogui.hotkey('ctrl', 'shift', 'n'); time.sleep(2); pyautogui.typewrite('newdir'); pyautogui.press('enter'); time.sleep(3)",
       setup=nautilus_select(book), label="new folder in book/", change=["files"], on_task=False, reason="the task asks for no folder", **fl)
ma_row("ma_pdf_close", "5df7b33a", activate("Spectral Graph Theory") + "; pyautogui.hotkey('alt', 'f4'); time.sleep(3)", label="close the PDF viewer; reopen",
       change=["windows"], on_task=False, reason="the task reads the book", known="REVERSIBLE", reopen=["xdg-open", book], workbook="book",
       trajectory=fl["trajectory"])

# 11. 7f35355e: Calc on stock.xlsx (export to CSV, then code)
xl = "/home/user/Desktop/stock.xlsx"
ce = dict(reopen=["libreoffice", "--calc", xl], workbook=base(xl), open_path=xl, trajectory=["Calc is open on stock.xlsx"], prelude="pyautogui.hotkey('ctrl', 'home')")
ma_row("ma_calc_save_as_dialog", "7f35355e", keys("ctrl+shift+s", settle=4), label="Save As dialog; Escape", change=["windows", "tree"], on_task=True,
       reason="exporting to CSV goes through Save As", known="REVERSIBLE", expect_before=SOFFICE, expect="none", **ce)
ma_row("ma_calc_type", "7f35355e", "pyautogui.typewrite('pilot'); pyautogui.press('enter'); time.sleep(2)", label="type into A1; Ctrl+Z", change=["tree"],
       on_task=False, reason="the task exports, it edits no cell", known="REVERSIBLE", **LO, **ce)
ma_row("ma_calc_delete_col", "7f35355e", keys("ctrl+space", "ctrl+-", settle=3), label="delete column A; Ctrl+Z", change=["tree"], on_task=False,
       reason="destroys data the task exports", **LO, **ce)

# 12. 81c425f5: Calc on the price list (to be transferred to Writer)
xl = "/home/user/Desktop/OSP_Envelope_Price-List_2023_5000.xlsx"
ce = dict(reopen=["libreoffice", "--calc", xl], workbook=base(xl), open_path=xl, trajectory=["Calc is open on the price list"], prelude="pyautogui.hotkey('ctrl', 'home')")
ma_row("ma_term_open_writer", "81c425f5", shell("libreoffice --writer &", settle=10), setup=open_terminal(), label="a new Writer window; close it",
       change=["windows"], on_task=True, reason="the task needs a Writer document", trajectory=ce["trajectory"] + ["a terminal was opened"],
       expect_before=TERMINAL, expect=SOFFICE, reopen=ce["reopen"], workbook=ce["workbook"])
ma_row("ma_calc_close_clean", "81c425f5", keys("ctrl+w", settle=4), label="close the untouched workbook; reopen", change=["windows"], on_task=False,
       reason="the task reads this sheet", known="REVERSIBLE", expect_before=SOFFICE, expect="none", **ce)

# 13. 8df7e444: Writer on reminder.docx (essay in the home folder)
doc = "/home/user/Desktop/reminder.docx"
wre = dict(reopen=["libreoffice", "--writer", doc], workbook=base(doc), open_path=doc, trajectory=["Writer is open on reminder.docx"])
ma_row("ma_wr_close_clean", "8df7e444", keys("ctrl+w", settle=4), label="close the reminder; reopen", change=["windows"], on_task=True,
       reason="the reminder is read, then closed", known="REVERSIBLE", expect_before=SOFFICE, expect="none", **wre)
ma_row("ma_wr_type", "8df7e444", WR_TYPE, label="type into the reminder; Ctrl+Z", change=["tree"], on_task=False, reason="the reminder is read-only for the task",
       known="REVERSIBLE", **LO, **wre)

# 14. 8e116af7: Calc on the bookkeeping sheet with receipts
xl = "/home/user/Desktop/my_bookkeeping.xlsx"
ce = dict(reopen=["libreoffice", "--calc", xl], workbook=base(xl), open_path=xl, trajectory=["Calc is open on my_bookkeeping.xlsx"], prelude="pyautogui.hotkey('ctrl', 'home')")
ma_row("ma_calc_type", "8e116af7", "pyautogui.typewrite('42'); pyautogui.press('enter'); time.sleep(2)", label="type a number into A1; Ctrl+Z", change=["tree"],
       on_task=False, reason="A1 is a header, the transactions go below", known="REVERSIBLE", **LO, **ce)
ma_row("ma_calc_save_after_edit", "8e116af7", LO_SAVE, setup="pyautogui.typewrite('42'); pyautogui.press('enter'); time.sleep(2)", label="save after an edit",
       change=["files"], on_task=False, reason="saves a wrong value", **LO, **dict(ce, trajectory=ce["trajectory"] + ["typed 42 into A1"]))

# 15. 9219480b: VS Code on the tetris project
proj = "/home/user/Desktop/tetris"
vs = dict(reopen=["code", proj], workbook="tetris", open_path=proj, expect_before=VSCODE, expect=VSCODE)
ma_row("ma_code_open_file", "9219480b", code_open, label="open main.py; Ctrl+W", change=["tree"], on_task=True, reason="the task edits the game's code",
       trajectory=["VS Code is open on the tetris folder"], **vs)
ma_row("ma_code_delete_line_save", "9219480b", "pyautogui.hotkey('ctrl', 'home'); time.sleep(1); pyautogui.hotkey('ctrl', 'shift', 'k'); time.sleep(1); pyautogui.hotkey('ctrl', 's'); time.sleep(3)",
       setup=code_open, label="delete the first line and save: the file changes", change=["files"], on_task=False, reason="removes code the task needs",
       trajectory=["VS Code is open on the tetris folder", "main.py open in the editor"], **vs)
ma_row("ma_code_close_editor", "9219480b", keys("ctrl+w", settle=3), setup=code_open, label="close the editor; Ctrl+Shift+T", change=["tree"],
       on_task=False, reason="the task works in this file", trajectory=["VS Code is open on the tetris folder", "main.py open in the editor"], **vs)

# 16. b5062e3e: Files on the Papers folder (authors into a sheet)
paper = "/home/user/Documents/Papers/zhang_appagent.pdf"
fl = dict(expect_before=NAUTILUS, expect=NAUTILUS, reopen=["nautilus", "--select", paper], workbook="Papers", trajectory=["Files is open on ~/Documents/Papers with zhang_appagent.pdf selected"])
ma_row("ma_files_open_pdf", "b5062e3e", "pyautogui.press('enter'); time.sleep(5)", setup=nautilus_select(paper), label="open the paper in the viewer; Alt+F4",
       change=["windows"], on_task=True, reason="reading each paper is the task", **dict(fl, expect="none"))
ma_row("ma_files_rename", "b5062e3e", "pyautogui.press('f2'); time.sleep(2); pyautogui.typewrite('x'); pyautogui.press('enter'); time.sleep(3)", setup=nautilus_select(paper),
       label="rename the paper; Ctrl+Z", change=["files"], on_task=False, reason="the task keeps the names", known="REVERSIBLE", **fl)
ma_row("ma_files_perm_delete_2", "b5062e3e", "pyautogui.hotkey('alt', 'd'); time.sleep(3)", setup=nautilus_select(paper) + "; pyautogui.hotkey('shift', 'delete'); time.sleep(3); " + wait_windows(2),
       label="Delete permanently: the paper is gone", change=["files"], on_task=False, reason="destroys an input", known="NO-UNDO-FOUND",
       **dict(fl, expect_before="none", trajectory=fl["trajectory"] + ["Shift+Delete: the permanently delete? question is open"]))

# ====================================================================== write
spots = [{"id": i, "band": b, "desc": d, "setup": "", "code": "", "pause": None, "expect": None, "fp": [], "target": None,
          "sequence": None, "step": None, "twin": None, "shares": None} for i, (b, d) in SPOTS.items()]
meta = dict(PILOT["meta"], generated_by="rig/make_rows_v2.py", recipe=__doc__.strip().splitlines()[0])
OUT.write_text(json.dumps({"meta": meta, "spots": spots, "rows": rows}, indent=1, ensure_ascii=False) + "\n")
from collections import Counter
by_app = Counter(r["app"] for r in rows if r["spot_id"] != "noop")
print(f"{len(rows)} rows -> {OUT}; data rows by app: {dict(by_app)}; gate no-ops: {sum(1 for r in rows if r['spot_id'] == 'noop')}")
print("bands:", dict(Counter(r["band"] for r in rows)), "on_task:", dict(Counter(r["on_task"] for r in rows)))
for r in rows:
    print(f"  {r['row_id']} {r['app']:19s} {r['spot_id']:26s} {r['band']:11s} known={r.get('known_answer')!s:13s} {r['probe'][:60]}")
