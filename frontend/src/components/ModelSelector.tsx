// frontend/src/components/ModelSelector.tsx

import { FC, useEffect, useState } from 'react';
import { FiCpu, FiAlertTriangle, FiInfo } from 'react-icons/fi';
import { ModelInfo } from '../types';
import { checkSystemCapabilities, getModelCompatibility, SystemCapabilities } from '../utils/systemCheck';

interface ModelSelectorProps {
  models: ModelInfo[];
  selectedModel: string;
  onModelChange: (model: string) => void;
  disabled?: boolean;
}

export const ModelSelector: FC<ModelSelectorProps> = ({
  models,
  selectedModel,
  onModelChange,
  disabled = false
}) => {
  const [systemInfo, setSystemInfo] = useState<SystemCapabilities | null>(null);
  const [showTooltip, setShowTooltip] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadSystemInfo = async () => {
      try {
        const info = await checkSystemCapabilities();
        setSystemInfo(info);
      } catch (error) {
        console.error('Failed to load system info:', error);
      } finally {
        setIsLoading(false);
      }
    };
    loadSystemInfo();
  }, []);

  const getModelStatus = (model: ModelInfo) => {
    if (!systemInfo) return null;
    return getModelCompatibility(model, systemInfo);
  };

  const selectedModelInfo = models.find(m => m.name === selectedModel);
  const selectedModelStatus = selectedModelInfo ? getModelStatus(selectedModelInfo) : null;

  if (isLoading) {
    return (
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium bg-gray-100 dark:bg-gray-700">
          <FiCpu className="w-4 h-4 animate-spin" />
          <span>Loading models...</span>
        </div>
      </div>
    );
  }

  if (!models.length) {
    return (
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300">
          <FiAlertTriangle className="w-4 h-4" />
          <span>No models available</span>
        </div>
      </div>
    );
  }

  return (
    <div className="relative">
      <div className="flex items-center gap-2">
        {/* Model Label */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300">
          <FiCpu className="w-4 h-4" />
          <span>Model:</span>
        </div>

        {/* Model Selector Dropdown */}
        <div className="relative">
          <select
            value={selectedModel}
            onChange={(e) => onModelChange(e.target.value)}
            disabled={disabled}
            className={`px-3 py-1.5 pr-8 rounded-lg text-sm font-medium border
              ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
              ${selectedModelStatus?.performance === 'poor' ? 'border-yellow-500 dark:border-yellow-600' : 'border-gray-200 dark:border-gray-700'}
              bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-200
              hover:border-blue-500 dark:hover:border-blue-400
              focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400`}
          >
            {models.map((model) => {
              const status = getModelStatus(model);
              return (
                <option
                  key={model.name}
                  value={model.name}
                  className={`
                    ${status?.performance === 'poor' ? 'text-yellow-600 dark:text-yellow-400' : ''}
                    ${status?.performance === 'moderate' ? 'text-blue-600 dark:text-blue-400' : ''}
                  `}
                >
                  {model.name} ({model.size_gb}GB)
                  {status?.warnings.length ? ' ⚠️' : ''}
                </option>
              );
            })}
          </select>
        </div>

        {/* Info Icon */}
        {selectedModelStatus?.warnings.length > 0 && (
          <button
            onMouseEnter={() => setShowTooltip(true)}
            onMouseLeave={() => setShowTooltip(false)}
            className="p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-600 text-gray-500 dark:text-gray-400"
          >
            <FiInfo className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Warning Tooltip */}
      {showTooltip && selectedModelStatus?.warnings.length > 0 && (
        <div className="absolute z-10 mt-2 p-3 max-w-xs bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg">
          <div className="flex items-start gap-2">
            <FiAlertTriangle className={`w-5 h-5 mt-0.5 flex-shrink-0 
              ${selectedModelStatus.performance === 'poor' ? 'text-yellow-500' : 'text-blue-500'}`} 
            />
            <div className="space-y-1">
              <p className="font-medium">System Compatibility</p>
              <ul className="text-sm text-gray-600 dark:text-gray-300 space-y-1">
                {selectedModelStatus.warnings.map((warning, i) => (
                  <li key={i}>• {warning}</li>
                ))}
              </ul>
              {selectedModelStatus.performance === 'poor' && (
                <p className="text-sm text-yellow-600 dark:text-yellow-400 mt-2">
                  This model may run slowly or cause system instability.
                </p>
              )}
              {selectedModelStatus.performance === 'moderate' && (
                <p className="text-sm text-blue-600 dark:text-blue-400 mt-2">
                  Performance may be limited on your system.
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ModelSelector;