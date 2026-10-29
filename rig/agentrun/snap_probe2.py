# Smoke test 2 (29 Oct): QEMU snapshots with apps open (VS Code + Writer, unsaved text), and 15 snapshots in a row
# (what an agent run of 15 steps needs). QMP through the tunnelled port, as in snap_probe.py.
import json, os, sys, time, glob
BASE = '/Users/ngchenmeng/ai-research/osworld-testing'
sys.path[:0] = [BASE, BASE + '/OSWorld', BASE + '/rig/agentrun']
os.chdir(BASE + '/OSWorld')
os.environ.setdefault('RIG_QEMU_MONITOR_PORT', '7101')
os.environ.setdefault('RIG_QEMU_QMP_PORT', '7102')
from snap_probe_lib import HMP, QMP
from desktop_env.desktop_env import DesktopEnv
from rig.agentrun.fidelity import screen_diff
OUT = '/Users/ngchenmeng/.claude/jobs/fd36bbb5/tmp/probe/p2'
os.makedirs(OUT, exist_ok=True)

task = json.load(open(BASE + '/rig/agentrun/tasks/examples/vs_code/___fix_todo_list.json'))
env = DesktopEnv(provider_name='modal', action_space='pyautogui', headless=True, require_a11y_tree=True, os_type='Ubuntu')
py = lambda c: (env.controller.execute_python_command(c) or {}).get('output', '').strip()
sh = lambda c: py("import subprocess; print(subprocess.run(%r, shell=True, capture_output=True, text=True, env={'DISPLAY': ':0', 'HOME': '/home/user', 'PATH': '/usr/bin:/bin:/usr/local/bin'}).stdout)" % c)
windows = lambda: sh("wmctrl -l | awk '{$1=$2=$3=\"\"; print}' | sed 's/^ *//' | sort")
files = lambda: py("import os; print(sorted(f for f in os.listdir('/home/user') if f.startswith('snap_')))")

def shot(name):
    s = env.controller.get_screenshot()
    p = f'{OUT}/{name}.png'
    if s:
        open(p, 'wb').write(s)
    return p if s else None

def tree_len():
    t = env.controller.get_accessibility_tree()
    return len(t) if t else None

def wait_server(seconds=120):
    t = time.time()
    while time.time() - t < seconds:
        try:
            if py("print('up')") == 'up':
                return round(time.time() - t)
        except Exception:
            pass
        time.sleep(3)
    return None

try:
    env.reset(task_config=task)
    m = HMP(env.provider.monitor_port); q = QMP(env.provider.qmp_port)
    node = next(b for b in q.cmd('query-block')['return'] if b['device'] == 'ide0-hd0')['inserted']['node-name']
    size = lambda: next(b for b in q.cmd('query-block')['return'] if b['device'] == 'ide0-hd0')['inserted']['image'].get('actual-size')
    print('disk node:', node, '| overlay size before:', size(), flush=True)

    # Apps open with unsaved text: VS Code editing todo.py, Writer with a new document
    sh("code /home/user/project/todo.py"); time.sleep(8)
    py("import pyautogui; pyautogui.hotkey('ctrl','end'); pyautogui.typewrite('\\n# UNSAVED_VSCODE_MARK', interval=0.03)")
    sh("setsid libreoffice --writer >/dev/null 2>&1 &"); time.sleep(25)
    py("import pyautogui; pyautogui.typewrite('UNSAVED WRITER TEXT 123', interval=0.03)"); time.sleep(2)
    w0 = windows(); s0 = shot('S0'); t0 = tree_len()
    print('windows before save:\n ', w0.replace('\n', '\n  '), '\n a11y tree chars:', t0, flush=True)

    r = q.job('snapshot-save', 'save1', tag='s1', vmstate=node, devices=[node])
    print('snapshot-save:', json.dumps(r)[:300], '| overlay size:', size(), flush=True)
    print('status:', q.cmd('query-status').get('return'), flush=True)

    # Change things: close Writer without saving, type more in VS Code, make a file
    sh("pkill -f soffice"); time.sleep(3)
    py("import pyautogui; pyautogui.typewrite('\\n# AFTER_SAVE_CHANGE', interval=0.03); open('/home/user/snap_after','w').write('x')")
    time.sleep(2)
    w1 = windows(); s1 = shot('S1_changed')
    print('windows after change:\n ', w1.replace('\n', '\n  '), f'\n screen diff S0 vs changed: {screen_diff(s0, s1):.1f}', flush=True)

    r = q.job('snapshot-load', 'load1', tag='s1', vmstate=node, devices=[node])
    st = q.cmd('query-status').get('return', {})
    print('snapshot-load:', json.dumps(r)[:300], '| status:', st, '| server answered after', wait_server(), 's', flush=True)
    if not st.get('running'):
        print('  cont:', q.cmd('cont'), flush=True)
    w2 = windows(); s2 = shot('S0_restored'); t2 = tree_len()
    print('windows after restore:\n ', w2.replace('\n', '\n  '), flush=True)
    print(f' same windows as before save: {w2 == w0} | screen diff S0 vs restored: {screen_diff(s0, s2):.1f} | a11y tree chars {t2} (before {t0}) | snap files: {files()}', flush=True)
    # Still responsive after restore: type into Writer and look again
    py("import pyautogui; pyautogui.typewrite(' AFTER RESTORE', interval=0.03)"); time.sleep(2)
    s3 = shot('S0_restored_typed')
    print(f' typing after restore changes the screen: diff {screen_diff(s2, s3):.1f}', flush=True)

    # 15 snapshots in a row, each after a small change; then load one in the middle
    times = []
    for k in range(2, 17):
        py(f"open('/home/user/snap_k{k:02d}','w').write('k')")
        t = time.time(); r = q.job('snapshot-save', f'save{k}', tag=f's{k}', vmstate=node, devices=[node])
        dt = round(time.time() - t, 1); times.append(dt)
        err = r.get('job', {}).get('error') or r.get('error')
        print(f'  s{k}: {dt}s overlay {size()}' + (f' ERROR {err}' if err else ''), flush=True)
        if err:
            break
    r = q.job('snapshot-load', 'load8', tag='s8', vmstate=node, devices=[node])
    print('load s8:', json.dumps(r)[:200], '| server after', wait_server(), 's | snap files (expect k02..k08):', files(), flush=True)
    print('info snapshots:\n', m.cmd('info snapshots'), flush=True)
except Exception as e:
    print('FAILED:', repr(e)[:1500], flush=True)
finally:
    env.close()
    print('closed', flush=True)
