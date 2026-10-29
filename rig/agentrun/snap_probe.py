# Smoke test (29 Oct): can the VM inside a Modal sandbox be saved and restored with QEMU's own monitor?
# Monitors are reached through tunnels (RIG_QEMU_MONITOR_PORT, RIG_QEMU_QMP_PORT), not sandbox exec.
# Run 1: HMP savevm refused (raw UEFI store pflash0). Run 2: QMP snapshot-save/-load on the disk only.
import json, os, sys, time, glob, re, socket
BASE = '/Users/ngchenmeng/ai-research/osworld-testing'
sys.path[:0] = [BASE, BASE + '/OSWorld']
os.chdir(BASE + '/OSWorld')
os.environ.setdefault('RIG_QEMU_MONITOR_PORT', '7101')
os.environ.setdefault('RIG_QEMU_QMP_PORT', '7102')
from desktop_env.desktop_env import DesktopEnv
OUT = '/Users/ngchenmeng/.claude/jobs/fd36bbb5/tmp/probe'

def connect(port, tries=30):
    for _ in range(tries):
        try:
            return socket.create_connection(('127.0.0.1', port), timeout=20)
        except Exception as e:
            last = e; time.sleep(5)
    raise RuntimeError(f'port {port} not reachable: {last!r}')

class HMP:
    def __init__(self, port):
        self.s = connect(port); self.read_prompt(20)
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

class QMP:
    def __init__(self, port):
        self.s = connect(port); self.f = self.s.makefile('rb'); self.s.settimeout(60)
        self.greeting = json.loads(self.f.readline())
        self.cmd('qmp_capabilities')
    def cmd(self, name, timeout=60, **args):
        self.s.settimeout(timeout)
        self.s.sendall(json.dumps({'execute': name, 'arguments': args} if args else {'execute': name}).encode() + b'\n')
        while True:
            msg = json.loads(self.f.readline())
            if 'event' in msg:
                continue
            return msg
    def job(self, name, job_id, timeout=1200, **args):
        r = self.cmd(name, **{'job-id': job_id, **args})
        if 'error' in r:
            return r
        t = time.time()
        while time.time() - t < timeout:
            jobs = {j['id']: j for j in self.cmd('query-jobs').get('return', [])}
            j = jobs.get(job_id)
            if j and j['status'] == 'concluded':
                self.cmd('job-dismiss', id=job_id)
                return {'job': j, 'seconds': round(time.time() - t)}
            time.sleep(2)
        return {'timeout': True}

task = json.load(open(glob.glob(BASE + '/rig/agentrun/tasks/examples/*/___fix_todo_list.json')[0]))
env = DesktopEnv(provider_name='modal', action_space='pyautogui', headless=True, require_a11y_tree=False, os_type='Ubuntu')
py = lambda c: (env.controller.execute_python_command(c) or {}).get('output', '').strip()
CHECK = "import os; print(os.path.exists('/home/user/snap_A'), os.path.exists('/home/user/snap_B'), sorted(f for f in os.listdir('/home/user') if f.startswith('snap_C')))"

def answer(seconds=180):
    # the VM server's answer after a restore, or None within `seconds` (a paused VM never answers)
    t = time.time()
    while time.time() - t < seconds:
        try:
            r = env.controller.execute_python_command(CHECK)
            if r and r.get('output'):
                return r['output'].strip(), round(time.time() - t)
        except Exception:
            pass
        time.sleep(5)
    return None, round(time.time() - t)

try:
    env.reset(task_config=task)
    m = HMP(env.provider.monitor_port); q = QMP(env.provider.qmp_port)
    print('qemu:', q.greeting.get('QMP', {}).get('version', {}).get('qemu'), flush=True)
    disk = next(b for b in q.cmd('query-block')['return'] if b['device'] == 'ide0-hd0')
    node = disk['inserted']['node-name']
    print('disk node:', node, disk['inserted']['file'], flush=True)
    print('marker A:', py("open('/home/user/snap_A','w').write('A'); import os; print(os.path.exists('/home/user/snap_A'))"), flush=True)
    r = q.job('snapshot-save', 'save1', tag='s1', vmstate=node, devices=[node])
    print('snapshot-save:', json.dumps(r)[:600], flush=True)
    print('status:', q.cmd('query-status').get('return'), flush=True)
    print('info snapshots:\n', m.cmd('info snapshots'), flush=True)
    print('change (A, B):', py("import os; os.remove('/home/user/snap_A'); open('/home/user/snap_B','w').write('B'); print(os.path.exists('/home/user/snap_A'), os.path.exists('/home/user/snap_B'))"), flush=True)
    for i in (1, 2, 3):
        r = q.job('snapshot-load', f'load{i}', tag='s1', vmstate=node, devices=[node])
        st = q.cmd('query-status').get('return', {})
        print(f'snapshot-load #{i}:', json.dumps(r)[:400], '| status:', st, flush=True)
        if not st.get('running'):
            print('  cont:', q.cmd('cont'), flush=True)
        got, waited = answer()
        print(f'  after restore [A exists, B exists, C files]: {got} (server answered after {waited}s)', flush=True)
        shot = env.controller.get_screenshot()
        print(f'  screenshot: {len(shot) if shot else None} bytes', flush=True)
        if shot:
            open(f'{OUT}/after_load{i}.png', 'wb').write(shot)
        if got is None:
            break
        print('  write C:', py("open('/home/user/snap_C%d','w').write('C'); print('ok')" % i), flush=True)
    print('info snapshots (end):\n', m.cmd('info snapshots'), flush=True)
except Exception as e:
    print('FAILED:', repr(e)[:1500], flush=True)
finally:
    env.close()
    print('closed', flush=True)
