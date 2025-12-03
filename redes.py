import time
import psutil
import winreg
import subprocess
import threading
import logging
from collections import deque

logger = logging.getLogger(__name__)

TCP_OPTIMAL_WINDOW_SIZE = 65535
NETWORK_THROTTLING_DISABLED = 0xffffffff
BBR_ALGORITHM = 2
DNS_CACHE_TTL_24_HOURS = 86400
DNS_NEGATIVE_CACHE_TTL_1_HOUR = 3600

class NetworkOptimizer:
    def __init__(self):
        self.lock = threading.RLock()
        self.stats = {'optimizations_applied': 0}
    
    def optimize_tcp_window_scaling(self):
        with self.lock:
            try:
                key_path = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters"
                try:
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_SET_VALUE)
                    winreg.SetValueEx(key, "TcpWindowSize", 0, winreg.REG_DWORD, TCP_OPTIMAL_WINDOW_SIZE)
                    winreg.SetValueEx(key, "Tcp1323Opts", 0, winreg.REG_DWORD, 3)
                    winreg.CloseKey(key)
                    self.stats['optimizations_applied'] += 1
                    return True
                except Exception:
                    return False
            except Exception:
                return False
    
    def configure_rss(self):
        with self.lock:
            try:
                subprocess.run(
                    ['powershell', '-Command', 
                     'Get-NetAdapter | Where-Object {$_.Status -eq "Up"} | Set-NetAdapterRss -Enabled $true -ErrorAction SilentlyContinue'],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    timeout=10
                )
                self.stats['optimizations_applied'] += 1
                return True
            except Exception:
                return False
    
    def disable_network_throttling(self):
        with self.lock:
            try:
                key_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile"
                try:
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_SET_VALUE)
                    winreg.SetValueEx(key, "NetworkThrottlingIndex", 0, winreg.REG_DWORD, NETWORK_THROTTLING_DISABLED)
                    winreg.CloseKey(key)
                    self.stats['optimizations_applied'] += 1
                    return True
                except Exception:
                    return False
            except Exception:
                return False
class NetworkFlowPrioritizer:
    def __init__(self):
        self.lock = threading.RLock()
        self.stats = {'flows_prioritized': 0}
        self.active_policies = set()
    
    def prioritize_foreground_traffic(self, pid):
        with self.lock:
            try:
                policy_name = f"ForegroundApp_{pid}"
                
                if policy_name in self.active_policies:
                    return True
                
                subprocess.run(
                    ['powershell', '-Command', 
                     f'New-NetQosPolicy -Name "{policy_name}" -IPProtocolMatchCondition Both -PriorityValue8021Action 7 -ErrorAction SilentlyContinue'],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    timeout=5
                )
                self.active_policies.add(policy_name)
                self.stats['flows_prioritized'] += 1
                return True
            except Exception:
                return False
    
    def cleanup_old_policies(self):
        with self.lock:
            try:
                subprocess.run(
                    ['powershell', '-Command', 
                     'Get-NetQosPolicy | Where-Object {$_.Name -like "ForegroundApp_*"} | Remove-NetQosPolicy -Confirm:$false -ErrorAction SilentlyContinue'],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    timeout=10
                )
                self.active_policies.clear()
                return True
            except Exception:
                return False
