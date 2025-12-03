import sys
import platform
import time
import ctypes
import json
import os
import subprocess
import threading
import gc
import heapq
import weakref
import math
import logging
from ctypes import wintypes
from collections import defaultdict, deque
from typing import Optional, List, Dict, Set, Any, Callable

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='optimus_prime.log',
    filemode='w'
)
logger = logging.getLogger(__name__)

import psutil
import win32process
import win32gui
import win32con
import win32api
import win32job
import win32file
import pywintypes
import winreg

from almacenamiento import (
    StorageOptimizer, AdaptiveReadAheadManager, WriteCoalescingManager, 
    StorageTierManager, DynamicDiskCacheTuner, IntelligentTRIMScheduler, 
    AggressiveWriteCache, CustomIOScheduler, NCQOptimizer, 
    AdvancedFileSystemCache, IOPriorityInheritance, AdaptiveIOScheduler, 
    MetadataOptimizer
)
from gpu import (
    GPUSchedulingOptimizer, PCIeBandwidthOptimizer, DirectXVulkanOptimizer
)
from ram import (
    WorkingSetOptimizer, LargePageManager, AdvancedWorkingSetTrimmer, 
    MemoryPriorityManager, AWEManager, NUMAAwareMemoryAllocator, 
    DynamicHugePagesManager, MemoryDeduplicationManager, 
    AdvancedMemoryPagePriorityManager
)
from kernel import (
    KernelOptimizer, AdvancedTimerCoalescer, AdaptiveTimerResolutionManager, 
    ContextSwitchReducer, TSCSynchronizer, DPCLatencyController, 
    AdvancedInterruptDPCOptimizer
)
from cpu import (
    CPUParkingController, HeterogeneousThreadScheduler, SMTScheduler, 
    CPUFrequencyScaler, L3CacheOptimizer, EnhancedCacheTopologyOptimizer, 
    AVXInstructionOptimizer, EnhancedSMTOptimizer, CPUPipelineOptimizer, 
    TLBOptimizer, CPUPinningEngine
)
from prioridades import (
    DynamicPriorityAlgorithm, RealtimePriorityManager, SystemResponsivenessController
)
from energia import (
    PowerManagementOptimizer, CStatesOptimizer, DynamicVoltageFrequencyScaler
)
from temperatura import (
    CPUTemperatureMonitor, ThermalAwareScheduler
)
from servicios import (
    ProcessServiceManager
)
from redes import (
    NetworkOptimizer, NetworkFlowPrioritizer, TCPCongestionControlTuner, 
    NetworkInterruptCoalescer, AdaptiveNetworkPollingManager, 
    TCPFastOpenOptimizer, DynamicNetworkBufferTuner, BBRCongestionControl, 
    NetworkPollingOptimizer, AggressiveDNSCache, EnhancedNetworkStackOptimizer
)
from perfiles import (
    AutomaticProfileManager, DynamicMultiLayerProfileSystem
)
from ajustes_varios import (
    CircularBuffer, CTypesStructurePool, SimpleBloomFilter, RegistryWriteBuffer, 
    HardwareDetector, OptimizationDecisionCache, IntegrityValidator, 
    ProcessSuspensionManager, ProcessHandleCache, ProcessSnapshotEngine, 
    BatchedSettingsApplicator, ForegroundDebouncer, ProcessTreeCache, 
    RealtimeTelemetryCollector, ProcessDependencyAnalyzer, 
    EnhancedSystemResponsivenessOptimizer
)


class LUID(ctypes.Structure):
    _fields_ = [("LowPart", wintypes.DWORD), ("HighPart", wintypes.LONG)]

class LUID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("Luid", LUID), ("Attributes", wintypes.DWORD)]

class TOKEN_PRIVILEGES(ctypes.Structure):
    _fields_ = [("PrivilegeCount", wintypes.DWORD), ("Privileges", LUID_AND_ATTRIBUTES * 1)]

class CACHE_DESCRIPTOR(ctypes.Structure):
    _fields_ = [
        ("Level", wintypes.BYTE),
        ("Associativity", wintypes.BYTE),
        ("LineSize", wintypes.WORD),
        ("Size", wintypes.DWORD),
        ("Type", wintypes.BYTE)
    ]

class SYSTEM_LOGICAL_PROCESSOR_INFORMATION_UNION(ctypes.Union):
    _fields_ = [
        ("ProcessorCore_Flags", wintypes.DWORD),
        ("NumaNode_NodeNumber", wintypes.DWORD),
        ("Cache", CACHE_DESCRIPTOR),
        ("Reserved", ctypes.c_ulonglong * 2)
    ]

class SYSTEM_LOGICAL_PROCESSOR_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("ProcessorMask", ctypes.c_ulonglong),
        ("Relationship", wintypes.DWORD),
        ("u", SYSTEM_LOGICAL_PROCESSOR_INFORMATION_UNION)
    ]

class PROCESSENTRY32(ctypes.Structure):
    _fields_ = [
        ('dwSize', wintypes.DWORD),
        ('cntUsage', wintypes.DWORD),
        ('th32ProcessID', wintypes.DWORD),
        ('th32DefaultHeapID', ctypes.POINTER(wintypes.ULONG)),
        ('th32ModuleID', wintypes.DWORD),
        ('cntThreads', wintypes.DWORD),
        ('th32ParentProcessID', wintypes.DWORD),
        ('pcPriClassBase', wintypes.LONG),
        ('dwFlags', wintypes.DWORD),
        ('szExeFile', ctypes.c_char * 260)
    ]

class THREADENTRY32(ctypes.Structure):
    _fields_ = [
        ('dwSize', wintypes.DWORD),
        ('cntUsage', wintypes.DWORD),
        ('th32ThreadID', wintypes.DWORD),
        ('th32OwnerProcessID', wintypes.DWORD),
        ('tpBasePri', wintypes.LONG),
        ('tpDeltaPri', wintypes.LONG),
        ('dwFlags', wintypes.DWORD)
    ]

class PROCESSOR_POWER_INFORMATION(ctypes.Structure):
    _fields_ = [
        ('Number', wintypes.ULONG),
        ('MaxMhz', wintypes.ULONG),
        ('CurrentMhz', wintypes.ULONG),
        ('MhzLimit', wintypes.ULONG),
        ('MaxIdleState', wintypes.ULONG),
        ('CurrentIdleState', wintypes.ULONG)
    ]

class GROUP_AFFINITY(ctypes.Structure):
    _fields_ = [
        ('Mask', ctypes.c_ulonglong),
        ('Group', wintypes.WORD),
        ('Reserved', wintypes.WORD * 3)
    ]

class PROCESSOR_RELATIONSHIP(ctypes.Structure):
    _fields_ = [
        ('Flags', wintypes.BYTE),
        ('EfficiencyClass', wintypes.BYTE),
        ('Reserved', wintypes.BYTE * 20),
        ('GroupCount', wintypes.WORD),
        ('GroupMask', GROUP_AFFINITY * 1)
    ]

