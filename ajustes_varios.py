import time
import psutil
import win32api
import win32con
import win32process
import winreg
import subprocess
import threading
import math
import weakref
from collections import defaultdict, deque
import ctypes
import logging
import platform

logger = logging.getLogger(__name__)

MAX_CACHE_SIZE = 10000
CACHE_CLEANUP_SIZE = 5000
WMIC_COMMAND_PATH = 'wmic'
PROCESS_QUERY_INFORMATION = 0x0400
WAIT_OBJECT_0 = 0x0
TH32CS_SNAPPROCESS = 0x00000002
MAX_PROCESS_SNAPSHOT_ITERATIONS = 10000

ntdll = ctypes.WinDLL('ntdll')
kernel32 = ctypes.WinDLL('kernel32')
SystemResponsivenessKey = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile"

class PROCESSENTRY32(ctypes.Structure):
    _fields_ = [('dwSize', ctypes.wintypes.DWORD), ('cntUsage', ctypes.wintypes.DWORD), ('th32ProcessID', ctypes.wintypes.DWORD), ('th32DefaultHeapID', ctypes.POINTER(ctypes.wintypes.ULONG)), ('th32ModuleID', ctypes.wintypes.DWORD), ('cntThreads', ctypes.wintypes.DWORD), ('th32ParentProcessID', ctypes.wintypes.DWORD), ('pcPriClassBase', ctypes.wintypes.LONG), ('dwFlags', ctypes.wintypes.DWORD), ('szExeFile', ctypes.c_char * 260)]
class THREADENTRY32(ctypes.Structure):
    _fields_ = [('dwSize', ctypes.wintypes.DWORD), ('cntUsage', ctypes.wintypes.DWORD), ('th32ThreadID', ctypes.wintypes.DWORD), ('th32OwnerProcessID', ctypes.wintypes.DWORD), ('tpBasePri', ctypes.wintypes.LONG), ('tpDeltaPri', ctypes.wintypes.LONG), ('dwFlags', ctypes.wintypes.DWORD)]
class PROCESS_POWER_THROTTLING_STATE(ctypes.Structure):
    _fields_ = [('Version', ctypes.wintypes.ULONG), ('ControlMask', ctypes.wintypes.ULONG), ('StateMask', ctypes.wintypes.ULONG)]

def binary_search_pid(sorted_pid_list, target_pid):
    left, right = 0, len(sorted_pid_list) - 1
    
    while left <= right:
        mid = (left + right) // 2
        if sorted_pid_list[mid] == target_pid:
            return mid
        elif sorted_pid_list[mid] < target_pid:
            left = mid + 1
        else:
            right = mid - 1
    
    return -1

def memoize_with_ttl(ttl_seconds=300):
    def decorator(func):
        cache = {}
        cache_times = {}
        lock = threading.RLock()
        
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            current_time = time.time()
            
            with lock:
                if key in cache:
                    if current_time - cache_times[key] < ttl_seconds:
                        return cache[key]
                    else:
                        del cache[key]
                        del cache_times[key]
                
                result = func(*args, **kwargs)
                cache[key] = result
                cache_times[key] = current_time
                
                if len(cache) > 1000:
                    sorted_items = sorted(cache_times.items(), key=lambda x: x[1])
                    for old_key, _ in sorted_items[:500]:
                        del cache[old_key]
                        del cache_times[old_key]
                
                return result
        
        return wrapper
    return decorator

class CircularBuffer:
    __slots__ = ('_buffer', '_size', '_head', '_count')
    
    def __init__(self, maxlen):
        self._buffer = [None] * maxlen
        self._size = maxlen
        self._head = 0
        self._count = 0
    
    def append(self, item):
        self._buffer[self._head] = item
        self._head = (self._head + 1) % self._size
        if self._count < self._size:
            self._count += 1
    
    def __len__(self):
        return self._count
    
    def __iter__(self):
        if self._count < self._size:
            for i in range(self._count):
                yield self._buffer[i]
        else:
            for i in range(self._size):
                idx = (self._head + i) % self._size
                yield self._buffer[idx]
    
    def clear(self):
        self._head = 0
        self._count = 0
        self._buffer = [None] * self._size
class CTypesStructurePool:
    __slots__ = ('_pools', 'lock', 'max_pool_size')
    
    def __init__(self, max_pool_size=10):
        self._pools = {}
        self.lock = threading.RLock()
        self.max_pool_size = max_pool_size
    
    def get_structure(self, structure_type):
        with self.lock:
            type_name = structure_type.__name__
            if type_name not in self._pools:
                self._pools[type_name] = []
            
            pool = self._pools[type_name]
            if pool:
                return pool.pop()
            else:
                return structure_type()
    
    def return_structure(self, structure):
        with self.lock:
            type_name = type(structure).__name__
            if type_name not in self._pools:
                self._pools[type_name] = []
            
            pool = self._pools[type_name]
            if len(pool) < self.max_pool_size:
                pool.append(type(structure)())
