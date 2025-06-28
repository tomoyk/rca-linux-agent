import json
import os
import shutil
import subprocess
import unittest

from rca_agent.agent import collect_local_metrics, collect_metrics, _SSHClient

class LocalMetricsTest(unittest.TestCase):
    def test_collect_local_metrics(self):
        metrics = collect_local_metrics()
        self.assertIn('memory_usage_percent', metrics)
        self.assertIn('cpu_usage_percent', metrics)

class LXCRemoteMetricsTest(unittest.TestCase):
    container_name = 'rca-agent-test'

    @unittest.skipIf(shutil.which('lxc-create') is None, 'lxc not installed')
    def setUp(self):
        try:
            subprocess.run([
                'lxc-create', '-n', self.container_name, '-t', 'download', '--',
                '-d', 'alpine', '-r', '3.16', '-a', 'amd64'
            ], check=True)
            subprocess.run(['lxc-start', '-n', self.container_name, '-d'], check=True)
        except Exception as exc:
            self.skipTest(f'Unable to start LXC container: {exc}')

    @unittest.skipIf(shutil.which('lxc-create') is None, 'lxc not installed')
    def tearDown(self):
        subprocess.run(['lxc-stop', '-n', self.container_name])
        subprocess.run(['lxc-destroy', '-n', self.container_name])

    @unittest.skipIf(shutil.which('lxc-create') is None, 'lxc not installed')
    def test_collect_metrics_from_container(self):
        try:
            ip = subprocess.check_output(['lxc-info', '-n', self.container_name, '-iH'], text=True).strip()
        except Exception as exc:
            self.skipTest(f'Could not obtain container IP: {exc}')
        env = os.environ.copy()
        env.update({
            'RCA_REMOTE_HOST': ip,
            'RCA_REMOTE_USER': 'root',
        })
        with _SSHClient(ip, 'root') as client:
            metrics = collect_metrics(client)
        self.assertIn('memory_usage_percent', metrics)