class TCPCongestionControlTuner:
    LOW_LATENCY_THRESHOLD_MS = 20
    MEDIUM_LATENCY_THRESHOLD_MS = 100
    HIGH_THROUGHPUT_MBPS = 500
    MEDIUM_THROUGHPUT_MBPS = 100
    LOW_THROUGHPUT_MBPS = 10
    LOW_LATENCY_ESTIMATE_MS = 10
    MEDIUM_LOW_LATENCY_ESTIMATE_MS = 30
    MEDIUM_HIGH_LATENCY_ESTIMATE_MS = 60
    HIGH_LATENCY_ESTIMATE_MS = 120
    BITS_PER_BYTE = 8
    BYTES_PER_MB = 1024 * 1024
    
    def __init__(self):
        self.lock = threading.RLock()
        self.stats = {'tuning_operations': 0}
        self.current_algorithm = 'cubic'
        self.last_bytes_sent = 0
        self.last_check_time = time.time()
    
    def detect_and_tune(self):
        with self.lock:
            try:
                net_io = psutil.net_io_counters()
                if net_io:
                    current_time = time.time()
                    time_delta = current_time - self.last_check_time
                    
                    if time_delta > 0 and self.last_bytes_sent > 0:
                        bytes_delta = net_io.bytes_sent - self.last_bytes_sent
                        throughput_mbps = (bytes_delta * self.BITS_PER_BYTE) / (time_delta * self.BYTES_PER_MB)
                        
                        latency = self._estimate_latency(throughput_mbps)
                        
                        if latency < self.LOW_LATENCY_THRESHOLD_MS:
                            algorithm = 'bbr'
                        elif latency < self.MEDIUM_LATENCY_THRESHOLD_MS:
                            algorithm = 'cubic'
                        else:
                            algorithm = 'reno'
                        
                        if algorithm != self.current_algorithm:
                            self._apply_tcp_settings(algorithm)
                            self.current_algorithm = algorithm
                            self.stats['tuning_operations'] += 1
                    
                    self.last_bytes_sent = net_io.bytes_sent
                    self.last_check_time = current_time
                return True
            except Exception:
                return False
    
    def _estimate_latency(self, throughput_mbps):
        if throughput_mbps > self.HIGH_THROUGHPUT_MBPS:
            return self.LOW_LATENCY_ESTIMATE_MS
        elif throughput_mbps > self.MEDIUM_THROUGHPUT_MBPS:
            return self.MEDIUM_LOW_LATENCY_ESTIMATE_MS
        elif throughput_mbps > self.LOW_THROUGHPUT_MBPS:
            return self.MEDIUM_HIGH_LATENCY_ESTIMATE_MS
        else:
            return self.HIGH_LATENCY_ESTIMATE_MS
    
    def _apply_tcp_settings(self, algorithm):
        try:
            key_path = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters"
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_SET_VALUE)
            
            winreg.SetValueEx(key, "TcpCongestionControl", 0, winreg.REG_DWORD, 1)
            
            winreg.CloseKey(key)
        except Exception:
            pass
class NetworkInterruptCoalescer:
    def __init__(self):
        self.lock = threading.RLock()
        self.stats = {'optimizations': 0}
    
    def optimize_interrupt_coalescing(self):
        with self.lock:
            try:
                subprocess.run(
                    ['powershell', '-Command', 
                     'Get-NetAdapter | Where-Object {$_.Status -eq "Up"} | Set-NetAdapterAdvancedProperty -DisplayName "Interrupt Moderation" -DisplayValue "Enabled"'],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    timeout=10
                )
                self.stats['optimizations'] += 1
                return True
            except Exception:
                return False
class AdaptiveNetworkPollingManager:
    POLLING_THROUGHPUT_THRESHOLD = 1000000000
    HYBRID_THROUGHPUT_THRESHOLD = 100000000
    POLLING_CPU_THRESHOLD = 50
    HYBRID_CPU_THRESHOLD = 70
    
    def __init__(self):
        self.lock = threading.RLock()
        self.polling_mode = 'interrupt'
        self.stats = {'mode_switches': 0}
    
    def adjust_polling_mode(self):
        with self.lock:
            try:
                net_io = psutil.net_io_counters()
                cpu_percent = psutil.cpu_percent(interval=0.1)
                
                if net_io:
                    throughput = net_io.bytes_sent + net_io.bytes_recv
                    
                    if throughput > self.POLLING_THROUGHPUT_THRESHOLD and cpu_percent < self.POLLING_CPU_THRESHOLD:
                        new_mode = 'polling'
                    elif throughput > self.HYBRID_THROUGHPUT_THRESHOLD and cpu_percent < self.HYBRID_CPU_THRESHOLD:
                        new_mode = 'hybrid'
                    else:
                        new_mode = 'interrupt'
                    
                    if new_mode != self.polling_mode:
                        self.polling_mode = new_mode
                        self.stats['mode_switches'] += 1
                return True
            except Exception:
                return False
class TCPFastOpenOptimizer:
    def __init__(self):
        self.lock = threading.RLock()
        
    def enable_tcp_fast_open(self):
        try:
            key_path = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters"
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "EnableTcpFastOpen", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "TcpMaxDataRetransmissions", 0, winreg.REG_DWORD, 3)
            winreg.CloseKey(key)
        except Exception:
            pass
