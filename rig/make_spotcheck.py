"""Build the human spot-check page for pilot rows (Paper draft 3.4: the author eyeballs a sample of the on-task
flags; 4.5: and of the executed labels).

For every row in the given run folders: the task instruction, the action, the before / after / after-undo
screenshots, the label the checker gave and the undo it found, plus two questions for the reviewer (is the label
right, is the on-task flag right) and a note.  A later run folder overrides an earlier one for the same row, so
`--runs rig/out/pilot_run2 rig/out/pilot_rerun` shows the re-run rows in place of the old ones.  Labels are the
re-compared ones where a --recompare ran.

Writes <out>/index.html and <out>/img/*.jpg (screenshots scaled to 1280 px).  Answers are kept in the published
page's db, collection `verdicts`, one document per row id: {label: right|wrong|unsure, on_task: right|wrong|unsure,
note, at}; read them back with the ArtifactData tool.

Usage:  OSWorld/.venv/bin/python -I rig/make_spotcheck.py --runs rig/out/pilot_run2 [more runs] [--out rig/out/spotcheck]
"""
import argparse

import json
import pathlib

from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
BASE = HERE.parent
TASK_DIR = BASE / "OSWorld" / "evaluation_examples" / "examples" / "libreoffice_calc"
WIDTH = 1280

KEY_NAMES = {"ctrl": "Ctrl", "shift": "Shift", "alt": "Alt", "escape": "Esc", "esc": "Esc", "enter": "Enter",
             "home": "Home", "end": "End", "delete": "Delete", "backspace": "Backspace", "tab": "Tab", "space": "Space"}


def step_words(step: str) -> str:
    """One undo step in the words a person would use."""
    if step == "reopen":
        return "reopen the file"
    kind, _, arg = step.partition(":")
    if kind == "key":
        return "+".join(KEY_NAMES.get(p, p.upper() if len(p) <= 3 else p.capitalize()) for p in arg.split("+"))
    if kind == "type":
        return f"type “{arg}”"
    if kind == "menu":
        return f"menu {arg}"
    return ""


def undo_words(seq):
    return [w for w in (step_words(s) for s in seq or []) if w]


def shrink(src: pathlib.Path, dst: pathlib.Path) -> bool:
    if not src.exists():
        return False
    if not dst.exists():
        im = Image.open(src).convert("RGB")
        if im.width > WIDTH:
            im = im.resize((WIDTH, round(im.height * WIDTH / im.width)), Image.LANCZOS)
        im.save(dst, "JPEG", quality=72, optimize=True)
    return True


def load_rows(runs):
    rows = {}
    for run in runs:
        run = pathlib.Path(run)
        f = run / "results_recompared.jsonl"
        if not f.exists():
            f = run / "results.jsonl"
        for line in f.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                rows[r["row_id"]] = (run, r)
    return [rows[k] for k in sorted(rows)]


def row_view(run: pathlib.Path, r: dict, img_dir: pathlib.Path) -> dict:
    rid = r["row_id"]
    label = r.get("executed_label_recompared") or r.get("executed_label")
    undo = r.get("shortest_undo_recompared", r.get("shortest_undo"))
    if r.get("status") == "broken_action":
        label = "BROKEN"
    shots = []
    for key, sub, caption in (("before", "S", "Before the action"), ("after", "S1", "After the action")):
        name = f"{rid}-{sub}.jpg"
        if shrink(run / rid / sub / "screenshot.png", img_dir / name):
            shots.append({"caption": caption, "src": f"img/{name}"})
    if label == "REVERSIBLE" and undo:
        idx = next((s["idx"] for s in r.get("undo_search", []) if s.get("seq") == undo), None)
        src = run / rid / f"c{idx:02d}" / "screenshot.png" if idx is not None else run / rid / "replay" / "screenshot.png"
        name = f"{rid}-undo.jpg"
        if shrink(src, img_dir / name):
            shots.append({"caption": "After the undo", "src": f"img/{name}"})
    task = {}
    tf = TASK_DIR / f"{r['task_id']}.json"
    if tf.exists():
        task = json.loads(tf.read_text())
    a = r.get("guessed_label_verbatim") or {}
    b = r.get("guessed_label_defined") or {}
    return {
        "id": rid,
        "action": (r.get("action") or {}).get("desc", r["spot_id"]),
        "spot": r["spot_id"],
        "band": r["band"],
        "workbook": r.get("workbook", ""),
        "instruction": task.get("instruction", ""),
        "on_task": r.get("on_task"),
        "on_task_reason": r.get("on_task_reason", ""),
        "target": r.get("target_cell"),
        "label": label,
        "undo": undo_words(undo),
        "tried": r.get("budget_used"),
        "guess_a": a.get("reversible"),
        "guess_b": b.get("reversible"),
        "shots": shots,
    }


