import metrics_collector
import log_analyzer
import diagnoser
import json
from datetime import datetime

def run_investigation():
    print("="*60)
    print(f"VM INVESTIGATION REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # 1. Collect Metrics
    print("")
    print("[1] Collecting System Metrics...")
    
    metrics = {
        'cpu_usage': metrics_collector.get_cpu_usage(),
        'load_avg': metrics_collector.get_load_average(),
        'memory': metrics_collector.get_memory_info(),
        'disk': metrics_collector.get_disk_usage(),
        'top_processes': metrics_collector.get_top_processes(5)
    }
    
    print(f"  - CPU Usage: {metrics['cpu_usage']:.1f}%")
    print(f"  - Load Average (1m): {metrics['load_avg'].get('1m')}")
    print(f"  - Memory Usage: {metrics['memory'].get('usage_pct')}%")
    print(f"  - Disk Usage (/): {metrics['disk'].get('usage_pct')}%")

    # 2. Analyze Logs
    print("")
    print("[2] Scanning Logs for Errors (Last 30 mins)...")
    recent_logs = log_analyzer.get_recent_logs(minutes=30)
    print(f"  - Found {len(recent_logs)} suspicious log entries.")
    if recent_logs:
        print("  - Sample logs:")
        for log in recent_logs[:3]:
            # Each log is a dict: {'timestamp': ..., 'message': ...}
            if isinstance(log, dict):
                print(f"    [{log['timestamp']}] {log['message'][:120]}...")
            else:
                print(f"    {log}")

    # 3. Diagnose Issues
    print("")
    print("[3] Diagnosing Potential Issues...")
    findings = diagnoser.diagnose(metrics, recent_logs)
    
    if not findings:
        print("  - No critical issues identified by current rules.")
    else:
        for f in findings:
            print("")
            print(f"  >>> [{f['level']}] {f['category']}: {f['message']}")
            print(f"      Detail: {f['detail']}")

    # 4. Top Resource Consumers (Contextual)
    if metrics['cpu_usage'] > 50 or metrics['memory']['usage_pct'] > 50:
        print("")
        print("[4] Top Memory Consuming Processes:")
        for p in metrics['top_processes']:
            print(f"  - PID {p['pid']:>7} | {p['name']:<20} | {p['rss_kb']:>10} KB")

    print("")
    print("="*60)
    print("End of Report")
    print("="*60)

if __name__ == "__main__":
    run_investigation()