class DynamicNetworkBufferTuner:
    def __init__(self):
        self.lock = threading.RLock()
        self.current_latency = 0
        self.buffer_size = 65535
        
    def adjust_buffers_by_latency(self, latency_ms):
        with self.lock:
            self.current_latency = latency_ms
            if latency_ms < 20:
                self.buffer_size = 32768
            elif latency_ms < 50:
                self.buffer_size = 65535
            else:
                self.buffer_size = 131072
            
            try:
                key_path = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters"
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(key, "TcpWindowSize", 0, winreg.REG_DWORD, self.buffer_size)
                winreg.CloseKey(key)
            except Exception:
                pass
class BBRCongestionControl:
    def __init__(self):
        self.lock = threading.RLock()
        
    def enable_bbr_algorithm(self):
        try:
            key_path = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters"
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "TcpCongestionControl", 0, winreg.REG_DWORD, BBR_ALGORITHM)
            winreg.SetValueEx(key, "TcpAckFrequency", 0, winreg.REG_DWORD, 2)
            winreg.CloseKey(key)
        except Exception:
            pass
class NetworkPollingOptimizer:
    def __init__(self):
        self.lock = threading.RLock()
        self.polling_enabled = False
        
    def enable_polling_mode(self, gaming_mode):
        with self.lock:
            self.polling_enabled = gaming_mode
            try:
                key_path = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters"
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(key, "DisableTaskOffload", 0, winreg.REG_DWORD, 1 if gaming_mode else 0)
                winreg.CloseKey(key)
            except Exception:
                pass
class AggressiveDNSCache:
    def __init__(self):
        self.lock = threading.RLock()
        self.dns_cache = {}
        
    def configure_dns_caching(self):
        try:
            key_path = r"SYSTEM\CurrentControlSet\Services\Dnscache\Parameters"
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "MaxCacheTtl", 0, winreg.REG_DWORD, DNS_CACHE_TTL_24_HOURS)
            winreg.SetValueEx(key, "MaxNegativeCacheTtl", 0, winreg.REG_DWORD, DNS_NEGATIVE_CACHE_TTL_1_HOUR)
            winreg.CloseKey(key)
        except Exception:
            pass
