'use client'

import { useState, useEffect, useRef } from 'react'
import { v4 as uuidv4 } from 'uuid'
import { BiBrain } from 'react-icons/bi'
import { FaSearch, FaNewspaper, FaPlay, FaImage } from 'react-icons/fa'
import { FiSend } from 'react-icons/fi'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/cjs/styles/prism'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  searchResults?: SearchResult[]
  searchSummary?: string
  thinkingContent?: string
}

interface SearchResult {
  type: 'text' | 'news' | 'image' | 'video'
  title: string
  link: string
  snippet?: string
  image?: string
  thumbnail?: string
  duration?: string
  source?: string
  date?: string
}

interface ChatProps {
  chatId: string
  clientId: string
  isSidebarOpen: boolean
}

interface SearchSettings {
  webSearchEnabled: boolean
  searchType: 'text' | 'news' | 'images' | 'videos'
  showSummary: boolean
}

export default function Chat({ chatId, clientId, isSidebarOpen }: ChatProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isConnected, setIsConnected] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [searchSettings, setSearchSettings] = useState<SearchSettings>({
    webSearchEnabled: true,
    searchType: 'text',
    showSummary: false
  })
  
  const wsRef = useRef<WebSocket | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    const adjustInputHeight = () => {
      if (inputRef.current) {
        inputRef.current.style.height = 'auto'
        inputRef.current.style.height = `${inputRef.current.scrollHeight}px`
      }
    }

    adjustInputHeight()
  }, [input])

  useEffect(() => {
    const connectWebSocket = () => {
      const ws = new WebSocket(`ws://localhost:8000/ws/${clientId}/${chatId}`)
      wsRef.current = ws

      ws.onopen = () => {
        setIsConnected(true)
        setIsLoading(false)
      }

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        
        if (data.type === 'stream') {
          setMessages(prev => {
            const lastMessage = prev[prev.length - 1]
            if (lastMessage?.role === 'assistant') {
              const newContent = lastMessage.content + data.content
              const thinkMatch = newContent.match(/<think>([\s\S]*?)<\/think>/)
              let thinkContent = lastMessage.thinkingContent || ''
              let responseContent = newContent
              
              if (thinkMatch) {
                thinkContent = thinkMatch[1]
                const parts = newContent.split(/<\/think>/)
                responseContent = parts.slice(1).join('</think>').trim()
              }
              
              return [...prev.slice(0, -1), {
                ...lastMessage,
                content: responseContent,
                thinkingContent: thinkContent
              }]
            } else {
              const thinkMatch = data.content.match(/<think>([\s\S]*?)<\/think>/)
              let thinkContent = ''
              let responseContent = data.content
              
              if (thinkMatch) {
                thinkContent = thinkMatch[1]
                const parts = data.content.split(/<\/think>/)
                responseContent = parts.slice(1).join('</think>').trim()
              }
              
              return [...prev, {
                id: uuidv4(),
                role: 'assistant',
                content: responseContent,
                timestamp: new Date(),
                thinkingContent: thinkContent
              }]
            }
          })
        } else if (data.type === 'complete') {
          setMessages(prev => {
            const lastMessage = prev[prev.length - 1]
            return [...prev.slice(0, -1), {
              ...lastMessage,
              searchResults: data.search_results,
              searchSummary: data.search_summary
            }]
          })
          setIsLoading(false)
        }
      }

      ws.onclose = () => {
        setIsConnected(false)
        setTimeout(connectWebSocket, 3000)
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        setIsConnected(false)
      }
    }

    connectWebSocket()
    return () => wsRef.current?.close()
  }, [chatId, clientId])

  const sendMessage = () => {
    if (!input.trim() || !isConnected || isLoading) return

    const message = {
      id: uuidv4(),
      role: 'user',
      content: input,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, message])
    setIsLoading(true)
    wsRef.current?.send(JSON.stringify({ 
      message: input,
      ...searchSettings
    }))
    setInput('')
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const renderSearchResult = (result: SearchResult, index: number) => {
    return (
      <div key={index} className="flex gap-3 items-start p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
        {result.type === 'image' ? (
          <img 
            src={result.thumbnail || result.image}
            alt={result.title}
            className="w-16 h-16 object-cover rounded"
          />
        ) : (
          <div className="w-16 h-16 bg-gray-200 dark:bg-gray-700 rounded flex-shrink-0 flex items-center justify-center">
            {result.type === 'video' && <FaPlay className="text-gray-600 dark:text-gray-400" />}
            {result.type === 'news' && <FaNewspaper className="text-gray-600 dark:text-gray-400" />}
            {result.type === 'text' && result.link && (
              <img 
                src={`https://www.google.com/s2/favicons?domain=${new URL(result.link).hostname}&sz=64`}
                alt=""
                className="w-8 h-8"
                onError={(e) => {
                  (e.target as HTMLImageElement).style.display = 'none'
                }}
              />
            )}
          </div>
        )}
        <div className="flex-1">
          <a 
            href={result.link}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 dark:text-blue-400 hover:underline font-medium"
          >
            {result.title}
          </a>
          {result.date && (
            <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              {result.date} - {result.source}
            </div>
          )}
          {result.snippet && (
            <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">{result.snippet}</p>
          )}
          {result.duration && (
            <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Duration: {result.duration}
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-screen bg-white dark:bg-gray-800">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <div key={message.id} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[70%] rounded-lg p-4 ${
              message.role === 'user' 
                ? 'bg-blue-600 text-white' 
                : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-100'
            }`}>
              {message.role === 'assistant' && message.thinkingContent && (
                <div className="bg-gray-50 dark:bg-gray-800 rounded-lg mb-4">
                  <div className="p-4">
                    <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400 mb-2">
                      <BiBrain className="w-5 h-5" />
                      <span className="font-medium">Thinking Process</span>
                    </div>
                    <div className="border-t border-gray-200 dark:border-gray-600 -mx-4 mb-3" />
                    <div className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                      {message.thinkingContent}
                    </div>
                  </div>
                </div>
              )}

              {message.searchSummary && (
                <div className="bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-4 mb-4">
                  <div className="font-medium text-yellow-800 dark:text-yellow-200 mb-2">Search Summary</div>
                  <div className="text-yellow-700 dark:text-yellow-100">
                    {message.searchSummary}
                  </div>
                </div>
              )}
              
              {message.role === 'assistant' ? (
                <ReactMarkdown
                  className="prose dark:prose-invert max-w-none"
                  components={{
                    code({node, inline, className, children, ...props}) {
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
                    {message.searchResults.map((result, index) => renderSearchResult(result, index))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center gap-2 mb-2">
            <button
              onClick={() => setSearchSettings(prev => ({
                ...prev,
                webSearchEnabled: !prev.webSearchEnabled
              }))}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                searchSettings.webSearchEnabled 
                  ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 hover:bg-blue-200 dark:hover:bg-blue-800' 
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
              }`}
            >
              <FaSearch className="w-4 h-4" />
              Web Search {searchSettings.webSearchEnabled ? 'On' : 'Off'}
            </button>
            
            {searchSettings.webSearchEnabled && (
              <>
                <select
                  value={searchSettings.searchType}
                  onChange={(e) => setSearchSettings(prev => ({
                    ...prev,
                    searchType: e.target.value as any
                  }))}
                  className="px-3 py-1.5 rounded-lg text-sm font-medium border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-200"
                >
                  <option value="text">Text Search</option>
                  <option value="news">News</option>
                  <option value="images">Images</option>
                  <option value="videos">Videos</option>
                </select>
                
                <button
                  onClick={() => setSearchSettings(prev => ({
                    ...prev,
                    showSummary: !prev.showSummary
                  }))}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                    searchSettings.showSummary 
                      ? 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300' 
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
                  }`}
                >
                  Auto-Summarize
                </button>
              </>
            )}
          </div>

          <div className="flex gap-2">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              className="flex-1 min-h-[44px] max-h-[200px] px-4 py-2 border border-gray-200 dark:border-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 resize-none"
              placeholder="Type your message..."
              disabled={!isConnected || isLoading}
            />
            <button
              onClick={sendMessage}
              disabled={!isConnected || isLoading || !input.trim()}
              className={`flex items-center justify-center w-10 h-10 rounded-lg transition-colors ${
                isConnected && !isLoading && input.trim()
                  ? 'bg-blue-600 hover:bg-blue-700 text-white'
                  : 'bg-gray-300 dark:bg-gray-600 text-gray-500 dark:text-gray-400 cursor-not-allowed'
              }`}
            >
              <FiSend className="w-5 h-5" />
            </button>
          </div>

          <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
            {!isConnected && (
              <span className="text-red-500">Disconnected - Reconnecting...</span>
            )}
            {isLoading && (
              <span className="text-blue-500">Generating response...</span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}