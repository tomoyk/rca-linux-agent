import os
import time
import re

def get_cpu_usage(interval=0.1):
    """
    Reads /proc/stat twice to calculate CPU usage percentage.
    """
    def read_cpu_stats():
        try:
            with open('/proc/stat', 'r') as f:
                line = f.readline()
                if not line:
                    return None
                parts = line.split()
                if parts[0] != 'cpu':
                    return None
                values = [float(x) for x in parts[1:]]
                # values: user nice system idle iowait irq softirq steal guest guest_nice
                # Idle time includes 'idle' and 'iowait'
                idle = values[3] + values[4]
                total = sum(values)
                return idle, total
        except Exception:
            return None

    stat1 = read_cpu_stats()
    if not stat1:
        return 0.0
    
    time.sleep(interval)
    
    stat2 = read_cpu_stats()
    if not stat2:
        return 0.0

    idle1, total1 = stat1
    idle2, total2 = stat2

    diff_idle = idle2 - idle1
    diff_total = total2 - total1

    if diff_total == 0:
        return 0.0
    
    usage = (1.0 - (diff_idle / diff_total)) * 100.0
    return usage

def get_load_average():
    """
    Reads /proc/loadavg for 1, 5, and 15 minute averages.
    """
    try:
        with open('/proc/loadavg', 'r') as f:
            line = f.readline()
            if not line:
                return None
            parts = line.split()
            return {
                '1m': float(parts[0]),
                '5m': float(parts[1]),
                '15m': float(parts[2])
            }
    except Exception:
        return None

def get_memory_info():
    """
    Parses /proc/meminfo for RAM usage details.
    """
    mem_info = {}
    try:
        with open('/proc/meminfo', 'r') as f:
            for line in f:
                parts = line.split(':')
                if len(parts) == 2:
                    name = parts[0].strip()
                    value_parts = parts[1].strip().split()
                    value = int(value_parts[0])
                    mem_info[name] = value
    except Exception:
        return None
    
    total = mem_info.get('MemTotal', 0)
    free = mem_info.get('MemFree', 0)
    buffers = mem_info.get('Buffers', 0)
    cached = mem_info.get('Cached', 0)
    available = mem_info.get('MemAvailable', free + buffers + cached)
    used = total - available
    
    usage_pct = (used / total * 100.0) if total > 0 else 0.0
    
    return {
        'total_kb': total,
        'used_kb': used,
        'free_kb': free,
        'available_kb': available,
        'usage_pct': round(usage_pct, 2)
    }

def get_disk_usage(path='/'):
    """
    Uses os.statvfs to get disk usage of a path.
    """
    try:
        st = os.statvfs(path)
        block_size = st.f_frsize
        
        total = st.f_blocks * block_size
        free = st.f_bfree * block_size
        available = st.f_bavail * block_size
        used = total - free
        
        usage_pct = (used / total * 100.0) if total > 0 else 0.0
        
        # Inodes
        inode_total = st.f_files
        inode_free = st.f_ffree
        inode_used = inode_total - inode_free
        inode_pct = (inode_used / inode_total * 100.0) if inode_total > 0 else 0.0
        
        return {
            'path': path,
            'total_bytes': total,
            'used_bytes': used,
            'free_bytes': free,
            'usage_pct': round(usage_pct, 2),
            'inode_pct': round(inode_pct, 2)
        }
    except Exception:
        return None

def get_top_processes(limit=5):
    """
    Finds top processes by memory usage (RSS).
    """
    processes = []
    pids = [p for p in os.listdir('/proc') if p.isdigit()]
    
    for pid in pids:
        try:
            with open(f'/proc/{pid}/status', 'r') as f:
                name = ""
                rss = 0
                for line in f:
                    if line.startswith('Name:'):
                        name = line.split(':')[1].strip()
                    elif line.startswith('VmRSS:'):
                        rss = int(line.split(':')[1].strip().split()[0])
                if rss > 0:
                    processes.append({'pid': pid, 'name': name, 'rss_kb': rss})
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
            
    # Sort by RSS descending
    processes.sort(key=lambda x: x['rss_kb'], reverse=True)
    return processes[:limit]

if __name__ == "__main__":
    print(f"CPU Usage: {round(get_cpu_usage(), 2)}%")
    print(f"Load Average: {get_load_average()}")
    print(f"Memory Info: {get_memory_info()}")
    print(f"Disk Usage (/): {get_disk_usage()}")
    print("\nTop Processes (Memory):")
    for p in get_top_processes():
        print(f" PID {p['pid']:>7} | {p['name']:<20} | {p['rss_kb']:>10} KB")
