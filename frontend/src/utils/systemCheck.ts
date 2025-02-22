import { SystemCapabilities, SystemSpecs } from '../types';

export const checkSystemCapabilities = async (): Promise<SystemCapabilities> => {
  let wsUrl = 'ws://localhost:8000';
  // Convert ws URL to http for system info request
  let httpUrl = wsUrl.replace('ws://', 'http://').replace('wss://', 'https://');
  
  try {
    // First try to get system info from backend
    const ws = new WebSocket(wsUrl);
    
    const systemInfo = await new Promise<SystemCapabilities>((resolve, reject) => {
      const timeout = setTimeout(() => {
        ws.close();
        reject(new Error('WebSocket connection timeout'));
      }, 5000);

      ws.onopen = () => {
        ws.send(JSON.stringify({ type: 'get_system_info' }));
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'system_info' && data.specs) {
            const specs: SystemSpecs = data.specs;
            clearTimeout(timeout);
            ws.close();
            resolve({
              memory: specs.memory_gb,
              memory_available: specs.memory_available_gb,
              gpu: specs.has_gpu,
              gpuInfo: specs.gpus.map(gpu => gpu.name).join(', '),
              cpu_cores: specs.cpu_cores,
              cpu_threads: specs.cpu_threads,
              platform: specs.platform,
              platform_version: specs.platform_version,
              processor: specs.processor
            });
          }
        } catch (e) {
          console.warn('Error parsing WebSocket message:', e);
        }
      };

      ws.onerror = (error) => {
        clearTimeout(timeout);
        reject(error);
      };
    });

    return systemInfo;
  } catch (e) {
    console.warn('Failed to get system info from WebSocket, falling back to HTTP:', e);
    
    try {
      // Fallback to HTTP request
      const response = await fetch(`${httpUrl}/system_info`);
      const data = await response.json();
      const specs: SystemSpecs = data.specs;
      
      return {
        memory: specs.memory_gb,
        memory_available: specs.memory_available_gb,
        gpu: specs.has_gpu,
        gpuInfo: specs.gpus.map(gpu => gpu.name).join(', '),
        cpu_cores: specs.cpu_cores,
        cpu_threads: specs.cpu_threads,
        platform: specs.platform,
        platform_version: specs.platform_version,
        processor: specs.processor
      };
    } catch (e) {
      console.warn('Failed to get system info from HTTP, falling back to browser detection:', e);
      return fallbackSystemCheck();
    }
  }
};

const fallbackSystemCheck = async (): Promise<SystemCapabilities> => {
  let capabilities: SystemCapabilities = {
    memory: 0,
    memory_available: 0,
    gpu: false,
    cpu_cores: 0,
    cpu_threads: 0,
    platform: navigator.platform
  };

  // Check memory
  try {
    if ('memory' in navigator) {
      // @ts-ignore: deviceMemory is not yet in Navigator type
      capabilities.memory = navigator.deviceMemory;
      capabilities.memory_available = capabilities.memory * 0.8; // Rough estimate
    }
  } catch (e) {
    console.warn('Could not detect system memory:', e);
  }

  // Check CPU cores
  try {
    if (navigator.hardwareConcurrency) {
      capabilities.cpu_threads = navigator.hardwareConcurrency;
      capabilities.cpu_cores = Math.floor(navigator.hardwareConcurrency / 2); // Rough estimate for physical cores
    }
  } catch (e) {
    console.warn('Could not detect CPU cores:', e);
  }

  // Check for GPU
  try {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl2') || canvas.getContext('webgl');
    
    if (gl) {
      const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
      if (debugInfo) {
        const renderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
        const vendor = gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL);
        
        capabilities.gpu = !/microsoft basic render driver/i.test(renderer);
        capabilities.gpuInfo = `${vendor} - ${renderer}`;

        // Check if it's likely a dedicated GPU
        const isDedicatedGPU = /nvidia|radeon|geforce|rtx|gtx/i.test(renderer);
        if (isDedicatedGPU) {
          capabilities.gpu = true;
        }
      }
    }
  } catch (e) {
    console.warn('Could not detect GPU capabilities:', e);
  }

  return capabilities;
};

export const getModelCompatibility = (
  model: { size_gb: number; ram_requirement: number },
  systemCapabilities: SystemCapabilities
): {
  compatible: boolean;
  warnings: string[];
  performance: 'good' | 'moderate' | 'poor';
} => {
  const warnings: string[] = [];
  let performance: 'good' | 'moderate' | 'poor' = 'good';

  // Check RAM requirements
  if (model.ram_requirement > systemCapabilities.memory) {
    warnings.push(`Requires ${model.ram_requirement}GB RAM (you have ${systemCapabilities.memory}GB)`);
    performance = 'poor';
  } else if (model.ram_requirement > systemCapabilities.memory_available) {
    warnings.push(`Requires ${model.ram_requirement}GB RAM (${systemCapabilities.memory_available}GB available)`);
    performance = 'moderate';
  }

  // Check GPU requirements
  if (model.size_gb > 10 && !systemCapabilities.gpu) {
    warnings.push('GPU recommended for optimal performance');
    performance = performance === 'poor' ? 'poor' : 'moderate';
  }

  // Check CPU cores for large models
  if (systemCapabilities.cpu_cores) {
    if (model.size_gb > 5) {
      if (systemCapabilities.cpu_cores < 4) {
        warnings.push('Model may run slowly on your CPU');
        performance = 'poor';
      } else if (systemCapabilities.cpu_cores < 8 && model.size_gb > 10) {
        warnings.push('More CPU cores recommended for optimal performance');
        performance = performance === 'poor' ? 'poor' : 'moderate';
      }
    }
  }

  return {
    compatible: performance !== 'poor',
    warnings,
    performance
  };
};