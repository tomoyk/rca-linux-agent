# RCA Linux Agent

This repository provides a simple Root Cause Analysis (RCA) agent built using the
[Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/). The
agent collects basic system metrics from a Linux machine including memory usage,
CPU usage, disk usage, inode usage, file descriptor usage and the status of
failed `systemd` services.

## Running the Agent

1. Install the required dependencies:

   ```bash
   pip install google-adk psutil paramiko
   ```

2. Set environment variables with the SSH connection information:

   * `RCA_REMOTE_HOST` - hostname or IP address of the target machine
   * `RCA_REMOTE_USER` - SSH username
   * `RCA_REMOTE_PASSWORD` - SSH password (optional when using a key)
   * `RCA_REMOTE_KEY` - path to a private key file (optional)

3. Execute the agent:

   ```bash
   python run_rca_agent.py
   ```

The script connects to the specified remote machine over SSH, gathers system
metrics and recent logs from any failed `systemd` services, then prints the
results in JSON format.
