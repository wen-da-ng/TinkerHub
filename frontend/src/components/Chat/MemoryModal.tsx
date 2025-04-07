import React from 'react';

interface MemoryModalProps {
  memory: any;
  onClose: () => void;
}

export const MemoryModal = ({ memory, onClose }: MemoryModalProps) => {
  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-neutral-800 rounded-2xl w-full max-w-3xl max-h-[80vh] overflow-hidden flex flex-col shadow-xl">
        <div className="p-4 border-b border-neutral-200 dark:border-neutral-700 flex justify-between items-center">
          <h2 className="text-xl font-medium">Memory Status</h2>
          <button 
            onClick={onClose}
            className="p-2 rounded-full hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
        
        <div className="p-4 overflow-y-auto flex-1">
          {memory ? (
            <div className="space-y-6">
              <div className="bg-neutral-50 dark:bg-neutral-900 p-4 rounded-xl">
                <h3 className="font-medium mb-2 text-neutral-700 dark:text-neutral-300">Short-term Memory</h3>
                <p className="text-neutral-600 dark:text-neutral-400">{memory.shortTermCount} messages</p>
              </div>
              
              <div className="bg-neutral-50 dark:bg-neutral-900 p-4 rounded-xl">
                <h3 className="font-medium mb-2 text-neutral-700 dark:text-neutral-300">Long-term Memory Topics</h3>
                {memory.longTermTopics.length > 0 ? (
                  <ul className="list-disc pl-5 text-neutral-600 dark:text-neutral-400">
                    {memory.longTermTopics.map((topic: string, index: number) => (
                      <li key={index}>{topic}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-neutral-500 dark:text-neutral-500">No topics in long-term memory</p>
                )}
              </div>
              
              <div className="bg-neutral-50 dark:bg-neutral-900 p-4 rounded-xl">
                <h3 className="font-medium mb-3 text-neutral-700 dark:text-neutral-300">Memory Facts</h3>
                {Object.keys(memory.facts).length > 0 ? (
                  <div className="space-y-3">
                    {Object.entries(memory.facts).map(([topic, facts]: [string, any]) => (
                      <div key={topic} className="bg-white dark:bg-neutral-800 p-3 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700">
                        <h4 className="font-medium text-neutral-800 dark:text-neutral-200">{topic}</h4>
                        <ul className="list-disc pl-5 mt-1">
                          {facts.map((fact: string, index: number) => (
                            <li key={index} className="text-sm text-neutral-600 dark:text-neutral-400">{fact}</li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-4">
                    <p className="text-neutral-500">No facts stored</p>
                    <p className="text-sm text-neutral-400 mt-2">
                      Facts are extracted automatically from your conversation. 
                      Try discussing specific topics or asking questions to generate facts.
                    </p>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-full">
              <div className="animate-pulse flex flex-col items-center">
                <svg className="animate-spin h-8 w-8 text-blue-500 mb-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <p className="text-neutral-500">Loading memory data...</p>
              </div>
            </div>
          )}
        </div>
        
        <div className="p-4 border-t border-neutral-200 dark:border-neutral-700">
          <button
            onClick={onClose}
            className="w-full py-2.5 bg-blue-500 hover:bg-blue-600 text-white rounded-lg font-medium transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};