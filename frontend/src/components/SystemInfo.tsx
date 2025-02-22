// frontend/src/components/SystemInfo.tsx
import { FC, useEffect, useState } from 'react';
import { FiCpu, FiHardDrive, FiMonitor } from 'react-icons/fi';
import { SystemCapabilities } from '../types';
import { checkSystemCapabilities } from '../utils/systemCheck';

export const SystemInfo: FC = () => {
  const [systemInfo, setSystemInfo] = useState<SystemCapabilities | null>(null);

  useEffect(() => {
    const loadSystemInfo = async () => {
      const info = await checkSystemCapabilities();
      setSystemInfo(info);
    };
    loadSystemInfo();
  }, []);

  if (!systemInfo) return null;

  return (
    <div className="p-4 border-t border-gray-200 dark:border-gray-700">
      <div className="text-xs text-gray-500 dark:text-gray-400 space-y-2">
        <div className="flex items-center gap-2">
          <FiHardDrive className="w-3 h-3" />
          <span>{systemInfo.memory}GB RAM ({systemInfo.memory_available}GB free)</span>
        </div>
        {systemInfo.cpu_cores && (
          <div className="flex items-center gap-2">
            <FiCpu className="w-3 h-3" />
            <span>{systemInfo.cpu_cores} CPU Cores ({systemInfo.cpu_threads} threads)</span>
          </div>
        )}
        {systemInfo.gpu && (
          <div className="flex items-center gap-2">
            <FiMonitor className="w-3 h-3" />
            <span>{systemInfo.gpuInfo || 'GPU Available'}</span>
          </div>
        )}
      </div>
    </div>
  );
};