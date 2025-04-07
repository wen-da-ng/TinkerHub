import React, { useState, useMemo } from 'react';
import Image from 'next/image';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm'; // Plugin for GitHub Flavored Markdown
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'; // For code block highlighting
import { vscDarkPlus, vs } from 'react-syntax-highlighter/dist/cjs/styles/prism'; // Code block themes
import { useTheme } from 'next-themes'; // To select the correct code theme
import { BrainCircuit } from 'lucide-react'; // Icons

import { ChatMessage as ChatMessageType } from '@/api/chat';

interface ChatMessageProps {
  message: ChatMessageType;
  onReply: (topic: string) => void;
}

export const ChatMessage = ({ message, onReply }: ChatMessageProps) => {
  const [showThinking, setShowThinking] = useState(false);
  const { theme } = useTheme(); // Get current theme

  // Pre-process content to separate thinking blocks using useMemo for performance
  const processedContent = useMemo(() => {
    const thinkTagRegex = /<think>([\s\S]*?)<\/think>/g;
    let thinkingContent: string | null = null;

    // Extract all thinking blocks and join them
    const thinkingParts: string[] = [];
    let match;
    while ((match = thinkTagRegex.exec(message.content)) !== null) {
      thinkingParts.push(match[1].trim()); // Add the captured content inside tags
    }
    if (thinkingParts.length > 0) {
      thinkingContent = thinkingParts.join('\n\n---\n\n'); // Join multiple blocks
    }

    // Create visible content by removing the think blocks
    const visibleContent = message.content.replace(thinkTagRegex, '').trim();

    return {
      // Ensure there's always some displayable content or a placeholder if only thinking exists
      visibleContent: visibleContent || (thinkingContent ? '(Contains only hidden thought process)' : ''),
      thinkingContent: thinkingContent,
    };
  }, [message.content]);

  // --- Syntax Highlighter Component ---
  const CodeBlock = ({ node, inline, className, children, ...props }: any) => {
    const match = /language-(\w+)/.exec(className || '');
    const codeTheme = theme === 'dark' ? vscDarkPlus : vs;

    return !inline && match ? (
      <SyntaxHighlighter
        style={codeTheme}
        language={match[1]}
        PreTag="div"
        {...props}
      >
        {String(children).replace(/\n$/, '')}
      </SyntaxHighlighter>
    ) : (
      <code
        className={`bg-neutral-200 dark:bg-neutral-700 px-1 py-0.5 rounded text-sm ${className || ''}`}
        {...props}
      >
        {children}
      </code>
    );
  };
  // --- End Syntax Highlighter ---

  // Extract a topic for the reply function (if needed)
  const getTopic = () => {
    const words = (processedContent.visibleContent || '').split(' ');
    return words.slice(0, 3).join(' ').replace(/[^\w\s]/gi, '');
  };

  // Determine if the message is from the system
  const isSystem = message.role === 'system';
  const hasThinking = processedContent.thinkingContent !== null;

  return (
    <div className={`
      group relative flex items-start gap-3
      ${message.role === 'user' ? 'justify-end' : ''}
    `}>
      {/* Sender Icon (AI) */}
      {message.role !== 'user' && !isSystem && (
        <Image
                src="/turtle.png"
                alt="AI Assistant Avatar"
                width={48} 
                height={48} 
                className="rounded-full object-cover"
            />
      )}

      {/* Message Bubble */}
      <div className={`
        px-4 py-3 rounded-2xl max-w-[85%] shadow-sm transition-all duration-200 ease-in-out
        ${message.role === 'user'
          ? 'bg-blue-500 dark:bg-blue-600 text-white ml-auto rounded-tr-none' // User bubble style
          : isSystem
            ? 'bg-gray-100 dark:bg-neutral-700/50 text-gray-600 dark:text-neutral-300 text-sm w-full border border-gray-200 dark:border-neutral-700' // System bubble style
            : 'bg-white dark:bg-neutral-800 border border-gray-200 dark:border-neutral-700 rounded-tl-none text-gray-800 dark:text-white'} // AI bubble style
      `}>

        {/* Visible Content Area */}
        {processedContent.visibleContent && (
          <div className="prose prose-sm dark:prose-invert max-w-none [&_p]:my-2 first:[&_p]:mt-0 last:[&_p]:mb-0">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]} // Add GFM support
              components={{
                // Customize rendering for better styling
                p: ({ node, ...props }) => <p className="mb-2 last:mb-0" {...props} />,
                ol: ({ node, ...props }) => <ol className="list-decimal list-inside my-2 pl-2" {...props} />,
                ul: ({ node, ...props }) => <ul className="list-disc list-inside my-2 pl-2" {...props} />,
                li: ({ node, ...props }) => <li className="mb-1" {...props} />,
                code: CodeBlock, // Use our custom component for code blocks
                pre: ({ node, ...props }) => <div className="my-2 rounded-md overflow-hidden bg-[#f6f8fa] dark:bg-[#1e1e1e]" {...props} />, // Wrapper for pre
                a: ({ node, ...props }) => <a className="text-blue-500 hover:underline" target="_blank" rel="noopener noreferrer" {...props} />,
              }}
            >{processedContent.visibleContent}</ReactMarkdown>
          </div>
        )}

        {/* Thinking Section Toggle and Content */}
        {hasThinking && (
          <>
            {/* Separator only if visible content also exists */}
            {processedContent.visibleContent && processedContent.visibleContent !== '(Contains only hidden thought process)' && (
              <hr className="my-2 border-gray-200 dark:border-neutral-700" />
            )}

            {/* Toggle Button */}
            <button
              onClick={() => setShowThinking(!showThinking)}
              className="flex items-center gap-1.5 text-xs text-blue-500 dark:text-blue-400 hover:text-blue-600 dark:hover:text-blue-300 font-medium py-1 rounded-md"
              aria-expanded={showThinking}
              aria-controls={`thinking-content-${message.id}`}
            >
              <BrainCircuit size={14} />
              {showThinking ? 'Hide thought process' : 'Show thought process'}
            </button>

            {/* Thinking Content (Conditional) */}
            {showThinking && (
              <div
                id={`thinking-content-${message.id}`}
                className="mt-2 p-3 rounded-lg bg-gray-100 dark:bg-neutral-700/60 border border-gray-200 dark:border-neutral-700 text-xs text-gray-600 dark:text-neutral-300 max-h-60 overflow-y-auto"
              >
                <div className="prose prose-xs dark:prose-invert max-w-none">
                  {/* Render thinking content also as markdown */}
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      p: ({ node, ...props }) => <p className="mb-1 last:mb-0" {...props} />,
                      code: CodeBlock, // Reuse code block component
                      pre: ({ node, ...props }) => <div className="my-1 rounded-md overflow-hidden bg-[#f6f8fa] dark:bg-[#1e1e1e]" {...props} />,
                    }}
                  >{processedContent.thinkingContent || ''}</ReactMarkdown>
                </div>
              </div>
            )}
          </>
        )}

        {/* Reply button (only for non-user, non-system messages) - Kept logic */}
        {message.role !== 'user' && !isSystem && (
          <div className="mt-1 text-xs text-right opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={() => onReply(getTopic())}
              className="text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200"
            >
              Reply
            </button>
          </div>
        )}
      </div>

      {/* User Icon */}
      {message.role === 'user' && (
        <div className="flex-shrink-0 w-12 h-12 rounded-full bg-gray-200 dark:bg-neutral-600 flex items-center justify-center text-gray-500 dark:text-neutral-300 text-xs font-medium shadow-sm">
          You
        </div>
      )}
    </div>
  );
};