import os
import re
import subprocess
from datetime import datetime, timedelta

def get_recent_logs(file_path='/var/log/syslog', keywords=['error', 'fail', 'critical', 'oom-killer', 'segfault', 'killed'], minutes=15):
    """
    Scans a log file for keywords within a recent time window.
    """
    if not os.path.exists(file_path):
        return []

    recent_logs = []
    now = datetime.now()
    cutoff = now - timedelta(minutes=minutes)
    
    try:
        with open(file_path, 'r') as f:
            for line in f:
                # Check for keywords first to avoid expensive parsing
                if any(kw.lower() in line.lower() for kw in keywords):
                    timestamp = parse_timestamp(line)
                    if timestamp and timestamp > cutoff:
                        recent_logs.append({
                            'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                            'message': line.strip()
                        })
    except PermissionError:
        return ["Permission denied reading " + file_path]
    except Exception as e:
        return [f"Error reading {file_path}: {str(e)}"]

    return recent_logs

def parse_timestamp(line):
    """
    Heuristic timestamp parsing for syslog lines.
    """
    # Try ISO format: 2026-02-23T10:45:01
    iso_match = re.search(r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})', line)
    if iso_match:
        try:
            return datetime.strptime(iso_match.group(1), '%Y-%m-%dT%H:%M:%S')
        except: pass

    # Try standard BSD syslog format: Feb 23 10:45:01
    bsd_match = re.search(r'^([A-Z][a-z]{2}\s+\d+\s+\d{2}:\d{2}:\d{2})', line)
    if bsd_match:
        try:
            ts_str = bsd_match.group(1)
            # Normalize whitespace
            ts_str = " ".join(ts_str.split())
            current_year = datetime.now().year
            return datetime.strptime(f"{current_year} {ts_str}", '%Y %b %d %H:%M:%S')
        except: pass
    
    return None

def get_dmesg_errors():
    """
    Runs dmesg and filters for errors.
    """
    try:
        output = subprocess.check_output(['dmesg', '--level=err,crit,alert,emerg'], universal_newlines=True)
        return output.strip().split('\n') if output.strip() else []
    except Exception:
        return []

if __name__ == "__main__":
    print("Checking Syslog for recent errors (last 15 mins):")
    logs = get_recent_logs()
    if logs:
        for log in logs:
            if isinstance(log, str): print(log)
            else: print(f"[{log['timestamp']}] {log['message']}")
    else:
        print("No critical logs found in /var/log/syslog.")
    
    print("\nChecking Dmesg critical errors:")
    d_logs = get_dmesg_errors()
    if d_logs:
        for l in d_logs: print(l)
    else:
        print("No critical dmesg errors found.")
