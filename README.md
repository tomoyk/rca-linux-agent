# RCA Linux Agent

This repository provides a simple Root Cause Analysis (RCA) agent built using the
[Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/). The
agent collects basic system metrics from a Linux machine including memory usage,
CPU usage, disk usage, inode usage, file descriptor usage and the status of
failed `systemd` services. It also lists the top CPU-consuming processes and
provides a short analysis with possible reasons for high CPU usage.

## Running the Agent

1. Install the required dependencies:

   ```bash
   pip install google-adk psutil paramiko
   ```

2. (Optional) Set environment variables with SSH connection information to
   collect metrics from another machine:

   * `RCA_REMOTE_HOST` - hostname or IP address of the target machine
   * `RCA_REMOTE_USER` - SSH username
   * `RCA_REMOTE_PASSWORD` - SSH password (optional when using a key)
   * `RCA_REMOTE_KEY` - path to a private key file (optional)
   * `RCA_REMOTE_PORT` - SSH port (defaults to 22)

3. Execute the agent:

   ```bash
   python run_rca_agent.py
   ```

If `RCA_REMOTE_HOST` is not set, metrics are collected from the local machine.
When `RCA_REMOTE_HOST` is provided, the script connects over SSH to gather
metrics and recent logs from any failed `systemd` services, then prints the
results in JSON format.

## Testing

Running `make test` executes the unit tests. If the `lxc` command is available
and the current user is permitted to create containers, the tests attempt to
launch a temporary LXC container with an SSH server to verify remote metric
collection. When LXC is unavailable, those tests are skipped.
