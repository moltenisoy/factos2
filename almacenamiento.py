import os
import time
import psutil
import win32file
import winreg
import subprocess
import threading
import ctypes
from collections import defaultdict, deque
import logging

logger = logging.getLogger(__name__)

NVME_OPTIMAL_QUEUE_DEPTH = 256
NVME_MAX_QUEUE_DEPTH = 1024
FILE_FLAG_SEQUENTIAL_SCAN = 0x08000000
IOCTL_STORAGE_QUERY_PROPERTY = 0x002D1400
PROCESS_SET_INFORMATION = 0x0200
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_SET_QUOTA = 0x0100
PROCESS_POWER_THROTTLING_EXECUTION_SPEED = 0x1
ProcessPowerThrottling = 77
ntdll = ctypes.WinDLL('ntdll')
kernel32 = ctypes.WinDLL('kernel32')

class PROCESS_POWER_THROTTLING_STATE(ctypes.Structure):
    _fields_ = [('Version', ctypes.wintypes.ULONG), ('ControlMask', ctypes.wintypes.ULONG), ('StateMask', ctypes.wintypes.ULONG)]

class StorageOptimizer:
    def __init__(self):
        self.lock = threading.RLock()
    
    def optimize_nvme_queue_depth(self):
        with self.lock:
            try:
                key_path = r"SYSTEM\CurrentControlSet\Services\stornvme\Parameters\Device"
                try:
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_SET_VALUE)
                    winreg.SetValueEx(key, "QueueDepth", 0, winreg.REG_DWORD, NVME_OPTIMAL_QUEUE_DEPTH)
                    winreg.CloseKey(key)
                    return True
                except Exception as e:
                    logger.error(f"Failed to optimize NVMe queue depth: {e}")
                    return False
            except Exception as e:
                logger.error(f"An unexpected error occurred in optimize_nvme_queue_depth: {e}")
                return False
    
    def optimize_file_system_cache(self):
        with self.lock:
            try:
                total_ram_gb = psutil.virtual_memory().total / (1024 ** 3)
                
                if total_ram_gb >= 16:
                    large_system_cache = 1
                else:
                    large_system_cache = 0
                
                key_path = r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management"
                try:
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_SET_VALUE)
                    winreg.SetValueEx(key, "LargeSystemCache", 0, winreg.REG_DWORD, large_system_cache)
                    winreg.CloseKey(key)
                    return True
                except Exception as e:
                    logger.error(f"Failed to optimize file system cache: {e}")
                    return False
            except Exception as e:
                logger.error(f"An unexpected error occurred in optimize_file_system_cache: {e}")
                return False
    
    def schedule_trim_during_idle(self):
        with self.lock:
            try:
                subprocess.run(
                    ['defrag', '/L'],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    timeout=10
                )
                return True
            except Exception as e:
                logger.error(f"Failed to schedule TRIM: {e}")
                return False
class AdaptiveReadAheadManager:
    SMALL_READAHEAD = 32 * 1024
    MEDIUM_READAHEAD = 64 * 1024
    NORMAL_READAHEAD = 128 * 1024
    LARGE_READAHEAD = 256 * 1024
    SEQUENTIAL_THRESHOLD = 0.8
    MEDIUM_THRESHOLD = 0.5
    
    def __init__(self):
        self.lock = threading.RLock()
        self.file_access_patterns = {}
    
    def analyze_access_pattern(self, file_path, offset):
        with self.lock:
            try:
                if file_path not in self.file_access_patterns:
                    self.file_access_patterns[file_path] = {
                        'sequential_count': 0,
                        'random_count': 0,
                        'last_offset': 0,
                        'offsets': deque(maxlen=10)
                    }
                
                pattern = self.file_access_patterns[file_path]
                pattern['offsets'].append(offset)
                
                if len(pattern['offsets']) >= 2:
                    deltas = [pattern['offsets'][i+1] - pattern['offsets'][i] 
                             for i in range(len(pattern['offsets'])-1)]
                    
                    if all(d > 0 for d in deltas):
                        pattern['sequential_count'] += 1
                        is_sequential = True
                    else:
                        pattern['random_count'] += 1
                        is_sequential = False
                    
                    pattern['last_offset'] = offset
                    return is_sequential
                
                return None
            except Exception as e:
                logger.error(f"Error analyzing access pattern for {file_path}: {e}")
                return None
    
    def get_recommended_readahead_size(self, file_path):
        with self.lock:
            if file_path not in self.file_access_patterns:
                return self.MEDIUM_READAHEAD
            
            pattern = self.file_access_patterns[file_path]
            total = pattern['sequential_count'] + pattern['random_count']
            
            if total == 0:
                return self.MEDIUM_READAHEAD
            
            sequential_ratio = pattern['sequential_count'] / total
            
            if sequential_ratio > self.SEQUENTIAL_THRESHOLD:
                return self.LARGE_READAHEAD
            elif sequential_ratio > self.MEDIUM_THRESHOLD:
                return self.NORMAL_READAHEAD
            else:
                return self.SMALL_READAHEAD
