import subprocess
import threading

class PowerManagementOptimizer:
    def __init__(self):
        self.lock = threading.RLock()
    
    def disable_pcie_aspm(self):
        with self.lock:
            try:
                subprocess.run(
                    ['powercfg', '/setacvalueindex', 'SCHEME_CURRENT', 'SUB_PCIEXPRESS', 'ASPM', '0'],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                subprocess.run(
                    ['powercfg', '/setactive', 'SCHEME_CURRENT'],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                return True
            except Exception:
                return False
    
    def disable_usb_selective_suspend(self):
        with self.lock:
            try:
                subprocess.run(
                    ['powercfg', '/setacvalueindex', 'SCHEME_CURRENT', 'SUB_USB', 'USBSELECTIVESUSPEND', '0'],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                subprocess.run(
                    ['powercfg', '/setactive', 'SCHEME_CURRENT'],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                return True
            except Exception:
                return False
class CStatesOptimizer:
    def __init__(self):
        self.lock = threading.RLock()
        self.c_states_disabled = False
    
    def disable_deep_c_states(self):
        with self.lock:
            try:
                subprocess.run(
                    ['powercfg', '/setacvalueindex', 'SCHEME_CURRENT', 'SUB_SLEEP', 'DEEPEST_CSTATE', '0'],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                subprocess.run(
                    ['powercfg', '/setactive', 'SCHEME_CURRENT'],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                self.c_states_disabled = True
                return True
            except Exception:
                return False
    
    def enable_deep_c_states(self):
        with self.lock:
            try:
                subprocess.run(
                    ['powercfg', '/setacvalueindex', 'SCHEME_CURRENT', 'SUB_SLEEP', 'DEEPEST_CSTATE', '6'],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                subprocess.run(
                    ['powercfg', '/setactive', 'SCHEME_CURRENT'],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                self.c_states_disabled = False
                return True
            except Exception:
                return False
class DynamicVoltageFrequencyScaler:
    HIGH_WORKLOAD_THRESHOLD = 80
    MEDIUM_WORKLOAD_THRESHOLD = 50
    MAX_THROTTLE = 0
    MEDIUM_THROTTLE = 50
    HIGH_THROTTLE = 100
    
    def __init__(self):
        self.lock = threading.RLock()
        self.per_core_states = {}
    
    def adjust_core_frequency(self, core_id, workload_level):
        with self.lock:
            try:
                if workload_level > self.HIGH_WORKLOAD_THRESHOLD:
                    throttle_percent = self.MAX_THROTTLE
                elif workload_level > self.MEDIUM_WORKLOAD_THRESHOLD:
                    throttle_percent = self.MEDIUM_THROTTLE
                else:
                    throttle_percent = self.HIGH_THROTTLE
                
                max_frequency_percent = 100 - throttle_percent
                
                subprocess.run(
                    ['powercfg', '/setacvalueindex', 'SCHEME_CURRENT', 'SUB_PROCESSOR', 
                     'PROCTHROTTLEMAX', str(max_frequency_percent)],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    timeout=2
                )
                
                self.per_core_states[core_id] = throttle_percent
                return True
            except Exception:
                return False
