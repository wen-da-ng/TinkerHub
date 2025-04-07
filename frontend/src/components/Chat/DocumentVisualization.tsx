import React, { useState } from 'react';

interface Chunk {
  id: string;
  content: string;
  metadata: {
    source?: string;
    page?: number;
    chunk?: number;
    chunk_of?: number;
    relevance?: number;
  };
}

interface DocumentVisualizationProps {
  documentName: string;
  chunks: Chunk[];
  activeChunks?: string[]; // IDs of chunks being analyzed or highlighted
  onChunkClick?: (chunkId: string) => void;
}

export const DocumentVisualization = ({ 
  documentName, 
  chunks, 
  activeChunks = [], 
  onChunkClick 
}: DocumentVisualizationProps) => {
  const [expandedChunk, setExpandedChunk] = useState<string | null>(null);

  const toggleChunk = (chunkId: string) => {
    setExpandedChunk(expandedChunk === chunkId ? null : chunkId);
    if (onChunkClick) {
      onChunkClick(chunkId);
    }
  };

  return (
    <div className="p-4"> 
      <h3 className="font-medium text-lg text-gray-900 dark:text-white mb-3">
        {documentName} <span className="text-base font-normal text-gray-500 dark:text-gray-400">({chunks.length} chunks)</span>
      </h3>

      <div className="flex flex-wrap gap-1 mb-4">
        {chunks.map((chunk, index) => ( 
          <button
            key={chunk.id || `chunk-${index}`} 
            onClick={() => toggleChunk(chunk.id)}
            className={`
              w-10 h-10 rounded-md flex items-center justify-center text-xs font-medium transition-colors border
              ${expandedChunk === chunk.id
                ? 'bg-blue-500 text-white border-blue-600'
                : activeChunks.includes(chunk.id)
                  ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 border-green-200 dark:border-green-800/30'
                  : 'bg-gray-100 dark:bg-neutral-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-neutral-600 border-gray-200 dark:border-neutral-600'
              }
            `}
            title={`Chunk ${chunk.metadata.chunk ?? index + 1}/${chunk.metadata.chunk_of || '?'}`}
          >
            {chunk.metadata.chunk ?? index + 1}
          </button>
        ))}
      </div>

      {expandedChunk && (
        <div className="mt-2 border border-gray-200 dark:border-neutral-700 rounded-md p-3 bg-gray-50 dark:bg-neutral-900/50">
          <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1 flex justify-between">
            <span>
              Chunk {chunks.find(c => c.id === expandedChunk)?.metadata.chunk || '?'} of {chunks.find(c => c.id === expandedChunk)?.metadata.chunk_of || '?'}
            </span>
            {chunks.find(c => c.id === expandedChunk)?.metadata.relevance != null && ( 
              <span>Relevance: {chunks.find(c => c.id === expandedChunk)?.metadata.relevance?.toFixed(2)}</span>
            )}
          </div>
          <div className="text-sm text-gray-800 dark:text-gray-200 max-h-48 overflow-y-auto prose prose-sm dark:prose-invert max-w-none">
            <div>{chunks.find(c => c.id === expandedChunk)?.content}</div>
          </div>
        </div>
      )}
    </div>
  );
};