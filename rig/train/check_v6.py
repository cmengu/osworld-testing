"""Free follow-up checks on the _v6w results (7 Nov 2026), written AFTER seeing score_v6.py output, so not part of its fixed tests."""
import json,statistics as st,collections,sys
sys.path.insert(0,'rig/train')
import score_v6 as S, compare_teacher as C
from score_forward import parse
O=json.load(open('rig/out/model_on_agent/predictions.json'))['rows']
N=json.load(open('rig/out/model_on_agent/predictions_v6.json'))['rows']
D=json.load(open('rig/agentrun/on_task_draft.json'))
flag=lambda r:(D.get(r) or D.get(r.replace('agr-','ag-')) or {}).get('on_task')
g=lambda P,r:st.mean(P[r]['guard_refuse']); v=lambda P,r:st.mean(P[r]['reversible_yes'])
print('all 70 refused old',sum(g(O,r)>=.5 for r in N),'new',sum(g(N,r)>=.5 for r in N))
print('REV head says not undoable: old',sum(v(O,r)<.5 for r in N),'new',sum(v(N,r)<.5 for r in N))
print('guard prob new: max',round(max(g(N,r) for r in N),3),'top5',sorted([round(g(N,r),3) for r in N])[-5:],'mean',round(st.mean(g(N,r) for r in N),3))
print('old mean',round(st.mean(g(O,r) for r in N),3))
for r in N:
    if flag(r) is False or g(O,r)>=.5:
        d=D.get(r) or D.get(r.replace('agr-','ag-')) or {}
        print(r,'flag',flag(r),'old g',round(g(O,r),2),'new g',round(g(N,r),2),'new rev',round(v(N,r),2),'|',str(d.get('reason'))[:70])
print('no flag rows:',[(r,round(g(O,r),2),round(g(N,r),2)) for r in N if flag(r) is None])
rows,head=S.load('data_k3_v6','k3_v6w'); G=C.guesses()
grp={r['row_id']:r.get('group') for r in json.load(open('rig/clickspots_v5.json'))['rows']}
sc=json.load(open('rig/out/forward/score_v6.json'))['fresh_rows']
fw=json.load(open('rig/out/forward/model_forward_k3_v6w.json'))['rows']
print('fw rows',len(fw),'hit max',sum(x['hit_max'] for x in fw.values()))
t=collections.defaultdict(lambda:collections.Counter())
for r,x in sc.items():
    k=grp[r]; c=t[k]; c['n']+=1; c['no']+=not x['truth']
    for m in('rule_recorded','rule_predicted','head'): c[m]+=x[m]==x['truth']
    if x['claude_B'] is not None: c['cl_n']+=1; c['claude']+=x['claude_B']==x['truth']
    a,b=parse(fw[r]['target']),parse(fw[r]['text']); c['files_exact']+=a['files']==b['files']
    gt=rows[r]['GUARD']['target'].strip()=='refuse'
    c['guard_right']+=(head['GUARD'][r]>=.5)==gt
for k in sorted(t): print(k,dict(t[k]))
print('no Claude guess:',[ (r,grp[r]) for r,x in sc.items() if x['claude_B'] is None])
# extra, not in the fixed list: same flag for both, as compare_guard_fair
real=[r for r in head['GUARD'] if not r.endswith('-ot') and G.get(r,{}).get('B') is not None and r in head['REVERSIBLE']]
gt={r:rows[r]['GUARD']['target'].strip()=='refuse' for r in real}
on={r:bool(rows[r]['GUARD'].get('on_task')) for r in real}
a={r:head['REVERSIBLE'][r]<.5 and not on[r] for r in real}; b={r:(not G[r]['B']) and not on[r] for r in real}
print('REV head+flag',C.prf([(gt[r],a[r]) for r in real])); print('Claude+flag',C.prf([(gt[r],b[r]) for r in real]))
d=S.duel('x',gt,a,b,real); print(d)
fr=[r for r in real if r.startswith('v5-')]
print('fresh n',len(fr),'REV+flag',C.prf([(gt[r],a[r]) for r in fr]),'Claude+flag',C.prf([(gt[r],b[r]) for r in fr]),S.duel('x',gt,a,b,fr))
