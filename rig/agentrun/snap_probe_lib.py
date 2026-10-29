# HMP and QMP clients for the tunnelled QEMU monitors (shared by the snapshot probes)
import json, re, socket, time

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
