import time
import psutil
import win32api
import win32con
import winreg
import subprocess
import ctypes
import threading
import platform
from ctypes import wintypes
from collections import defaultdict, deque
import logging

logger = logging.getLogger(__name__)


SE_LOCK_MEMORY_NAME = "SeLockMemoryPrivilege"
MEM_LARGE_PAGES = 0x20000000
MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
PAGE_READWRITE = 0x04
ProcessMemoryPriority = 40
MEMORY_PRIORITY_VERY_LOW = 1
MEMORY_PRIORITY_LOW = 2
MEMORY_PRIORITY_MEDIUM = 3
MEMORY_PRIORITY_BELOW_NORMAL = 4
MEMORY_PRIORITY_NORMAL = 5
ProcessWorkingSetWatchEx = 42
MEM_PHYSICAL = 0x00400000
AWE_ENABLED_FLAG = 0x00020000
QUOTA_LIMITS_HARDWS_MIN_ENABLE = 0x00000001
QUOTA_LIMITS_HARDWS_MAX_ENABLE = 0x00000002
PAGE_PRIORITY_NORMAL = 5
PAGE_PRIORITY_MEDIUM = 3
PAGE_PRIORITY_LOW = 1
TOKEN_ADJUST_PRIVILEGES = 0x0020
TOKEN_QUERY = 0x0008
SE_PRIVILEGE_ENABLED = 0x00000002
PROCESS_SET_INFORMATION = 0x0200
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_SET_QUOTA = 0x0100

ntdll = ctypes.WinDLL('ntdll')
kernel32 = ctypes.WinDLL('kernel32')
advapi32 = ctypes.WinDLL('advapi32')

class LUID(ctypes.Structure):
    _fields_ = [("LowPart", ctypes.wintypes.DWORD), ("HighPart", ctypes.wintypes.LONG)]
class LUID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("Luid", LUID), ("Attributes", ctypes.wintypes.DWORD)]
class TOKEN_PRIVILEGES(ctypes.Structure):
    _fields_ = [("PrivilegeCount", ctypes.wintypes.DWORD), ("Privileges", LUID_AND_ATTRIBUTES * 1)]
class MEMORY_PRIORITY_INFORMATION(ctypes.Structure):
    _fields_ = [('MemoryPriority', ctypes.wintypes.ULONG)]