class SimpleBloomFilter:
    __slots__ = ('_bit_array', '_size', '_hash_count')
    
    def __init__(self, expected_elements=100, false_positive_rate=0.01):
        self._size = int(-(expected_elements * math.log(false_positive_rate)) / (math.log(2) ** 2))
        self._hash_count = int((self._size / expected_elements) * math.log(2))
        self._bit_array = [False] * self._size
    
    def _hashes(self, item):
        h1 = hash(item)
        h2 = (h1 >> 16) ^ (h1 << 16)
        for i in range(self._hash_count):
            yield (h1 + i * h2) % self._size
    
    def add(self, item):
        for h in self._hashes(item):
            self._bit_array[h] = True
    
    def contains(self, item):
        return all(self._bit_array[h] for h in self._hashes(item))
class RegistryWriteBuffer:
    __slots__ = ('buffer', 'lock', 'flush_interval', 'last_flush', 'max_buffer_size')
    
    def __init__(self, flush_interval=5.0, max_buffer_size=50):
        self.buffer = []
        self.lock = threading.RLock()
        self.flush_interval = flush_interval
        self.last_flush = time.time()
        self.max_buffer_size = max_buffer_size
    
    def queue_write(self, key_path, value_name, value_type, value_data):
        with self.lock:
            if not key_path or not isinstance(key_path, str):
                return
            if not isinstance(value_name, str):
                return
            
            self.buffer.append((key_path, value_name, value_type, value_data))
            
            if len(self.buffer) >= self.max_buffer_size:
                self.flush()
            elif time.time() - self.last_flush >= self.flush_interval:
                self.flush()
    
    def flush(self):
        with self.lock:
            if not self.buffer:
                return
            
            for key_path, value_name, value_type, value_data in self.buffer:
                key = None
                try:
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, 
                                        winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY)
                    winreg.SetValueEx(key, value_name, 0, value_type, value_data)
                except (OSError, PermissionError, WindowsError):
                    pass
                finally:
                    if key:
                        try:
                            winreg.CloseKey(key)
                        except Exception:
                            pass
            
            self.buffer.clear()
            self.last_flush = time.time()

class HardwareDetector:
    def __init__(self):
        self.cpu_vendor = None
        self.cpu_model = None
        self.gpu_vendor = None
        self.storage_types = set()
        self._detect_hardware()
    
    def _detect_hardware(self):
        self._detect_cpu()
        self._detect_gpu()
        self._detect_storage()
    
    def _detect_cpu(self):
        try:
            import subprocess
            import shutil
            
            wmic_cmd = shutil.which(WMIC_COMMAND_PATH)
            if not wmic_cmd:
                wmic_cmd = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32', 'wmic.exe')
                if not os.path.exists(wmic_cmd):
                    return
            
            result = subprocess.run(
                [wmic_cmd, 'cpu', 'get', 'manufacturer,name', '/format:list'],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == 'Windows' else 0
            )
            if result.returncode == 0:
                cpu_info = result.stdout
                if 'Intel' in cpu_info:
                    self.cpu_vendor = 'Intel'
                elif 'AMD' in cpu_info or 'Advanced Micro Devices' in cpu_info:
                    self.cpu_vendor = 'AMD'
                for line in cpu_info.split('\n'):
                    if line.startswith('Name='):
                        self.cpu_model = line.split('=', 1)[1].strip()
                        break
            else:
                pass
        except subprocess.TimeoutExpired:
            pass
        except FileNotFoundError:
            pass
        except Exception:
            pass
    
    def _detect_gpu(self):
        try:
            import subprocess
            import shutil
            
            wmic_cmd = shutil.which(WMIC_COMMAND_PATH)
            if not wmic_cmd:
                wmic_cmd = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32', 'wmic.exe')
                if not os.path.exists(wmic_cmd):
                    return
            
            result = subprocess.run(
                [wmic_cmd, 'path', 'win32_VideoController', 'get', 'name', '/format:list'],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == 'Windows' else 0
            )
            if result.returncode == 0:
                gpu_info = result.stdout
                if 'NVIDIA' in gpu_info or 'GeForce' in gpu_info or 'Quadro' in gpu_info:
                    self.gpu_vendor = 'NVIDIA'
                elif 'AMD' in gpu_info or 'Radeon' in gpu_info:
                    self.gpu_vendor = 'AMD'
                elif 'Intel' in gpu_info:
                    self.gpu_vendor = 'Intel'
            else:
                pass
        except subprocess.TimeoutExpired:
            pass
        except FileNotFoundError:
            pass
        except Exception:
            pass
    
    def _detect_storage(self):
        try:
            import subprocess
            import shutil
            
            wmic_cmd = shutil.which(WMIC_COMMAND_PATH)
            if not wmic_cmd:
                wmic_cmd = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32', 'wmic.exe')
                if not os.path.exists(wmic_cmd):
                    return
            
            result = subprocess.run(
                [wmic_cmd, 'diskdrive', 'get', 'MediaType,Model,InterfaceType', '/format:list'],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == 'Windows' else 0
            )
            if result.returncode == 0:
                disk_info = result.stdout
                if 'SSD' in disk_info or 'Solid State' in disk_info:
                    self.storage_types.add('SSD')
                if 'HDD' in disk_info or 'Fixed hard disk' in disk_info:
                    self.storage_types.add('HDD')
                if 'NVMe' in disk_info or 'NVME' in disk_info:
                    self.storage_types.add('NVMe')
            else:
                pass
        except subprocess.TimeoutExpired:
            pass
        except FileNotFoundError:
            pass
        except Exception:
            pass
    
    def is_intel_cpu(self):
        return self.cpu_vendor == 'Intel'
    
    def is_amd_cpu(self):
        return self.cpu_vendor == 'AMD'
    
    def is_nvidia_gpu(self):
        return self.gpu_vendor == 'NVIDIA'
    
    def is_amd_gpu(self):
        return self.gpu_vendor == 'AMD'
    
    def has_nvme(self):
        return 'NVMe' in self.storage_types
    
    def has_ssd(self):
        return 'SSD' in self.storage_types
