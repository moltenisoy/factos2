import time
import psutil
import win32api
import win32con
import win32process
import subprocess
import ctypes
from ctypes import wintypes
import threading
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

if ctypes.sizeof(ctypes.c_void_p) == 8:
    ULONG_PTR = ctypes.c_uint64
else:
    ULONG_PTR = ctypes.c_uint32

RelationProcessorCore = 0
RelationNumaNode = 1
RelationCache = 2
RelationProcessorPackage = 3
RelationGroup = 4
RelationAll = 0xFFFF
CacheUnified = 0
CacheInstruction = 1
CacheData = 2
CacheTrace = 3
TH32CS_SNAPTHREAD = 0x00000004
THREAD_SET_INFORMATION = 0x0020
THREAD_QUERY_INFORMATION = 0x0040
ThreadPowerThrottling = 49
THREAD_POWER_THROTTLING_EXECUTION_SPEED = 0x1
THREAD_POWER_THROTTLING_VALID_FLAGS = 0x1
QUOTA_LIMITS_HARDWS_MIN_ENABLE = 0x00000001
QUOTA_LIMITS_HARDWS_MAX_ENABLE = 0x00000002
PROCESS_SET_INFORMATION = 0x0200
PROCESS_QUERY_INFORMATION = 0x0400

ntdll = ctypes.WinDLL('ntdll')
kernel32 = ctypes.WinDLL('kernel32')

class GROUP_AFFINITY(ctypes.Structure):
    _fields_ = [('Mask', ctypes.c_ulonglong), ('Group', ctypes.wintypes.WORD), ('Reserved', ctypes.wintypes.WORD * 3)]
class PROCESSOR_RELATIONSHIP(ctypes.Structure):
    _fields_ = [('Flags', ctypes.wintypes.BYTE), ('EfficiencyClass', ctypes.wintypes.BYTE), ('Reserved', ctypes.wintypes.BYTE * 20), ('GroupCount', ctypes.wintypes.WORD), ('GroupMask', GROUP_AFFINITY * 1)]
class SYSTEM_LOGICAL_PROCESSOR_INFORMATION_EX_UNION(ctypes.Union):
    _fields_ = [('Processor', PROCESSOR_RELATIONSHIP)]
class SYSTEM_LOGICAL_PROCESSOR_INFORMATION_EX(ctypes.Structure):
    _fields_ = [('Relationship', ctypes.wintypes.DWORD), ('Size', ctypes.wintypes.DWORD), ('u', SYSTEM_LOGICAL_PROCESSOR_INFORMATION_EX_UNION)]
class THREADENTRY32(ctypes.Structure):
    _fields_ = [('dwSize', ctypes.wintypes.DWORD), ('cntUsage', ctypes.wintypes.DWORD), ('th32ThreadID', ctypes.wintypes.DWORD), ('th32OwnerProcessID', ctypes.wintypes.DWORD), ('tpBasePri', ctypes.wintypes.LONG), ('tpDeltaPri', ctypes.wintypes.LONG), ('dwFlags', ctypes.wintypes.DWORD)]
class THREAD_POWER_THROTTLING_STATE(ctypes.Structure):
    _fields_ = [('Version', ctypes.wintypes.ULONG), ('ControlMask', ctypes.wintypes.ULONG), ('StateMask', ctypes.wintypes.ULONG)]
class CACHE_DESCRIPTOR(ctypes.Structure):
    _fields_ = [("Level", ctypes.wintypes.BYTE), ("Associativity", ctypes.wintypes.BYTE), ("LineSize", ctypes.wintypes.WORD), ("Size", ctypes.wintypes.DWORD), ("Type", ctypes.wintypes.BYTE)]
class SYSTEM_LOGICAL_PROCESSOR_INFORMATION_UNION(ctypes.Union):
    _fields_ = [("ProcessorCore_Flags", ctypes.wintypes.DWORD), ("NumaNode_NodeNumber", ctypes.wintypes.DWORD), ("Cache", CACHE_DESCRIPTOR), ("Reserved", ctypes.c_ulonglong * 2)]
class SYSTEM_LOGICAL_PROCESSOR_INFORMATION(ctypes.Structure):
    _fields_ = [("ProcessorMask", ctypes.c_ulonglong), ("Relationship", ctypes.wintypes.DWORD), ("u", SYSTEM_LOGICAL_PROCESSOR_INFORMATION_UNION)]

