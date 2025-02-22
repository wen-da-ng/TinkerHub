import psutil
import platform
import subprocess
import logging
from typing import Dict
import json

logger = logging.getLogger(__name__)

class SystemInfo:
    @staticmethod
    def get_system_specs() -> Dict:
        try:
            # Get RAM info
            memory = psutil.virtual_memory()
            memory_gb = round(memory.total / (1024 * 1024 * 1024), 1)
            
            # Get CPU info
            cpu_cores = psutil.cpu_count(logical=False)  # Physical cores
            cpu_threads = psutil.cpu_count(logical=True)  # Logical cores

            # Get GPU info using Windows Management Instrumentation (WMI)
            gpu_info = []
            if platform.system() == 'Windows':
                try:
                    # Get GPU name
                    output = subprocess.check_output(
                        ['wmic', 'path', 'win32_VideoController', 'get', 'name'],
                        universal_newlines=True
                    )
                    gpu_names = [line.strip() for line in output.splitlines()[1:] if line.strip()]

                    # Get GPU memory for each GPU
                    output = subprocess.check_output(
                        ['wmic', 'path', 'win32_VideoController', 'get', 'AdapterRAM'],
                        universal_newlines=True
                    )
                    gpu_memory = [
                        round(int(line.strip()) / (1024 * 1024 * 1024), 1) 
                        for line in output.splitlines()[1:] 
                        if line.strip() and line.strip().isdigit()
                    ]

                    # Combine information
                    for i, name in enumerate(gpu_names):
                        gpu_info.append({
                            'name': name,
                            'memory_total': gpu_memory[i] if i < len(gpu_memory) else None
                        })
                except Exception as e:
                    logger.warning(f"Could not get detailed GPU info: {e}")
                    if gpu_names:
                        gpu_info = [{'name': name} for name in gpu_names]

            return {
                'memory_gb': memory_gb,
                'memory_available_gb': round(memory.available / (1024 * 1024 * 1024), 1),
                'memory_percent': memory.percent,
                'cpu_cores': cpu_cores,
                'cpu_threads': cpu_threads,
                'cpu_percent': psutil.cpu_percent(),
                'platform': platform.system(),
                'platform_version': platform.version(),
                'processor': platform.processor(),
                'gpus': gpu_info,
                'has_gpu': bool(gpu_info and any('nvidia' in gpu['name'].lower() or 
                                               'radeon' in gpu['name'].lower() or 
                                               'geforce' in gpu['name'].lower() or 
                                               'rtx' in gpu['name'].lower() or 
                                               'gtx' in gpu['name'].lower() 
                                               for gpu in gpu_info))
            }
        except Exception as e:
            logger.error(f"Error getting system specs: {e}")
            return {
                'memory_gb': 0,
                'memory_available_gb': 0,
                'memory_percent': 0,
                'cpu_cores': 0,
                'cpu_threads': 0,
                'cpu_percent': 0,
                'platform': platform.system(),
                'platform_version': '',
                'processor': '',
                'gpus': [],
                'has_gpu': False,
                'error': str(e)
            }

system_info = SystemInfo()