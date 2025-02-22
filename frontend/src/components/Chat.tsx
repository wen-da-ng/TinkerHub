// frontend/src/components/Chat.tsx
'use client'

import { useState, useEffect, useRef } from 'react'
import { v4 as uuidv4 } from 'uuid'
import { Message, SearchSettings as SearchSettingsType, ChatProps, FileInfo, ModelInfo } from './types'
import { useWebSocket } from './useWebSocket'
import { MessageBubble } from './MessageBubble'
import { ChatInput } from './ChatInput'
import { SearchSettings } from './SearchSettings'
import { ModelSelector } from './ModelSelector'
import { DEFAULT_SEARCH_SETTINGS, MESSAGES } from './config'

export default function Chat({ chatId, clientId, isSidebarOpen }: ChatProps) {
    const [messages, setMessages] = useState<Message[]>([])
    const [isLoading, setIsLoading] = useState(false)
    const [searchSettings, setSearchSettings] = useState<SearchSettingsType>(DEFAULT_SEARCH_SETTINGS)
    const [availableModels, setAvailableModels] = useState<ModelInfo[]>([])
    const [selectedModel, setSelectedModel] = useState<string>("")
    const [error, setError] = useState<string>("")
    const messagesEndRef = useRef<HTMLDivElement>(null)
  
    const { send, isConnected, requestModels } = useWebSocket(clientId, chatId, searchSettings, (data) => {
      if (data.type === 'stream') {
        setMessages(prev => processStreamMessage(prev, data.content))
      } else if (data.type === 'complete') {
        setMessages(prev => addSearchResults(prev, data.search_results, data.search_summary))
        setIsLoading(false)
      } else if (data.type === 'models') {
        setAvailableModels(data.models || [])
      } else if (data.type === 'error') {
        setError(data.message)
        setIsLoading(false)
      }
    })

    useEffect(() => {
      if (isConnected) {
        requestModels()
      }
    }, [isConnected])

    useEffect(() => {
      if (availableModels.length > 0 && !selectedModel) {
        setSelectedModel(availableModels[0].name)
      }
    }, [availableModels])

    const processStreamMessage = (prev: Message[], content: string) => {
        const lastMessage = prev[prev.length - 1]
        const thinkMatch = content.match(/<think>([\s\S]*?)<\/think>/)
        
        if (lastMessage?.role === 'assistant') {
          return updateExistingMessage(prev, content, thinkMatch)
        }
        return createNewMessage(prev, content, thinkMatch)
    }
      
    const updateExistingMessage = (prev: Message[], content: string, thinkMatch: RegExpMatchArray | null) => {
        const lastMessage = prev[prev.length - 1]
        const newContent = lastMessage.content + content
        const allThinkMatch = newContent.match(/<think>([\s\S]*?)<\/think>/)
        
        let thinkContent = lastMessage.thinkingContent || ''
        let responseContent = newContent
      
        if (allThinkMatch) {
          thinkContent = allThinkMatch[1]
          const parts = newContent.split('</think>')
          responseContent = parts[parts.length - 1].trim()
        }
        
        return [
          ...prev.slice(0, -1), 
          { 
            ...lastMessage, 
            content: responseContent, 
            thinkingContent: thinkContent,
            model: selectedModel
          }
        ]
    }

    const createNewMessage = (prev: Message[], content: string, thinkMatch: RegExpMatchArray | null) => {
        const { thinkContent, responseContent } = parseThinkContent(content, thinkMatch)
        
        return [
          ...prev,
          {
            id: uuidv4(),
            role: 'assistant',
            content: responseContent,
            timestamp: new Date(),
            thinkingContent: thinkContent,
            model: selectedModel
          }
        ]
    }

    const parseThinkContent = (content: string, thinkMatch: RegExpMatchArray | null) => {
        if (!thinkMatch) return { thinkContent: '', responseContent: content }
        
        const thinkContent = thinkMatch[1]
        const responseContent = content.split('</think>')[1]?.trim() || ''
        return { thinkContent, responseContent }
    }

    const addSearchResults = (prev: Message[], results: any, summary: string) => {
        const lastMessage = prev[prev.length - 1]
        return [
          ...prev.slice(0, -1),
          { ...lastMessage, searchResults: results, searchSummary: summary }
        ]
    }

    const sendMessage = (input: string, files?: FileInfo[]) => {
        if (!selectedModel) {
            setError("Please wait for models to load or select a model")
            return
        }
        
        const message = {
          id: uuidv4(),
          role: 'user',
          content: input,
          timestamp: new Date(),
          files: files,
          model: selectedModel
        }
        
        setMessages(prev => [...prev, message])
        setIsLoading(true)
        setError("")
        send(input, files, selectedModel)
    }

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages])

    return (
        <div className="flex flex-col h-screen bg-white dark:bg-gray-800">
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((message) => (
              <div key={message.id} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <MessageBubble message={message} />
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          <div className="border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
            <div className="max-w-4xl mx-auto">
              <div className="flex flex-wrap items-center gap-2 mb-4">
                <ModelSelector
                  models={availableModels}
                  selectedModel={selectedModel}
                  onModelChange={setSelectedModel}
                  disabled={!isConnected || isLoading}
                />
                <SearchSettings 
                  settings={searchSettings}
                  onChange={setSearchSettings}
                />
              </div>
              
              <ChatInput 
                onSend={sendMessage}
                disabled={!isConnected || isLoading || !selectedModel}
              />

              <div className="mt-2 text-xs">
                {!isConnected && <span className="text-red-500">{MESSAGES.disconnected}</span>}
                {isLoading && <span className="text-blue-500">{MESSAGES.generating}</span>}
                {error && <span className="text-red-500">{error}</span>}
              </div>
            </div>
          </div>
        </div>
    )
}