class WriteCoalescingManager:
    def __init__(self):
        self.lock = threading.RLock()
        self.write_buffers = {}
        self.buffer_size_limit = 1024 * 1024
    
    def buffer_write(self, file_id, data, is_critical=False):
        with self.lock:
            try:
                if is_critical:
                    return False
                
                if file_id not in self.write_buffers:
                    self.write_buffers[file_id] = []
                
                self.write_buffers[file_id].append(data)
                total_size = sum(len(d) for d in self.write_buffers[file_id])
                
                if total_size >= self.buffer_size_limit:
                    self.write_buffers[file_id] = []
                    return True
                
                return False
            except Exception as e:
                logger.error(f"Error buffering write for {file_id}: {e}")
                return False
class StorageTierManager:
    def __init__(self):
        self.lock = threading.RLock()
        self.storage_tiers = self._detect_storage_tiers()
        self.file_access_counts = {}
    
    def _detect_storage_tiers(self):
        tiers = []
        try:
            partitions = psutil.disk_partitions()
            for partition in partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    
                    is_nvme = 'nvme' in partition.device.lower()
                    
                    is_removable = 'removable' in partition.opts.lower() if hasattr(partition, 'opts') else False
                    
                    tier_info = {
                        'mountpoint': partition.mountpoint,
                        'total': usage.total,
                        'fstype': partition.fstype,
                        'is_nvme': is_nvme,
                        'is_removable': is_removable
                    }
                    tiers.append(tier_info)
                except Exception as e:
                    logger.warning(f"Could not get info for partition {partition.mountpoint}: {e}")
        except Exception as e:
            logger.error(f"Failed to detect storage tiers: {e}")
        
        tiers.sort(key=lambda x: (x['is_nvme'], not x['is_removable']), reverse=True)
        return tiers
    
    def track_file_access(self, file_path):
        with self.lock:
            if file_path not in self.file_access_counts:
                self.file_access_counts[file_path] = 0
            self.file_access_counts[file_path] += 1
class DynamicDiskCacheTuner:
    LARGE_CACHE = 1
    NORMAL_CACHE = 0
    LARGE_CACHE_RAM_THRESHOLD_GB = 8
    NORMAL_CACHE_RAM_THRESHOLD_GB = 4
    BYTES_PER_GB = 1024 ** 3
    
    def __init__(self):
        self.lock = threading.RLock()
    
    def tune_cache(self):
        with self.lock:
            try:
                memory = psutil.virtual_memory()
                available_gb = memory.available / self.BYTES_PER_GB
                
                if available_gb > self.LARGE_CACHE_RAM_THRESHOLD_GB:
                    cache_size = self.LARGE_CACHE
                elif available_gb > self.NORMAL_CACHE_RAM_THRESHOLD_GB:
                    cache_size = self.NORMAL_CACHE
                else:
                    cache_size = self.NORMAL_CACHE
                
                key_path = r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management"
                try:
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_SET_VALUE)
                    winreg.SetValueEx(key, "LargeSystemCache", 0, winreg.REG_DWORD, cache_size)
                    winreg.CloseKey(key)
                    return True
                except Exception as e:
                    logger.error(f"Failed to tune disk cache: {e}")
                    return False
            except Exception as e:
                logger.error(f"An unexpected error occurred in tune_cache: {e}")
                return False
class IntelligentTRIMScheduler:
    def __init__(self):
        self.lock = threading.RLock()
        self.last_trim = 0
        self.trim_interval = 3600
        self.gaming_mode = False
        self.system_idle = False
        
    def should_execute_trim(self):
        with self.lock:
            if self.gaming_mode:
                return False
            current_time = time.time()
            if current_time - self.last_trim < self.trim_interval:
                return False
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent < 10:
                self.system_idle = True
                return True
            return False
    
    def execute_trim(self):
        if self.should_execute_trim():
            try:
                subprocess.run(['defrag', '/L', 'C:'], capture_output=True, timeout=300)
                self.last_trim = time.time()
            except Exception as e:
                logger.error(f"Failed to execute TRIM: {e}")
    
    def set_gaming_mode(self, enabled):
        with self.lock:
            self.gaming_mode = enabled
