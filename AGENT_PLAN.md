# VM Troubleshooting Agent Implementation Plan

## Overview
A lightweight Python-based agent to investigate system issues (CPU, RAM, Disk, Logs) without external dependencies.

## 1. Metrics Collection (Enhance metrics_collector.py)
- [ ] **System-wide Metrics**: (Done) CPU, LoadAvg, RAM, Disk.
- [ ] **Top Process Identification**: 
    - Parse `/proc/[pid]/stat` and `/proc/[pid]/status`.
    - Identify top 5 CPU and Memory consuming processes when system usage is high.

## 2. Log Analysis (New module: log_analyzer.py)
- [ ] **Syslog/Messages Scan**:
    - Read `/var/log/syslog` or `/var/log/messages`.
    - Filter for critical keywords: `error`, `fail`, `critical`, `oom-killer`, `segmentation fault`.
- [ ] **Kernel Ring Buffer (dmesg)**:
    - Check for hardware/driver issues or I/O errors.
- [ ] **Time Windowing**:
    - Focus on logs from the last 10-30 minutes.

## 3. Diagnostic Logic (New module: diagnoser.py)
- [ ] **Rule-based Engine**:
    - **OOM Detection**: High RAM usage + "Out of memory" in logs.
    - **CPU Bottleneck**: High LoadAvg/CPU usage + identification of the specific process.
    - **Disk Issue**: Usage > 90% or I/O errors in dmesg.
    - **Application Crash**: Repeated "segfault" or "exit code" in syslog.

## 4. Main Entry Point (investigator_agent.py)
- [ ] **Report Generation**:
    - Summarize system status.
    - List "Anomalies Found".
    - Provide "Candidate Causes".

## Constraints
- Use only Python standard libraries.
- No `pip install` required.
- Minimal performance impact.
