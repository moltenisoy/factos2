import time
import psutil
import win32process
import winreg
import threading
import logging

logger = logging.getLogger(__name__)


PRIORITY_CLASSES = {
    'IDLE': win32process.IDLE_PRIORITY_CLASS,
    'BELOW_NORMAL': win32process.BELOW_NORMAL_PRIORITY_CLASS,
    'NORMAL': win32process.NORMAL_PRIORITY_CLASS,
    'ABOVE_NORMAL': win32process.ABOVE_NORMAL_PRIORITY_CLASS,
    'HIGH': win32process.HIGH_PRIORITY_CLASS,
    'REALTIME': win32process.REALTIME_PRIORITY_CLASS
}
PROCESS_SET_INFORMATION = 0x0200
SystemResponsivenessKey = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile"

class DynamicPriorityAlgorithm:
    def __init__(self, handle_cache):
        self.handle_cache = handle_cache
        self.lock = threading.RLock()
        self.process_metrics = {}
        self.stats = {'priority_adjustments': 0, 'processes_analyzed': 0}
    
    def analyze_process(self, pid):
        with self.lock:
            try:
                proc = psutil.Process(pid)
                cpu_percent = proc.cpu_percent(interval=0.1)
                io_counters = proc.io_counters()
                memory_info = proc.memory_info()
                num_threads = proc.num_threads()
                create_time = proc.create_time()
                
                current_time = time.time()
                execution_time = current_time - create_time
                
                io_rate = (io_counters.read_bytes + io_counters.write_bytes) / max(execution_time, 1)
                
                children = proc.children(recursive=True)
                num_dependencies = len(children)
                
                score = self._calculate_priority_score(
                    cpu_percent, io_rate, memory_info.rss, 
                    execution_time, num_threads, num_dependencies
                )
                
                self.process_metrics[pid] = {
                    'score': score,
                    'cpu': cpu_percent,
                    'io_rate': io_rate,
                    'memory': memory_info.rss,
                    'execution_time': execution_time,
                    'threads': num_threads,
                    'dependencies': num_dependencies,
                    'last_update': current_time
                }
                
                self.stats['processes_analyzed'] += 1
                return score
            except Exception:
                return 50
    
    def _calculate_priority_score(self, cpu, io_rate, memory, exec_time, threads, deps):
        cpu_score = min(cpu / 100.0 * 30, 30)
        io_score = min((io_rate / (1024 * 1024 * 100)) * 20, 20)
        mem_score = min((memory / (1024 * 1024 * 1024)) * 15, 15)
        time_score = min((exec_time / 3600) * 10, 10)
        thread_score = min((threads / 50) * 15, 15)
        dep_score = min((deps / 10) * 10, 10)
        
        total_score = cpu_score + io_score + mem_score + time_score + thread_score + dep_score
        return min(max(total_score, 0), 100)
    
    def adjust_priority(self, pid, is_foreground):
        with self.lock:
            try:
                score = self.analyze_process(pid)
                
                if is_foreground:
                    if score > 70:
                        priority_class = PRIORITY_CLASSES['HIGH']
                    elif score > 40:
                        priority_class = PRIORITY_CLASSES['ABOVE_NORMAL']
                    else:
                        priority_class = PRIORITY_CLASSES['NORMAL']
                else:
                    if score > 70:
                        priority_class = PRIORITY_CLASSES['NORMAL']
                    elif score > 40:
                        priority_class = PRIORITY_CLASSES['BELOW_NORMAL']
                    else:
                        priority_class = PRIORITY_CLASSES['IDLE']
                
                handle = self.handle_cache.get_handle(pid, PROCESS_SET_INFORMATION)
                if handle:
                    win32process.SetPriorityClass(int(handle), priority_class)
                    self.stats['priority_adjustments'] += 1
                    return True
            except Exception:
                pass
            return False
class RealtimePriorityManager:
    GLITCH_DETECTION_THRESHOLD = 0.001
    GLITCH_COUNT_THRESHOLD = 3
    
    def __init__(self, handle_cache):
        self.handle_cache = handle_cache
        self.lock = threading.RLock()
        self.monitored_processes = {}
        self.stats = {'adjustments': 0, 'glitches_detected': 0}
    
    def monitor_realtime_process(self, pid, process_name):
        with self.lock:
            try:
                process_name_lower = process_name.lower()
                is_audio = any(x in process_name_lower for x in ['audio', 'sound', 'music', 'spotify', 'discord'])
                is_video = any(x in process_name_lower for x in ['video', 'stream', 'obs', 'zoom', 'teams'])
                is_game = any(x in process_name_lower for x in ['game', 'dx11', 'dx12', 'vulkan'])
                
                if is_audio or is_video or is_game:
                    proc = psutil.Process(pid)
                    cpu_times = proc.cpu_times()
                    
                    if pid not in self.monitored_processes:
                        self.monitored_processes[pid] = {
                            'last_cpu_time': cpu_times.user + cpu_times.system,
                            'glitch_count': 0,
                            'type': 'audio' if is_audio else 'video' if is_video else 'game'
                        }
                    else:
                        data = self.monitored_processes[pid]
                        current_cpu_time = cpu_times.user + cpu_times.system
                        cpu_delta = current_cpu_time - data['last_cpu_time']
                        
                        if cpu_delta < self.GLITCH_DETECTION_THRESHOLD and data['type'] in ['audio', 'video']:
                            data['glitch_count'] += 1
                            self.stats['glitches_detected'] += 1
                            
                            if data['glitch_count'] > self.GLITCH_COUNT_THRESHOLD:
                                self._boost_priority(pid)
                        else:
                            data['glitch_count'] = max(0, data['glitch_count'] - 1)
                        
                        data['last_cpu_time'] = current_cpu_time
            except Exception:
                pass
    
    def _boost_priority(self, pid):
        with self.lock:
            try:
                handle = self.handle_cache.get_handle(pid, PROCESS_SET_INFORMATION)
                if handle:
                    win32process.SetPriorityClass(int(handle), PRIORITY_CLASSES['HIGH'])
                    self.stats['adjustments'] += 1
                    return True
            except Exception:
                pass
            return False
class SystemResponsivenessController:
    def __init__(self):
        self.lock = threading.RLock()
        self.current_value = 20
    
    def set_responsiveness(self, value):
        with self.lock:
            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, SystemResponsivenessKey, 0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(key, "SystemResponsiveness", 0, winreg.REG_DWORD, value)
                winreg.CloseKey(key)
                self.current_value = value
                return True
            except Exception as e:
                logger.debug(f"Error setting system responsiveness to {value}: {type(e).__name__}: {e}")
            return False
    
    def set_for_performance(self):
        return self.set_responsiveness(0)
    
    def set_for_balanced(self):
        return self.set_responsiveness(20)
    
    def set_for_background(self):
        return self.set_responsiveness(40)
