# Build the v2 row page (every v2 row, its label and shortest undo, a per-app summary) as one HTML file.  Moved from the
# job temp dir on 25 Oct 2026; the subtitle text describes the 24-25 Oct run and should be edited before a new publish.
#     /usr/bin/python3 -I rig/make_rows_page.py
import json, os, html, collections, time
BASE = '/Users/ngchenmeng/ai-research/osworld-testing'
rows = json.load(open(f'{BASE}/rig/clickspots_v2.json'))
spots = {s['id']: s for s in rows['spots']}
rows = rows['rows']
coll = {}
for b in 'abc':
    for i in open(f'{BASE}/rig/batches/main_v2_{b}.txt').read().strip().split(','): coll[i] = b
res = {}
errs = set()
for b in 'abc':
    rec = {}
    p = f'{BASE}/rig/out/v2_{b}/results_recompared.jsonl'
    if os.path.exists(p):
        for l in open(p):
            r = json.loads(l); rec[r['row_id']] = r
    for l in open(f'{BASE}/rig/out/v2_{b}/results.jsonl'):
        r = json.loads(l)
        if r.get('status') in ('ok', 'broken_action', 'noise') and (r['row_id'] not in rec or rec[r['row_id']].get('started_at') != r.get('started_at')):
            rec[r['row_id']] = r
    live = {json.loads(l)['row_id'] for l in open(f'{BASE}/rig/out/v2_{b}/results.jsonl') if json.loads(l).get('status') in ('ok', 'broken_action', 'noise')}
    rec = {k: v for k, v in rec.items() if k in live}
    res.update(rec)
    for l in open(f'{BASE}/rig/out/v2_{b}/results.jsonl'):
        r = json.loads(l)
        if r.get('status') == 'error' and r['row_id'] not in res and r['row_id'] not in rec: errs.add(r['row_id'])
APP = {'libreoffice-impress': 'Impress', 'libreoffice-writer': 'Writer', 'vs_code': 'VS Code', 'thunderbird': 'Thunderbird', 'multi_apps': 'Multi-app'}
def label(r):
    if not r: return ('queued', 'queued', '', '')
    if r == 'err': return ('error', 'network error', '', '')
    if r['status'] == 'broken_action': return ('broken', 'broken', '', f"{int(r.get('row_seconds',0)//60)} min")
    if r['status'] == 'noise': return ('noise', 'noise', '', '')
    lab = r.get('executed_label_recompared') or r.get('executed_label') or ''
    undo = r.get('shortest_undo_recompared', r.get('shortest_undo')) or []
    return (lab.lower().replace('-', ''), lab, ' ; '.join(undo), f"{int(r.get('row_seconds',0)//60)} min")
counts = collections.Counter(); byapp = collections.defaultdict(collections.Counter)
trs = []
for r in rows:
    rid = r['row_id']; rr = res.get(rid) or ('err' if rid in errs else None); cls, lab, undo, mins = label(rr)
    if rid not in coll: cls, lab = 'excluded', 'excluded'
    counts[lab] += 1; byapp[APP[r['app']]][lab] += 1
    trs.append(f"<tr class='{cls}'><td class='mono'>{rid}</td><td>{coll.get(rid,'–')}</td><td>{APP[r['app']]}</td><td class='mono small'>{r['task_id'][:8]}</td>"
               f"<td>{html.escape(spots[r['spot_id']]['desc'])}</td><td><span class='band {r['band']}'>{r['band']}</span></td><td>{'yes' if r['on_task'] else 'no'}</td>"
               f"<td><span class='pill {cls}'>{html.escape(lab)}</span></td><td class='mono small'>{html.escape(undo)}</td><td class='num'>{mins}</td></tr>")
done = sum(v for k, v in counts.items() if k not in ('queued', 'excluded', 'network error'))
stamp = time.strftime('%d %b %Y %H:%M')
COLS = ['REVERSIBLE', 'NO-UNDO-FOUND', 'UNCONFIRMED', 'broken', 'network error', 'excluded']
def arow(name, c):
    d = sum(c[k] for k in COLS[:4])
    return f"<tr><td>{name}</td>" + ''.join(f"<td class='num'>{c[k] or ''}</td>" for k in COLS) + f"<td class='num'><b>{d}</b> / {sum(c.values())}</td></tr>"