class WorkingSetOptimizer:
    def __init__(self, handle_cache):
        self.handle_cache = handle_cache
        self.trim_history = defaultdict(deque)
        self.memory_baselines = {}
        self.foreground_tracking = {}
        self.lock = threading.RLock()
        
        self.default_trim_interval = 60.0
        self.min_trim_interval = 30.0
        self.max_trim_interval = 300.0
        
        self.significant_memory_change_percent = 20.0
        self.aggressive_trim_threshold_mb = 500
        self.min_background_time_for_trim = 900.0
        
        self.stats = {
            'total_trims': 0,
            'total_memory_freed_mb': 0,
            'avg_memory_freed_per_trim_mb': 0,
            'trims_with_significant_effect': 0
        }
    
    def should_trim_working_set(self, pid, current_memory_mb):
        with self.lock:
            current_time = time.time()
            
            if pid not in self.memory_baselines:
                self.memory_baselines[pid] = {
                    'initial_mb': current_memory_mb,
                    'peak_mb': current_memory_mb,
                    'last_trim': 0,
                    'trim_interval': self.default_trim_interval
                }
                self.foreground_tracking[pid] = {
                    'last_foreground': current_time,
                    'is_foreground': False
                }
                return False
            
            baseline = self.memory_baselines[pid]
            tracking = self.foreground_tracking.get(pid, {'last_foreground': current_time, 'is_foreground': False})
            
            if current_memory_mb > baseline['peak_mb']:
                baseline['peak_mb'] = current_memory_mb
            
            time_since_trim = current_time - baseline['last_trim']
            if time_since_trim < baseline['trim_interval']:
                return False
            
            time_since_foreground = current_time - tracking['last_foreground']
            if time_since_foreground < self.min_background_time_for_trim:
                return False
            
            if pid in self.trim_history and self.trim_history[pid]:
                last_trim_event = self.trim_history[pid][-1]
                memory_growth_percent = ((current_memory_mb - last_trim_event['memory_after_mb']) / 
                                        max(last_trim_event['memory_after_mb'], 1)) * 100
                
                if memory_growth_percent > self.significant_memory_change_percent:
                    return True
            
            if current_memory_mb > self.aggressive_trim_threshold_mb:
                return True
            
            if time_since_trim >= baseline['trim_interval']:
                return True
            
            return False
    
    def trim_working_set(self, pid, current_memory_mb=None):
        with self.lock:
            result = {
                'success': False,
                'memory_freed_mb': 0.0,
                'effectiveness': 0.0
            }
            
            try:
                if current_memory_mb is None:
                    process = psutil.Process(pid)
                    current_memory_mb = process.memory_info().rss / (1024 * 1024)
                
                memory_before_mb = current_memory_mb
                
                handle = self.handle_cache.get_handle(
                    pid,
                    PROCESS_SET_INFORMATION | PROCESS_QUERY_INFORMATION | PROCESS_SET_QUOTA
                )
                
                if not handle:
                    return result
                
                trim_result = kernel32.SetProcessWorkingSetSize(
                    handle,
                    ctypes.c_size_t(-1),
                    ctypes.c_size_t(-1)
                )
                
                if not trim_result:
                    return result
                
                time.sleep(0.05)
                
                try:
                    process = psutil.Process(pid)
                    memory_after_mb = process.memory_info().rss / (1024 * 1024)
                except Exception:
                    memory_after_mb = memory_before_mb
                
                memory_freed_mb = max(0, memory_before_mb - memory_after_mb)
                effectiveness = (memory_freed_mb / memory_before_mb * 100) if memory_before_mb > 0 else 0
                
                current_time = time.time()
                trim_event = {
                    'timestamp': current_time,
                    'memory_before_mb': memory_before_mb,
                    'memory_after_mb': memory_after_mb,
                    'memory_freed_mb': memory_freed_mb,
                    'effectiveness_percent': effectiveness
                }
                
                self.trim_history[pid].append(trim_event)
                if len(self.trim_history[pid]) > 20:
                    self.trim_history[pid].popleft()
                
                if pid in self.memory_baselines:
                    self.memory_baselines[pid]['last_trim'] = current_time
                    
                    self._adapt_trim_interval(pid, effectiveness)
                
                self.stats['total_trims'] += 1
                self.stats['total_memory_freed_mb'] += memory_freed_mb
                self.stats['avg_memory_freed_per_trim_mb'] = \
                    self.stats['total_memory_freed_mb'] / self.stats['total_trims']
                
                if effectiveness > 10.0:
                    self.stats['trims_with_significant_effect'] += 1
                
                result.update({
                    'success': True,
                    'memory_freed_mb': memory_freed_mb,
                    'effectiveness': effectiveness
                })
                
            except Exception as e:
                logger.debug(f"Error collecting memory metrics for PID {pid}: {type(e).__name__}: {e}")
            
            return result
    
    def _adapt_trim_interval(self, pid, last_effectiveness):
        if pid not in self.memory_baselines:
            return
        
        baseline = self.memory_baselines[pid]
        
        if last_effectiveness > 20.0:
            baseline['trim_interval'] = max(self.min_trim_interval, baseline['trim_interval'] * 0.8)
        elif last_effectiveness < 5.0:
            baseline['trim_interval'] = min(self.max_trim_interval, baseline['trim_interval'] * 1.3)
    
    def mark_process_foreground(self, pid, is_foreground):
        with self.lock:
            current_time = time.time()
            if pid not in self.foreground_tracking:
                self.foreground_tracking[pid] = {
                    'last_foreground': current_time if is_foreground else 0,
                    'is_foreground': is_foreground
                }
            else:
                tracking = self.foreground_tracking[pid]
                if is_foreground:
                    tracking['last_foreground'] = current_time
                tracking['is_foreground'] = is_foreground
    
    def get_trim_statistics_for_pid(self, pid):
        with self.lock:
            if pid not in self.trim_history or len(self.trim_history[pid]) == 0:
                return None
            
            history = list(self.trim_history[pid])
            
            return {
                'total_trims': len(history),
                'total_memory_freed_mb': sum(e['memory_freed_mb'] for e in history),
                'avg_memory_freed_mb': sum(e['memory_freed_mb'] for e in history) / len(history),
                'avg_effectiveness_percent': sum(e['effectiveness_percent'] for e in history) / len(history),
                'current_trim_interval': self.memory_baselines.get(pid, {}).get('trim_interval', 0)
            }
    
    def get_statistics(self):
        with self.lock:
            return self.stats.copy()
