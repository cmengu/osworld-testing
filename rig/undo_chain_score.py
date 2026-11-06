"""Step 2 score: the chained undo plans on the 99 H3 rows, from the same runs as the other sources (h3, n5, rt, ch), not the sq/rl rechecks.

    OSWorld/.venv/bin/python -I rig/undo_chain_score.py    # -> rig/out/undo_eval/chain_score.json
"""
import json, glob, collections, sys, pathlib, re
from math import comb
BASE = pathlib.Path('.').resolve(); sys.path.insert(0, str(BASE))
from rig.undo_eval_retry import load, DROPPED, norm
s, n, new, tgt, rec = load()
rows = [r for r in s if r in n and n[r] != "needs a run" and r not in DROPPED]
b = json.load(open('rig/out/undo_eval/chain_build.json'))
def strip(p): return tuple(x for x in norm(p) if not x.startswith('wait:'))
# same evidence as the earlier best-of-two: h3*, n5_*, rt_* runs only, plus ch*_* for new plans; not sq_* or rl_* rechecks
ex = collections.defaultdict(list); srcs = collections.defaultdict(set)
for f in glob.glob('rig/out/*/results.jsonl'):
    d = pathlib.Path(f).parent.name
    if not re.match(r'(h3|n5_|rt_|ch2?_)', d): continue
    for l in open(f):
        r = json.loads(l)
        if r.get('status') == 'ok' and r.get('plans'):
            for p in r['plans']:
                if p.get('executed') is False: continue
                st = strip(p.get('parsed') or p.get('steps') or [])
                ex[(r['row_id'], st)].append(bool(p.get('match')))
second = collections.defaultdict(dict)
for f in glob.glob('rig/out/rt_*/results.jsonl'):
    for l in open(f):
        r = json.loads(l)
        if r.get('status') == 'ok' and r.get('plans'):
            for p in r['plans']:
                for src in p['source'].split('+'):
                    second[r['row_id']][src] = second[r['row_id']].get(src, False) or bool(p.get('match'))
chain = {r for r in rows if any(ex.get((r, strip(b[r]['plan'])), []))}
new_ok = {r for r in rows if n[r] == 'ok' or second.get(r, {}).get('model_v5')}
cl = {r for r in rows if s[r]['claude'] == 'ok' or second.get(r, {}).get('claude')}
unk = [r for r in rows if (r, strip(b[r]['plan'])) not in ex]
def sign(a, c):
    m, k = a + c, min(a, c)
    return round(min(1.0, 2 * sum(comb(m, i) for i in range(k + 1)) / 2 ** m), 3) if m else 1.0
out = {"rows": len(rows), "evidence": "h3, n5, rt, ch runs only (same tries as the other sources)", "chain": len(chain), "model_alone": len(new_ok), "claude": len(cl),
       "no_execution_found": unk, "chain_only_vs_claude_only": [len(chain - cl), len(cl - chain)], "p_vs_claude": sign(len(chain - cl), len(cl - chain)),
       "chain_only_vs_model_only": [len(chain - new_ok), len(new_ok - chain)], "p_vs_model": sign(len(chain - new_ok), len(new_ok - chain)),
       "chain_or_claude": len(chain | cl), "gained_vs_model": sorted(chain - new_ok), "lost_vs_model": sorted(new_ok - chain)}
json.dump(out, open('rig/out/undo_eval/chain_score.json', 'w'), indent=1); print(json.dumps(out, indent=1))