class OptimizationDecisionCache:
    __slots__ = ('cache', 'ttl', 'lock')
    
    def __init__(self, ttl_seconds=300):
        self.cache = {}
        self.ttl = ttl_seconds
        self.lock = threading.RLock()
    
    def get(self, pid, decision_type):
        with self.lock:
            key = (pid, decision_type)
            if key in self.cache:
                entry = self.cache[key]
                if time.time() - entry['timestamp'] < self.ttl:
                    return entry['value']
                else:
                    del self.cache[key]
            return None
    
    def set(self, pid, decision_type, value):
        with self.lock:
            if not isinstance(pid, int) or pid <= 0:
                return
            if not decision_type or not isinstance(decision_type, str):
                return
            
            key = (pid, decision_type)
            self.cache[key] = {'value': value, 'timestamp': time.time()}
            
            if len(self.cache) > MAX_CACHE_SIZE:
                sorted_items = sorted(self.cache.items(), key=lambda x: x[1]['timestamp'])
                for old_key, _ in sorted_items[:CACHE_CLEANUP_SIZE]:
                    del self.cache[old_key]
    
    def invalidate(self, pid):
        with self.lock:
            keys_to_remove = [k for k in self.cache.keys() if k[0] == pid]
            for key in keys_to_remove:
                del self.cache[key]
    
    def cleanup_expired(self):
        with self.lock:
            current_time = time.time()
            keys_to_remove = []
            for k, v in list(self.cache.items()):
                if current_time - v['timestamp'] >= self.ttl:
                    keys_to_remove.append(k)
            
            for key in keys_to_remove:
                try:
                    del self.cache[key]
                except KeyError:
                    pass
class IntegrityValidator:
    __slots__ = ('handle_cache', 'lock', 'validation_history', 'batch_queue')
    
    def __init__(self, handle_cache):
        self.handle_cache = handle_cache
        self.lock = threading.RLock()
        self.validation_history = defaultdict(list)
        self.batch_queue = []
    
    def validate_priority(self, pid, expected_priority):
        with self.lock:
            try:
                handle = self.handle_cache.get_handle(pid, PROCESS_QUERY_INFORMATION)
                if handle:
                    actual_priority = win32process.GetPriorityClass(handle)
                    result = actual_priority == expected_priority
                    self.validation_history[pid].append({
                        'type': 'priority',
                        'expected': expected_priority,
                        'actual': actual_priority,
                        'success': result,
                        'timestamp': time.time()
                    })
                    return result
            except Exception:
                return False
    
    def validate_affinity(self, pid, expected_cores):
        with self.lock:
            try:
                handle = self.handle_cache.get_handle(pid, PROCESS_QUERY_INFORMATION)
                if handle:
                    actual_cores = get_process_affinity_direct(handle)
                    if actual_cores:
                        result = set(actual_cores) == set(expected_cores)
                        self.validation_history[pid].append({
                            'type': 'affinity',
                            'expected': expected_cores,
                            'actual': actual_cores,
                            'success': result,
                            'timestamp': time.time()
                        })
                        return result
            except Exception:
                return False
    
    def get_validation_stats(self, pid):
        with self.lock:
            if pid in self.validation_history:
                history = self.validation_history[pid]
                total = len(history)
                successes = sum(1 for v in history if v['success'])
                return {'total': total, 'successes': successes, 'success_rate': successes / total if total > 0 else 0}
            return None
    
    def queue_validation(self, pid, validation_type, expected_value):
        with self.lock:
            self.batch_queue.append((pid, validation_type, expected_value))
    
    def process_batch_validations(self):
        with self.lock:
            if not self.batch_queue:
                return {}
            
            results = {}
            for pid, val_type, expected in self.batch_queue:
                try:
                    if val_type == 'priority':
                        results[(pid, val_type)] = self.validate_priority(pid, expected)
                    elif val_type == 'affinity':
                        results[(pid, val_type)] = self.validate_affinity(pid, expected)
                except Exception:
                    results[(pid, val_type)] = False
                    continue
            
            self.batch_queue.clear()
            return results