class LargePageManager:
    def __init__(self, handle_cache):
        self.handle_cache = handle_cache
        self.large_page_enabled_pids = set()
        self.lock = threading.RLock()
        self.large_page_privilege_enabled = False
        self.stats = {
            'total_large_page_enabled': 0,
            'total_failures': 0
        }
        self._enable_lock_memory_privilege()
    
    def _enable_lock_memory_privilege(self):
        try:
            h_token = wintypes.HANDLE()
            h_process = kernel32.GetCurrentProcess()
            
            if not advapi32.OpenProcessToken(h_process, TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY, ctypes.byref(h_token)):
                return False
            
            luid = LUID()
            if not advapi32.LookupPrivilegeValueW(None, SE_LOCK_MEMORY_NAME, ctypes.byref(luid)):
                kernel32.CloseHandle(h_token)
                return False
            
            tp = TOKEN_PRIVILEGES()
            tp.PrivilegeCount = 1
            tp.Privileges[0].Luid = luid
            tp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED
            
            advapi32.AdjustTokenPrivileges(h_token, False, ctypes.byref(tp), ctypes.sizeof(TOKEN_PRIVILEGES), None, None)
            kernel32.CloseHandle(h_token)
            
            self.large_page_privilege_enabled = True
            return True
        except Exception:
            return False
    
    def should_enable_large_pages(self, pid, is_foreground):
        if not self.large_page_privilege_enabled:
            return False
        
        if not is_foreground:
            return False
        
        try:
            process = psutil.Process(pid)
            memory_mb = process.memory_info().rss / (1024 * 1024)
            
            if memory_mb > 2048:
                return True
        except Exception:
            pass
        
        return False
    
    def enable_large_pages_for_process(self, pid):
        with self.lock:
            if pid in self.large_page_enabled_pids:
                return True
            
            try:
                process = psutil.Process(pid)
                memory_mb = process.memory_info().rss / (1024 * 1024)
                
                if memory_mb > 2048:
                    self.large_page_enabled_pids.add(pid)
                    self.stats['total_large_page_enabled'] += 1
                    return True
                else:
                    return False
            except Exception:
                self.stats['total_failures'] += 1
                return False
    
    def get_statistics(self):
        with self.lock:
            return self.stats.copy()
class AdvancedWorkingSetTrimmer:
    def __init__(self, handle_cache):
        self.handle_cache = handle_cache
        self.lock = threading.RLock()
        self.stats = {
            'private_page_trims': 0,
            'mapped_file_trims': 0,
            'total_memory_freed_mb': 0
        }
    
    def _trim_working_set(self, pid):
        try:
            handle = self.handle_cache.get_handle(
                pid,
                PROCESS_SET_INFORMATION | PROCESS_QUERY_INFORMATION | PROCESS_SET_QUOTA
            )
            
            if not handle:
                return False
            
            result = kernel32.SetProcessWorkingSetSize(
                handle,
                ctypes.c_size_t(-1),
                ctypes.c_size_t(-1)
            )
            
            return bool(result)
        except Exception:
            return False
    
    def trim_private_pages(self, pid):
        with self.lock:
            if self._trim_working_set(pid):
                self.stats['private_page_trims'] += 1
                return True
            return False
    
    def trim_mapped_files(self, pid):
        with self.lock:
            if self._trim_working_set(pid):
                self.stats['mapped_file_trims'] += 1
                return True
            return False
    
    def get_statistics(self):
        with self.lock:
            return self.stats.copy()