class SYSTEM_LOGICAL_PROCESSOR_INFORMATION_EX_UNION(ctypes.Union):
    _fields_ = [
        ('Processor', PROCESSOR_RELATIONSHIP)
    ]

class SYSTEM_LOGICAL_PROCESSOR_INFORMATION_EX(ctypes.Structure):
    _fields_ = [
        ('Relationship', wintypes.DWORD),
        ('Size', wintypes.DWORD),
        ('u', SYSTEM_LOGICAL_PROCESSOR_INFORMATION_EX_UNION)
    ]

class PROCESS_POWER_THROTTLING_STATE(ctypes.Structure):
    _fields_ = [
        ('Version', wintypes.ULONG),
        ('ControlMask', wintypes.ULONG),
        ('StateMask', wintypes.ULONG)
    ]

class MEMORY_PRIORITY_INFORMATION(ctypes.Structure):
    _fields_ = [
        ('MemoryPriority', wintypes.ULONG)
    ]

class THREAD_POWER_THROTTLING_STATE(ctypes.Structure):
    _fields_ = [
        ('Version', wintypes.ULONG),
        ('ControlMask', wintypes.ULONG),
        ('StateMask', wintypes.ULONG)
    ]

class FILETIME(ctypes.Structure):
    _fields_ = [
        ('dwLowDateTime', wintypes.DWORD),
        ('dwHighDateTime', wintypes.DWORD)
    ]

class BY_HANDLE_FILE_INFORMATION(ctypes.Structure):
    _fields_ = [
        ('dwFileAttributes', wintypes.DWORD),
        ('ftCreationTime', FILETIME),
        ('ftLastAccessTime', FILETIME),
        ('ftLastWriteTime', FILETIME),
        ('dwVolumeSerialNumber', wintypes.DWORD),
        ('nFileSizeHigh', wintypes.DWORD),
        ('nFileSizeLow', wintypes.DWORD),
        ('nNumberOfLinks', wintypes.DWORD),
        ('nFileIndexHigh', wintypes.DWORD),
        ('nFileIndexLow', wintypes.DWORD)
    ]

kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
ntdll = ctypes.WinDLL('ntdll', use_last_error=True)
advapi32 = ctypes.WinDLL('advapi32', use_last_error=True)
user32 = ctypes.WinDLL('user32', use_last_error=True)
if ctypes.sizeof(ctypes.c_void_p) == 8:
    ULONG_PTR = ctypes.c_uint64
else:
    ULONG_PTR = ctypes.c_uint32
ULONGLONG = ctypes.c_ulonglong

def enable_debug_privilege():
    h_token = None
    try:
        h_token = wintypes.HANDLE()
        h_process = kernel32.GetCurrentProcess()
        
        if not advapi32.OpenProcessToken(h_process, TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY, ctypes.byref(h_token)):
            return False
        
        luid = LUID()
        if not advapi32.LookupPrivilegeValueW(None, "SeDebugPrivilege", ctypes.byref(luid)):
            return False
        
        tp = TOKEN_PRIVILEGES()
        tp.PrivilegeCount = 1
        tp.Privileges[0].Luid = luid
        tp.Privileges[0].Attributes = 2 
        
        result = advapi32.AdjustTokenPrivileges(
            h_token, False, ctypes.byref(tp), 
            ctypes.sizeof(TOKEN_PRIVILEGES), None, None
        )
        
        error = kernel32.GetLastError()
        return result != 0 and error == 0
        
    except Exception as e:
        logger.error(f"Failed to enable debug privilege: {e}")
        return False
    finally:
        if h_token:
            try:
                kernel32.CloseHandle(h_token)
            except Exception as e:
                logger.debug(f"Failed to close token handle: {e}")

def set_process_affinity_direct(handle, core_list):
    try:
        if not handle or not core_list:
            return False
        
        max_cores = psutil.cpu_count(logical=True)
        if any(core < 0 or core >= max_cores for core in core_list):
            return False
        
        affinity_mask = sum(1 << core for core in core_list)
        result = kernel32.SetProcessAffinityMask(handle, ULONG_PTR(affinity_mask))
        
        if result != 0:
            return True
        else:
            return False
    except Exception as e:
        logger.error(f"Failed to set process affinity: {e}")
        return False

def get_process_affinity_direct(handle):
    try:
        if not handle:
            return None
        
        process_mask = ULONG_PTR()
        system_mask = ULONG_PTR()
        
        if kernel32.GetProcessAffinityMask(handle, ctypes.byref(process_mask), ctypes.byref(system_mask)):
            cores = []
            mask = process_mask.value
            core_idx = 0
            max_cores = psutil.cpu_count(logical=True)
            
            while mask and core_idx < max_cores:
                if mask & 1:
                    cores.append(core_idx)
                mask >>= 1
                core_idx += 1
            
            return cores if cores else None
        
        error_code = kernel32.GetLastError()
        if error_code != 0:
            logger.debug(f"get_process_affinity_direct failed with error code: {error_code}")
        return None
        
    except Exception as e:
        logger.error(f"Failed to get process affinity: {e}")
        return None

def set_page_priority_for_pid(pid, page_priority):
    h_process = None
    try:
        if not isinstance(pid, int) or pid <= 0:
            return False
        if not isinstance(page_priority, int) or not (1 <= page_priority <= 5):
            return False
        
        h_process = kernel32.OpenProcess(PROCESS_SET_INFORMATION | PROCESS_QUERY_INFORMATION, False, pid)
        if not h_process:
            error_code = kernel32.GetLastError()
            if error_code != 5:
                pass
            return False
        
        priority_value = ctypes.c_ulong(page_priority)
        result = ntdll.NtSetInformationProcess(h_process, 39, ctypes.byref(priority_value), ctypes.sizeof(priority_value))
        
        if result == 0:
            return True
        else:
            return False
            
    except Exception as e:
        logger.error(f"Failed to set page priority for pid {pid}: {e}")
        return False
    finally:
        if h_process:
            try:
                kernel32.CloseHandle(h_process)
            except Exception as e:
                logger.debug(f"Failed to close handle for pid {pid}: {e}")

def set_priority_boost(pid, disable_boost):
    h_process = None
    try:
        if not isinstance(pid, int) or pid <= 0:
            return False
        if not isinstance(disable_boost, bool):
            return False
        
        h_process = win32api.OpenProcess(win32con.PROCESS_SET_INFORMATION | win32con.PROCESS_QUERY_INFORMATION, False, pid)
        if not h_process:
            return False
        
        result = kernel32.SetProcessPriorityBoost(int(h_process), wintypes.BOOL(disable_boost))
        
        if result:
            return True
        else:
            return False
            
    except (pywintypes.error, Exception) as e:
        logger.error(f"Failed to set priority boost for pid {pid}: {e}")
        return False
    finally:
        if h_process:
            try:
                win32api.CloseHandle(h_process)
            except Exception as e:
                logger.debug(f"Failed to close handle for pid {pid}: {e}")

