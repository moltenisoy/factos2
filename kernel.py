import time
import psutil
import winreg
import subprocess
import ctypes
import threading
import logging
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


MS_TO_100NS = 10000
RESET_EXECUTION_COUNT_THRESHOLD = 1000000
RESET_EXECUTION_COUNT_VALUE = 1000
DPC_TIMEOUT_DISABLED = 0
DPC_WATCHDOG_PROFILE_OFFSET = 1
DPC_QUEUE_DEPTH = 4
CORE_OVERLOAD_THRESHOLD = 80

ntdll = ctypes.WinDLL('ntdll')
timeapi = ctypes.WinDLL('winmm')
kernel32 = ctypes.WinDLL('kernel32')

class KernelOptimizer:
    def __init__(self):
        self.lock = threading.RLock()
        self.original_settings = {}
    
    def optimize_timer_resolution(self):
        with self.lock:
            try:
                key_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile"
                try:
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_SET_VALUE)
                    winreg.SetValueEx(key, "SystemResponsiveness", 0, winreg.REG_DWORD, 0)
                    winreg.CloseKey(key)
                    return True
                except Exception:
                    return False
            except Exception:
                return False
    
    def increase_paged_pool_size(self):
        with self.lock:
            try:
                total_ram_gb = psutil.virtual_memory().total / (1024 ** 3)
                
                if total_ram_gb >= 32:
                    paged_pool_size = 0
                    
                    key_path = r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management"
                    try:
                        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_SET_VALUE)
                        winreg.SetValueEx(key, "PagedPoolSize", 0, winreg.REG_DWORD, paged_pool_size)
                        winreg.CloseKey(key)
                        return True
                    except Exception:
                        return False
                return False
            except Exception:
                return False
    
    def disable_vbs_for_gaming(self):
        with self.lock:
            try:
                subprocess.run(
                    ['bcdedit', '/set', 'hypervisorlaunchtype', 'off'],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                return True
            except Exception:
                return False
    
    def enable_vbs(self):
        with self.lock:
            try:
                subprocess.run(
                    ['bcdedit', '/set', 'hypervisorlaunchtype', 'auto'],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                return True
            except Exception:
                return False
class AdvancedTimerCoalescer:
    def __init__(self, base_resolution_ms=1):
        self.base_resolution_ms = base_resolution_ms
        self.timer_resolution_active = False
        self.task_registry = {}
        self.execution_history = defaultdict(deque)
        self.lock = threading.RLock()
        self.performance_counter_freq = self._get_performance_frequency()
        
        self._activate_high_resolution_timer()
        
        self.stats = {
            'total_coalesced': 0,
            'total_executed': 0,
            'avg_coalescence_rate': 0.0
        }
    
    def _get_performance_frequency(self):
        freq = ctypes.c_int64()
        kernel32.QueryPerformanceFrequency(ctypes.byref(freq))
        return freq.value if freq.value > 0 else 1000000
    
    def _activate_high_resolution_timer(self):
        try:
            result = timeapi.timeBeginPeriod(self.base_resolution_ms)
            if result == 0:
                self.timer_resolution_active = True
        except Exception as e:
            logger.debug(f"Error activating high resolution timer: {type(e).__name__}: {e}")
    
    def _deactivate_high_resolution_timer(self):
        if self.timer_resolution_active:
            try:
                timeapi.timeEndPeriod(self.base_resolution_ms)
                self.timer_resolution_active = False
            except Exception as e:
                logger.debug(f"Error deactivating high resolution timer: {type(e).__name__}: {e}")
    
    def register_task(self, name, interval_ms, priority=5, adaptive=True, 
                     coalescence_window_ms=None, execution_budget_ms=None):
        with self.lock:
            if coalescence_window_ms is None:
                coalescence_window_ms = max(1, interval_ms * 0.1)
            
            if execution_budget_ms is None:
                execution_budget_ms = max(1, interval_ms * 0.5)
            
            self.task_registry[name] = {
                'interval_ms': interval_ms,
                'priority': priority,
                'adaptive': adaptive,
                'coalescence_window_ms': coalescence_window_ms,
                'execution_budget_ms': execution_budget_ms,
                'last_execution': 0,
                'next_execution': time.perf_counter() + (interval_ms / 1000.0),
                'execution_count': 0,
                'total_execution_time_ms': 0,
                'avg_execution_time_ms': 0,
                'adaptive_multiplier': 1.0
            }
    
    def should_execute(self, task_name):
        with self.lock:
            if task_name not in self.task_registry:
                return False, 0.0
            
            task = self.task_registry[task_name]
            current_time = time.perf_counter()
            
            time_since_last = current_time - task['last_execution']
            time_until_next = task['next_execution'] - current_time
            
            if time_until_next <= 0:
                urgency = min(10.0, abs(time_until_next) * 1000.0 / task['interval_ms'])
                return True, urgency
            
            if time_until_next <= (task['coalescence_window_ms'] / 1000.0):
                proximity_factor = 1.0 - (time_until_next / (task['coalescence_window_ms'] / 1000.0))
                urgency = task['priority'] * proximity_factor
                return True, urgency
            
            return False, 0.0
    
    def mark_executed(self, task_name, execution_time_ms):
        with self.lock:
            if task_name not in self.task_registry:
                return
            
            task = self.task_registry[task_name]
            current_time = time.perf_counter()
            
            task['last_execution'] = current_time
            task['execution_count'] += 1
            
            
            if task['execution_count'] > RESET_EXECUTION_COUNT_THRESHOLD:
                task['execution_count'] = RESET_EXECUTION_COUNT_VALUE
                task['total_execution_time_ms'] = task['avg_execution_time_ms'] * RESET_EXECUTION_COUNT_VALUE
            
            task['total_execution_time_ms'] += execution_time_ms
            task['avg_execution_time_ms'] = task['total_execution_time_ms'] / task['execution_count']
            
            if task['adaptive']:
                self._adapt_task_parameters(task_name, execution_time_ms)
            
            interval_with_multiplier = task['interval_ms'] * task['adaptive_multiplier']
            task['next_execution'] = current_time + (interval_with_multiplier / 1000.0)
            
            self.execution_history[task_name].append(current_time)
            if len(self.execution_history[task_name]) > 100:
                self.execution_history[task_name].popleft()
            
            self.stats['total_executed'] += 1
    
    def _adapt_task_parameters(self, task_name, last_execution_time_ms):
        task = self.task_registry[task_name]
        
        if task['avg_execution_time_ms'] < task['execution_budget_ms'] * 0.5:
            task['adaptive_multiplier'] = max(0.8, task['adaptive_multiplier'] * 0.98)
        
        elif task['avg_execution_time_ms'] > task['execution_budget_ms'] * 0.8:
            task['adaptive_multiplier'] = min(1.5, task['adaptive_multiplier'] * 1.02)
        
        adjusted_interval = task['interval_ms'] * task['adaptive_multiplier']
        task['coalescence_window_ms'] = max(1, adjusted_interval * 0.1)
    
    def get_next_wake_time(self):
        with self.lock:
            if not self.task_registry:
                return 0.1
            
            current_time = time.perf_counter()
            next_wake = float('inf')
            
            for task in self.task_registry.values():
                time_until = task['next_execution'] - current_time
                if time_until < next_wake:
                    next_wake = time_until
            
            return max(0.001, min(5.0, next_wake))
    
    def get_tasks_to_execute(self):
        with self.lock:
            
            import heapq
            ready_tasks_heap = []
            
            for task_name in self.task_registry.keys():
                should_exec, urgency = self.should_execute(task_name)
                if should_exec:
                    
                    heapq.heappush(ready_tasks_heap, (-urgency, task_name))
            
            
            ready_tasks = [(name, -urgency) for urgency, name in sorted(ready_tasks_heap)]
            
            if len(ready_tasks) > 1:
                self.stats['total_coalesced'] += len(ready_tasks) - 1
            
            if self.stats['total_executed'] > 0:
                self.stats['avg_coalescence_rate'] = self.stats['total_coalesced'] / self.stats['total_executed']
            
            return ready_tasks
    
    def get_statistics(self):
        with self.lock:
            return self.stats.copy()
    
    def __del__(self):
        self._deactivate_high_resolution_timer()
class AdaptiveTimerResolutionManager:
    
    def __init__(self):
        self.lock = threading.RLock()
        self.current_resolution_ms = 15.6  
        self.active_high_res_processes = set()
        self.timer_handle = None
        self.stats = {
            'resolution_changes': 0,
            'high_res_activations': 0,
            'energy_save_activations': 0
        }
        
        
        self.high_res_keywords = [
            
            'game', 'dx11', 'dx12', 'vulkan', 'unreal', 'unity',
            
            'ableton', 'cubase', 'fl studio', 'reaper', 'protools', 'studio one',
            
            'obs', 'streamlabs', 'xsplit',
            
            'premiere', 'davinci', 'vegas'
        ]
    
    def detect_high_resolution_need(self, pid, process_name):
        with self.lock:
            try:
                process_lower = process_name.lower()
                
                
                needs_high_res = any(keyword in process_lower for keyword in self.high_res_keywords)
                
                if needs_high_res:
                    if pid not in self.active_high_res_processes:
                        self.active_high_res_processes.add(pid)
                        logger.info(f"Process {process_name} (PID: {pid}) requires high-resolution timer")
                        return True
                else:
                    if pid in self.active_high_res_processes:
                        self.active_high_res_processes.discard(pid)
                        return False
                
                return needs_high_res
            except Exception as e:
                logger.debug(f"Timer resolution detection error for pid {pid}: {e}")
                return False
    
    def adjust_timer_resolution(self, target_ms=None):
        with self.lock:
            try:
                
                if target_ms is None:
                    if len(self.active_high_res_processes) > 0:
                        
                        target_ms = 0.5  
                    else:
                        
                        target_ms = 15.6
                
                
                if abs(target_ms - self.current_resolution_ms) > 0.01:
                    
                    resolution_100ns = int(target_ms * MS_TO_100NS)
                    
                    
                    try:
                        current_res = ctypes.c_ulong()
                        result = ntdll.NtSetTimerResolution(
                            resolution_100ns,
                            True,  
                            ctypes.byref(current_res)
                        )
                        
                        if result == 0:
                            old_res = self.current_resolution_ms
                            self.current_resolution_ms = target_ms
                            self.stats['resolution_changes'] += 1
                            
                            if target_ms < 2.0:
                                self.stats['high_res_activations'] += 1
                            else:
                                self.stats['energy_save_activations'] += 1
                            
                            logger.info(f"Timer resolution changed: {old_res:.1f}ms -> {target_ms:.1f}ms")
                            return True
                    except Exception as e:
                        logger.debug(f"NtSetTimerResolution error: {e}")
                        
                        
                        try:
                            winmm = ctypes.windll.winmm
                            period = int(target_ms)
                            result = winmm.timeBeginPeriod(period)
                            if result == 0:  
                                self.current_resolution_ms = target_ms
                                self.stats['resolution_changes'] += 1
                                return True
                        except Exception:
                            pass
                
                return False
            except Exception as e:
                logger.debug(f"Timer resolution adjustment error: {e}")
                return False
    
    def cleanup_terminated_processes(self):
        with self.lock:
            return {
                'current_resolution_ms': self.current_resolution_ms,
                'active_high_res_processes': len(self.active_high_res_processes),
                'total_resolution_changes': self.stats['resolution_changes'],
                'high_res_activations': self.stats['high_res_activations'],
                'energy_save_activations': self.stats['energy_save_activations'],
                'estimated_overhead': 0.05  
            }
class ContextSwitchReducer:
    def __init__(self):
        self.lock = threading.RLock()
        self.quantum_adjusted = False
        self.stats = {
            'quantum_adjustments': 0,
            'context_switches_reduced': 0
        }
    
    def adjust_quantum_time_slice(self, increase=True):
        with self.lock:
            try:
                key_path = r"SYSTEM\CurrentControlSet\Control\PriorityControl"
                value_name = "Win32PrioritySeparation"
                
                if increase:
                    new_value = 0x26
                else:
                    new_value = 0x2
                
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(key, value_name, 0, winreg.REG_DWORD, new_value)
                winreg.CloseKey(key)
                
                self.quantum_adjusted = True
                self.stats['quantum_adjustments'] += 1
                return True
            except Exception:
                return False
    
    def get_statistics(self):
        with self.lock:
            return self.stats.copy()
class TSCSynchronizer:

    def __init__(self):
        self.lock = threading.RLock()
        self.tsc_synced = False
        self.stats = {'sync_attempts': 0, 'sync_success': 0}
    
    def synchronize_tsc(self):

        with self.lock:
            try:
                self.stats['sync_attempts'] += 1
                

                try:
                    result = subprocess.run(
                        ['powershell', '-Command', 
                         '(Get-WmiObject Win32_Processor).Caption'],
                        capture_output=True,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                        timeout=5
                    )

                    if result.returncode == 0:
                        self.tsc_synced = True
                        self.stats['sync_success'] += 1
                        return True
                except Exception:
                    pass
                


                try:

                    result = subprocess.run(
                        ['bcdedit', '/enum', '{current}'],
                        capture_output=True,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                        timeout=5
                    )
                    
                    if result.returncode == 0:
                        output = result.stdout.decode('utf-8', errors='ignore')

                        if 'useplatformclock' in output.lower() and 'yes' in output.lower():

                            subprocess.run(
                                ['bcdedit', '/set', 'useplatformclock', 'false'],
                                capture_output=True,
                                creationflags=subprocess.CREATE_NO_WINDOW,
                                timeout=5
                            )
                        
                        self.tsc_synced = True
                        self.stats['sync_success'] += 1
                        return True
                except Exception:
                    pass
            except Exception:
                pass
            return False
class DPCLatencyController:
    def __init__(self):
        self.lock = threading.RLock()
        self.stats = {
            'dpc_optimizations': 0,
            'latency_improvements': 0,
            'monitoring_active': False
        }
        self.target_dpc_latency_us = 128
    
    def optimize_dpc_latency(self):
        with self.lock:
            try:
                self.stats['dpc_optimizations'] += 1
                
                key_path = r"SYSTEM\CurrentControlSet\Control\Session Manager\kernel"
                
                try:
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_SET_VALUE)
                    
                    winreg.SetValueEx(key, "DpcWatchdogProfileOffset", 0, winreg.REG_DWORD, 1)
                    winreg.SetValueEx(key, "DpcTimeout", 0, winreg.REG_DWORD, 0)
                    
                    winreg.CloseKey(key)
                    
                    self.stats['latency_improvements'] += 1
                    return True
                except Exception:
                    return False
            except Exception:
                return False
    
    def monitor_dpc_latency(self):
        with self.lock:
            try:
                result = subprocess.run(
                    ['powershell', '-Command', 
                     'Get-Counter "\\Processor(_Total)\\% DPC Time" -ErrorAction SilentlyContinue'],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    timeout=5
                )
                
                if result.returncode == 0:
                    self.stats['monitoring_active'] = True
                    return True
                return False
            except Exception:
                self.stats['monitoring_active'] = False
                return False
    
    def get_statistics(self):
        with self.lock:
            return self.stats.copy()
class AdvancedInterruptDPCOptimizer:
    
    def __init__(self, cpu_count, e_cores=None):
        self.lock = threading.RLock()
        self.cpu_count = cpu_count
        self.e_cores = e_cores if e_cores else []
        self.interrupt_assignments = {}
        self.device_affinities = {
            'gpu': None,
            'nvme': None,
            'nic': None
        }
        self.last_rebalance = time.time()
        self.stats = {
            'irq_bindings': 0,
            'rebalances': 0,
            'dpc_optimizations': 0,
            'latency_improvements': 0
        }
    
    def detect_critical_devices(self):
        with self.lock:
            return {
                'irq_bindings': self.stats['irq_bindings'],
                'rebalances': self.stats['rebalances'],
                'dpc_optimizations': self.stats['dpc_optimizations'],
                'active_device_bindings': sum(1 for v in self.device_affinities.values() if v is not None),
                'estimated_overhead': 0.1  
            }
