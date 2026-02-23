def diagnose(metrics, logs):
    """
    Analyzes metrics and logs to identify potential issues.
    """
    findings = []
    
    # 1. CPU Diagnosis
    cpu_usage = metrics.get('cpu_usage', 0)
    load_avg = metrics.get('load_avg', {}).get('1m', 0)
    if cpu_usage > 80 or load_avg > 2.0:
        findings.append({
            'level': 'CRITICAL' if cpu_usage > 95 else 'WARNING',
            'category': 'CPU',
            'message': f"High CPU/Load detected (CPU: {cpu_usage:.1f}%, Load: {load_avg})",
            'detail': "Check top CPU consuming processes."
        })

    # 2. Memory Diagnosis
    mem_info = metrics.get('memory', {})
    usage_pct = mem_info.get('usage_pct', 0)
    if usage_pct > 85:
        findings.append({
            'level': 'CRITICAL' if usage_pct > 95 else 'WARNING',
            'category': 'Memory',
            'message': f"High Memory usage: {usage_pct}%",
            'detail': "OOM Killer might trigger soon."
        })
    
    # Check for OOM in logs
    oom_logs = [l for l in logs if 'oom-killer' in l.get('message', '').lower() or 'out of memory' in l.get('message', '').lower()]
    if oom_logs:
        findings.append({
            'level': 'CRITICAL',
            'category': 'Memory',
            'message': "OOM Killer activity detected in logs!",
            'detail': oom_logs[0]['message']
        })

    # 3. Disk Diagnosis
    disk_usage = metrics.get('disk', {})
    disk_pct = disk_usage.get('usage_pct', 0)
    if disk_pct > 90:
        findings.append({
            'level': 'CRITICAL' if disk_pct > 98 else 'WARNING',
            'category': 'Disk',
            'message': f"Disk space is low: {disk_pct}%",
            'detail': f"Path: {disk_usage.get('path')}"
        })
    
    # 4. Process-specific Issues
    segfault_logs = [l for l in logs if 'segfault' in l.get('message', '').lower()]
    if segfault_logs:
        findings.append({
            'level': 'WARNING',
            'category': 'Application',
            'message': "Process segmentation faults detected.",
            'detail': segfault_logs[0]['message']
        })

    # 5. General Error Log Summary
    if len(logs) > 0:
        findings.append({
            'level': 'INFO',
            'category': 'Logs',
            'message': f"Detected {len(logs)} entries with suspicious keywords in logs.",
            'detail': "See raw logs for details or check for repeated failures."
        })

    return findings