def load_config():
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(script_dir, 'config.json')
        if not os.path.exists(config_path):
            return {'whitelist': []}
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return {'whitelist': []}

class PrefetchOptimizer:
    def __init__(self):
        pass
    def optimize_prefetch_for_process(self, pid, exe_path):
        pass

class InterruptAffinityOptimizer:
    def __init__(self, e_cores):
        pass
    def optimize_interrupt_affinity(self):
        pass

class MultiLevelTimerCoalescer:
    def __init__(self):
        pass
    def execute_due_tasks(self):
        pass

class SystemCallBatcher:
    def __init__(self):
        pass

class UnifiedProcessManager:
    def _apply_initial_optimizations(self):
        pass

    def __init__(self):
        self.lock = threading.RLock()
        
        self.cpu_count = psutil.cpu_count(logical=True)
        self.topology = self._query_cpu_topology()
        self.pe_core_sets = self._classify_pe_cores()
        self.core_config = self._build_core_config()
        
        self.affinity_mask_cache = {}
        for key, cores in self.core_config.items():
            mask = sum(1 << c for c in cores)
            self.affinity_mask_cache[tuple(sorted(cores))] = mask
        
        self.process_states = {}
        self.applied_states = {}
        self.minimized_processes = {}
        self.pid_to_job = {}
        self.jobs = {}
        self.foreground_pid = None
        self.whitelist = set()
        self.config_last_modified = 0
        
        self.interned_process_names = {}
        common_names = [
            'chrome.exe', 'firefox.exe', 'msedge.exe', 'explorer.exe',
            'svchost.exe', 'system', 'idle', 'dwm.exe', 'csrss.exe',
            'lsass.exe', 'services.exe', 'winlogon.exe', 'smss.exe'
        ]
        for name in common_names:
            self.interned_process_names[name] = sys.intern(name)
        
        self.timer_coalescer = AdvancedTimerCoalescer(base_resolution_ms=1)
        self._register_coalesced_tasks()
        
        self.handle_cache = ProcessHandleCache(max_cache_size=256, handle_ttl_seconds=30.0)
        
        self.process_snapshot = ProcessSnapshotEngine(cache_ttl_ms=500)
        
        self.settings_applicator = BatchedSettingsApplicator(self.handle_cache)
        
        self.workingset_optimizer = WorkingSetOptimizer(self.handle_cache)
        
        self.foreground_debouncer = ForegroundDebouncer(debounce_time_ms=300, hysteresis_time_ms=150)
        
        self.process_tree = ProcessTreeCache(rebuild_interval_ms=2000)
        
        self.cpu_pinning = CPUPinningEngine(self.handle_cache, self.cpu_count, self.topology)
        
        self.large_page_manager = LargePageManager(self.handle_cache)
        
        self.advanced_ws_trimmer = AdvancedWorkingSetTrimmer(self.handle_cache)
        
        self.prefetch_optimizer = PrefetchOptimizer()
        
        self.memory_priority_manager = MemoryPriorityManager(self.handle_cache)
        
        self.process_service_manager = ProcessServiceManager()
        
        self.cpu_parking_controller = CPUParkingController()
        
        self.heterogeneous_scheduler = HeterogeneousThreadScheduler(
            self.handle_cache, 
            self.pe_core_sets.get('p_cores', []),
            self.pe_core_sets.get('e_cores', [])
        )
        
        self.context_switch_reducer = ContextSwitchReducer()
        
        self.smt_scheduler = SMTScheduler(self.cpu_count)
        
        self.cpu_frequency_scaler = CPUFrequencyScaler()
        
        self.awe_manager = AWEManager(self.handle_cache)
        
        self.interrupt_affinity_optimizer = InterruptAffinityOptimizer(
            self.pe_core_sets.get('e_cores', [])
        )
        
        self.dpc_latency_controller = DPCLatencyController()
        
        self.temp_monitor = CPUTemperatureMonitor()
        
        self.c_states_optimizer = CStatesOptimizer()
        self.storage_optimizer = StorageOptimizer()
        self.network_optimizer = NetworkOptimizer()
        self.power_optimizer = PowerManagementOptimizer()
        self.kernel_optimizer = KernelOptimizer()
        
        self.dynamic_priority_algo = DynamicPriorityAlgorithm(self.handle_cache)
        self.telemetry_collector = RealtimeTelemetryCollector()
        self.profile_manager = AutomaticProfileManager()
        self.numa_allocator = NUMAAwareMemoryAllocator()
        self.huge_pages_manager = DynamicHugePagesManager(self.handle_cache)
        self.memory_dedup_manager = MemoryDeduplicationManager()
        self.realtime_priority_mgr = RealtimePriorityManager(self.handle_cache)
        
        self.readahead_manager = AdaptiveReadAheadManager()
        self.write_coalescer = WriteCoalescingManager()
        self.storage_tier_mgr = StorageTierManager()
        self.disk_cache_tuner = DynamicDiskCacheTuner()
        
        self.network_flow_prioritizer = NetworkFlowPrioritizer()
        self.tcp_congestion_tuner = TCPCongestionControlTuner()
        self.network_interrupt_coalescer = NetworkInterruptCoalescer()
        self.adaptive_polling_mgr = AdaptiveNetworkPollingManager()
        
        self.multilevel_timer_coalescer = MultiLevelTimerCoalescer()
        self.syscall_batcher = SystemCallBatcher()
        self.dvfs_scaler = DynamicVoltageFrequencyScaler()
        
        self._l3_cache_optimizer = None
        self._avx_instruction_optimizer = None
        self._enhanced_smt_optimizer = None
        self._cpu_pipeline_optimizer = None
        self._tsc_synchronizer = None
        self._tlb_optimizer = None
        self._advanced_numa_optimizer = None
        self._memory_scrubbing_optimizer = None
        self._cache_coherency_optimizer = None
        self._memory_bandwidth_manager = None
        
        self._trim_scheduler = None
        self._write_cache_optimizer = None
        self._io_scheduler = None
        self._ncq_optimizer = None
        self._fs_cache_optimizer = None
        self._io_priority_inheritance = None
        self._metadata_optimizer = None
        self._tcp_fast_open = None
        self._network_buffer_tuner = None
        self._bbr_congestion = None
        self._network_polling = None
        self._dns_cache = None
        self._gpu_scheduler = None
        self._pcie_optimizer = None
        self._dx_vulkan_optimizer = None
        
        self._dynamic_multilayer_profiles = None
        self._enhanced_cache_topology = None
        self._advanced_memory_page_priority = None
        self._adaptive_io_scheduler = None
        
        self._advanced_interrupt_dpc = None
        self._adaptive_timer_resolution = None
        self._enhanced_network_stack = None
        self._enhanced_system_responsiveness = None
        
        self._thermal_aware_scheduler = None
        self._process_dependency_analyzer = None
        
        self.hardware_detector = HardwareDetector()
        self.decision_cache = OptimizationDecisionCache(ttl_seconds=300)
        self.integrity_validator = IntegrityValidator(self.handle_cache)
        self.suspension_manager = ProcessSuspensionManager()
        self.responsiveness_controller = SystemResponsivenessController()
        
        self.load_whitelist()
        
        self.ram_monitor_active = True
        self.last_ram_cleanup = 0
        self.ram_cleanup_cooldown = 3600
        self.start_ram_monitor()
        
        self.win_event_hook = None
        self._start_foreground_hook_thread()
        
        self.blacklist_names = {
            'system', 'idle', 'smss.exe', 'csrss.exe', 'wininit.exe', 'winlogon.exe',
            'services.exe', 'lsass.exe', 'svchost.exe', 'fontdrvhost.exe', 'registry',
            'memcompression', 'sihost.exe', 'dwm.exe', 'ctfmon.exe',
            'cmd.exe', 'python.exe', 'pythonw.exe', 'conhost.exe',
            'taskmgr.exe', 'taskhosw.exe', 'runtimebroker.exe'
        }
        self.blacklist_contains = ['\\windows\\', 'defender', 'msmpeng.exe', 'wuauclt.exe', 'tiworker.exe']
        
        self.blacklist_bloom = SimpleBloomFilter(expected_elements=len(self.blacklist_names) * 2)
        for name in self.blacklist_names:
            self.blacklist_bloom.add(name)
        
        self.modules_enabled = {
            'almacenamiento': True,
            'gpu': True,
            'ram': True,
            'kernel': True,
            'cpu': True,
            'prioridades': True,
            'energia': True,
            'temperatura': True,
            'servicios': True,
            'redes': True,
            'perfiles': True,
            'ajustes_varios': True,
        }
        
        self._apply_initial_optimizations()

    def toggle_module(self, name, status):
        with self.lock:
            if name in self.modules_enabled:
                self.modules_enabled[name] = status
    
    @property
    def l3_cache_optimizer(self):
        if self._l3_cache_optimizer is None:
            self._l3_cache_optimizer = L3CacheOptimizer(self.topology)
        return self._l3_cache_optimizer
    
    @property
    def avx_instruction_optimizer(self):
        if self._avx_instruction_optimizer is None:
            self._avx_instruction_optimizer = AVXInstructionOptimizer(self.handle_cache, self.cpu_count)
        return self._avx_instruction_optimizer
    
    @property
    def enhanced_smt_optimizer(self):
        if self._enhanced_smt_optimizer is None:
            self._enhanced_smt_optimizer = EnhancedSMTOptimizer(self.topology, self.cpu_count)
        return self._enhanced_smt_optimizer
    
    @property
    def tlb_optimizer(self):
        if self._tlb_optimizer is None:
            self._tlb_optimizer = TLBOptimizer(self.handle_cache)
        return self._tlb_optimizer
    
    @property
    def advanced_numa_optimizer(self):
        if self._advanced_numa_optimizer is None:
            self._advanced_numa_optimizer = AdvancedNUMAOptimizer(self.handle_cache)
        return self._advanced_numa_optimizer
    
    @property
    def cache_coherency_optimizer(self):
        if self._cache_coherency_optimizer is None:
            self._cache_coherency_optimizer = CacheCoherencyOptimizer()
        return self._cache_coherency_optimizer
    
    @property
    def memory_bandwidth_manager(self):
        if self._memory_bandwidth_manager is None:
            self._memory_bandwidth_manager = MemoryBandwidthManager(self.handle_cache)
        return self._memory_bandwidth_manager
    
    @property
    def io_priority_inheritance(self):
        if self._io_priority_inheritance is None:
            self._io_priority_inheritance = IOPriorityInheritance(self.handle_cache)
        return self._io_priority_inheritance
    
    @property
    def dynamic_multilayer_profiles(self):
        if self._adaptive_io_scheduler is None:
            self._adaptive_io_scheduler = AdaptiveIOScheduler(self.handle_cache)
        return self._adaptive_io_scheduler
    
    @property
    def advanced_interrupt_dpc(self):
        if self._adaptive_timer_resolution is None:
            self._adaptive_timer_resolution = AdaptiveTimerResolutionManager()
        return self._adaptive_timer_resolution
    
    @property
    def enhanced_network_stack(self):
        if self._enhanced_system_responsiveness is None:
            self._enhanced_system_responsiveness = EnhancedSystemResponsivenessOptimizer()
        return self._enhanced_system_responsiveness
    
    @property
    def thermal_aware_scheduler(self):
        if self._process_dependency_analyzer is None:
            self._process_dependency_analyzer = ProcessDependencyAnalyzer(self.handle_cache)
        return self._process_dependency_analyzer
    
    def _intern_process_name(self, name):
        if name in self.interned_process_names:
            return self.interned_process_names[name]
        
        interned = sys.intern(name)
        
        if len(self.interned_process_names) > 500:
            self.interned_process_names = dict(list(self.interned_process_names.items())[:250])
        self.interned_process_names[name] = interned
        return interned
    
    def is_whitelisted(self, pid: int) -> bool:
        try:
            
            if not isinstance(pid, int) or pid <= 0:
                return False
            
            process = psutil.Process(pid)
            if not process.is_running():
                return False
            
            name = self._intern_process_name(process.name().lower())
            exe = ''
            try:
                exe = process.exe().lower()
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                pass
            
            
            if name in self.whitelist:
                return True
            
            
            for w in self.whitelist:
                if w and exe and w in exe:
                    return True
            
            return False
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
        except Exception as e:
            logger.debug(f"Error checking whitelist for pid {pid}: {e}")
            return False
    
    def is_blacklisted(self, pid: int) -> bool:
        try:
            
            if not isinstance(pid, int) or pid <= 0:
                return True
            
            p = psutil.Process(pid)
            if not p.is_running():
                return True
            
            name = self._intern_process_name(p.name().lower())
            
            
            
            if self.blacklist_bloom.contains(name):
                
                if name in self.blacklist_names:
                    return True
            
            
            if not name.endswith('.exe'):
                return True
            
            try:
                username = p.username()
                if username and username.lower().startswith(('nt authority\\', 'local service', 'network service')):
                    return True
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                
                return True
            
            
            
            try:
                if hasattr(p, 'session_id'):
                    session_id = p.session_id() if callable(p.session_id) else None
                    if session_id is not None and session_id == 0:
                        return True
            except (psutil.AccessDenied, psutil.NoSuchProcess, AttributeError):
                logger.debug(f"Could not check session_id for pid {pid}")
            
            try:
                exe = p.exe().lower()
                if any(token in exe for token in self.blacklist_contains):
                    return True
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                pass
                
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return True
        except Exception as e:
            logger.debug(f"Error checking blacklist for pid {pid}: {e}")
            return True
        
        return False
    
    def _start_foreground_hook_thread(self):
        def hook_thread():
            @ctypes.WINFUNCTYPE(None, ctypes.wintypes.HANDLE, ctypes.wintypes.DWORD, ctypes.wintypes.HWND, ctypes.wintypes.LONG, ctypes.wintypes.LONG, ctypes.wintypes.DWORD, ctypes.wintypes.DWORD)
            def callback(hWinEventHook, event, hwnd, idObject, idChild, dwEventThread, dwmsEventTime):
                try:
                    if event == 3 and hwnd:
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                        if pid:
                            self._on_foreground_changed(pid)
                except Exception as e:
                    logger.debug(f"Error in window event hook callback: {e}")
            
            try:
                self.win_event_hook = user32.SetWinEventHook(
                    3, 3, 0,
                    callback, 0, 0, 0
                )
                
                msg = wintypes.MSG()
                while user32.GetMessageW(ctypes.byref(msg), 0, 0, 0) != 0:
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))
            except Exception as e:
                logger.error(f"Failed to set up window event hook: {e}")
                while True:
                    time.sleep(5)
        
        t = threading.Thread(target=hook_thread, name="ForegroundHookThread", daemon=True)
        t.start()
    
    def _on_foreground_changed(self, new_pid):
        try:
            
            if not new_pid or not isinstance(new_pid, int) or new_pid <= 0:
                return
            
            
            if not psutil.pid_exists(new_pid):
                return
            
            is_known = self.is_whitelisted(new_pid)
            self.foreground_debouncer.request_foreground_change(
                new_pid,
                self._apply_foreground_change_internal,
                is_known,
                new_pid
            )
        except Exception as e:
            logger.error(f"Error handling foreground change for pid {new_pid}: {e}")
    
    def _apply_foreground_change_internal(self, new_pid):
        with self.lock:
            try:
                
                if not new_pid or new_pid == self.foreground_pid:
                    return
                
                old_pid = self.foreground_pid
                self.foreground_pid = new_pid
                
                
                if old_pid and old_pid > 0 and psutil.pid_exists(old_pid):
                    try:
                        self.apply_settings_to_process_group(old_pid, False)
                    except Exception as e:
                        logger.error(f"Error applying background settings to old pid {old_pid}: {e}")
                
                
                if new_pid and new_pid > 0 and psutil.pid_exists(new_pid):
                    try:
                        self.apply_settings_to_process_group(new_pid, True)
                    except Exception as e:
                        logger.error(f"Error applying foreground settings to new pid {new_pid}: {e}")
                        
            except Exception as e:
                logger.error(f"Critical error in applying foreground change: {e}")
    
    def get_process_children(self, parent_pid: int) -> List[int]:
        return self.process_tree.get_all_descendants(parent_pid)
    
    def get_processes_by_name(self, process_name: str) -> List[int]:
        return self.process_snapshot.get_process_by_name(process_name)
    
    def _desired_settings_for_role(self, is_foreground: bool, pid: Optional[int] = None) -> tuple:
        cores = self.core_config['foreground'] if is_foreground else self.core_config['background']
        priority = 10 if is_foreground else 4
        io_priority = 2 if is_foreground else 0
        thread_io_priority = 2 if is_foreground else 0
        
        page_priority = 5
        if not is_foreground:
            if pid and pid in self.minimized_processes:
                time_minimized = time.time() - self.minimized_processes[pid]
                if time_minimized > 1800:
                    page_priority = 1
                else:
                    page_priority = 3
            else:
                page_priority = 3
        
        disable_boost = False
        trim_working_set = not is_foreground
        use_eco_qos = not is_foreground
        
        return cores, priority, io_priority, thread_io_priority, page_priority, disable_boost, trim_working_set, use_eco_qos
    
    def _get_applied_state(self, pid: int) -> Dict:
        return self.applied_states.get(pid, {})
    
    def _set_applied_state(self, pid: int, state: Dict) -> None:
        self.applied_states[pid] = state
    
    def apply_all_settings(self, pid: int, is_foreground: bool):
        
        if self.is_whitelisted(pid) or self.is_blacklisted(pid):
            return
        
        cached_decision = self.decision_cache.get(pid, 'settings')
        if cached_decision and cached_decision.get('is_foreground') == is_foreground:
            return
        
        
        gc_was_enabled = gc.isenabled()
        if gc_was_enabled:
            gc.disable()
        
        try:
            if is_foreground:
                if pid in self.minimized_processes:
                    del self.minimized_processes[pid]
                if self.suspension_manager.suspended_processes.get(pid):
                    self.suspension_manager.resume_process(pid)
            elif not is_foreground and pid not in self.minimized_processes:
                self.minimized_processes[pid] = time.time()
            
            try:
                process = psutil.Process(pid)
                process_name = process.name()
                
                self.profile_manager.detect_profile(process_name)
                profile_settings = self.profile_manager.get_profile_settings()
            except Exception as e:
                logger.debug(f"Could not get profile for {process_name}, using Balanced. Error: {e}")
                profile_settings = self.profile_manager.get_profile_settings('Balanced')
            
            cores, desired_prio, desired_io, desired_thread_io, desired_page, desired_disable_boost, trim_ws, use_eco_qos = \
                self._desired_settings_for_role(is_foreground, pid)
            
            prev = self._get_applied_state(pid)
            
            settings_to_apply = {}
            
            if prev.get('cores') != cores:
                settings_to_apply['affinity'] = cores
            
            if prev.get('priority') != desired_prio:
                settings_to_apply['priority'] = desired_prio
            
            if prev.get('io') != desired_io:
                settings_to_apply['io_priority'] = desired_io
            
            if prev.get('thread_io') != desired_thread_io:
                settings_to_apply['thread_io_priority'] = desired_thread_io
            
            if prev.get('page') != desired_page:
                settings_to_apply['page_priority'] = desired_page
            
            if prev.get('disable_boost') != desired_disable_boost:
                settings_to_apply['disable_boost'] = desired_disable_boost
            
            if use_eco_qos and prev.get('eco_qos') != True:
                settings_to_apply['eco_qos'] = True
            
            if trim_ws and not is_foreground:
                try:
                    process = psutil.Process(pid)
                    memory_mb = process.memory_info().rss / (1024 * 1024)
                    
                    self.workingset_optimizer.mark_process_foreground(pid, is_foreground)
                    
                    if self.workingset_optimizer.should_trim_working_set(pid, memory_mb):
                        settings_to_apply['trim_working_set'] = True
                except Exception as e:
                    logger.debug(f"Error checking working set for pid {pid}: {e}")
            else:
                self.workingset_optimizer.mark_process_foreground(pid, is_foreground)
            
            if settings_to_apply:
                result = self.settings_applicator.apply_batched_settings(pid, settings_to_apply)
                
                if result['success']:
                    new_state = prev.copy()
                    new_state.update({
                        'cores': cores,
                        'priority': desired_prio,
                        'io': desired_io,
                        'thread_io': desired_thread_io,
                        'page': desired_page,
                        'disable_boost': desired_disable_boost,
                        'eco_qos': use_eco_qos
                    })
                    self._set_applied_state(pid, new_state)
                    
                    self.decision_cache.set(pid, 'settings', {'is_foreground': is_foreground, 'timestamp': time.time()})
                    
                    if 'priority' in result['applied']:
                        self.integrity_validator.validate_priority(pid, desired_prio)
                    if 'affinity' in result['applied']:
                        self.integrity_validator.validate_affinity(pid, cores)
            
            try:
                self.telemetry_collector.collect_metrics()
                
                if not self.telemetry_collector.should_throttle():
                    self.dynamic_priority_algo.adjust_priority(pid, is_foreground)
            except Exception as e:
                logger.debug(f"Error in telemetry or dynamic priority for pid {pid}: {e}")
            
            if is_foreground:
                try:
                    process = psutil.Process(pid)
                    process_name = process.name()
                    num_threads = process.num_threads()
                    
                    if num_threads <= 2:
                        workload = 'single_thread'
                        is_latency_sensitive = True
                    elif num_threads <= 8:
                        workload = 'latency_sensitive'
                        is_latency_sensitive = True
                    else:
                        workload = 'throughput'
                        is_latency_sensitive = False
                    
                    self.cpu_pinning.apply_intelligent_pinning(pid, cores, workload)
                    
                    self.heterogeneous_scheduler.classify_and_schedule_threads(pid, is_latency_sensitive)
                    
                    if is_latency_sensitive:
                        self.smt_scheduler.assign_to_physical_cores(pid)
                    
                    self.cpu_frequency_scaler.set_turbo_mode(enable=True)
                    
                    if self.large_page_manager.should_enable_large_pages(pid, is_foreground):
                        self.large_page_manager.enable_large_pages_for_process(pid)
                    
                    if self.awe_manager.is_32bit_process(pid):
                        try:
                            process_mem_mb = process.memory_info().rss / (1024 * 1024)
                            if process_mem_mb > 1024:
                                self.awe_manager.enable_awe_for_process(pid)
                        except Exception as e:
                            logger.debug(f"Error enabling AWE for pid {pid}: {e}")
                    
                    minimized_time = 0
                    if pid in self.minimized_processes:
                        minimized_time = time.time() - self.minimized_processes[pid]
                    
                    self.memory_priority_manager.set_memory_priority(pid, 5, is_foreground, minimized_time)
                    
                    try:
                        exe_path = process.exe()
                        self.prefetch_optimizer.optimize_prefetch_for_process(pid, exe_path)
                    except Exception as e:
                        logger.debug(f"Error optimizing prefetch for pid {pid}: {e}")
                    
                    try:
                        self.numa_allocator.optimize_process_numa(pid, cores)
                    except Exception as e:
                        logger.debug(f"Error optimizing NUMA for pid {pid}: {e}")
                    
                    try:
                        self.huge_pages_manager.monitor_process(pid)
                    except Exception as e:
                        logger.debug(f"Error monitoring huge pages for pid {pid}: {e}")
                    
                    try:
                        self.realtime_priority_mgr.monitor_realtime_process(pid, process_name)
                    except Exception as e:
                        logger.debug(f"Error monitoring realtime process for pid {pid}: {e}")
                    
                    try:
                        self.network_flow_prioritizer.prioritize_foreground_traffic(pid)
                    except Exception as e:
                        logger.debug(f"Error prioritizing network flow for pid {pid}: {e}")
                    
                    try:
                        process = psutil.Process(pid)
                        process_name = process.name()
                        
                        if self.l3_cache_optimizer.cache_groups:
                            self.l3_cache_optimizer.optimize_process_cache_locality(pid, is_critical=True, handle_cache=self.handle_cache)
                    except Exception as e:
                        logger.debug(f"Error optimizing L3 cache for pid {pid}: {e}")
                    
                    try:
                        process = psutil.Process(pid)
                        process_name = process.name()
                        
                        if self.avx_instruction_optimizer.detect_avx_usage(pid, process_name):
                            self.avx_instruction_optimizer.optimize_avx_process(pid)
                    except Exception as e:
                        logger.debug(f"Error optimizing AVX for pid {pid}: {e}")
                    
                    try:
                        if num_threads <= 4:
                            self.enhanced_smt_optimizer.optimize_for_latency(pid, self.handle_cache)
                        else:
                            self.enhanced_smt_optimizer.optimize_for_throughput(pid, self.handle_cache)
                    except Exception as e:
                        logger.debug(f"Error optimizing SMT for pid {pid}: {e}")
                    
                    try:
                        self.cpu_pipeline_optimizer.optimize_instruction_ordering(pid, is_critical=True)
                    except Exception as e:
                        logger.debug(f"Error optimizing CPU pipeline for pid {pid}: {e}")
                    
                    try:
                        self.tlb_optimizer.optimize_memory_layout(pid)
                    except Exception as e:
                        logger.debug(f"Error optimizing TLB for pid {pid}: {e}")
                    
                    try:
                        if len(self.advanced_numa_optimizer.numa_nodes) > 1:
                            self.advanced_numa_optimizer.optimize_numa_placement(pid)
                    except Exception as e:
                        logger.debug(f"Error optimizing advanced NUMA for pid {pid}: {e}")
                    
                    try:
                        self.cache_coherency_optimizer.optimize_thread_placement(pid, self.handle_cache)
                    except Exception as e:
                        logger.debug(f"Error optimizing cache coherency for pid {pid}: {e}")
                    
                    try:
                        self.memory_bandwidth_manager.prioritize_foreground_memory_access(pid)
                    except Exception as e:
                        logger.debug(f"Error prioritizing memory bandwidth for pid {pid}: {e}")
                    
                    try:
                        self.io_priority_inheritance.inherit_io_priority(pid, desired_io)
                    except Exception as e:
                        logger.debug(f"Error inheriting I/O priority for pid {pid}: {e}")
                    
                except Exception as e:
                    logger.error(f"Unhandled error in foreground optimization for pid {pid}: {e}")
            else:
                try:
                    minimized_time = 0
                    if pid in self.minimized_processes:
                        minimized_time = time.time() - self.minimized_processes[pid]
                    
                    self.memory_priority_manager.set_memory_priority(pid, 2, is_foreground, minimized_time)
                    
                    self.advanced_ws_trimmer.trim_private_pages(pid)
                    
                    self.heterogeneous_scheduler.classify_and_schedule_threads(pid, is_latency_sensitive=False)
                    
                    try:
                        self.memory_dedup_manager.enable_memory_compression(pid)
                    except Exception as e:
                        logger.debug(f"Error enabling memory deduplication for pid {pid}: {e}")
                    
                    try:
                        self.memory_bandwidth_manager.limit_background_bandwidth(pid)
                    except Exception as e:
                        logger.debug(f"Error limiting background memory bandwidth for pid {pid}: {e}")
                    
                    try:
                        self.io_priority_inheritance.throttle_background_io(pid)
                    except Exception as e:
                        logger.debug(f"Error throttling background I/O for pid {pid}: {e}")
                except Exception as e:
                    logger.error(f"Unhandled error in background optimization for pid {pid}: {e}")
        finally:
            
            if gc_was_enabled:
                gc.enable()
    
    def apply_settings_to_process_group(self, pid, is_foreground):
        
        if not isinstance(pid, int) or pid <= 0:
            logger.debug(f"apply_settings_to_process_group called with invalid pid: {pid}")
            return
        
        
        if not isinstance(is_foreground, bool):
            is_foreground = bool(is_foreground)
        
        try:
            main_process = psutil.Process(pid)
            process_name = main_process.name()
            
            if not process_name.lower().endswith('.exe'):
                return
            
            if self.is_whitelisted(pid) or self.is_blacklisted(pid):
                return
            
            pids_to_set = set()
            pids_to_set.add(pid)
            pids_to_set.update(self.get_process_children(pid))
            
            for p in self.get_processes_by_name(process_name):
                try:
                    if psutil.Process(p).username() == main_process.username():
                        pids_to_set.add(p)
                except Exception:
                    pids_to_set.add(p)
            
            job_key = self._get_job_key(pid)
            job_handle = self._ensure_job_for_group(job_key, is_foreground)
            
            e_cores = self.pe_core_sets.get('e_cores', [])
            
            for target_pid in list(pids_to_set):
                if not psutil.pid_exists(target_pid):
                    continue
                
                if self.is_whitelisted(target_pid) or self.is_blacklisted(target_pid):
                    continue
                
                if job_handle:
                    self._assign_pid_to_job(target_pid, job_handle)
                
                if not is_foreground and e_cores:
                    try:
                        handle = win32api.OpenProcess(PROCESS_SET_INFORMATION | PROCESS_QUERY_INFORMATION, False, target_pid)
                        if handle:
                            try:
                                set_process_affinity_direct(handle, e_cores)
                            finally:
                                win32api.CloseHandle(handle)
                    except Exception as e:
                        logger.debug(f"Could not set background affinity for {target_pid}: {e}")
                
                self.apply_all_settings(target_pid, is_foreground)
        
        except Exception as e:
            logger.error(f"Error applying settings to process group for pid {pid}: {e}")
    
    def _get_job_key(self, pid):
        try:
            p = psutil.Process(pid)
            name = p.name().lower()
            session = p.session_id()
            return (name, session)
        except Exception as e:
            logger.debug(f"Could not create job key for pid {pid}: {e}")
            return (str(pid), 0)
    
    def _ensure_job_for_group(self, job_key, is_foreground):
        job_info = self.jobs.get(job_key)
        if not job_info:
            try:
                hJob = win32job.CreateJobObject(None, f"UPM_JOB_{job_key[0]}_{job_key[1]}")
                self.jobs[job_key] = {'handle': hJob, 'is_foreground': None}
                job_info = self.jobs[job_key]
            except Exception as e:
                logger.error(f"Failed to create job object for key {job_key}: {e}")
                return None
        
        try:
            if job_info['is_foreground'] != is_foreground:
                cpu_usage = psutil.cpu_percent(interval=0.1)
                
                if is_foreground:
                    cpu_rate = 95
                else:
                    if cpu_usage < 30:
                        cpu_rate = 50
                    else:
                        cpu_rate = 25
                
                try:
                    info = win32job.QueryInformationJobObject(job_info['handle'], win32job.JobObjectCpuRateControlInformation)
                    info['ControlFlags'] = 1 | 4
                    info['CpuRate'] = cpu_rate * 100
                    win32job.SetInformationJobObject(job_info['handle'], win32job.JobObjectCpuRateControlInformation, info)
                except Exception:
                    try:
                        data = {
                            'ControlFlags': 1 | 4,
                            'CpuRate': cpu_rate * 100
                        }
                        win32job.SetInformationJobObject(job_info['handle'], win32job.JobObjectCpuRateControlInformation, data)
                    except Exception as e:
                        logger.debug(f"Failed to set CPU rate for job {job_key}: {e}")
                
                job_info['is_foreground'] = is_foreground
        except Exception as e:
            logger.error(f"Error ensuring job for group {job_key}: {e}")
        
        return job_info['handle']
    
    def _assign_pid_to_job(self, pid, job_handle):
        if pid in self.pid_to_job:
            return
        
        try:
            hProc = win32api.OpenProcess(
                win32con.PROCESS_SET_QUOTA | win32con.PROCESS_TERMINATE | 
                win32con.PROCESS_SET_INFORMATION | win32con.PROCESS_QUERY_INFORMATION,
                False, pid
            )
            try:
                win32job.AssignProcessToJobObject(job_handle, hProc)
                self.pid_to_job[pid] = job_handle
            except Exception as e:
                logger.debug(f"Failed to assign pid {pid} to job: {e}")
            finally:
                win32api.CloseHandle(hProc)
        except Exception as e:
            logger.error(f"Failed to open process {pid} to assign to job: {e}")
    
    def get_ram_usage_percent(self):
        try:
            vm = psutil.virtual_memory()
            return vm.percent
        except Exception as e:
            logger.error(f"Failed to get RAM usage: {e}")
            return 0
    
    def get_standby_memory_percent(self):
        try:
            vm = psutil.virtual_memory()
            standby_mb = vm.cached / (1024 * 1024)
            total_mb = vm.total / (1024 * 1024)
            return (standby_mb / total_mb) * 100 if total_mb > 0 else 0
        except Exception as e:
            logger.error(f"Failed to get standby memory: {e}")
            return 0
    
    def clear_ram_cache(self):
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            exe_path = os.path.join(script_dir, 'emptystandbylist.exe')
            if os.path.exists(exe_path):
                subprocess.Popen(exe_path, creationflags=subprocess.CREATE_NO_WINDOW)
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to clear RAM cache: {e}")
            return False
    
    def ram_monitor_worker(self):
        while self.ram_monitor_active:
            try:
                current_time = time.time()
                time_since_cleanup = current_time - self.last_ram_cleanup
                
                if time_since_cleanup >= self.ram_cleanup_cooldown:
                    ram_usage = self.get_ram_usage_percent()
                    standby_percent = self.get_standby_memory_percent()
                    
                    if ram_usage >= 75 and standby_percent >= 40:
                        self.clear_ram_cache()
                        self.last_ram_cleanup = current_time
                        time.sleep(self.ram_cleanup_cooldown)
                    else:
                        time.sleep(60)
                else:
                    remaining_cooldown = self.ram_cleanup_cooldown - time_since_cleanup
                    time.sleep(min(remaining_cooldown, 60))
            except Exception as e:
                logger.error(f"Error in RAM monitor worker: {e}")
                time.sleep(60)
    
    def start_ram_monitor(self):
        try:
            self.ram_monitor_thread = threading.Thread(target=self.ram_monitor_worker, daemon=True, name="RamMonitorThread")
            self.ram_monitor_thread.start()
        except Exception as e:
            logger.error(f"Failed to start RAM monitor: {e}")
    
    def get_foreground_window_pid(self):
        try:
            hwnd = win32gui.GetForegroundWindow()
            if hwnd:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                return pid
        except Exception as e:
            logger.debug(f"Error getting foreground window pid: {e}")
        return None
    
    def clean_zombie_processes(self):
        to_del = []
        for pid in list(self.process_states.keys()):
            try:
                if not psutil.pid_exists(pid):
                    to_del.append(pid)
            except Exception as e:
                logger.debug(f"Error checking if pid {pid} exists: {e}")
                to_del.append(pid)
        
        for pid in to_del:
            try:
                self.process_states.pop(pid, None)
                self.applied_states.pop(pid, None)
                self.pid_to_job.pop(pid, None)
                self.decision_cache.invalidate(pid)
            except Exception as e:
                logger.error(f"Error cleaning up zombie process {pid}: {e}")
    
    def _check_and_suspend_inactive_processes(self):
        current_time = time.time()
        for pid, state in list(self.process_states.items()):
            if self.is_whitelisted(pid) or self.is_blacklisted(pid):
                continue
            
            if not state.get('is_foreground') and pid != self.foreground_pid:
                last_foreground = self.minimized_processes.get(pid, current_time)
                if self.suspension_manager.should_suspend(pid, last_foreground):
                    try:
                        if psutil.pid_exists(pid):
                            self.suspension_manager.suspend_process(pid)
                    except Exception as e:
                        logger.error(f"Error suspending process {pid}: {e}")
    
    def update_all_processes(self):
        ready_tasks = self.timer_coalescer.get_tasks_to_execute()
        
        for task_name, urgency in ready_tasks:
            start_time = time.perf_counter()
            
            try:
                if task_name == 'whitelist_reload':
                    self.load_whitelist()
                
                elif task_name == 'process_cache_update':
                    current_exe_processes = self.process_snapshot.get_process_snapshot()
                
                elif task_name == 'zombie_cleanup':
                    self.clean_zombie_processes()
                
                elif task_name == 'foreground_check':
                    current_foreground_pid = self.get_foreground_window_pid()
                    with self.lock:
                        if current_foreground_pid and current_foreground_pid != self.foreground_pid:
                            self._on_foreground_changed(current_foreground_pid)
                
                elif task_name == 'process_tree_rebuild':
                    self.process_tree.rebuild_tree()
                
                elif task_name == 'handle_cache_cleanup':
                    self.handle_cache.cleanup_stale_handles()
                
                elif task_name == 'cpu_pinning_cleanup':
                    self.cpu_pinning.cleanup_dead_processes()
                
                elif task_name == 'decision_cache_cleanup':
                    self.decision_cache.cleanup_expired()
                
                elif task_name == 'process_suspension_check':
                    self._check_and_suspend_inactive_processes()
            
            except Exception as e:
                logger.error(f"Error executing coalesced task {task_name}: {e}")
            
            end_time = time.perf_counter()
            execution_time_ms = (end_time - start_time) * 1000
            
            self.timer_coalescer.mark_executed(task_name, execution_time_ms)
        
        try:
            current_exe_processes = self.process_snapshot.get_process_snapshot()
            
            with self.lock:
                for pid, info in current_exe_processes.items():
                    if self.is_whitelisted(pid) or self.is_blacklisted(pid):
                        continue
                    
                    if pid not in self.process_states:
                        is_fg = (pid == self.foreground_pid)
                        self.apply_settings_to_process_group(pid, is_fg)
                        self.process_states[pid] = {
                            'name': info['name'],
                            'is_foreground': is_fg,
                            'created_at': time.time()
                        }
                
                for pid in list(self.process_states.keys()):
                    if pid not in current_exe_processes:
                        self.process_states.pop(pid, None)
                        self.applied_states.pop(pid, None)
                        self.pid_to_job.pop(pid, None)
        
        except Exception as e:
            logger.error(f"Error in main process update loop: {e}")
    
    def run(self):
        try:
            self.context_switch_reducer.adjust_quantum_time_slice(increase=True)
            
            self.interrupt_affinity_optimizer.optimize_interrupt_affinity()
            
            self.dpc_latency_controller.optimize_dpc_latency()
            
            self.timer_coalescer.register_task('thermal_check', interval_ms=3000, priority=7)
            
            try:
                self.network_interrupt_coalescer.optimize_interrupt_coalescing()
            except Exception as e:
                logger.warning(f"Could not optimize network interrupt coalescing: {e}")
            
            try:
                self.tcp_congestion_tuner.detect_and_tune()
            except Exception as e:
                logger.warning(f"Could not tune TCP congestion: {e}")
            
            
            gc.disable()
            
            iteration_count = 0
            while True:
                if self.modules_enabled['ajustes_varios']:
                    self.update_all_processes()
                
                if self.modules_enabled['temperatura'] and self.temp_monitor.monitoring_active:
                    self.manage_thermal_throttling()
                
                iteration_count += 1
                
                if self.modules_enabled['redes'] and iteration_count % 10 == 0:
                    try:
                        self.adaptive_polling_mgr.adjust_polling_mode()
                    except Exception as e:
                        logger.debug(f"Error adjusting network polling: {e}")
                
                if self.modules_enabled['almacenamiento'] and iteration_count % 20 == 0:
                    try:
                        self.disk_cache_tuner.tune_cache()
                    except Exception as e:
                        logger.debug(f"Error tuning disk cache: {e}")
                    
                    try:
                        self.multilevel_timer_coalescer.execute_due_tasks()
                    except Exception as e:
                        logger.debug(f"Error executing multi-level timer tasks: {e}")
                
                if self.modules_enabled['redes'] and iteration_count % 30 == 0:
                    try:
                        self.tcp_congestion_tuner.detect_and_tune()
                    except Exception as e:
                        logger.debug(f"Error tuning TCP congestion: {e}")
                
                if self.modules_enabled['ram'] and iteration_count % 50 == 0:
                    try:
                        self.memory_scrubbing_optimizer.schedule_scrubbing_low_load()
                    except Exception as e:
                        logger.debug(f"Error scheduling memory scrubbing: {e}")
                
                if iteration_count % 100 == 0:
                    try:
                        cpu_percent = psutil.cpu_percent(interval=0.1)
                        if cpu_percent < 30:
                            gc.collect(generation=0)
                    except Exception as e:
                        logger.debug(f"Error during periodic garbage collection: {e}")
                
                if self.modules_enabled['almacenamiento'] and iteration_count % 100 == 0:
                    try:
                        self.trim_scheduler.execute_trim()
                    except Exception as e:
                        logger.debug(f"Error executing TRIM scheduler: {e}")
                
                sleep_time = self.timer_coalescer.get_next_wake_time()
                time.sleep(sleep_time)
        
        except Exception as e:
            logger.critical(f"Main loop crashed: {e}")
        finally:
            self.handle_cache.close_all()
            self.timer_coalescer._deactivate_high_resolution_timer()
            self.temp_monitor.cleanup()

def main() -> None:
    pass

if __name__ == "__main__":
    main()
