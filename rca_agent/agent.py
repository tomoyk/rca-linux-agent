import json
import os
import resource
import subprocess
from typing import AsyncGenerator, Dict, List

import paramiko
import psutil


class _SSHClient:
    """Helper for running commands on a remote machine via SSH."""

    def __init__(
        self,
        host: str,
        user: str,
        *,
        password: str | None = None,
        key: str | None = None,
        port: int = 22,
    ):
        self.host = host
        self.user = user
        self.password = password
        self.key = key
        self.port = port
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def __enter__(self):
        connect_kwargs = {
            "hostname": self.host,
            "port": self.port,
            "username": self.user,
        }
        if self.key:
            connect_kwargs["key_filename"] = self.key
        else:
            connect_kwargs["password"] = self.password
        self.client.connect(**connect_kwargs)
        return self

    def run(self, cmd: str) -> str:
        stdin, stdout, stderr = self.client.exec_command(cmd)
        return stdout.read().decode()

    def __exit__(self, exc_type, exc, tb):
        self.client.close()
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.genai import types


def _inode_usage(path: str) -> float:
    try:
        stats = os.statvfs(path)
        if stats.f_files == 0:
            return 0.0
        used = stats.f_files - stats.f_favail
        return 100.0 * used / stats.f_files
    except Exception:
        return 0.0


def _fd_usage() -> float:
    try:
        soft_limit, _ = resource.getrlimit(resource.RLIMIT_NOFILE)
        used = len(os.listdir('/proc/self/fd'))
        return 100.0 * used / soft_limit if soft_limit else 0.0
    except Exception:
        return 0.0


def _failed_services() -> list[str]:
    try:
        output = subprocess.check_output(
            ['systemctl', '--failed', '--no-legend', '--plain'],
            text=True,
            stderr=subprocess.STDOUT,
        )
        return [line.split()[0] for line in output.strip().splitlines() if line]
    except Exception as exc:
        return [f'error: {exc}']


def _service_logs(service: str) -> List[str]:
    """Return the last few lines of a systemd service's log."""
    try:
        output = subprocess.check_output(
            ['journalctl', '-u', service, '--no-pager', '-n', '20'],
            text=True,
            stderr=subprocess.STDOUT,
        )
        return output.strip().splitlines()
    except Exception:
        return []


def _top_processes(count: int = 5) -> List[str]:
    """Return a list of the top CPU-consuming local processes."""
    try:
        output = subprocess.check_output(
            ['ps', '-eo', 'pid,comm,%cpu', '--sort=-%cpu'],
            text=True,
        )
        lines = output.strip().splitlines()[1:count + 1]
        return [line.strip() for line in lines]
    except Exception:
        return []


def _remote_memory_usage(client: _SSHClient) -> float:
    out = client.run("free | awk '/Mem:/ {print ($3/$2)*100}'")
    try:
        return float(out.strip())
    except Exception:
        return 0.0


def _remote_cpu_usage(client: _SSHClient) -> float:
    cmd = "top -bn1 | grep 'Cpu(s)' | awk '{print 100 - $8}'"
    out = client.run(cmd)
    try:
        return float(out.strip())
    except Exception:
        return 0.0


def _remote_disk_usage(client: _SSHClient) -> float:
    out = client.run("df -P / | tail -1 | awk '{print $5}'")
    try:
        return float(out.strip().strip('%'))
    except Exception:
        return 0.0


def _remote_inode_usage(client: _SSHClient) -> float:
    out = client.run("df -Pi / | tail -1 | awk '{print $5}'")
    try:
        return float(out.strip().strip('%'))
    except Exception:
        return 0.0


def _remote_fd_usage(client: _SSHClient) -> float:
    out = client.run('cat /proc/sys/fs/file-nr')
    try:
        alloc, _, max_files = [float(x) for x in out.split()[:3]]
        return (alloc / max_files) * 100 if max_files > 0 else 0.0
    except Exception:
        return 0.0


