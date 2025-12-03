import time
import psutil
import subprocess
import threading
import logging
from collections import defaultdict, deque
import ctypes

logger = logging.getLogger(__name__)

if ctypes.sizeof(ctypes.c_void_p) == 8:
    ULONG_PTR = ctypes.c_uint64
else:
    ULONG_PTR = ctypes.c_uint32

PROCESS_SET_INFORMATION = 0x0200
PROCESS_QUERY_INFORMATION = 0x0400

TEMP_DELTA_PER_LOAD = 15
TEMP_CENTERING_OFFSET = 7.5

try:
    import clr
    clr.AddReference('LibreHardwareMonitorLib.dll')
    from LibreHardwareMonitor import Hardware
    TEMP_MONITORING_AVAILABLE = True
except Exception:
    TEMP_MONITORING_AVAILABLE = False
    
kernel32 = None
ntdll = None

class CPUTemperatureMonitor:

    MIN_TEMP_FALLBACK = 35.0
    MAX_TEMP_FALLBACK = 75.0
    
    def __init__(self):
        self.lock = threading.RLock()
        self.current_temp = 0.0
        self.is_laptop = self._is_laptop()
        self.max_temp_desktop = 70
        self.max_temp_laptop = 78
        self.max_temp = self.max_temp_laptop if self.is_laptop else self.max_temp_desktop
        self.monitoring_active = False
        self.hardware_monitor = None
        self.cpu_sensor = None

        self.temp_range = self.MAX_TEMP_FALLBACK - self.MIN_TEMP_FALLBACK
        
        if TEMP_MONITORING_AVAILABLE:
            self._init_hardware_monitor()
    
    def _is_laptop(self):
        try:
            battery = psutil.sensors_battery()
            return battery is not None
        except Exception:
            try:
                result = subprocess.run(
                    ['powershell', '-Command', 
                     '(Get-WmiObject -Class Win32_SystemEnclosure).ChassisTypes'],
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    timeout=5
                )
                if result.returncode == 0:
                    chassis_types = result.stdout.strip()
                    laptop_types = ['8', '9', '10', '11', '12', '14', '18', '21', '30', '31']
                    for lt in laptop_types:
                        if lt in chassis_types:
                            return True
            except Exception:
                pass
        return False
    
    def _init_hardware_monitor(self):
        try:
            computer = Hardware.Computer()
            computer.IsCpuEnabled = True
            computer.Open()
            self.hardware_monitor = computer
            
            for hardware in computer.Hardware:
                if hardware.HardwareType == Hardware.HardwareType.Cpu:
                    hardware.Update()
                    for sensor in hardware.Sensors:
                        if sensor.SensorType == Hardware.SensorType.Temperature:
                            if 'Package' in sensor.Name or 'Core Average' in sensor.Name:
                                self.cpu_sensor = (hardware, sensor)
                                self.monitoring_active = True
                                break
                    if self.cpu_sensor:
                        break
        except Exception:
            self.monitoring_active = False
    
    def _calculate_temp_from_cpu_usage(self):
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            return self.MIN_TEMP_FALLBACK + (cpu_percent / 100.0 * self.temp_range)
        except Exception:
            return 45.0
    
    def get_current_temperature(self):
        with self.lock:
            if not self.monitoring_active or not self.cpu_sensor:
                self.current_temp = self._calculate_temp_from_cpu_usage()
                return self.current_temp
            
            try:
                hardware, sensor = self.cpu_sensor
                hardware.Update()
                if sensor.Value:
                    self.current_temp = float(sensor.Value)
                return self.current_temp
            except Exception:
                if self.current_temp == 0.0:
                    self.current_temp = self._calculate_temp_from_cpu_usage()
                return self.current_temp
    
    def is_overheating(self):
        temp = self.get_current_temperature()
        return temp >= self.max_temp
    
    def set_max_temperature(self, temp):
        with self.lock:
            self.max_temp = max(50, min(100, temp))
    
    def increase_max_temp(self):
        with self.lock:
            self.max_temp = min(100, self.max_temp + 1)
    
    def decrease_max_temp(self):
        with self.lock:
            self.max_temp = max(50, self.max_temp - 1)
    
    def cleanup(self):
        with self.lock:
            if self.hardware_monitor:
                try:
                    self.hardware_monitor.Close()
                except Exception:
                    pass
