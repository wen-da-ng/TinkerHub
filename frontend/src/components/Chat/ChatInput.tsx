import React, { useState } from 'react';

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  isProcessing: boolean;
  selectedAnalysisType: 'normal' | 'analyze' | 'analyze_with_code';
}

export const ChatInput = ({ onSendMessage, isProcessing, selectedAnalysisType }: ChatInputProps) => {
  const [message, setMessage] = useState('');

  const getPlaceholder = () => {
    switch (selectedAnalysisType) {
      case 'analyze':
        return 'Enter document name to analyze...';
      case 'analyze_with_code':
        return 'Enter document name to analyze with code...';
      default:
        return 'Type your message...';
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !isProcessing) {
      onSendMessage(message);
      setMessage('');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex items-center gap-2">
      <div className="relative flex-1">
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          className="w-full p-3 pr-10 rounded-2xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          placeholder={getPlaceholder()}
          rows={1}
          disabled={isProcessing}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSubmit(e);
            }
          }}
          style={{ 
            minHeight: '56px', 
            maxHeight: '200px' 
          }}
          onInput={(e) => {
            const target = e.target as HTMLTextAreaElement;
            target.style.height = 'auto';
            target.style.height = `${Math.min(target.scrollHeight, 200)}px`;
          }}
        />
      </div>
      <button
        type="submit"
        disabled={isProcessing || !message.trim()}
        className={`p-3 rounded-full w-12 h-12 flex items-center justify-center ${
          isProcessing || !message.trim() 
            ? 'bg-neutral-200 dark:bg-neutral-700 text-neutral-400 dark:text-neutral-500' 
            : 'bg-blue-500 hover:bg-blue-600 text-white'
        } transition-colors`}
      >
        {isProcessing ? (
          <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        ) : (
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M22 2L11 13"></path>
            <path d="M22 2l-7 20-4-9-9-4 20-7z"></path>
          </svg>
        )}
      </button>
    </form>
  );
};