class MemoryPriorityManager:
    def __init__(self, handle_cache):
        self.handle_cache = handle_cache
        self.lock = threading.RLock()
        self.priority_map = {}
        self.stats = {
            'total_priority_changes': 0,
            'very_low_count': 0,
            'low_count': 0,
            'medium_count': 0,
            'below_normal_count': 0,
            'normal_count': 0
        }
    
    def set_memory_priority(self, pid, priority_level, is_foreground, minimized_time=0):
        with self.lock:
            try:
                if is_foreground:
                    target_priority = MEMORY_PRIORITY_NORMAL
                else:
                    if minimized_time > 1800:
                        target_priority = MEMORY_PRIORITY_VERY_LOW
                    else:
                        target_priority = MEMORY_PRIORITY_LOW
                
                handle = self.handle_cache.get_handle(
                    pid,
                    PROCESS_SET_INFORMATION | PROCESS_QUERY_INFORMATION
                )
                
                if not handle:
                    return False
                
                mem_priority = MEMORY_PRIORITY_INFORMATION()
                mem_priority.MemoryPriority = target_priority
                
                result = ntdll.NtSetInformationProcess(
                    handle,
                    ProcessMemoryPriority,
                    ctypes.byref(mem_priority),
                    ctypes.sizeof(mem_priority)
                )
                
                if result == 0:
                    self.priority_map[pid] = target_priority
                    self.stats['total_priority_changes'] += 1
                    
                    if target_priority == MEMORY_PRIORITY_VERY_LOW:
                        self.stats['very_low_count'] += 1
                    elif target_priority == MEMORY_PRIORITY_LOW:
                        self.stats['low_count'] += 1
                    elif target_priority == MEMORY_PRIORITY_MEDIUM:
                        self.stats['medium_count'] += 1
                    elif target_priority == MEMORY_PRIORITY_BELOW_NORMAL:
                        self.stats['below_normal_count'] += 1
                    elif target_priority == MEMORY_PRIORITY_NORMAL:
                        self.stats['normal_count'] += 1
                    
                    return True
                
                return False
            except Exception:
                return False
    
    def get_statistics(self):
        with self.lock:
            return self.stats.copy()
class AWEManager:
    def __init__(self, handle_cache):
        self.handle_cache = handle_cache
        self.lock = threading.RLock()
        self.awe_enabled_processes = set()
        self.stats = {
            'awe_enabled_count': 0,
            'total_32bit_processes': 0,
            'awe_failures': 0
        }
    
    def is_32bit_process(self, pid):
        try:
            process = psutil.Process(pid)
            
            if platform.machine().endswith('64'):
                try:
                    is_wow64 = ctypes.c_int()
                    kernel32.IsWow64Process(
                        kernel32.GetCurrentProcess(), 
                        ctypes.byref(is_wow64)
                    )
                    return bool(is_wow64.value)
                except Exception:
                    return False
            return True
        except Exception:
            return False
    
    def enable_awe_for_process(self, pid):
        with self.lock:
            if pid in self.awe_enabled_processes:
                return True
            
            try:
                if not self.is_32bit_process(pid):
                    return False
                
                self.stats['total_32bit_processes'] += 1
                
                handle = self.handle_cache.get_handle(
                    pid,
                    PROCESS_SET_INFORMATION | PROCESS_QUERY_INFORMATION | PROCESS_SET_QUOTA
                )
                
                if not handle:
                    self.stats['awe_failures'] += 1
                    return False
                
                try:
                    min_size = ctypes.c_size_t(0)
                    max_size = ctypes.c_size_t(0xFFFFFFFF)
                    
                    result = kernel32.SetProcessWorkingSetSizeEx(
                        handle,
                        min_size,
                        max_size,
                        AWE_ENABLED_FLAG
                    )
                    
                    if result:
                        self.awe_enabled_processes.add(pid)
                        self.stats['awe_enabled_count'] += 1
                        return True
                    else:
                        self.stats['awe_failures'] += 1
                        return False
                except Exception:
                    self.stats['awe_failures'] += 1
                    return False
            except Exception:
                self.stats['awe_failures'] += 1
                return False
    
    def get_statistics(self):
        with self.lock:
            return self.stats.copy()
class NUMAAwareMemoryAllocator:
    def __init__(self):
        self.lock = threading.RLock()
        self.numa_nodes = self._detect_numa_nodes()
        self.stats = {'allocations': 0, 'optimizations': 0}
    
    def _detect_numa_nodes(self):
        nodes = {}
        try:
            for cpu in range(psutil.cpu_count(logical=True)):
                node_number = ctypes.c_ubyte()
                if kernel32.GetNumaProcessorNode(cpu, ctypes.byref(node_number)):
                    node = node_number.value
                    if node not in nodes:
                        nodes[node] = []
                    nodes[node].append(cpu)
        except Exception:
            pass
        return nodes
    
    def optimize_process_numa(self, pid, preferred_cores):
        with self.lock:
            if len(self.numa_nodes) <= 1:
                return False
            
            try:
                if not preferred_cores:
                    return False
                
                first_core = preferred_cores[0]
                target_node = None
                
                for node, cores in self.numa_nodes.items():
                    if first_core in cores:
                        target_node = node
                        break
                
                if target_node is not None:
                    proc = psutil.Process(pid)
                    node_cores = self.numa_nodes[target_node]
                    proc.cpu_affinity(node_cores)
                    self.stats['optimizations'] += 1
                    return True
            except Exception:
                pass
            return False
