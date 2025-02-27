import { FC } from 'react'
import { Message } from './types'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/cjs/styles/prism'
import { FaVolumeUp } from 'react-icons/fa'
import { BiBrain } from 'react-icons/bi'
import { FiFile } from 'react-icons/fi'

export const MessageBubble: FC<{ message: Message }> = ({ message }) => {
  const requestAudioPlayback = async (content: string) => {
    try {
      const response = await fetch('http://localhost:8000/tts/play', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: content }),
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
        <div className="flex-1">
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
                <div className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                  {message.thinkingContent}
                </div>
              </div>
            </div>
          )}

          {message.role === 'assistant' ? (
            <ReactMarkdown
              className="prose dark:prose-invert max-w-none"
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
          ) : (
            <div className="whitespace-pre-wrap">{message.content}</div>
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