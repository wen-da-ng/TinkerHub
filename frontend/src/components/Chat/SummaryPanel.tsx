import React from 'react';
import ReactMarkdown from 'react-markdown';

interface SummaryPanelProps {
  summary: string;
  onClose: () => void;
}

export const SummaryPanel = ({ summary, onClose }: SummaryPanelProps) => {
  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-neutral-800 rounded-2xl w-full max-w-2xl max-h-[80vh] overflow-hidden flex flex-col shadow-xl">
        <div className="p-4 border-b border-neutral-200 dark:border-neutral-700 flex justify-between items-center">
          <h2 className="text-xl font-medium">Conversation Summary</h2>
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
          {summary ? (
            <div className="prose dark:prose-invert max-w-none bg-neutral-50 dark:bg-neutral-900 p-4 rounded-xl">
              <ReactMarkdown
                components={{
                  p: ({ node, ...props }) => <p className="mb-2 last:mb-0" {...props} />,
                  pre: ({ node, ...props }) => (
                    <pre className="bg-neutral-800 dark:bg-black text-neutral-100 p-2 rounded overflow-auto" {...props} />
                  ),
                  code: ({ node, inline, ...props }) => 
                    inline ? 
                      <code className="bg-neutral-200 dark:bg-neutral-700 px-1 py-0.5 rounded" {...props} /> : 
                      <code {...props} />
                }}
              >{summary}</ReactMarkdown>
            </div>
          ) : (
            <div className="text-center py-10 bg-neutral-50 dark:bg-neutral-900 rounded-xl">
              <p className="text-neutral-500">No summary available yet</p>
              <p className="text-sm text-neutral-400 mt-2">
                Summaries are generated automatically as you chat.
                Continue your conversation to generate a summary.
              </p>
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