class CPUParkingController:
    def __init__(self):
        self.lock = threading.RLock()
        self.parking_disabled_cores = set()
    
    def disable_cpu_parking(self, core_id):
        with self.lock:
            try:
                result = subprocess.run(
                    ['powercfg', '/setacvalueindex', 'SCHEME_CURRENT', 'SUB_PROCESSOR', 'CPMINCORES', '100'],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                
                if result.returncode == 0:
                    self.parking_disabled_cores.add(core_id)
                    return True
                return False
            except Exception:
                return False
    
    def enable_cpu_parking(self, core_id):
        with self.lock:
            try:
                result = subprocess.run(
                    ['powercfg', '/setacvalueindex', 'SCHEME_CURRENT', 'SUB_PROCESSOR', 'CPMINCORES', '0'],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                
                if result.returncode == 0:
                    self.parking_disabled_cores.discard(core_id)
                    return True
                return False
            except Exception:
                return False
    
    def get_statistics(self):
        with self.lock:
            pass
class HeterogeneousThreadScheduler:
    def __init__(self, handle_cache, p_cores, e_cores):
        self.handle_cache = handle_cache
        self.p_cores = p_cores
        self.e_cores = e_cores
        self.lock = threading.RLock()
        self.thread_classifications = {}
    
    def classify_and_schedule_threads(self, pid, is_latency_sensitive):
        with self.lock:
            try:
                snapshot_handle = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0)
                
                if snapshot_handle == -1 or snapshot_handle == 0:
                    return False
                
                threads_scheduled = 0
                target_cores = self.p_cores if is_latency_sensitive else self.e_cores
                
                if not target_cores:
                    target_cores = self.p_cores
                
                try:
                    te32 = THREADENTRY32()
                    te32.dwSize = ctypes.sizeof(THREADENTRY32)
                    
                    if kernel32.Thread32First(snapshot_handle, ctypes.byref(te32)):
                        while True:
                            try:
                                if te32.th32OwnerProcessID == pid:
                                    thread_id = te32.th32ThreadID
                                    
                                    thread_handle = kernel32.OpenThread(
                                        THREAD_SET_INFORMATION | THREAD_QUERY_INFORMATION,
                                        False,
                                        thread_id
                                    )
                                    
                                    if thread_handle:
                                        try:
                                            if is_latency_sensitive:
                                                throttling_state = THREAD_POWER_THROTTLING_STATE()
                                                throttling_state.Version = 1
                                                throttling_state.ControlMask = THREAD_POWER_THROTTLING_VALID_FLAGS
                                                throttling_state.StateMask = 0
                                                
                                                ntdll.NtSetInformationThread(
                                                    thread_handle,
                                                    ThreadPowerThrottling,
                                                    ctypes.byref(throttling_state),
                                                    ctypes.sizeof(throttling_state)
                                                )
                                            
                                            affinity_mask = 0
                                            for core in target_cores:
                                                affinity_mask |= (1 << core)
                                            
                                            kernel32.SetThreadAffinityMask(thread_handle, affinity_mask)
                                            
                                            threads_scheduled += 1
                                            
                                            self.thread_classifications[thread_id] = 'latency' if is_latency_sensitive else 'throughput'
                                            
                                        finally:
                                            kernel32.CloseHandle(thread_handle)
                            except Exception:
                                pass
                            
                            if not kernel32.Thread32Next(snapshot_handle, ctypes.byref(te32)):
                                break
                finally:
                    kernel32.CloseHandle(snapshot_handle)
                
                return threads_scheduled > 0
                
            except Exception:
                return False
    
    def get_statistics(self):
        with self.lock:
            pass
class SMTScheduler:
    def __init__(self, cpu_count):
        self.cpu_count = cpu_count
        self.lock = threading.RLock()
        self.sibling_map = {}
        self._detect_siblings()
    
    def _detect_siblings(self):
        try:
            returned_length = wintypes.DWORD(0)
            kernel32.GetLogicalProcessorInformationEx(RelationProcessorCore, None, ctypes.byref(returned_length))
            buf_size = returned_length.value
            
            if buf_size > 0:
                buf = (ctypes.c_byte * buf_size)()
                if kernel32.GetLogicalProcessorInformationEx(RelationProcessorCore, ctypes.byref(buf), ctypes.byref(returned_length)):
                    offset = 0
                    while offset < buf_size:
                        entry = SYSTEM_LOGICAL_PROCESSOR_INFORMATION_EX.from_buffer_copy(buf[offset:])
                        if entry.Relationship == RelationProcessorCore:
                            proc_rel = entry.u.Processor
                            if proc_rel.GroupCount > 0:
                                mask = proc_rel.GroupMask[0].Mask
                                cpus = []
                                bit = 0
                                temp_mask = mask
                                while temp_mask:
                                    if temp_mask & 1:
                                        cpus.append(bit)
                                    temp_mask >>= 1
                                    bit += 1
                                
                                for cpu in cpus:
                                    self.sibling_map[cpu] = [c for c in cpus if c != cpu]
                        
                        offset += entry.Size
        except Exception:
            pass
    
    def get_physical_cores_only(self):
        with self.lock:
            physical_cores = set()
            for core in range(self.cpu_count):
                if core not in self.sibling_map or not self.sibling_map[core]:
                    physical_cores.add(core)
                elif core not in physical_cores:
                    skip = False
                    for sibling in self.sibling_map[core]:
                        if sibling in physical_cores:
                            skip = True
                            break
                    if not skip:
                        physical_cores.add(core)
            
            return list(physical_cores) if physical_cores else list(range(self.cpu_count))
    
    def assign_to_physical_cores(self, pid):
        with self.lock:
            try:
                physical_cores = self.get_physical_cores_only()
                
                handle = win32api.OpenProcess(PROCESS_SET_INFORMATION | PROCESS_QUERY_INFORMATION, False, pid)
                if not handle:
                    return False
                
                try:
                    affinity_mask = 0
                    for core in physical_cores:
                        affinity_mask |= (1 << core)
                    
                    result = kernel32.SetProcessAffinityMask(handle, ULONG_PTR(affinity_mask))
                    
                    if result:
                        return True
                    
                    return False
                finally:
                    win32api.CloseHandle(handle)
            except Exception:
                return False
    
    def get_statistics(self):
        with self.lock:
            pass
class CPUFrequencyScaler:
    def __init__(self):
        self.lock = threading.RLock()
    
    def set_turbo_mode(self, enable=True):
        with self.lock:
            try:
                if enable:
                    result = subprocess.run(
                        ['powercfg', '/setacvalueindex', 'SCHEME_CURRENT', 'SUB_PROCESSOR', 'PERFBOOSTMODE', '2'],
                        capture_output=True,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                else:
                    result = subprocess.run(
                        ['powercfg', '/setacvalueindex', 'SCHEME_CURRENT', 'SUB_PROCESSOR', 'PERFBOOSTMODE', '0'],
                        capture_output=True,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                
                if result.returncode == 0:
                    subprocess.run(['powercfg', '/setactive', 'SCHEME_CURRENT'], 
                                 capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                    return True
                return False
            except Exception:
                return False
    
    def get_statistics(self):
        with self.lock:
            pass
class L3CacheOptimizer:
    def __init__(self, topology):
        self.lock = threading.RLock()
        self.topology = topology
        self.cache_groups = self._detect_l3_cache_groups()
        self.process_assignments = {}
    
    def _detect_l3_cache_groups(self):
        cache_groups = defaultdict(set)
        try:
            returned_length = wintypes.DWORD(0)
            kernel32.GetLogicalProcessorInformation(None, ctypes.byref(returned_length))
            
            if returned_length.value > 0:
                buf = (ctypes.c_byte * returned_length.value)()
                if not kernel32.GetLogicalProcessorInformation(ctypes.byref(buf), ctypes.byref(returned_length)):
                    return cache_groups
                
                entry_size = ctypes.sizeof(SYSTEM_LOGICAL_PROCESSOR_INFORMATION)
                entry_count = returned_length.value // entry_size
                
                for i in range(entry_count):
                    offset = i * entry_size
                    entry = SYSTEM_LOGICAL_PROCESSOR_INFORMATION.from_buffer_copy(buf[offset:offset+entry_size])
                    
                    if entry.Relationship == RelationCache:
                        cache_desc = entry.u.Cache
                        if cache_desc.Level == 3:
                            mask = entry.ProcessorMask
                            cores = []
                            core_idx = 0
                            while mask:
                                if mask & 1:
                                    cores.append(core_idx)
                                mask >>= 1
                                core_idx += 1
                            
                            cache_id = i
                            cache_groups[cache_id].update(cores)
        except Exception:
            pass
        return cache_groups
    
    def optimize_process_cache_locality(self, pid, is_critical=False, handle_cache=None):
        with self.lock:
            try:
                if not self.cache_groups:
                    return False
                
                if is_critical and handle_cache:
                    best_cache_group = None
                    min_processes = float('inf')
                    
                    for cache_id, cores in self.cache_groups.items():
                        process_count = sum(1 for p_cores in self.process_assignments.values() 
                                          if any(c in cores for c in p_cores))
                        if process_count < min_processes:
                            min_processes = process_count
                            best_cache_group = cores
                    
                    if best_cache_group:
                        handle = handle_cache.get_handle(pid, PROCESS_SET_INFORMATION | PROCESS_QUERY_INFORMATION)
                        if handle:
                            affinity_mask = sum(1 << core for core in best_cache_group)
                            result = kernel32.SetProcessAffinityMask(handle, ULONG_PTR(affinity_mask))
                            if result:
                                self.process_assignments[pid] = list(best_cache_group)
                                return True
            except Exception:
                pass
            return False
    
    def detect_cache_contention(self, pid_list):
        with self.lock:
            try:
                for cache_id, cores in self.cache_groups.items():
                    processes_in_group = [pid for pid, assigned_cores in self.process_assignments.items()
                                         if pid in pid_list and any(c in cores for c in assigned_cores)]
                    if len(processes_in_group) > len(cores) / 2:
                        return True, cache_id, processes_in_group
            except Exception:
                pass
            return False, None, []
class EnhancedCacheTopologyOptimizer:
    
    def __init__(self, topology):
        self.lock = threading.RLock()
        self.topology = topology
        self.l2_cache_groups = self._detect_l2_cache_groups()
        self.l3_cache_groups = self._detect_l3_cache_groups()
        self.process_cache_assignments = {}
        self.cache_contention_scores = defaultdict(float)
        self.last_rebalance = time.time()
    
    def _detect_l2_cache_groups(self):
        cache_groups = defaultdict(set)
        try:
            returned_length = wintypes.DWORD(0)
            kernel32.GetLogicalProcessorInformation(None, ctypes.byref(returned_length))
            
            if returned_length.value > 0:
                buf = (ctypes.c_byte * returned_length.value)()
                if not kernel32.GetLogicalProcessorInformation(ctypes.byref(buf), ctypes.byref(returned_length)):
                    return cache_groups
                
                entry_size = ctypes.sizeof(SYSTEM_LOGICAL_PROCESSOR_INFORMATION)
                entry_count = returned_length.value // entry_size
                
                for i in range(entry_count):
                    offset = i * entry_size
                    entry = SYSTEM_LOGICAL_PROCESSOR_INFORMATION.from_buffer_copy(buf[offset:offset+entry_size])
                    
                    if entry.Relationship == RelationCache:
                        cache_desc = entry.u.Cache
                        if cache_desc.Level == 2:
                            mask = entry.ProcessorMask
                            cores = self._mask_to_cores(mask)
                            cache_id = f"L2_{i}"
                            cache_groups[cache_id].update(cores)
        except Exception as e:
            logger.debug(f"L2 cache detection error: {e}")
        return cache_groups
    
    def _detect_l3_cache_groups(self):
        cache_groups = defaultdict(set)
        try:
            returned_length = wintypes.DWORD(0)
            kernel32.GetLogicalProcessorInformation(None, ctypes.byref(returned_length))
            
            if returned_length.value > 0:
                buf = (ctypes.c_byte * returned_length.value)()
                if not kernel32.GetLogicalProcessorInformation(ctypes.byref(buf), ctypes.byref(returned_length)):
                    return cache_groups
                
                entry_size = ctypes.sizeof(SYSTEM_LOGICAL_PROCESSOR_INFORMATION)
                entry_count = returned_length.value // entry_size
                
                for i in range(entry_count):
                    offset = i * entry_size
                    entry = SYSTEM_LOGICAL_PROCESSOR_INFORMATION.from_buffer_copy(buf[offset:offset+entry_size])
                    
                    if entry.Relationship == RelationCache:
                        cache_desc = entry.u.Cache
                        if cache_desc.Level == 3:
                            mask = entry.ProcessorMask
                            cores = self._mask_to_cores(mask)
                            cache_id = f"L3_{i}"
                            cache_groups[cache_id].update(cores)
        except Exception as e:
            logger.debug(f"L3 cache detection error: {e}")
        return cache_groups
    
    def _mask_to_cores(self, mask):
        cores = []
        core_idx = 0
        while mask:
            if mask & 1:
                cores.append(core_idx)
            mask >>= 1
            core_idx += 1
        return cores
    
    def assign_process_to_cache_group(self, pid, process_name, related_pids=None, handle_cache=None):
        with self.lock:
            try:
                if not self.l3_cache_groups and not self.l2_cache_groups:
                    return False
                
                target_cache_group = None
                
                if related_pids:
                    for cache_id, cores in self.l3_cache_groups.items():
                        related_count = sum(
                            1 for rel_pid in related_pids
                            if self.process_cache_assignments.get(rel_pid, {}).get('cache_group') == cache_id
                        )
                        if related_count > 0:
                            target_cache_group = cache_id
                            break
                
                if not target_cache_group:
                    min_contention = float('inf')
                    for cache_id in self.l3_cache_groups.keys():
                        contention = self.cache_contention_scores.get(cache_id, 0)
                        if contention < min_contention:
                            min_contention = contention
                            target_cache_group = cache_id
                
                if target_cache_group and handle_cache:
                    cores = self.l3_cache_groups[target_cache_group]
                    handle = handle_cache.get_handle(pid, PROCESS_SET_INFORMATION | PROCESS_QUERY_INFORMATION)
                    if handle:
                        affinity_mask = sum(1 << core for core in cores)
                        result = kernel32.SetProcessAffinityMask(handle, ULONG_PTR(affinity_mask))
                        if result:
                            self.process_cache_assignments[pid] = {
                                'cache_group': target_cache_group,
                                'cores': list(cores),
                                'assigned_at': time.time()
                            }
                            logger.debug(f"Process {pid} assigned to cache group {target_cache_group}")
                            return True
            except Exception as e:
                logger.debug(f"Cache assignment error for pid {pid}: {e}")
            return False
    
    def detect_and_rebalance_contention(self, active_pids, handle_cache=None):
        with self.lock:
            try:
                current_time = time.time()
                
                if current_time - self.last_rebalance < 30:
                    return False
                
                self.last_rebalance = current_time
                
                for cache_id, cores in self.l3_cache_groups.items():
                    processes_in_group = [
                        pid for pid in active_pids
                        if self.process_cache_assignments.get(pid, {}).get('cache_group') == cache_id
                    ]
                    
                    contention = len(processes_in_group) / max(len(cores), 1)
                    self.cache_contention_scores[cache_id] = contention
                    
                    if contention > 2.0:
                        logger.info(f"High cache contention in {cache_id}: {contention:.2f}")
                
                high_contention_groups = [
                    cache_id for cache_id, score in self.cache_contention_scores.items()
                    if score > 2.0
                ]
                
                if high_contention_groups and handle_cache:
                    self._rebalance_processes(active_pids, high_contention_groups, handle_cache)
                    return True
                    
            except Exception as e:
                logger.debug(f"Cache contention detection error: {e}")
            return False
    
    def _rebalance_processes(self, active_pids, high_contention_groups, handle_cache):
        try:
            
            low_contention_groups = [
                cache_id for cache_id, score in self.cache_contention_scores.items()
                if score < 1.0 and cache_id not in high_contention_groups
            ]
            
            if not low_contention_groups:
                return
            
            
            for high_cache_id in high_contention_groups:
                processes_to_move = [
                    pid for pid in active_pids
                    if self.process_cache_assignments.get(pid, {}).get('cache_group') == high_cache_id
                ]
                
                
                move_count = min(len(processes_to_move) // 2, len(low_contention_groups))
                
                for i, pid in enumerate(processes_to_move[:move_count]):
                    target_cache_id = low_contention_groups[i % len(low_contention_groups)]
                    cores = self.l3_cache_groups[target_cache_id]
                    
                    handle = handle_cache.get_handle(pid, PROCESS_SET_INFORMATION | PROCESS_QUERY_INFORMATION)
                    if handle:
                        affinity_mask = sum(1 << core for core in cores)
                        result = kernel32.SetProcessAffinityMask(handle, ULONG_PTR(affinity_mask))
                        if result:
                            self.process_cache_assignments[pid] = {
                                'cache_group': target_cache_id,
                                'cores': list(cores),
                                'assigned_at': time.time()
                            }
                            logger.debug(f"Rebalanced process {pid} from {high_cache_id} to {target_cache_id}")
        except Exception as e:
            logger.debug(f"Rebalancing error: {e}")
    
    def get_stats(self):
        with self.lock:
            pass
class AVXInstructionOptimizer:

    def __init__(self, handle_cache, cpu_count):
        self.lock = threading.RLock()
        self.handle_cache = handle_cache
        self.cpu_count = cpu_count
        self.avx_processes = {}
        self.avx_capable_cores = self._detect_avx_cores()
    
    def _detect_avx_cores(self):

        try:
            result = subprocess.run(
                ['powershell', '-Command', 
                 '(Get-WmiObject Win32_Processor).Description'],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=5
            )
            
            if result.returncode == 0:


                return list(range(self.cpu_count))
        except Exception:
            pass
        

        return list(range(self.cpu_count))
    
    def detect_avx_usage(self, pid, process_name):

        with self.lock:
            try:
                process_lower = process_name.lower()
                avx_indicators = ['render', 'encode', 'decode', 'video', 'blender', 'maya', 
                                'handbrake', 'ffmpeg', 'premiere', 'davinci', 'x264', 'x265',
                                'scientific', 'matlab', 'mathematica', 'numpy']
                
                is_avx_process = any(indicator in process_lower for indicator in avx_indicators)
                
                if is_avx_process:
                    self.avx_processes[pid] = {
                        'name': process_name,
                        'detected_at': time.time(),
                        'optimized': False
                    }
                    return True
            except Exception:
                pass
            return False
    
    def optimize_avx_process(self, pid):

        with self.lock:
            try:
                if pid not in self.avx_processes or self.avx_processes[pid]['optimized']:
                    return False
                
                if self.avx_capable_cores:
                    handle = self.handle_cache.get_handle(pid, PROCESS_SET_INFORMATION | PROCESS_QUERY_INFORMATION)
                    if handle:

                        cores_to_use = max(len(self.avx_capable_cores) // 2, min(4, len(self.avx_capable_cores)))
                        affinity_mask = sum(1 << core for core in self.avx_capable_cores[:cores_to_use])
                        result = kernel32.SetProcessAffinityMask(handle, ULONG_PTR(affinity_mask))
                        if result:
                            self.avx_processes[pid]['optimized'] = True
                            
                            try:
                                win32process.SetPriorityClass(handle, win32process.ABOVE_NORMAL_PRIORITY_CLASS)
                            except Exception:
                                pass
                            return True
            except Exception:
                pass
            return False
class EnhancedSMTOptimizer:

    def __init__(self, topology, cpu_count):
        self.lock = threading.RLock()
        self.topology = topology
        self.cpu_count = cpu_count
        self.physical_cores = self._detect_physical_cores()
        self.smt_pairs = self._detect_smt_pairs()
        self.process_smt_config = {}
    
    def _detect_physical_cores(self):

        try:
            return list(range(psutil.cpu_count(logical=False)))
        except Exception:
            return list(range(self.cpu_count // 2))
    
    def _detect_smt_pairs(self):

        pairs = {}
        try:
            logical_count = psutil.cpu_count(logical=True)
            physical_count = psutil.cpu_count(logical=False)
            
            if logical_count == physical_count * 2:
                for i in range(physical_count):
                    pairs[i] = [i, i + physical_count]
        except Exception:
            pass
        return pairs
    
    def optimize_for_latency(self, pid, handle_cache):

        with self.lock:
            try:
                if not self.physical_cores:
                    return False
                
                handle = handle_cache.get_handle(pid, PROCESS_SET_INFORMATION | PROCESS_QUERY_INFORMATION)
                if handle:
                    affinity_mask = sum(1 << core for core in self.physical_cores)
                    result = kernel32.SetProcessAffinityMask(handle, ULONG_PTR(affinity_mask))
                    if result:
                        self.process_smt_config[pid] = 'latency'
                        return True
            except Exception:
                pass
            return False
    
    def optimize_for_throughput(self, pid, handle_cache):

        with self.lock:
            try:
                handle = handle_cache.get_handle(pid, PROCESS_SET_INFORMATION | PROCESS_QUERY_INFORMATION)
                if handle:
                    affinity_mask = (1 << self.cpu_count) - 1
                    result = kernel32.SetProcessAffinityMask(handle, ULONG_PTR(affinity_mask))
                    if result:
                        self.process_smt_config[pid] = 'throughput'
                        return True
            except Exception:
                pass
            return False
class CPUPipelineOptimizer:

    def __init__(self, handle_cache):
        self.lock = threading.RLock()
        self.handle_cache = handle_cache
    
    def optimize_instruction_ordering(self, pid, is_critical=False):

        with self.lock:
            try:
                handle = self.handle_cache.get_handle(pid, PROCESS_SET_INFORMATION | PROCESS_QUERY_INFORMATION)
                if not handle:
                    return False
                
                if is_critical:
                    kernel32.SetProcessPriorityBoost(handle, wintypes.BOOL(False))
                    
                    try:
                        win32process.SetPriorityClass(handle, win32process.HIGH_PRIORITY_CLASS)
                    except Exception:
                        pass
                    
                    return True
            except Exception:
                pass
            return False
class TLBOptimizer:

    def __init__(self, handle_cache):
        self.lock = threading.RLock()
        self.handle_cache = handle_cache
        self.large_page_processes = set()
    
    def enable_large_pages(self, pid):

        with self.lock:
            try:
                if pid in self.large_page_processes:
                    return True
                
                handle = self.handle_cache.get_handle(pid, PROCESS_SET_QUOTA | PROCESS_QUERY_INFORMATION)
                if handle:
                    min_ws = 1024 * 1024 * 1024
                    max_ws = 4 * 1024 * 1024 * 1024
                    flags = QUOTA_LIMITS_HARDWS_MIN_ENABLE | QUOTA_LIMITS_HARDWS_MAX_ENABLE
                    
                    result = kernel32.SetProcessWorkingSetSizeEx(handle, min_ws, max_ws, flags)
                    if result:
                        self.large_page_processes.add(pid)
                        return True
            except Exception:
                pass
            return False
    
    def optimize_memory_layout(self, pid):

        with self.lock:
            try:
                proc = psutil.Process(pid)
                mem_info = proc.memory_info()
                
                if mem_info.rss > 512 * 1024 * 1024:
                    return self.enable_large_pages(pid)
            except Exception:
                pass
            return False
class CPUPinningEngine:
    def __init__(self, handle_cache, cpu_count, numa_topology=None):
        self.handle_cache = handle_cache
        self.cpu_count = cpu_count
        self.numa_topology = numa_topology or {}
        
        self.pinned_processes = {}
        self.core_assignments = defaultdict(set)
        self.thread_affinity_cache = {}
        
        self.lock = threading.RLock()
        
    def pin_process_to_core(self, pid, core_id, pin_threads=True):
        with self.lock:
            result = {
                'success': False,
                'threads_pinned': 0,
                'core': core_id
            }
            
            if core_id >= self.cpu_count or core_id < 0:
                return result
            
            try:
                handle = win32api.OpenProcess(PROCESS_SET_INFORMATION | PROCESS_QUERY_INFORMATION, False, pid)
                if not handle:
                    return result
                
                try:
                    success = set_process_affinity_direct(handle, [core_id])
                    
                    if not success:
                        return result
                    
                    threads_pinned = 0
                    if pin_threads:
                        threads_pinned = self._pin_process_threads(pid, core_id)
                    
                    self.pinned_processes[pid] = {
                        'core': core_id,
                        'timestamp': time.time(),
                        'thread_count': threads_pinned,
                        'pin_threads': pin_threads
                    }
                    
                    self.core_assignments[core_id].add(pid)
                    
                    result.update({
                        'success': True,
                        'threads_pinned': threads_pinned
                    })
                    
                finally:
                    win32api.CloseHandle(handle)
                
            except Exception as e:
                logger.debug(f"Error pinning threads for PID {pid}: {type(e).__name__}: {e}")
            
            return result
    
    def _pin_process_threads(self, pid, core_id):
        threads_pinned = 0
        
        try:
            snapshot_handle = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0)
            
            if snapshot_handle == -1 or snapshot_handle == 0:
                return 0
            
            try:
                te32 = THREADENTRY32()
                te32.dwSize = ctypes.sizeof(THREADENTRY32)
                
                if kernel32.Thread32First(snapshot_handle, ctypes.byref(te32)):
                    while True:
                        try:
                            if te32.th32OwnerProcessID == pid:
                                thread_id = te32.th32ThreadID
                                
                                thread_handle = kernel32.OpenThread(
                                    THREAD_SET_INFORMATION | THREAD_QUERY_INFORMATION,
                                    False,
                                    thread_id
                                )
                                
                                if thread_handle:
                                    try:
                                        kernel32.SetThreadIdealProcessor(thread_handle, core_id)
                                        
                                        affinity_mask = 1 << core_id
                                        kernel32.SetThreadAffinityMask(thread_handle, affinity_mask)
                                        
                                        threads_pinned += 1
                                        
                                        if pid not in self.thread_affinity_cache:
                                            self.thread_affinity_cache[pid] = {}
                                        self.thread_affinity_cache[pid][thread_id] = core_id
                                        
                                    finally:
                                        kernel32.CloseHandle(thread_handle)
                        except Exception as e:
                            logger.debug(f"Error pinning thread {thread_id}: {type(e).__name__}: {e}")
                        
                        if not kernel32.Thread32Next(snapshot_handle, ctypes.byref(te32)):
                            break
            finally:
                kernel32.CloseHandle(snapshot_handle)
        
        except Exception:
            pass
        
        return threads_pinned
    
    def unpin_process(self, pid):
        with self.lock:
            if pid not in self.pinned_processes:
                return False
            
            try:
                handle = win32api.OpenProcess(PROCESS_SET_INFORMATION | PROCESS_QUERY_INFORMATION, False, pid)
                if not handle:
                    return False
                
                try:
                    all_cores = list(range(self.cpu_count))
                    set_process_affinity_direct(handle, all_cores)
                    
                    pinning_info = self.pinned_processes[pid]
                    core_id = pinning_info['core']
                    
                    del self.pinned_processes[pid]
                    self.core_assignments[core_id].discard(pid)
                    
                    if pid in self.thread_affinity_cache:
                        del self.thread_affinity_cache[pid]
                    
                    return True
                
                finally:
                    win32api.CloseHandle(handle)
                
            except Exception:
                return False
    
    def get_least_loaded_core(self, core_candidates):
        if not core_candidates:
            return 0
        
        with self.lock:
            loads = {}
            for core_id in core_candidates:
                loads[core_id] = len(self.core_assignments.get(core_id, set()))
            
            try:
                per_cpu_percent = psutil.cpu_percent(interval=0.1, percpu=True)
                
                scores = {}
                for core_id in core_candidates:
                    cpu_load = per_cpu_percent[core_id] if core_id < len(per_cpu_percent) else 50
                    pinned_load = loads[core_id] * 10
                    
                    scores[core_id] = (cpu_load * 0.6) + (pinned_load * 0.4)
                
                return min(scores.keys(), key=lambda c: scores[c])
                
            except Exception:
                return min(loads.keys(), key=lambda c: loads[c])
    
    def get_numa_preferred_cores(self, available_cores):
        if not self.numa_topology or not self.numa_topology.get('numa_nodes'):
            return available_cores
        
        try:
            numa_nodes = self.numa_topology.get('numa_nodes', {})
            
            for node_id, node_cores in numa_nodes.items():
                intersection = set(available_cores) & node_cores
                if intersection and len(intersection) >= 2:
                    return list(intersection)
            
            return available_cores
        except Exception:
            return available_cores
    
    def apply_intelligent_pinning(self, pid, available_cores, workload_type='general'):
        with self.lock:
            try:
                numa_cores = self.get_numa_preferred_cores(available_cores)
                
                handle = win32api.OpenProcess(PROCESS_SET_INFORMATION | PROCESS_QUERY_INFORMATION, False, pid)
                if not handle:
                    return {'success': False}
                
                try:
                    process = psutil.Process(pid)
                    num_threads = process.num_threads()
                    
                    if workload_type == 'single_thread' or num_threads <= 2:
                        best_core = self.get_least_loaded_core(numa_cores)
                        return self.pin_process_to_core(pid, best_core, pin_threads=True)
                    
                    elif workload_type == 'latency_sensitive':
                        if len(numa_cores) >= 2:
                            sorted_cores = sorted(numa_cores, 
                                                key=lambda c: len(self.core_assignments.get(c, set())))
                            selected_cores = sorted_cores[:2]
                            
                            set_process_affinity_direct(handle, selected_cores)
                            return {'success': True, 'cores': selected_cores, 'mode': 'soft_affinity'}
                        else:
                            best_core = self.get_least_loaded_core(numa_cores)
                            return self.pin_process_to_core(pid, best_core, pin_threads=True)
                    
                    elif workload_type == 'throughput':
                        set_process_affinity_direct(handle, numa_cores)
                        return {'success': True, 'cores': numa_cores, 'mode': 'affinity_only'}
                    
                    else:
                        if num_threads <= 4:
                            cores_to_use = numa_cores[:min(4, len(numa_cores))]
                            set_process_affinity_direct(handle, cores_to_use)
                            return {'success': True, 'cores': cores_to_use, 'mode': 'limited_affinity'}
                        else:
                            set_process_affinity_direct(handle, numa_cores)
                            return {'success': True, 'cores': numa_cores, 'mode': 'full_affinity'}
                
                finally:
                    try:
                        win32api.CloseHandle(handle)
                    except Exception:
                        pass
                        
            except Exception:
                return {'success': False}
    
    def get_pinning_info(self, pid):
        with self.lock:
            return self.pinned_processes.get(pid, None)
    
    def get_core_assignments(self):
        with self.lock:
            return {core: list(pids) for core, pids in self.core_assignments.items()}
    
    def cleanup_dead_processes(self):
        with self.lock:
            dead_pids = []
            
            for pid in list(self.pinned_processes.keys()):
                if not psutil.pid_exists(pid):
                    dead_pids.append(pid)
            
            for pid in dead_pids:
                pinning_info = self.pinned_processes[pid]
                core_id = pinning_info['core']
                
                del self.pinned_processes[pid]
                self.core_assignments[core_id].discard(pid)
                
                if pid in self.thread_affinity_cache:
                    del self.thread_affinity_cache[pid]
            
    def get_statistics(self):
        with self.lock:
            pass
