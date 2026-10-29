# Smoke test (29 Oct): can the VM inside a Modal sandbox be saved and restored with QEMU's own monitor?
# The monitor is a second HMP monitor (RIG_QEMU_MONITOR_PORT) reached through a tunnel, not sandbox exec.
import json, os, sys, time, glob, re, socket
BASE = '/Users/ngchenmeng/ai-research/osworld-testing'
sys.path[:0] = [BASE, BASE + '/OSWorld']
os.chdir(BASE + '/OSWorld')
os.environ.setdefault('RIG_QEMU_MONITOR_PORT', '7101')
from desktop_env.desktop_env import DesktopEnv

class HMP:
    def __init__(self, port):
        self.port = port; self.s = None
    def connect(self, tries=30):
        for i in range(tries):
            try:
                self.s = socket.create_connection(('127.0.0.1', self.port), timeout=20)
                return self.read_prompt(20)
            except Exception as e:
                last = e; time.sleep(5)
        raise RuntimeError(f'monitor not reachable: {last!r}')
    def read_prompt(self, timeout):
        self.s.settimeout(timeout); buf = b''; t = time.time()
        while b'(qemu)' not in buf:
            if time.time() - t > timeout:
                raise TimeoutError(buf[-500:])
            chunk = self.s.recv(65536)
            if not chunk:
                raise ConnectionError('monitor closed: ' + buf[-300:].decode(errors='replace'))
            buf += chunk
        text = re.sub(rb'\xff[\xfb-\xfe].|\x1b\[[0-9;]*[A-Za-z]|\r', b'', buf).decode(errors='replace')
        return text.rsplit('(qemu)', 1)[0].strip()
    def cmd(self, c, timeout=60):
        self.s.sendall((c + '\n').encode())
        out = self.read_prompt(timeout)
        return out.split('\n', 1)[1].strip() if '\n' in out else ''

task = json.load(open(glob.glob(BASE + '/rig/agentrun/tasks/examples/*/___fix_todo_list.json')[0]))
env = DesktopEnv(provider_name='modal', action_space='pyautogui', headless=True, require_a11y_tree=False, os_type='Ubuntu')
py = lambda c: (env.controller.execute_python_command(c) or {}).get('output', '').strip()
try:
    env.reset(task_config=task)
    port = env.provider.monitor_port
    print('monitor relay port:', port, flush=True)
    m = HMP(port); m.connect()
    print('info status:', m.cmd('info status'), flush=True)
    print('info block:\n', m.cmd('info block'), flush=True)
    print('marker A:', py("open('/home/user/snap_A','w').write('A'); import os; print(os.path.exists('/home/user/snap_A'))"), flush=True)
    t = time.time(); out = m.cmd('savevm s1', timeout=1200)
    print(f'savevm s1: {time.time()-t:.0f}s | {out[-400:]!r}', flush=True)
    print('info snapshots:\n', m.cmd('info snapshots'), flush=True)
    print('change:', py("import os; os.remove('/home/user/snap_A'); open('/home/user/snap_B','w').write('B'); print(os.path.exists('/home/user/snap_A'), os.path.exists('/home/user/snap_B'))"), flush=True)
    for i in (1, 2):
        t = time.time(); out = m.cmd('loadvm s1', timeout=1200)
        dt = time.time() - t; ok = None
        for _ in range(24):
            try:
                ok = py("import os; print(os.path.exists('/home/user/snap_A'), os.path.exists('/home/user/snap_B'), [f for f in os.listdir('/home/user') if f.startswith('snap_C')])")
                if ok: break
            except Exception:
                pass
            time.sleep(5)
        print(f'loadvm #{i}: {dt:.0f}s (+{time.time()-t-dt:.0f}s until the VM server answered) | {out[-300:]!r}', flush=True)
        print(f'  after restore [A exists, B exists, C files]: {ok}', flush=True)
        shot = env.controller.get_screenshot()
        print(f'  screenshot after restore: {len(shot) if shot else None} bytes', flush=True)
        if shot:
            open(f'/Users/ngchenmeng/.claude/jobs/fd36bbb5/tmp/probe/after_loadvm{i}.png', 'wb').write(shot)
        print('  write C:', py("open('/home/user/snap_C%d','w').write('C'); print('ok')" % i), flush=True)
    print('info snapshots (end):\n', m.cmd('info snapshots'), flush=True)
except Exception as e:
    print('FAILED:', repr(e)[:1500], flush=True)
finally:
    env.close()
    print('closed', flush=True)