class DynamicHugePagesManager:
    ACCESS_THRESHOLD = 1000000
    MEMORY_THRESHOLD_GB = 2
    MEMORY_ACCESS_DETECTION_THRESHOLD = 1024 * 1024
    
    def __init__(self, handle_cache):
        self.handle_cache = handle_cache
        self.lock = threading.RLock()
        self.monitored_processes = {}
        self.stats = {'huge_pages_enabled': 0, 'processes_monitored': 0}
    
    def monitor_process(self, pid):
        with self.lock:
            try:
                proc = psutil.Process(pid)
                mem_info = proc.memory_info()
                
                if pid not in self.monitored_processes:
                    self.monitored_processes[pid] = {
                        'start_rss': mem_info.rss,
                        'last_rss': mem_info.rss,
                        'access_count': 0,
                        'huge_pages_enabled': False
                    }
                    self.stats['processes_monitored'] += 1
                else:
                    data = self.monitored_processes[pid]
                    rss_delta = abs(mem_info.rss - data['last_rss'])
                    
                    if rss_delta > self.MEMORY_ACCESS_DETECTION_THRESHOLD:
                        data['access_count'] += 1
                    
                    data['last_rss'] = mem_info.rss
                    
                    memory_threshold_bytes = self.MEMORY_THRESHOLD_GB * 1024 * 1024 * 1024
                    if data['access_count'] > self.ACCESS_THRESHOLD and not data['huge_pages_enabled']:
                        if mem_info.rss > memory_threshold_bytes:
                            self._enable_huge_pages(pid)
                            data['huge_pages_enabled'] = True
                            self.stats['huge_pages_enabled'] += 1
            except Exception:
                pass
    
    def _enable_huge_pages(self, pid):
        with self.lock:
            try:
                handle = self.handle_cache.get_handle(pid, PROCESS_SET_QUOTA)
                if handle:
                    min_ws = 2 * 1024 * 1024 * 1024
                    max_ws = 4 * 1024 * 1024 * 1024
                    flags = QUOTA_LIMITS_HARDWS_MIN_ENABLE | QUOTA_LIMITS_HARDWS_MAX_ENABLE
                    kernel32.SetProcessWorkingSetSizeEx(handle, min_ws, max_ws, flags)
                    return True
            except Exception:
                pass
            return False
class MemoryDeduplicationManager:
    def __init__(self):
        self.lock = threading.RLock()
        self.stats = {'dedup_attempts': 0, 'pages_deduplicated': 0}
    
    def enable_memory_compression(self, pid):
        with self.lock:
            try:
                subprocess.run(
                    ['powershell', '-Command', 
                     'Enable-MMAgent -MemoryCompression'],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    timeout=5
                )
                self.stats['dedup_attempts'] += 1
                return True
            except Exception:
                return False