class AggressiveWriteCache:
    def __init__(self):
        self.lock = threading.RLock()
        self.write_buffer_size = 512 * 1024 * 1024
        
    def optimize_write_cache_for_gaming(self):
        try:
            key_path = r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management"
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "LargeSystemCache", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "IoPageLockLimit", 0, winreg.REG_DWORD, self.write_buffer_size)
            winreg.CloseKey(key)
        except Exception as e:
            logger.error(f"Failed to optimize write cache for gaming: {e}")
class CustomIOScheduler:
    def __init__(self):
        self.lock = threading.RLock()
        self.read_priority = 2
        self.write_priority = 1
        
    def prioritize_reads_for_gaming(self):
        try:
            key_path = r"SYSTEM\CurrentControlSet\Services\Disk"
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "TimeOutValue", 0, winreg.REG_DWORD, 10)
            winreg.CloseKey(key)
        except Exception as e:
            logger.error(f"Failed to prioritize reads for gaming: {e}")
class NCQOptimizer:
    def __init__(self):
        self.lock = threading.RLock()
        self.queue_depth_gaming = 32
        self.queue_depth_transfer = 256
        self.current_mode = 'normal'
        
    def set_queue_depth_for_gaming(self, gaming_mode):
        with self.lock:
            depth = self.queue_depth_gaming if gaming_mode else self.queue_depth_transfer
            self.current_mode = 'gaming' if gaming_mode else 'transfer'
            try:
                key_path = r"SYSTEM\CurrentControlSet\Services\storahci\Parameters\Device"
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(key, "QueueDepth", 0, winreg.REG_DWORD, depth)
                winreg.CloseKey(key)
            except Exception as e:
                logger.error(f"Failed to set NCQ queue depth: {e}")
class AdvancedFileSystemCache:
    def __init__(self):
        self.lock = threading.RLock()
        
    def optimize_cache_for_gaming(self):
        try:
            key_path = r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management"
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "DisablePagingExecutive", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "LargeSystemCache", 0, winreg.REG_DWORD, 0)
            winreg.CloseKey(key)
        except Exception as e:
            logger.error(f"Failed to optimize advanced file system cache for gaming: {e}")
class IOPriorityInheritance:
    def __init__(self, handle_cache):
        self.lock = threading.RLock()
        self.handle_cache = handle_cache
        self.io_priorities = {}
        
    def inherit_io_priority(self, pid, priority):
        with self.lock:
            try:
                handle = self.handle_cache.get_handle(pid, PROCESS_SET_INFORMATION)
                if handle:
                    self.io_priorities[pid] = priority
                    return True
            except Exception as e:
                logger.error(f"Failed to inherit I/O priority for pid {pid}: {e}")
            return False
    
    def throttle_background_io(self, pid):
        with self.lock:
            try:
                handle = self.handle_cache.get_handle(pid, PROCESS_SET_INFORMATION)
                if handle:
                    throttle = PROCESS_POWER_THROTTLING_STATE()
                    throttle.Version = 1
                    throttle.ControlMask = PROCESS_POWER_THROTTLING_EXECUTION_SPEED
                    throttle.StateMask = PROCESS_POWER_THROTTLING_EXECUTION_SPEED
                    ntdll.NtSetInformationProcess(handle, ProcessPowerThrottling, ctypes.byref(throttle), ctypes.sizeof(throttle))
                    return True
            except Exception as e:
                logger.error(f"Failed to throttle background I/O for pid {pid}: {e}")
            return False
