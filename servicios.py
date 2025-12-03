import json
import os
import psutil
import threading

class ProcessServiceManager:
    def __init__(self):
        self.lock = threading.RLock()
        self.database = {}
        self.load_database()
        self.stats = {
            'services_stopped': 0,
            'services_disabled': 0,
            'processes_suspended': 0,
            'processes_throttled': 0
        }
    
    def load_database(self):
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(script_dir, 'process_service_database.json')
            if os.path.exists(db_path):
                with open(db_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                if not isinstance(data, dict):
                    self.database = {}
                    return
                
                self.database = data
        except json.JSONDecodeError:
            self.database = {}
        except Exception:
            self.database = {}
    
    def get_process_config(self, process_name):
        try:
            processes_section = self.database.get('procesos') or self.database.get('processes', {})
            
            system_procs = processes_section.get('procesos_sistema') or processes_section.get('system_processes', [])
            for proc in system_procs:
                if proc.get('name', '').lower() == process_name.lower():
                    return proc
            
            third_party_procs = processes_section.get('terceros_comunes') or processes_section.get('common_third_party', [])
            for proc in third_party_procs:
                if proc.get('name', '').lower() == process_name.lower():
                    return proc
            
            return None
        except Exception:
            return None
    
    def should_apply_action(self, process_name, cpu_percent, ram_percent, disk_percent):
        config = self.get_process_config(process_name)
        if not config:
            return False, None
        
        action = config.get('action_on_threshold')
        if not action:
            return False, None
        
        cpu_threshold = config.get('cpu_threshold_percent', 100)
        ram_threshold = config.get('ram_threshold_mb', 999999)
        
        try:
            process_list = [p for p in psutil.process_iter(['name']) if p.info['name'].lower() == process_name.lower()]
            if process_list:
                proc = process_list[0]
                proc_cpu = proc.cpu_percent(interval=0.1)
                proc_ram_mb = proc.memory_info().rss / (1024 * 1024)
                
                if proc_cpu > cpu_threshold or proc_ram_mb > ram_threshold:
                    return True, action
        except Exception:
            pass
        
        return False, None
    
    def get_statistics(self):
        with self.lock:
            return self.stats.copy()
