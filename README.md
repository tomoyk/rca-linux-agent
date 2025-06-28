# RCA Linux Agent

This repository provides a simple Root Cause Analysis (RCA) agent built using the
[Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/). The
agent collects basic system metrics from a Linux machine including memory usage,
CPU usage, disk usage, inode usage, file descriptor usage and the status of
failed `systemd` services.

## Running the Agent

1. Install the required dependencies:

   ```bash
   pip install google-adk psutil
   ```

2. Execute the agent:

   ```bash
   python run_rca_agent.py
   ```

The script runs a minimal ADK runner that invokes the agent once and prints the
collected metrics in JSON format.
