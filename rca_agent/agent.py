import json
import os
import resource
import subprocess
from typing import AsyncGenerator

import psutil
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


def collect_metrics() -> dict:
    return {
        'memory_usage_percent': psutil.virtual_memory().percent,
        'cpu_usage_percent': psutil.cpu_percent(interval=1.0),
        'disk_usage_percent': psutil.disk_usage('/').percent,
        'inode_usage_percent': _inode_usage('/'),
        'fd_usage_percent': _fd_usage(),
        'failed_systemd_services': _failed_services(),
    }


class RCALinuxAgent(BaseAgent):
    """Simple agent to gather Linux metrics."""

    name: str = 'rca_agent'
    description: str = 'Collect system metrics for RCA'

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        metrics = collect_metrics()
        text = json.dumps(metrics, indent=2)
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(role=self.name, parts=[types.Part(text=text)]),
        )


root_agent = RCALinuxAgent()
