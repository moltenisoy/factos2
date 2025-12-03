import winreg
import subprocess
import threading

HARDWARE_SCHEDULING_MODE_2 = 2

class GPUSchedulingOptimizer:
    def __init__(self):
        self.lock = threading.RLock()
        
    def enable_hardware_gpu_scheduling(self):
        try:
            key_path = r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers"
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "HwSchMode", 0, winreg.REG_DWORD, HARDWARE_SCHEDULING_MODE_2)
            winreg.CloseKey(key)
        except Exception:
            pass

class PCIeBandwidthOptimizer:
    def __init__(self):
        self.lock = threading.RLock()
        
    def maximize_pcie_bandwidth(self):
        try:
            key_path = r"SYSTEM\CurrentControlSet\Services\pci\Parameters"
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "ASPMOptOut", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key)
        except Exception:
            pass

class DirectXVulkanOptimizer:
    def __init__(self):
        self.lock = threading.RLock()
        
    def optimize_rendering_performance(self):
        try:
            key_path = r"SOFTWARE\Microsoft\DirectX"
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "DisableDebugLayer", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key)
        except Exception:
            pass