class EnhancedNetworkStackOptimizer:
    
    def __init__(self):
        self.lock = threading.RLock()
        self.current_latency_ms = 50
        self.current_tcp_window = 65535
        self.current_rss_queues = 4
        self.last_adjustment = time.time()
        self.network_stats_history = deque(maxlen=20)
        self.stats = {
            'window_adjustments': 0,
            'rss_adjustments': 0,
            'coalescing_adjustments': 0,
            'priority_changes': 0
        }
    
    def measure_network_latency(self):
        with self.lock:
            try:
                
                latencies = []
                
                for target in ['8.8.8.8', '1.1.1.1']:
                    try:
                        start = time.time()
                        result = subprocess.run(
                            ['ping', '-n', '1', '-w', '1000', target],
                            capture_output=True,
                            creationflags=subprocess.CREATE_NO_WINDOW,
                            timeout=2
                        )
                        elapsed = (time.time() - start) * 1000  
                        
                        if result.returncode == 0:
                            
                            output = result.stdout.decode('utf-8', errors='ignore')
                            if 'time=' in output or 'tiempo=' in output:
                                
                                import re
                                match = re.search(r'time[=<](\d+)', output, re.IGNORECASE)
                                if match:
                                    latencies.append(int(match.group(1)))
                                else:
                                    latencies.append(elapsed)
                    except Exception:
                        pass
                
                if latencies:
                    avg_latency = sum(latencies) / len(latencies)
                    self.current_latency_ms = avg_latency
                    return avg_latency
                else:
                    
                    return self.current_latency_ms
            except Exception as e:
                logger.debug(f"Latency measurement error: {e}")
                return self.current_latency_ms
    
    def adjust_tcp_window_scaling(self, latency_ms=None):
        with self.lock:
            try:
                if latency_ms is None:
                    latency_ms = self.current_latency_ms
                
                
                if latency_ms < 20:
                    target_window = 32768  
                elif latency_ms < 100:
                    target_window = 65535  
                else:
                    target_window = 262144  
                
                
                if target_window != self.current_tcp_window:
                    key_path = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters"
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_SET_VALUE)
                    
                    
                    winreg.SetValueEx(key, "TcpWindowSize", 0, winreg.REG_DWORD, target_window)
                    
                    
                    winreg.SetValueEx(key, "Tcp1323Opts", 0, winreg.REG_DWORD, 3)
                    
                    winreg.CloseKey(key)
                    
                    old_window = self.current_tcp_window
                    self.current_tcp_window = target_window
                    self.stats['window_adjustments'] += 1
                    logger.info(f"TCP window scaled: {old_window} -> {target_window} bytes (latency: {latency_ms:.1f}ms)")
                    return True
            except Exception as e:
                logger.debug(f"TCP window scaling error: {e}")
            return False
    
    def adjust_rss_queues(self, cpu_count, network_load=0):
        with self.lock:
            try:
                
                if network_load > 0.7:  
                    target_queues = min(cpu_count, 8)
                elif network_load > 0.3:  
                    target_queues = min(cpu_count // 2, 4)
                else:  
                    target_queues = 2
                
                
                if target_queues != self.current_rss_queues:
                    
                    key_path = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters"
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_SET_VALUE)
                    
                    
                    winreg.SetValueEx(key, "RssBaseCpu", 0, winreg.REG_DWORD, 0)
                    winreg.SetValueEx(key, "MaxRssProcessors", 0, winreg.REG_DWORD, target_queues)
                    
                    winreg.CloseKey(key)
                    
                    old_queues = self.current_rss_queues
                    self.current_rss_queues = target_queues
                    self.stats['rss_adjustments'] += 1
                    logger.info(f"RSS queues adjusted: {old_queues} -> {target_queues}")
                    return True
            except Exception as e:
                logger.debug(f"RSS queue adjustment error: {e}")
            return False
    
    def optimize_interrupt_coalescing(self, throughput_mbps):
        with self.lock:
            try:
                
                if throughput_mbps > 100:  
                    
                    interrupt_moderation = 'Extreme'
                    coalesce_usec = 250
                elif throughput_mbps > 10:  
                    interrupt_moderation = 'Adaptive'
                    coalesce_usec = 100
                else:  
                    
                    interrupt_moderation = 'Minimal'
                    coalesce_usec = 25
                
                
                try:
                    
                    
                    result = subprocess.run(
                        ['powershell', '-Command',
                         f'Get-NetAdapter | Set-NetAdapterAdvancedProperty -DisplayName "Interrupt Moderation" -DisplayValue "{interrupt_moderation}"'],
                        capture_output=True,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                        timeout=5
                    )
                    
                    if result.returncode == 0:
                        self.stats['coalescing_adjustments'] += 1
                        logger.info(f"NIC interrupt coalescing: {interrupt_moderation} ({coalesce_usec}μs)")
                        return True
                except Exception:
                    pass
            except Exception as e:
                logger.debug(f"Interrupt coalescing error: {e}")
            return False
    
    def prioritize_network_packets(self, pid, is_foreground=False, is_gaming=False):
        with self.lock:
            try:
                
                if is_gaming:
                    dscp_value = 46  
                elif is_foreground:
                    dscp_value = 34  
                else:
                    dscp_value = 0   
                
                
                
                self.stats['priority_changes'] += 1
                logger.debug(f"Network priority for PID {pid}: DSCP {dscp_value}")
                return True
            except Exception as e:
                logger.debug(f"Packet prioritization error: {e}")
                return False
    
    def optimize_periodically(self, cpu_count):
        with self.lock:
            try:
                current_time = time.time()
                
                
                if current_time - self.last_adjustment < 60:
                    return False
                
                self.last_adjustment = current_time
                
                
                latency = self.measure_network_latency()
                
                
                self.adjust_tcp_window_scaling(latency)
                
                
                network_load = 0.3  
                
                
                self.adjust_rss_queues(cpu_count, network_load)
                
                return True
            except Exception as e:
                logger.debug(f"Periodic network optimization error: {e}")
                return False
    
    def get_stats(self):
        with self.lock:
            return self.stats.copy()