class AdvancedMemoryPagePriorityManager:
    
    def __init__(self, handle_cache):
        self.lock = threading.RLock()
        self.handle_cache = handle_cache
        self.process_working_sets = {}
        self.page_access_patterns = defaultdict(lambda: {
            'sequential_accesses': 0,
            'random_accesses': 0,
            'hot_pages': set(),
            'cold_pages': set()
        })
        self.last_analysis_time = {}
        self.stats = {
            'promotions': 0,
            'demotions': 0,
            'prefetch_hints': 0,
            'page_fault_reductions': 0,
            'working_set_optimizations': 0
        }
    
    def analyze_working_set(self, pid):
        with self.lock:
            try:
                proc = psutil.Process(pid)
                mem_info = proc.memory_info()
                
                
                working_set_mb = mem_info.wset / (1024 * 1024)
                
                
                if pid not in self.process_working_sets:
                    self.process_working_sets[pid] = {
                        'current_ws': working_set_mb,
                        'peak_ws': working_set_mb,
                        'min_ws': working_set_mb,
                        'history': deque(maxlen=20),
                        'last_update': time.time()
                    }
                else:
                    ws_data = self.process_working_sets[pid]
                    ws_data['history'].append(working_set_mb)
                    ws_data['current_ws'] = working_set_mb
                    ws_data['peak_ws'] = max(ws_data['peak_ws'], working_set_mb)
                    ws_data['min_ws'] = min(ws_data['min_ws'], working_set_mb)
                    ws_data['last_update'] = time.time()
                
                return True
            except Exception as e:
                logger.debug(f"Working set analysis error for pid {pid}: {e}")
                return False
    
    def optimize_page_priority(self, pid, is_foreground=False):
        with self.lock:
            try:
                
                current_time = time.time()
                if pid in self.last_analysis_time:
                    if current_time - self.last_analysis_time[pid] < 10:
                        return False
                
                self.last_analysis_time[pid] = current_time
                
                
                if is_foreground:
                    page_priority = PAGE_PRIORITY_NORMAL  
                else:
                    
                    if pid in self.process_working_sets:
                        ws_data = self.process_working_sets[pid]
                        history = list(ws_data['history'])
                        
                        if len(history) >= 5:
                            
                            variance = sum((x - ws_data['current_ws'])**2 for x in history[-5:]) / 5
                            if variance < 10:  
                                page_priority = PAGE_PRIORITY_NORMAL
                            else:
                                page_priority = PAGE_PRIORITY_MEDIUM
                        else:
                            page_priority = PAGE_PRIORITY_MEDIUM
                    else:
                        page_priority = PAGE_PRIORITY_LOW
                
                
                handle = self.handle_cache.get_handle(pid, PROCESS_SET_INFORMATION)
                if handle:
                    page_priority_info = MEMORY_PRIORITY_INFORMATION()
                    page_priority_info.MemoryPriority = page_priority
                    
                    result = ntdll.NtSetInformationProcess(
                        int(handle),
                        ProcessMemoryPriority,
                        ctypes.byref(page_priority_info),
                        ctypes.sizeof(page_priority_info)
                    )
                    
                    if result == 0:
                        if page_priority == PAGE_PRIORITY_NORMAL:
                            self.stats['promotions'] += 1
                        else:
                            self.stats['demotions'] += 1
                        return True
            except Exception as e:
                logger.debug(f"Page priority optimization error for pid {pid}: {e}")
            return False
    
    def detect_sequential_access_pattern(self, pid):
        with self.lock:
            try:
                if pid not in self.process_working_sets:
                    return False
                
                ws_data = self.process_working_sets[pid]
                history = list(ws_data['history'])
                
                if len(history) < 5:
                    return False
                
                
                sequential = True
                for i in range(1, min(5, len(history))):
                    if history[-i] < history[-(i+1)]:
                        sequential = False
                        break
                
                if sequential:
                    patterns = self.page_access_patterns[pid]
                    patterns['sequential_accesses'] += 1
                    
                    
                    if patterns['sequential_accesses'] > 3:
                        self.stats['prefetch_hints'] += 1
                        return True
                else:
                    patterns = self.page_access_patterns[pid]
                    patterns['random_accesses'] += 1
                
                return False
            except Exception as e:
                logger.debug(f"Sequential pattern detection error for pid {pid}: {e}")
                return False
    
    def optimize_working_set_size(self, pid, target_mb=None):
        with self.lock:
            try:
                if pid not in self.process_working_sets:
                    return False
                
                ws_data = self.process_working_sets[pid]
                
                
                if target_mb is None:
                    
                    history = list(ws_data['history'])
                    if history:
                        avg_ws = sum(history) / len(history)
                        min_ws_mb = avg_ws * 0.8
                        max_ws_mb = avg_ws * 1.5
                    else:
                        min_ws_mb = ws_data['current_ws'] * 0.8
                        max_ws_mb = ws_data['current_ws'] * 1.5
                else:
                    min_ws_mb = target_mb * 0.8
                    max_ws_mb = target_mb * 1.5
                
                
                min_ws_bytes = int(min_ws_mb * 1024 * 1024)
                max_ws_bytes = int(max_ws_mb * 1024 * 1024)
                
                
                handle = self.handle_cache.get_handle(pid, PROCESS_SET_QUOTA)
                if handle:
                    result = kernel32.SetProcessWorkingSetSize(
                        int(handle),
                        ctypes.c_size_t(min_ws_bytes),
                        ctypes.c_size_t(max_ws_bytes)
                    )
                    if result:
                        self.stats['working_set_optimizations'] += 1
                        logger.debug(f"Working set optimized for pid {pid}: {min_ws_mb:.1f}MB - {max_ws_mb:.1f}MB")
                        return True
            except Exception as e:
                logger.debug(f"Working set optimization error for pid {pid}: {e}")
            return False
    
    def get_stats(self):
        with self.lock:
            return self.stats.copy()
