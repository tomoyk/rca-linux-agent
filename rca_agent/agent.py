import os
import json
import resource
import subprocess
import tempfile
from typing import AsyncGenerator, Dict, List, Optional

import paramiko
import psutil
from google.adk.agents import Agent, BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.genai import types


def _get_key_params(key: Optional[str]):
    """keyがファイルパスならそのまま、内容なら一時ファイルに書き出してkey_filenameに渡す。"""
    if key and os.path.exists(key):
        return {"key_filename": key}
    elif key:
        tmp = tempfile.NamedTemporaryFile(delete=False)
        tmp.write(key.encode())
        tmp.close()
        return {"key_filename": tmp.name}
    else:
        return {}


class _SSHClient:
    """SSH経由でリモートコマンドを実行するヘルパークラス。"""

    def __init__(
        self,
        host: str,
        user: str,
        password: Optional[str] = None,
        key: Optional[str] = None,
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
            key_params = _get_key_params(self.key)
            connect_kwargs.update(key_params)
        elif self.password:
            connect_kwargs["password"] = self.password
        self.client.connect(**connect_kwargs)
        return self

    def run(self, cmd: str) -> str:
        stdin, stdout, stderr = self.client.exec_command(cmd)
        return stdout.read().decode()

    def __exit__(self, exc_type, exc, tb):
        self.client.close()


def _remote_metric(client: _SSHClient, cmd: str, postproc=lambda x: x) -> float:
    """リモートでコマンド実行し、floatで返す。"""
    out = client.run(cmd)
    try:
        return float(postproc(out.strip()))
    except Exception:
        return 0.0


def _remote_memory_usage(client: _SSHClient) -> float:
    return _remote_metric(client, "free | awk '/Mem:/ {print ($3/$2)*100}'")


# def _remote_memory_usage_details(client: _SSHClient) -> Dict[str, float]:
#     out = client.run("free -h")
#     lines = out.strip().splitlines()
#     headers = lines[0].split()
#     values = lines[1].split()
#     return {header: float(value) for header, value in zip(headers, values)}


def _remote_cpu_usage(client: _SSHClient) -> float:
    return _remote_metric(client, "top -bn1 | grep 'Cpu(s)' | awk '{print 100 - $8}'")


def _remote_disk_usage(client: _SSHClient) -> float:
    return _remote_metric(
        client, "df -P / | tail -1 | awk '{print $5}'", lambda x: x.strip("%")
    )


def _remote_inode_usage(client: _SSHClient) -> float:
    return _remote_metric(
        client, "df -Pi / | tail -1 | awk '{print $5}'", lambda x: x.strip("%")
    )


def _remote_fd_usage(client: _SSHClient) -> float:
    out = client.run("cat /proc/sys/fs/file-nr")
    try:
        alloc, _, max_files = [float(x) for x in out.split()[:3]]
        return (alloc / max_files) * 100 if max_files > 0 else 0.0
    except Exception:
        return 0.0


def _remote_failed_services(client: _SSHClient) -> List[str]:
    out = client.run("systemctl --failed --no-legend --plain --no-pager")
    return [line.split()[0] for line in out.strip().splitlines() if line]


def _remote_services(client: _SSHClient) -> list:
    out = client.run("systemctl list-units --type=service --no-pager --no-legend")
    return [line.split()[0] for line in out.strip().splitlines() if line]


def _remote_service_logs(client: _SSHClient, service: str) -> List[str]:
    out = client.run(f"journalctl -u {service} --no-pager -n 20 2>/dev/null")
    return out.strip().splitlines()


def _get_key_content(key: Optional[str]) -> Optional[str]:
    """keyがファイルパスなら内容を返し、内容ならそのまま返す。"""
    if key and os.path.exists(key):
        with open(key) as f:
            return f.read()
    return key


def collect_remote_metrics(
    host: str,
    user: str,
    password: Optional[str] = None,
    key: Optional[str] = None,
    port: int = 22,
) -> Dict[str, object]:
    """リモートマシンの主要メトリクスとsystemdサービス情報を収集。"""
    key_content = _get_key_content(key)
    with _SSHClient(
        host, user, password=password, key=key_content, port=port
    ) as client:
        failed = _remote_failed_services(client)
        logs = {srv: _remote_service_logs(client, srv) for srv in failed}
        services = _remote_services(client)
        return {
            "memory_usage_percent": _remote_memory_usage(client),
            "cpu_usage_percent": _remote_cpu_usage(client),
            "disk_usage_percent": _remote_disk_usage(client),
            "inode_usage_percent": _remote_inode_usage(client),
            "fd_usage_percent": _remote_fd_usage(client),
            "failed_systemd_services": failed,
            "services": services,
            "systemd_logs": logs,
        }


class RCALinuxAgent(BaseAgent):
    """リモート/ローカルのLinuxメトリクスを収集するRCAエージェント。"""

    name: str = "rca_agent"
    description: str = "Collect system metrics for RCA"

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        host = os.environ.get("RCA_REMOTE_HOST", "127.0.0.1")
        user = os.environ.get("RCA_REMOTE_USER", "root")
        password = os.environ.get("RCA_REMOTE_PASSWORD")
        key = os.environ.get("RCA_REMOTE_KEY")
        port = int(os.environ.get("RCA_REMOTE_PORT", "22"))
        metrics = collect_remote_metrics(host, user, password, key, port)

        text = json.dumps(metrics, indent=2)
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(role=self.name, parts=[types.Part(text=text)]),
        )


root_agent = Agent(
    name="rca_agent",
    model="gemini-2.0-flash",
    description="Collect and explain system metrics, including CPU usage, disk, and systemd services (all and failed).",
    instruction="You can ask about CPU, disk, and systemd service status (all or failed).",
    tools=[collect_remote_metrics],
)
