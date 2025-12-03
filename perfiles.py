import time
from collections import defaultdict, deque
import threading
import logging

logger = logging.getLogger(__name__)

PAGE_PRIORITY_NORMAL = 5

class AutomaticProfileManager:
    def __init__(self):
        self.lock = threading.RLock()
        self.current_profile = 'Balanced'
        self.profiles = {
            'Gaming': {
                'keywords': ['game', 'steam', 'epic', 'origin', 'uplay', 'battle.net', 'gog', 'dx11', 'dx12', 'vulkan'],
                'cpu_priority': 'HIGH',
                'memory_priority': 'NORMAL',
                'io_priority': 'HIGH',
                'disable_background': True
            },
            'Productivity': {
                'keywords': ['office', 'word', 'excel', 'powerpoint', 'outlook', 'teams', 'slack', 'zoom'],
                'cpu_priority': 'ABOVE_NORMAL',
                'memory_priority': 'NORMAL',
                'io_priority': 'NORMAL',
                'disable_background': False
            },
            'Video Editing': {
                'keywords': ['premiere', 'aftereffects', 'davinci', 'vegas', 'handbrake', 'ffmpeg'],
                'cpu_priority': 'HIGH',
                'memory_priority': 'HIGH',
                'io_priority': 'HIGH',
                'disable_background': True
            },
            'Coding': {
                'keywords': ['code', 'visual studio', 'intellij', 'pycharm', 'eclipse', 'atom', 'sublime'],
                'cpu_priority': 'ABOVE_NORMAL',
                'memory_priority': 'NORMAL',
                'io_priority': 'NORMAL',
                'disable_background': False
            },
            'Balanced': {
                'keywords': [],
                'cpu_priority': 'NORMAL',
                'memory_priority': 'NORMAL',
                'io_priority': 'NORMAL',
                'disable_background': False
            }
        }
        self.stats = {'profile_switches': 0}
    
    def detect_profile(self, process_name):
        with self.lock:
            process_lower = process_name.lower()
            
            for profile_name, profile_data in self.profiles.items():
                if profile_name == 'Balanced':
                    continue
                for keyword in profile_data['keywords']:
                    if keyword in process_lower:
                        if self.current_profile != profile_name:
                            self.current_profile = profile_name
                            self.stats['profile_switches'] += 1
                        return profile_name
            
            if self.current_profile != 'Balanced':
                self.current_profile = 'Balanced'
                self.stats['profile_switches'] += 1
            return 'Balanced'
    
    def get_profile_settings(self, profile_name=None):
        with self.lock:
            if profile_name is None:
                profile_name = self.current_profile
            return self.profiles.get(profile_name, self.profiles['Balanced'])