class ThermalAwareScheduler:
    
    def __init__(self, cpu_count, temp_monitor):
        self.lock = threading.RLock()
        self.cpu_count = cpu_count
        self.temp_monitor = temp_monitor
        self.per_core_temps = {}
        self.core_load_history = defaultdict(lambda: deque(maxlen=10))
        self.last_migration = {}
        self.last_rotation = time.time()
        self.stats = {
            'migrations': 0,
            'rotations': 0,
            'throttle_preventions': 0
        }
        
        
        self.hot_threshold = 75  
        self.cool_threshold = 60  
        self.critical_threshold = 85  
    
    def get_per_core_temperatures(self):
        with self.lock:
            try:
                
                base_temp = self.temp_monitor.get_current_temperature()
                
                
                per_core_percent = psutil.cpu_percent(interval=0.1, percpu=True)
                
                
                for core_idx, load_percent in enumerate(per_core_percent):
                    
                    temp_delta = (load_percent / 100.0) * TEMP_DELTA_PER_LOAD
                    estimated_temp = base_temp + temp_delta - TEMP_CENTERING_OFFSET  
                    self.per_core_temps[core_idx] = max(30, min(100, estimated_temp))
                    
                    
                    self.core_load_history[core_idx].append(load_percent)
                
                return self.per_core_temps.copy()
            except Exception as e:
                logger.debug(f"Per-core temperature estimation error: {e}")
                
                return {i: base_temp for i in range(self.cpu_count)} if 'base_temp' in locals() else {}
    
    def find_coolest_cores(self, count=4):
        with self.lock:
            temps = self.get_per_core_temperatures()
            hot_cores = [
                core_idx for core_idx, temp in temps.items()
                if temp >= self.hot_threshold
            ]
            return hot_cores
    
    def migrate_process_to_cooler_cores(self, pid, handle_cache):
        with self.lock:
            try:
                current_time = time.time()
                
                
                if pid in self.last_migration:
                    if current_time - self.last_migration[pid] < 30:
                        return False
                
                
                coolest_cores = self.find_coolest_cores(count=4)
                
                if not coolest_cores:
                    return False
                
                
                handle = handle_cache.get_handle(pid, PROCESS_SET_INFORMATION | PROCESS_QUERY_INFORMATION)
                if handle:
                    affinity_mask = sum(1 << core for core in coolest_cores)
                    result = kernel32.SetProcessAffinityMask(handle, ULONG_PTR(affinity_mask))
                    
                    if result:
                        self.last_migration[pid] = current_time
                        self.stats['migrations'] += 1
                        logger.info(f"Process {pid} migrated to cooler cores: {coolest_cores}")
                        return True
            except Exception as e:
                logger.debug(f"Process migration error for PID {pid}: {e}")
            return False
    
    def rotate_loads_for_heat_distribution(self, active_pids, handle_cache):
        with self.lock:
            try:
                current_time = time.time()
                
                
                if current_time - self.last_rotation < 60:
                    return False
                
                self.last_rotation = current_time
                
                
                cores_per_group = max(2, self.cpu_count // 4)
                groups = []
                for i in range(0, self.cpu_count, cores_per_group):
                    groups.append(list(range(i, min(i + cores_per_group, self.cpu_count))))
                
                
                for idx, pid in enumerate(active_pids[:len(groups)]):
                    try:
                        group_idx = idx % len(groups)
                        cores = groups[group_idx]
                        
                        handle = handle_cache.get_handle(pid, PROCESS_SET_INFORMATION)
                        if handle:
                            affinity_mask = sum(1 << core for core in cores)
                            kernel32.SetProcessAffinityMask(handle, ULONG_PTR(affinity_mask))
                    except Exception:
                        pass
                
                self.stats['rotations'] += 1
                logger.debug(f"Load rotation applied to {len(groups)} core groups")
                return True
            except Exception as e:
                logger.debug(f"Load rotation error: {e}")
                return False
    
    def predict_and_prevent_throttling(self):
        with self.lock:
            try:
                temps = self.get_per_core_temperatures()
                
                
                hot_cores = [
                    core_idx for core_idx, temp in temps.items()
                    if temp >= self.critical_threshold - 5  
                ]
                
                if hot_cores:
                    
                    avg_temp = sum(temps.values()) / len(temps)
                    
                    if avg_temp > self.hot_threshold:
                        
                        self.stats['throttle_preventions'] += 1
                        logger.warning(f"Thermal throttling predicted! Hot cores: {hot_cores}, Avg temp: {avg_temp:.1f}°C")
                        return True
            except Exception as e:
                logger.debug(f"Throttling prediction error: {e}")
            return False
    
    def get_stats(self):
        with self.lock:
            return self.stats.copy()