class AdaptiveIOScheduler:
    
    def __init__(self, handle_cache):
        self.lock = threading.RLock()
        self.handle_cache = handle_cache
        self.process_io_patterns = defaultdict(lambda: {
            'sequential_reads': 0,
            'random_reads': 0,
            'sequential_writes': 0,
            'random_writes': 0,
            'total_operations': 0,
            'last_pattern': None,
            'last_update': time.time()
        })
        self.nvme_queue_depth = 256  
        self.io_priorities = {}
        self.last_adjustment = time.time()
    
    def detect_io_pattern(self, pid):
        with self.lock:
            try:
                proc = psutil.Process(pid)
                io_counters = proc.io_counters()
                
                pattern_data = self.process_io_patterns[pid]
                current_time = time.time()
                
                
                if pattern_data['total_operations'] > 0:
                    time_delta = current_time - pattern_data['last_update']
                    
                    if time_delta > 0:
                        
                        read_rate = io_counters.read_count / max(time_delta, 1)
                        write_rate = io_counters.write_count / max(time_delta, 1)
                        
                        
                        if read_rate > write_rate * 2:
                            if read_rate > 1000:  
                                pattern = 'sequential_read'
                                pattern_data['sequential_reads'] += 1
                            else:
                                pattern = 'random_read'
                                pattern_data['random_reads'] += 1
                        elif write_rate > read_rate * 2:
                            if write_rate > 1000:
                                pattern = 'sequential_write'
                                pattern_data['sequential_writes'] += 1
                            else:
                                pattern = 'random_write'
                                pattern_data['random_writes'] += 1
                        else:
                            pattern = pattern_data['last_pattern']  
                        
                        pattern_data['last_pattern'] = pattern
                        pattern_data['total_operations'] += 1
                        pattern_data['last_update'] = current_time
                        
                        return pattern
                else:
                    
                    pattern_data['total_operations'] = 1
                    pattern_data['last_update'] = current_time
                    
            except Exception as e:
                logger.debug(f"I/O pattern detection error for pid {pid}: {e}")
            return None
    
    def adjust_nvme_queue_depth(self, system_load):
        with self.lock:
            try:
                current_time = time.time()
                
                
                if current_time - self.last_adjustment < 30:
                    return False
                
                self.last_adjustment = current_time
                
                
                total_io_ops = sum(
                    data['total_operations'] 
                    for data in self.process_io_patterns.values()
                )
                
                
                if system_load < 0.3:  
                    new_queue_depth = 32
                elif system_load < 0.6:  
                    new_queue_depth = 128
                elif system_load < 0.8:  
                    new_queue_depth = 512
                else:  
                    new_queue_depth = 1024
                
                
                if total_io_ops > 10000:
                    new_queue_depth = min(new_queue_depth * 2, NVME_MAX_QUEUE_DEPTH)
                
                if new_queue_depth != self.nvme_queue_depth:
                    self.nvme_queue_depth = new_queue_depth
                    logger.info(f"NVMe queue depth adjusted to {new_queue_depth}")
                    
                    
                    try:
                        key_path = r"SYSTEM\CurrentControlSet\Services\stornvme\Parameters\Device"
                        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_SET_VALUE)
                        winreg.SetValueEx(key, "QueueDepth", 0, winreg.REG_DWORD, new_queue_depth)
                        winreg.CloseKey(key)
                    except Exception as e:
                        logger.error(f"Failed to set NVMe queue depth in registry: {e}")
                    
                    return True
            except Exception as e:
                logger.debug(f"NVMe queue depth adjustment error: {e}")
            return False
    
    def prioritize_io(self, pid, is_interactive=False, is_foreground=False):
        with self.lock:
            try:
                
                if is_foreground:
                    io_priority = 2  
                elif is_interactive:
                    io_priority = 1  
                else:
                    io_priority = 0  
                
                
                handle = self.handle_cache.get_handle(pid, PROCESS_SET_INFORMATION)
                if handle:
                    
                    try:
                        proc = psutil.Process(pid)
                        for thread in proc.threads():
                            thread_handle = kernel32.OpenThread(
                                THREAD_SET_INFORMATION,
                                False,
                                thread.id
                            )
                            if thread_handle:
                                
                                ntdll.NtSetInformationThread(
                                    thread_handle,
                                    43,
                                    ctypes.byref(ctypes.c_ulong(io_priority)),
                                    ctypes.sizeof(ctypes.c_ulong)
                                )
                                kernel32.CloseHandle(thread_handle)
                        
                        self.io_priorities[pid] = io_priority
                        logger.debug(f"I/O priority for pid {pid} set to {io_priority}")
                        return True
                    except Exception as e:
                        logger.debug(f"Failed to set I/O priority for threads of pid {pid}: {e}")
            except Exception as e:
                logger.debug(f"I/O prioritization error for pid {pid}: {e}")
            return False
    
    def optimize_for_pattern(self, pid, pattern):
        with self.lock:
            try:
                if not pattern:
                    return False
                
                
                if 'sequential' in pattern:
                    
                    
                    
                    pattern_data = self.process_io_patterns[pid]
                    pattern_data['optimization_hint'] = 'sequential'
                    return True
                else:
                    
                    pattern_data = self.process_io_patterns[pid]
                    pattern_data['optimization_hint'] = 'random'
                    return True
            except Exception as e:
                logger.debug(f"Pattern optimization error for pid {pid}: {e}")
            return False
    
    def get_stats(self):
        with self.lock:
            pass
class MetadataOptimizer:
    def __init__(self):
        self.lock = threading.RLock()
        self.dir_cache = {}
        
    def optimize_metadata_operations(self):
        try:
            key_path = r"SYSTEM\CurrentControlSet\Control\FileSystem"
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "NtfsDisableLastAccessUpdate", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "NtfsDisable8dot3NameCreation", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key)
        except Exception as e:
            logger.error(f"Failed to optimize metadata operations: {e}")