def _remote_failed_services(client: _SSHClient) -> List[str]:
    out = client.run('systemctl --failed --no-legend --plain')
    services = [line.split()[0] for line in out.strip().splitlines() if line]
    return services


def _remote_service_logs(client: _SSHClient, service: str) -> List[str]:
    out = client.run(f'journalctl -u {service} --no-pager -n 20 2>/dev/null')
    return out.strip().splitlines()


def _remote_top_processes(client: _SSHClient, count: int = 5) -> List[str]:
    """Return a list of the top CPU-consuming processes."""
    cmd = f"ps -eo pid,comm,%cpu --sort=-%cpu | head -n {count + 1}"
    out = client.run(cmd)
    lines = out.strip().splitlines()[1:]
    return [line.strip() for line in lines]


def collect_metrics(client: _SSHClient) -> Dict[str, object]:
    failed = _remote_failed_services(client)
    logs = {srv: _remote_service_logs(client, srv) for srv in failed}
    return {
        'memory_usage_percent': _remote_memory_usage(client),
        'cpu_usage_percent': _remote_cpu_usage(client),
        'disk_usage_percent': _remote_disk_usage(client),
        'inode_usage_percent': _remote_inode_usage(client),
        'fd_usage_percent': _remote_fd_usage(client),
        'failed_systemd_services': failed,
        'systemd_logs': logs,
        'top_cpu_processes': _remote_top_processes(client),
    }


def collect_local_metrics() -> Dict[str, object]:
    """Collect metrics from the local machine."""
    failed = _failed_services()
    logs = {srv: _service_logs(srv) for srv in failed}
    return {
        'memory_usage_percent': psutil.virtual_memory().percent,
        'cpu_usage_percent': psutil.cpu_percent(interval=0.1),
        'disk_usage_percent': psutil.disk_usage('/').percent,
        'inode_usage_percent': _inode_usage('/'),
        'fd_usage_percent': _fd_usage(),
        'failed_systemd_services': failed,
        'systemd_logs': logs,
        'top_cpu_processes': _top_processes(),
    }


def analyze_metrics(metrics: Dict[str, object]) -> List[str]:
    """Return human-readable analysis of the metrics."""
    reasons: List[str] = []
    cpu = metrics.get('cpu_usage_percent', 0.0)
    memory = metrics.get('memory_usage_percent', 0.0)
    if cpu > 80:
        procs = metrics.get('top_cpu_processes', [])
        if procs:
            reasons.append(
                f"High CPU usage detected ({cpu:.1f}%). Top processes: "
                + ", ".join(procs)
            )
        else:
            reasons.append(f"High CPU usage detected ({cpu:.1f}%).")
    if memory > 90:
        reasons.append(
            f"Memory usage is high ({memory:.1f}%). This may lead to increased CPU usage due to swapping."
        )
    if metrics.get('failed_systemd_services'):
        services = ", ".join(metrics['failed_systemd_services'])
        reasons.append(f"Failed systemd services detected: {services}.")
    if not reasons:
        reasons.append("No immediate issues detected.")
    return reasons


class RCALinuxAgent(BaseAgent):
    """Simple agent to gather Linux metrics."""

    name: str = 'rca_agent'
    description: str = 'Collect system metrics for RCA'

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        host = os.environ.get('RCA_REMOTE_HOST')
        if host:
            user = os.environ.get('RCA_REMOTE_USER', 'root')
            password = os.environ.get('RCA_REMOTE_PASSWORD')
            key = os.environ.get('RCA_REMOTE_KEY')
            port = int(os.environ.get('RCA_REMOTE_PORT', '22'))

            with _SSHClient(host, user, password=password, key=key, port=port) as client:
                metrics = collect_metrics(client)
        else:
            metrics = collect_local_metrics()
        analysis = analyze_metrics(metrics)
        result = {
            'metrics': metrics,
            'analysis': analysis,
        }
        text = json.dumps(result, indent=2)
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(role=self.name, parts=[types.Part(text=text)]),
        )


root_agent = RCALinuxAgent()
