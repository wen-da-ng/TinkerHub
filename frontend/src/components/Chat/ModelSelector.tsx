import React, { useEffect, useState } from 'react';
import { Model, getModels, setModel } from '@/api/chat';

interface ModelSelectorProps {
  sessionId: string;
  onModelChange: (model: string) => void;
}

export const ModelSelector = ({ sessionId, onModelChange }: ModelSelectorProps) => {
  const [models, setModels] = useState<Model[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    const fetchModels = async () => {
      setLoading(true);
      const availableModels = await getModels();
      setModels(availableModels);
      
      // Set default selected model to the first one if available
      if (availableModels.length > 0 && !selectedModel) {
        setSelectedModel(availableModels[0].name);
      }
      
      setLoading(false);
    };

    fetchModels();
  }, [selectedModel]);

  const handleModelChange = async (modelName: string) => {
    setSelectedModel(modelName);
    setIsOpen(false);
    
    const success = await setModel(modelName, sessionId);
    if (success) {
      onModelChange(modelName);
    }
  };

  return (
    <div className="relative">
      <div className="flex items-center">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="px-3 py-1.5 rounded-full bg-neutral-100 dark:bg-neutral-700 text-sm flex items-center gap-1.5 hover:bg-neutral-200 dark:hover:bg-neutral-600 transition-colors"
        >
          <span className="hidden sm:inline">Model:</span>
          <span className="font-medium truncate max-w-[100px]">{selectedModel || 'Loading...'}</span>
          <svg 
            xmlns="http://www.w3.org/2000/svg" 
            width="12" 
            height="12" 
            viewBox="0 0 24 24" 
            fill="none" 
            stroke="currentColor" 
            strokeWidth="2" 
            strokeLinecap="round" 
            strokeLinejoin="round"
            className={`transition-transform ${isOpen ? 'rotate-180' : ''}`}
          >
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </button>
      </div>

      {isOpen && (
        <div className="absolute right-0 mt-1 bg-white dark:bg-neutral-800 rounded-lg shadow-lg border border-neutral-200 dark:border-neutral-700 overflow-hidden z-50 w-60">
          <div className="p-2">
            <div className="text-xs font-medium text-neutral-500 dark:text-neutral-400 mb-1 px-2 pt-1">
              Select Model
            </div>
            <div className="max-h-64 overflow-y-auto">
              {loading ? (
                <div className="text-center py-2 text-sm text-neutral-500 dark:text-neutral-400">
                  Loading...
                </div>
              ) : models.length === 0 ? (
                <div className="text-center py-2 text-sm text-neutral-500 dark:text-neutral-400">
                  No models available
                </div>
              ) : (
                <div className="space-y-0.5">
                  {models.map((model) => (
                    <button
                      key={model.name}
                      className={`
                        w-full text-left px-2 py-1.5 rounded text-sm flex justify-between items-center
                        ${selectedModel === model.name 
                          ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400' 
                          : 'hover:bg-neutral-100 dark:hover:bg-neutral-700 text-neutral-800 dark:text-neutral-200'}
                      `}
                      onClick={() => handleModelChange(model.name)}
                    >
                      <span className="truncate">{model.name}</span>
                      <span className="text-xs text-neutral-500 dark:text-neutral-400 ml-2">{model.size}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};