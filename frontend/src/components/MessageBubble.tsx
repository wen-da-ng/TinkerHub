import { FC } from 'react'
import { Message } from './types'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/cjs/styles/prism'
import { FaVolumeUp } from 'react-icons/fa'
import { BiBrain } from 'react-icons/bi'
import { FiFile } from 'react-icons/fi'

export const MessageBubble: FC<{ message: Message }> = ({ message }) => {
  const stripMarkdown = (text: string) => {
    if (!text) return '';
    
    // Process array-like text
    if ((text.startsWith('[') && text.endsWith(']')) || (text.startsWith("['") && text.endsWith("']"))) {
      try {
        const matches = text.match(/['"](.+?)['"]/g);
        if (matches) {
          const items = matches.map(m => m.replace(/^['"]|['"]$/g, '').trim()).filter(Boolean);
          return items.join('. ') + (items[items.length-1].endsWith('.') ? '' : '.');
        }
      } catch (e) {
        console.warn('Error processing array-like text:', e);
      }
    }
    
    // Remove markdown formatting
    return removeMarkdownFormatting(text);
  };
  
  const removeMarkdownFormatting = (text: string) => {
    // Remove code blocks with a placeholder
    let cleaned = text.replace(/```[\s\S]*?```/g, 'Code block omitted.');
    
    // Remove inline code
    cleaned = cleaned.replace(/`([^`]+)`/g, '$1');
    
    // Remove headers
    cleaned = cleaned.replace(/^#{1,6}\s+(.+)$/gm, '$1');
    
    // Remove emphasis markers
    cleaned = cleaned.replace(/(\*\*|__)(.*?)\1/g, '$2');
    cleaned = cleaned.replace(/(\*|_)(.*?)\1/g, '$2');
    
    // Convert links to plain text
    cleaned = cleaned.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1');
    
    // Convert list items to natural speech
    cleaned = cleaned.replace(/^\s*[\-\*\+]\s+/gm, '• ');
    cleaned = cleaned.replace(/^\s*\d+\.\s+/gm, '. ');
    
    // Remove HTML tags (except for thinking tags)
    cleaned = cleaned.replace(/<(?!think)(?!\/think)[^>]+>/g, '');
    
    // Remove userStyle tags
    cleaned = cleaned.replace(/<userStyle>.*?<\/userStyle>/g, '');
    
    // Normalize punctuation
    cleaned = cleaned.replace(/\.{2,}/g, '...');
    cleaned = cleaned.replace(/\.(\s*\.)+/g, '.');
    cleaned = cleaned.replace(/\,(\s*\.)+/g, '.');
    
    // Remove solitary periods on their own line
    cleaned = cleaned.replace(/^\s*\.\s*$/gm, '');
    
    // Normalize whitespace
    cleaned = cleaned.replace(/\n{3,}/g, '\n\n');
    cleaned = cleaned.replace(/\s{2,}/g, ' ');
    
    // Ensure proper sentence spacing
    cleaned = cleaned.replace(/([.!?])\s*([A-Z])/g, '$1 $2');
    
    return cleaned.trim();
  };

  const requestAudioPlayback = async (content: string) => {
    try {
      const cleanedContent = stripMarkdown(content);
      console.log("Original content length:", content.length);
      console.log("Cleaned content length:", cleanedContent.length);
      
      const response = await fetch('http://localhost:8000/tts/play', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: cleanedContent }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to generate audio');
      }
    } catch (error) {
      console.error('Error playing audio:', error);
    }
  };

  return (
    <div className={`max-w-[70%] rounded-lg p-4 ${
      message.role === 'user' 
        ? 'bg-blue-600 text-white' 
        : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-100'
    }`}>
      <div className="flex justify-between items-start gap-2">
        <div className="flex-1 overflow-hidden">
          {message.files && message.files.length > 0 && (
            <div className="mb-4 space-y-2">
              <div className="font-medium text-sm opacity-80">Uploaded Files:</div>
              <div className="flex flex-wrap gap-2">
                {message.files.map((file, index) => (
                  <div 
                    key={index}
                    className="flex flex-col items-start gap-2 p-3 bg-opacity-20 bg-gray-500 rounded-lg"
                  >
                    {file.isImage && file.imageData ? (
                      <>
                        <img 
                          src={file.imageData} 
                          alt={file.name}
                          className="max-w-[300px] max-h-[300px] rounded-lg object-contain"
                        />
                        {file.caption && (
                          <div className="text-sm text-gray-200 dark:text-gray-300 italic">
                            "{file.caption}"
                          </div>
                        )}
                        <div className="flex items-center gap-2 text-sm">
                          <FiFile className="w-4 h-4" />
                          <span className="truncate max-w-[150px]">{file.name}</span>
                        </div>
                      </>
                    ) : (
                      <div className="flex items-center gap-2">
                        <FiFile className="w-4 h-4" />
                        <span className="truncate max-w-[150px]">{file.name}</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {message.role === 'assistant' && message.thinkingContent && (
            <div className="bg-gray-50 dark:bg-gray-800 rounded-lg mb-4">
              <div className="p-4">
                <div className="flex items-center justify-between gap-2 text-gray-600 dark:text-gray-400 mb-2">
                  <span className="font-medium">Thinking Process</span>
                  <button
                    onClick={() => requestAudioPlayback(message.thinkingContent!)}
                    className="flex-shrink-0 p-2 rounded-full hover:bg-gray-200 dark:hover:bg-gray-600"
                    title="Play thinking process audio"
                  >
                    <BiBrain className="w-4 h-4" />
                  </button>
                </div>
                <div className="border-t border-gray-200 dark:border-gray-600 -mx-4 mb-3" />
                <div className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap break-words">
                  {message.thinkingContent}
                </div>
              </div>
            </div>
          )}

          {message.role === 'assistant' ? (
            <div className="prose dark:prose-invert max-w-none overflow-hidden break-words">
              <ReactMarkdown
                components={{
                  code({ inline, className, children, ...props }) {
                    const match = /language-(\w+)/.exec(className || '')
                    return !inline && match ? (
                      <SyntaxHighlighter
                        style={oneDark}
                        language={match[1]}
                        PreTag="div"
                        className="rounded-md"
                        {...props}
                      >
                        {String(children).replace(/\n$/, '')}
                      </SyntaxHighlighter>
                    ) : (
                      <code className={`${className} bg-gray-200 dark:bg-gray-800 rounded px-1`} {...props}>
                        {children}
                      </code>
                    )
                  }
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          ) : (
            <div className="whitespace-pre-wrap break-words">{message.content}</div>
          )}

          {message.searchResults && message.searchResults.length > 0 && (
            <div className="mt-4 border-t border-gray-200 dark:border-gray-600 pt-4">
              <div className="font-semibold mb-2">Search Results:</div>
              <div className="space-y-3">
                {message.searchResults.map((result, index) => (
                  <div key={index} className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
                    <a 
                      href={result.link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 dark:text-blue-400 hover:underline font-medium"
                    >
                      {result.title}
                    </a>
                    {result.snippet && (
                      <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">
                        {result.snippet}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {message.searchSummary && (
            <div className="mt-4 border-t border-gray-200 dark:border-gray-600 pt-4">
              <div className="font-semibold mb-2">Search Summary:</div>
              <div className="text-sm text-gray-600 dark:text-gray-300">
                {message.searchSummary}
              </div>
            </div>
          )}
        </div>
        
        {message.role === 'assistant' && (
          <button
            onClick={() => requestAudioPlayback(message.content)}
            className="flex-shrink-0 p-2 rounded-full hover:bg-gray-200 dark:hover:bg-gray-600"
            title="Play response audio"
          >
            <FaVolumeUp className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
};