class DynamicMultiLayerProfileSystem:
    
    def __init__(self):
        self.lock = threading.RLock()
        self.current_scenario = 'browsing'
        self.scenario_history = deque(maxlen=100)
        self.process_patterns = defaultdict(lambda: {
            'co_occurrence': defaultdict(int),  
            'hourly_usage': defaultdict(int),    
            'typical_load': defaultdict(list)    
        })
        self.scenario_start_time = time.time()
        self.stats = {
            'scenario_switches': 0,
            'auto_adjustments': 0,
            'pattern_learnings': 0
        }
        
        
        self.scenarios = {
            'gaming': {
                'keywords': ['game', 'steam', 'epic', 'origin', 'uplay', 'battle.net', 
                           'gog', 'dx11', 'dx12', 'vulkan', 'unreal', 'unity'],
                'priority': {
                    'cpu': 'HIGH',
                    'memory': 'NORMAL',
                    'io': 'HIGH',
                    'page': PAGE_PRIORITY_NORMAL
                },
                'affinity': {
                    'prefer_physical_cores': True,
                    'avoid_smt_sharing': True,
                    'isolate_from_background': True
                },
                'system': {
                    'responsiveness': 10,
                    'timer_resolution': 0.5,
                    'disable_background_tasks': True,
                    'gpu_priority': 'HIGH'
                },
                'weight': 10
            },
            'productivity': {
                'keywords': ['office', 'word', 'excel', 'powerpoint', 'outlook', 'teams',
                           'slack', 'zoom', 'webex', 'notes', 'onenote'],
                'priority': {
                    'cpu': 'ABOVE_NORMAL',
                    'memory': 'NORMAL',
                    'io': 'NORMAL',
                    'page': PAGE_PRIORITY_NORMAL
                },
                'affinity': {
                    'prefer_physical_cores': False,
                    'avoid_smt_sharing': False,
                    'isolate_from_background': False
                },
                'system': {
                    'responsiveness': 20,
                    'timer_resolution': 1.0,
                    'disable_background_tasks': False,
                    'gpu_priority': 'NORMAL'
                },
                'weight': 7
            },
            'rendering': {
                'keywords': ['premiere', 'aftereffects', 'davinci', 'vegas', 'handbrake',
                           'ffmpeg', 'blender', 'maya', '3dsmax', 'cinema4d'],
                'priority': {
                    'cpu': 'HIGH',
                    'memory': 'HIGH',
                    'io': 'HIGH',
                    'page': PAGE_PRIORITY_NORMAL
                },
                'affinity': {
                    'prefer_physical_cores': True,
                    'avoid_smt_sharing': False,
                    'isolate_from_background': True
                },
                'system': {
                    'responsiveness': 15,
                    'timer_resolution': 1.0,
                    'disable_background_tasks': True,
                    'gpu_priority': 'HIGH'
                },
                'weight': 9
            },
            'development': {
                'keywords': ['code', 'visual studio', 'intellij', 'pycharm', 'eclipse',
                           'atom', 'sublime', 'vscode', 'rider', 'android studio'],
                'priority': {
                    'cpu': 'ABOVE_NORMAL',
                    'memory': 'ABOVE_NORMAL',
                    'io': 'ABOVE_NORMAL',
                    'page': PAGE_PRIORITY_NORMAL
                },
                'affinity': {
                    'prefer_physical_cores': False,
                    'avoid_smt_sharing': False,
                    'isolate_from_background': False
                },
                'system': {
                    'responsiveness': 20,
                    'timer_resolution': 1.0,
                    'disable_background_tasks': False,
                    'gpu_priority': 'NORMAL'
                },
                'weight': 6
            },
            'browsing': {
                'keywords': ['chrome', 'firefox', 'edge', 'brave', 'opera', 'safari'],
                'priority': {
                    'cpu': 'NORMAL',
                    'memory': 'NORMAL',
                    'io': 'NORMAL',
                    'page': PAGE_PRIORITY_NORMAL
                },
                'affinity': {
                    'prefer_physical_cores': False,
                    'avoid_smt_sharing': False,
                    'isolate_from_background': False
                },
                'system': {
                    'responsiveness': 20,
                    'timer_resolution': 1.0,
                    'disable_background_tasks': False,
                    'gpu_priority': 'NORMAL'
                },
                'weight': 3
            }
        }
    
    def detect_scenario(self, active_processes):
        with self.lock:
            scenario_scores = defaultdict(float)
            current_hour = time.localtime().tm_hour
            
            
            for proc in active_processes:
                proc_lower = proc.lower()
                
                for scenario_name, scenario_data in self.scenarios.items():
                    for keyword in scenario_data['keywords']:
                        if keyword in proc_lower:
                            
                            score = scenario_data['weight']
                            
                            
                            hourly_pattern = self.process_patterns[proc]['hourly_usage']
                            if hourly_pattern.get(current_hour, 0) > 0:
                                score *= 1.2
                            
                            scenario_scores[scenario_name] += score
            
            
            if not scenario_scores:
                detected_scenario = 'browsing'
                confidence = 0.5
            else:
                detected_scenario = max(scenario_scores.items(), key=lambda x: x[1])[0]
                total_score = sum(scenario_scores.values())
                confidence = scenario_scores[detected_scenario] / total_score if total_score > 0 else 0
            
            
            if detected_scenario != self.current_scenario:
                self.scenario_history.append({
                    'scenario': detected_scenario,
                    'timestamp': time.time(),
                    'confidence': confidence
                })
                self.current_scenario = detected_scenario
                self.scenario_start_time = time.time()
                self.stats['scenario_switches'] += 1
                logger.info(f"Scenario switched to: {detected_scenario} (confidence: {confidence:.2f})")
            
            return detected_scenario, confidence
    
    def learn_process_patterns(self, pid, process_name, cpu_percent, memory_percent):
        with self.lock:
            try:
                current_hour = time.localtime().tm_hour
                patterns = self.process_patterns[process_name]
                
                
                patterns['hourly_usage'][current_hour] += 1
                
                
                patterns['typical_load']['cpu'].append(cpu_percent)
                patterns['typical_load']['memory'].append(memory_percent)
                
                
                if len(patterns['typical_load']['cpu']) > 100:
                    patterns['typical_load']['cpu'].pop(0)
                if len(patterns['typical_load']['memory']) > 100:
                    patterns['typical_load']['memory'].pop(0)
                
                
                
                self.stats['pattern_learnings'] += 1
                
            except Exception as e:
                logger.debug(f"Pattern learning error for {process_name}: {e}")
    
    def get_adaptive_settings(self, process_name, pid=None):
        with self.lock:
            scenario_settings = self.scenarios.get(self.current_scenario, self.scenarios['browsing'])
            
            
            patterns = self.process_patterns.get(process_name, {})
            
            
            settings = {
                'priority': scenario_settings['priority'].copy(),
                'affinity': scenario_settings['affinity'].copy(),
                'system': scenario_settings['system'].copy(),
                'predicted_load': {
                    'cpu': 0,
                    'memory': 0
                }
            }
            
            
            if patterns and 'typical_load' in patterns:
                cpu_loads = patterns['typical_load'].get('cpu', [])
                mem_loads = patterns['typical_load'].get('memory', [])
                
                if cpu_loads:
                    settings['predicted_load']['cpu'] = sum(cpu_loads) / len(cpu_loads)
                if mem_loads:
                    settings['predicted_load']['memory'] = sum(mem_loads) / len(mem_loads)
            
            self.stats['auto_adjustments'] += 1
            return settings
    
    def get_scenario_metrics(self):
