# VM Troubleshooting Agent

A lightweight, zero-dependency Python tool for investigating Linux system issues (CPU, RAM, Disk, Logs). Designed for rapid troubleshooting on virtual machines where installing external monitoring tools might be impractical.

## Features

- **Metrics Collection**: Real-time snapshots of CPU usage, Load Average, RAM usage, and Disk space.
- **Top Process Identification**: Identifies the most resource-intensive processes (by Memory RSS).
- **Log Analysis**: Scans `/var/log/syslog` (or `/var/log/messages`) and `dmesg` for critical errors, OOM events, and segmentation faults within a configurable time window (default 30 mins).
- **Automated Diagnostics**: Rule-based engine that correlates metrics and logs to identify:
  - CPU bottlenecks
  - Out of Memory (OOM) conditions and OOM-killer activity
  - Critical Disk space usage
  - Application crashes (segfaults)
- **Zero Dependencies**: Uses only Python standard libraries. No `pip install` required.

## Project Structure

- `investigator_agent.py`: Main entry point. Coordinates collection, analysis, and report generation.
- `metrics_collector.py`: Scrapes system metrics from `/proc` and `os.statvfs`.
- `log_analyzer.py`: Parses system logs and `dmesg` for suspicious patterns.
- `diagnoser.py`: Contains the logic for identifying system health issues based on collected data.

## Usage

Simply run the main script with Python 3:

```bash
python3 investigator_agent.py
```

*Note: Some features (like reading `/var/log/syslog` or running `dmesg`) may require root/sudo privileges depending on your system configuration.*

```bash
sudo python3 investigator_agent.py
```

## Sample Output

```text
============================================================
VM INVESTIGATION REPORT - 2026-02-23 14:30:05
============================================================

[1] Collecting System Metrics...
  - CPU Usage: 12.5%
  - Load Average (1m): 0.45
  - Memory Usage: 78.2%
  - Disk Usage (/): 45.1%

[2] Scanning Logs for Errors (Last 30 mins)...
  - Found 2 suspicious log entries.
  - Sample logs:
    [2026-02-23 14:15:01] kernel: [1234.56] Out of memory: Kill process 999 (my_app)...

[3] Diagnosing Potential Issues...

  >>> [CRITICAL] Memory: OOM Killer activity detected in logs!
      Detail: kernel: [1234.56] Out of memory: Kill process 999 (my_app)

[4] Top Memory Consuming Processes:
  - PID    1234 | python3              |     256400 KB
  - PID    2345 | nginx                |      45200 KB
...
============================================================
End of Report
============================================================
```

## Constraints

- Requires Python 3.x.
- Designed specifically for Linux systems (uses `/proc` filesystem).
