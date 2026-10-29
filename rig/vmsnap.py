"""QEMU snapshots of the VM inside a Modal sandbox (29 Oct).

The collector's resets were a fresh start plus the row's setup for every undo candidate; for agent rows the setup is
the agent's earlier steps, whose replays diverged from the agent's own run and ran rows out of time.  A snapshot of
the VM restores the exact state in seconds instead (rig/agentrun/snap_probe.py, snap_probe2.py: three restores in a
row exact, apps open and closed apps back, 15 snapshots of about 4.6 GB each in one sandbox).

The OSWorld clone's Modal provider opens QEMU's QMP socket on a tunnelled port when RIG_QEMU_QMP_PORT is set
(rig/agentrun/provider_monitor.diff); sandbox exec is not used, its TLS check fails from this Mac.  HMP savevm is
refused there ("Device 'pflash0' is writable but does not support snapshots": the raw UEFI store), so snapshots go
through QMP snapshot-save / snapshot-load on the disk node alone.  A snapshot lives inside the sandbox's disk overlay
and is gone when the sandbox closes.
"""
import json
import socket
import time


class VMSnapError(Exception):
    pass


class VMSnap:
    def __init__(self, env, timeout: float = 600):
        port = getattr(env.provider, "qmp_port", None)
        if not port:
            raise VMSnapError("no QMP port: set RIG_QEMU_QMP_PORT before the sandbox starts")
        self.env = env
        self.timeout = timeout
        self.s = socket.create_connection(("127.0.0.1", port), timeout=30)
        self.f = self.s.makefile("rb")
        greeting = json.loads(self.f.readline())
        self.qemu = greeting.get("QMP", {}).get("version", {}).get("qemu")
        self._cmd("qmp_capabilities")
        disk = next(b for b in self._cmd("query-block")["return"] if b["device"] == "ide0-hd0")
        self.node = disk["inserted"]["node-name"]
        # snapshots already in the disk: an adopted sandbox keeps those the agent's run saved (sNN, lib_run_single.py)
        self.tags = {sn["name"] for sn in disk["inserted"]["image"].get("snapshots", [])}
        self.n = 0

    def _cmd(self, name, **args):
        self.s.settimeout(60)
        self.s.sendall(json.dumps({"execute": name, "arguments": args} if args else {"execute": name}).encode() + b"\n")
        while True:
            line = self.f.readline()
            if not line:
                raise VMSnapError("QMP connection closed")
            msg = json.loads(line)
            if "event" not in msg:
                return msg

    def _job(self, name, **args):
        self.n += 1
        jid = f"{name}-{self.n}"
        r = self._cmd(name, **{"job-id": jid, "vmstate": self.node, "devices": [self.node], **args})
        if "error" in r:
            raise VMSnapError(f"{name}: {r['error'].get('desc', r['error'])}")
        t0 = time.time()
        while time.time() - t0 < self.timeout:
            job = next((j for j in self._cmd("query-jobs").get("return", []) if j["id"] == jid), None)
            if job and job["status"] == "concluded":
                self._cmd("job-dismiss", id=jid)
                if job.get("error"):
                    raise VMSnapError(f"{name}: {job['error']}")
                return time.time() - t0
            time.sleep(0.5)
        raise VMSnapError(f"{name}: no end in {self.timeout:.0f}s")

    def running(self) -> bool:
        return bool(self._cmd("query-status").get("return", {}).get("running"))

    def save(self, tag: str) -> float:
        t0 = time.time()
        self._job("snapshot-save", tag=tag)
        self.tags.add(tag)
        if not self.running():
            self._cmd("cont")
        return time.time() - t0

    def load(self, tag: str, server_wait: float = 120) -> float:
        """Restore `tag` and wait until the VM's command server answers.  A failed restore leaves QEMU paused
        (snap_probe.py, 29 Oct: the VM never answered again), so the VM is resumed before the error is raised."""
        if tag not in self.tags:
            raise VMSnapError(f"no snapshot {tag}")
        t0 = time.time()
        try:
            self._job("snapshot-load", tag=tag)
        finally:
            if not self.running():
                self._cmd("cont")
        while time.time() - t0 < server_wait:
            try:
                r = self.env.controller.execute_python_command("print('up')")
                if r and (r.get("output") or "").strip() == "up":
                    return time.time() - t0
            except Exception:
                pass
            time.sleep(2)
        raise VMSnapError(f"VM server silent {server_wait:.0f}s after restoring {tag}")

    def delete(self, tag: str):
        if tag in self.tags:
            self.tags.discard(tag)
            try:
                self._job("snapshot-delete", tag=tag)
            except VMSnapError:
                pass

    def overlay_bytes(self):
        disk = next(b for b in self._cmd("query-block")["return"] if b["device"] == "ide0-hd0")
        return disk["inserted"]["image"].get("actual-size")

    def close(self):
        try:
            self.s.close()
        except Exception:
            pass