PAGE = r"""<title>Pilot Spot Check</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Sans+Condensed:wght@600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: a review queue. One row per card, screenshots side by side, the two questions under them. */
:root {
  --bg: #f3f5f4; --surface: #ffffff; --fg: #17201d; --muted: #5b6863; --line: #d7dedb;
  --accent: #1f6f5c; --accent-ink: #ffffff;
  --ok: #1d7a46; --ok-bg: #e2f3e8; --warn: #9a5b00; --warn-bg: #fbeed6; --bad: #b3261e; --bad-bg: #fbe3e1;
  --display: "IBM Plex Sans Condensed", "Arial Narrow", sans-serif;
  --body: "IBM Plex Sans", system-ui, sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, Menlo, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #101614; --surface: #18201d; --fg: #e4ebe8; --muted: #9aa8a2; --line: #2b3632;
  --accent: #5cc3a6; --accent-ink: #0d1a16;
  --ok: #6fd39a; --ok-bg: #173527; --warn: #f0b85a; --warn-bg: #3a2a10; --bad: #ff8a80; --bad-bg: #3d1a18; color-scheme: dark } }
:root[data-theme="dark"] {
  --bg: #101614; --surface: #18201d; --fg: #e4ebe8; --muted: #9aa8a2; --line: #2b3632;
  --accent: #5cc3a6; --accent-ink: #0d1a16;
  --ok: #6fd39a; --ok-bg: #173527; --warn: #f0b85a; --warn-bg: #3a2a10; --bad: #ff8a80; --bad-bg: #3d1a18; color-scheme: dark }
* { box-sizing: border-box }
body { background: var(--bg); color: var(--fg); font: 15px/1.5 var(--body); }
body::before { content: ""; position: fixed; inset: 0 0 auto; height: env(safe-area-inset-top, 0px); z-index: 10; background: var(--surface) }
.wrap { max-width: 1240px; margin: 0 auto; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }
header.top { position: sticky; top: env(safe-area-inset-top, 0px); z-index: 5; background: var(--surface); border-bottom: 1px solid var(--line); }
header.top .wrap { display: flex; flex-wrap: wrap; gap: 8px 20px; align-items: center; padding-block: 10px; }
h1 { font: 600 20px/1.2 var(--display); letter-spacing: .01em; margin: 0; text-wrap: balance }
.progress { font: 500 13px var(--mono); color: var(--muted); font-variant-numeric: tabular-nums }
.filters { display: flex; gap: 6px; margin-left: auto; flex-wrap: wrap }
.filters button, .ans button { font: 500 13px var(--body); border: 1px solid var(--line); background: var(--surface); color: var(--fg); border-radius: 6px; padding: 5px 11px; cursor: pointer }
.filters button[aria-pressed="true"] { background: var(--accent); color: var(--accent-ink); border-color: var(--accent) }
button:focus-visible, textarea:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px }
.intro { padding-block: 18px 6px; color: var(--muted); max-width: 70ch; display: grid; gap: 6px }
.intro p { margin: 0 }
.notice { margin: 8px 0 0; padding: 8px 12px; border-radius: 6px; background: var(--warn-bg); color: var(--warn); font-size: 14px }
main.wrap { display: grid; gap: 18px; padding-block: 12px 48px }
article { background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 16px; display: grid; gap: 12px; min-width: 0 }
.head { display: flex; flex-wrap: wrap; gap: 6px 12px; align-items: baseline }
.rid { font: 500 13px var(--mono); color: var(--muted) }
.what { font: 600 17px/1.3 var(--display); margin: 0; flex: 1 1 320px; min-width: 0 }
.chips { display: flex; gap: 6px; flex-wrap: wrap }
.chip { font: 500 12px var(--body); letter-spacing: .03em; text-transform: uppercase; padding: 2px 8px; border-radius: 999px; background: var(--bg); color: var(--muted); border: 1px solid var(--line) }
.chip.ok { background: var(--ok-bg); color: var(--ok); border-color: transparent }
.chip.warn { background: var(--warn-bg); color: var(--warn); border-color: transparent }
.chip.bad { background: var(--bad-bg); color: var(--bad); border-color: transparent }
.task { margin: 0; color: var(--muted); font-size: 14px; max-width: 95ch }
.task b { color: var(--fg); font-weight: 500 }
.shots { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 10px }
figure { margin: 0; min-width: 0 }
figure img { width: 100%; height: auto; border: 1px solid var(--line); border-radius: 4px; cursor: zoom-in; display: block; background: var(--bg) }
figcaption { font-size: 13px; color: var(--muted); margin-top: 4px }
.facts { display: grid; grid-template-columns: max-content 1fr; gap: 4px 14px; font-size: 14px; margin: 0 }
.facts dt { color: var(--muted) }
.facts dd { margin: 0; min-width: 0 }
kbd { font: 500 12.5px var(--mono); padding: 1px 6px; border: 1px solid var(--line); border-bottom-width: 2px; border-radius: 4px; background: var(--bg) }
.qs { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px; border-top: 1px solid var(--line); padding-top: 12px }
.q { display: grid; gap: 6px; min-width: 0 }
.q label, .q .ql { font-weight: 500; font-size: 14px }
.ans { display: flex; gap: 6px; flex-wrap: wrap }
.ans button[aria-pressed="true"][data-v="right"] { background: var(--ok-bg); color: var(--ok); border-color: var(--ok) }
.ans button[aria-pressed="true"][data-v="wrong"] { background: var(--bad-bg); color: var(--bad); border-color: var(--bad) }
.ans button[aria-pressed="true"][data-v="unsure"] { background: var(--warn-bg); color: var(--warn); border-color: var(--warn) }
.ans button:disabled { opacity: .55; cursor: default }
textarea { width: 100%; min-height: 38px; resize: vertical; font: 14px var(--body); color: var(--fg); background: var(--bg); border: 1px solid var(--line); border-radius: 6px; padding: 6px 8px }
.saved { font-size: 12px; color: var(--muted); min-height: 1em }
dialog { border: 0; padding: 0; background: transparent; max-width: 96vw; max-height: 94vh }
dialog::backdrop { background: rgb(0 0 0 / .78) }
dialog img { max-width: 96vw; max-height: 90vh; display: block; border-radius: 4px }
dialog p { color: #fff; margin: 6px 0 0; font-size: 13px }
.empty { color: var(--muted); padding: 24px 0 }
@media (prefers-reduced-motion: reduce) { * { transition: none !important } }
</style>

<header class="top"><div class="wrap">
  <h1>Pilot Spot Check</h1>
  <span class="progress" id="progress">loading answers…</span>
  <div class="filters" role="group" aria-label="Show">
    <button id="f-all" data-f="all" aria-pressed="true">All rows</button>
    <button id="f-open" data-f="open" aria-pressed="false">Not answered</button>
    <button id="f-noundo" data-f="noundo" aria-pressed="false">No undo found</button>
  </div>
</div></header>

<section class="wrap intro">
  <p>Each card is one recorded action. Compare the three screenshots, then answer two questions.</p>
  <p><b>Label.</b> "Can be undone" means the checker found key presses that put the screen and the files back exactly as before the action; the third screenshot shows the result. "No undo found" means none of the attempts did.</p>
  <p><b>On task.</b> "On task" means the action only changes what the task itself asks to change, or changes nothing.</p>
  <p class="notice" id="notice" hidden></p>
</section>

<main class="wrap" id="rows"></main>

<dialog id="zoom"><img id="zoom-img" alt=""><p id="zoom-cap"></p></dialog>

<script type="application/json" id="data">__DATA__</script>
<script>
const ROWS = JSON.parse(document.getElementById("data").textContent);
const LABEL = {REVERSIBLE: ["Can be undone", "ok"], "NO-UNDO-FOUND": ["No undo found", "warn"], BROKEN: ["Action did nothing", "bad"]};
const answers = {};
let db = null, writable = true, filter = "all";
const saving = {};

function el(tag, attrs, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k === "class") e.className = v; else if (k === "text") e.textContent = v; else e.setAttribute(k, v);
  }
  for (const k of kids) if (k != null) e.append(k);
  return e;
}

function chip(text, cls) { return el("span", {class: "chip" + (cls ? " " + cls : ""), text}); }

function question(row, field, title, opts) {
  const box = el("div", {class: "q"}, el("span", {class: "ql", text: title}));
  const ans = el("div", {class: "ans", role: "group", "aria-label": title});
  for (const [v, t] of opts) {
    const b = el("button", {type: "button", "data-v": v, "data-row": row.id, "data-field": field, id: `${row.id}-${field}-${v}`, "aria-pressed": "false", text: t});
    b.addEventListener("click", () => answer(row.id, {[field]: (answers[row.id] || {})[field] === v ? null : v}));
    ans.append(b);
  }
  box.append(ans);
  return box;
}

function card(row) {
  const [ltext, lcls] = LABEL[row.label] || [row.label, ""];
  const art = el("article", {id: row.id});
  art.append(el("div", {class: "head"},
    el("span", {class: "rid", text: row.id}),
    el("h2", {class: "what", text: row.action}),
    el("div", {class: "chips"}, chip(ltext, lcls), chip(row.on_task ? "On task" : "Off task"), chip(row.band))));
  if (row.instruction) art.append(el("p", {class: "task"}, el("b", {text: "Task: "}), row.instruction));
  const shots = el("div", {class: "shots"});
  for (const s of row.shots) {
    const img = el("img", {src: s.src, alt: `${s.caption}, ${row.id}`, loading: "lazy"});
    img.addEventListener("click", () => zoom(s.src, `${row.id} · ${s.caption}`));
    shots.append(el("figure", {}, img, el("figcaption", {text: s.caption})));
  }
  art.append(shots);
  const facts = el("dl", {class: "facts"});
  const undo = el("dd");
  if (row.undo.length) row.undo.forEach((w, i) => { if (i) undo.append(", "); undo.append(el("kbd", {text: w})); });
  else undo.textContent = row.label === "BROKEN" ? "not searched: the action changed nothing on screen or on disk" : `none of ${row.tried ?? "the"} attempts brought it back`;
  facts.append(el("dt", {text: "Undo found"}), undo);
  facts.append(el("dt", {text: "Workbook"}), el("dd", {text: row.workbook + (row.target ? ` · cell ${row.target}` : "")}));
  facts.append(el("dt", {text: "Why on/off task"}), el("dd", {text: row.on_task_reason}));
  const g = v => v === true ? "undoable" : v === false ? "one-way" : "no answer";
  facts.append(el("dt", {text: "Model guesses"}), el("dd", {text: `SafePred prompt: ${g(row.guess_a)} · our definition: ${g(row.guess_b)}`}));
  art.append(facts);
  const qs = el("div", {class: "qs"});
  qs.append(question(row, "label", `Is "${ltext}" right?`, [["right", "Right"], ["wrong", "Wrong"], ["unsure", "Can't tell"]]));
  qs.append(question(row, "on_task", `Is "${row.on_task ? "On task" : "Off task"}" right?`, [["right", "Right"], ["wrong", "Wrong"], ["unsure", "Can't tell"]]));
  const note = el("textarea", {id: `${row.id}-note`, placeholder: "Note (optional): what looks wrong", "aria-label": `Note for ${row.id}`});
  note.addEventListener("change", () => answer(row.id, {note: note.value.trim()}));
  qs.append(el("div", {class: "q"}, el("label", {for: `${row.id}-note`, text: "Note"}), note, el("span", {class: "saved", id: `${row.id}-saved`})));
  art.append(qs);
  return art;
}

function zoom(src, cap) {
  const d = document.getElementById("zoom");
  document.getElementById("zoom-img").src = src;
  document.getElementById("zoom-cap").textContent = cap + " · click to close";
  d.showModal();
}
document.getElementById("zoom").addEventListener("click", e => e.currentTarget.close());

function paint() {
  let done = 0;
  for (const row of ROWS) {
    const a = answers[row.id] || {};
    if (a.label && a.on_task) done++;
    for (const f of ["label", "on_task"]) {
      for (const b of document.querySelectorAll(`button[data-row="${row.id}"][data-field="${f}"]`)) {
        b.setAttribute("aria-pressed", String(a[f] === b.dataset.v));
        b.disabled = !writable;
      }
    }
    const note = document.getElementById(`${row.id}-note`);
    if (note && document.activeElement !== note && (a.note || "") !== note.value) note.value = a.note || "";
    if (note) note.disabled = !writable;
    const art = document.getElementById(row.id);
    const show = filter === "all" || (filter === "open" && !(a.label && a.on_task)) || (filter === "noundo" && row.label === "NO-UNDO-FOUND");
    art.hidden = !show;
  }
  document.getElementById("progress").textContent = db ? `${done} of ${ROWS.length} answered` : `${ROWS.length} rows`;
}

async function answer(id, patch) {
  if (!db || !writable) return;
  const next = Object.assign({}, answers[id] || {}, patch, {at: new Date().toISOString()});
  for (const k of Object.keys(next)) if (next[k] === null) delete next[k];
  answers[id] = next;
  paint();
  const saved = document.getElementById(`${id}-saved`);
  while (saving[id]) await saving[id];
  saving[id] = db.doc(`verdicts/${id}`).set(next).then(() => { saved.textContent = "Saved"; },
    e => {
      if (e && e.code === "invalid_argument") { writable = false; showNotice("You can read this page but not answer on it."); paint(); }
      else saved.textContent = "Not saved: " + (e && e.message ? e.message : "try again");
    }).finally(() => { saving[id] = null; });
}

function showNotice(text) { const n = document.getElementById("notice"); n.textContent = text; n.hidden = false; }

for (const b of document.querySelectorAll(".filters button")) b.addEventListener("click", () => {
  filter = b.dataset.f;
  for (const o of document.querySelectorAll(".filters button")) o.setAttribute("aria-pressed", String(o === b));
  paint();
});

const main = document.getElementById("rows");
if (!ROWS.length) main.append(el("p", {class: "empty", text: "No rows in this run."}));
for (const row of ROWS) main.append(card(row));
paint();

(async () => {
  try {
    db = window.claude && window.claude.use ? await window.claude.use("db") : null;
  } catch (e) { db = null; }
  if (!db) { writable = false; showNotice("Answers can't be saved in this view. Open the page on claude.ai, signed in, to answer."); paint(); return; }
  try {
    const user = await window.claude.use("user");
    if (user && (await user.can("data.write")) === false) { writable = false; showNotice("You can read this page but not answer on it."); }
  } catch (e) {}
  db.collection("verdicts").onSnapshot(snap => {
    for (const d of snap.docs) if (d.exists) answers[d.id] = Object.assign({}, d.data());
    paint();
  }, () => showNotice("Saved answers stopped updating. Reload the page to see the latest."));
  paint();
})();
</script>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", default=[str(HERE / "out" / "pilot_run2")])
    ap.add_argument("--out", default=str(HERE / "out" / "spotcheck"))
    args = ap.parse_args()
    out = pathlib.Path(args.out)
    if not out.is_absolute():
        out = (BASE / out).resolve()
    img = out / "img"
    img.mkdir(parents=True, exist_ok=True)
    views = [row_view(run, r, img) for run, r in load_rows([BASE / r if not pathlib.Path(r).is_absolute() else r for r in args.runs])]
    data = json.dumps(views, ensure_ascii=False).replace("</", "<\\/")
    (out / "index.html").write_text(PAGE.replace("__DATA__", data))
    size = sum(f.stat().st_size for f in img.glob("*.jpg"))
    labels = {}
    for v in views:
        labels[v["label"]] = labels.get(v["label"], 0) + 1
    print(f"{len(views)} rows {labels}; {len(list(img.glob('*.jpg')))} images {size / 1e6:.1f} MB -> {out / 'index.html'}")


if __name__ == "__main__":
    main()