apptab = ''.join(arow(a, byapp[a]) for a in ['Multi-app', 'Impress', 'Writer', 'VS Code', 'Thunderbird'] if a in byapp) + arow('<b>All</b>', counts)
page = f"""<title>v2 Rows</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
/* layout: one summary strip, then a single sortable-by-eye table; status pills carry the state */
:root {{ --bg:#f7f6f2; --fg:#1f2320; --muted:#6b7068; --line:#dcd9d0; --head:#ece9e0; --ok:#1f6f43; --okbg:#dff1e4; --no:#8a3b1f; --nobg:#f6e1d6; --unc:#7a5a00; --uncbg:#f7ecc8; --q:#5a6670; --qbg:#e6eaee; --brk:#5c2d8a; --brkbg:#eadff5;
  --display:"IBM Plex Sans", system-ui, sans-serif; --mono:"IBM Plex Mono", ui-monospace, Menlo, monospace; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#15171a; --fg:#e8e6df; --muted:#9a9f97; --line:#2c3036; --head:#1e2126; --ok:#8fd4a8; --okbg:#173524; --no:#f0a98a; --nobg:#3d1f12; --unc:#f0d27a; --uncbg:#3a2f0a; --q:#aab3bb; --qbg:#23282d; --brk:#cdb0ec; --brkbg:#2d1b44; color-scheme: dark }} }}
:root[data-theme="dark"] {{ --bg:#15171a; --fg:#e8e6df; --muted:#9a9f97; --line:#2c3036; --head:#1e2126; --ok:#8fd4a8; --okbg:#173524; --no:#f0a98a; --nobg:#3d1f12; --unc:#f0d27a; --uncbg:#3a2f0a; --q:#aab3bb; --qbg:#23282d; --brk:#cdb0ec; --brkbg:#2d1b44; color-scheme: dark }}
body {{ background: var(--bg); color: var(--fg); font-family: var(--display); padding-block: 24px; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }}
h1 {{ font-size: 1.4rem; margin: 0 0 4px; text-wrap: balance; }}
.sub {{ color: var(--muted); margin: 0 0 16px; }}
.strip {{ display: flex; flex-wrap: wrap; gap: 8px 18px; margin-bottom: 18px; font-variant-numeric: tabular-nums; }}
.strip span b {{ font-weight: 600; }}
.wrap {{ overflow-x: auto; border: 1px solid var(--line); border-radius: 6px; }}
table {{ border-collapse: collapse; width: 100%; font-size: 0.86rem; }}
th {{ text-align: left; background: var(--head); padding: 8px 10px; position: sticky; top: 0; font-size: 0.72rem; letter-spacing: 0.04em; text-transform: uppercase; color: var(--muted); }}
td {{ padding: 6px 10px; border-top: 1px solid var(--line); vertical-align: top; }}
.mono {{ font-family: var(--mono); font-size: 0.8rem; }} .small {{ font-size: 0.74rem; color: var(--muted); }} .num {{ text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }}
.pill {{ display: inline-block; padding: 1px 8px; border-radius: 10px; font-size: 0.74rem; font-weight: 600; white-space: nowrap; }}
.pill.reversible {{ color: var(--ok); background: var(--okbg); }} .pill.noundofound {{ color: var(--no); background: var(--nobg); }} .pill.unconfirmed {{ color: var(--unc); background: var(--uncbg); }}
.pill.error {{ color: var(--no); background: transparent; border: 1px dashed var(--no); }}
.summary {{ max-width: 760px; margin-bottom: 22px; }} .summary tr:last-child td {{ border-top: 2px solid var(--line); }}
.pill.queued, .pill.excluded {{ color: var(--q); background: var(--qbg); }} .pill.broken, .pill.noise {{ color: var(--brk); background: var(--brkbg); }}
.band {{ font-size: 0.74rem; color: var(--muted); }} .band.destructive {{ color: var(--no); }} .band.boundary {{ color: var(--unc); }}
tr.excluded td {{ opacity: 0.5; }}
</style>
<h1>v2 Rows</h1>
<p class="sub">The 98 data rows and 3 gate no-ops of the OSWorld-proportional run, 24 October. Labels are the recompared ones where a recompare exists. Updated {stamp}. A DNS outage from about 23:20 on 24 October failed every row after that; the rerun started at 11:30 on 25 October, stopped at 12:55 on the Modal spend limit, restarted at 13:17, stopped at 15:00 by the battery guard, and restarted at 15:17 on power. Rows marked network error are waiting their turn.</p>
<div class="strip"><span><b>{done}</b> done</span><span><b>{counts.get('REVERSIBLE',0)}</b> REVERSIBLE</span><span><b>{counts.get('NO-UNDO-FOUND',0)}</b> NO-UNDO-FOUND</span><span><b>{counts.get('UNCONFIRMED',0)}</b> UNCONFIRMED</span><span><b>{counts.get('broken',0)}</b> broken</span><span><b>{counts.get('network error',0)}</b> network error</span><span><b>{counts.get('excluded',0)}</b> excluded</span></div>
<div class="wrap summary"><table><thead><tr><th>App</th><th>Reversible</th><th>No undo found</th><th>Unconfirmed</th><th>Broken</th><th>Network error</th><th>Excluded</th><th>Done / rows</th></tr></thead><tbody>{apptab}</tbody></table></div>
<div class="wrap"><table><thead><tr><th>Row</th><th>Coll.</th><th>App</th><th>Task</th><th>Action</th><th>Band</th><th>On task</th><th>Label</th><th>Shortest undo</th><th>Time</th></tr></thead><tbody>
{''.join(trs)}
</tbody></table></div>
"""
out = f'{BASE}/rig/out/v2_rows.html'  # git-ignored; publish as a new artifact (the 24-25 Oct page is gone)
open(out, 'w').write(page); print(out, len(page), 'bytes; done', done, dict(counts))
