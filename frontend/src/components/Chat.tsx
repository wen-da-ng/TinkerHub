'use client'

import { useState, useEffect, useRef } from 'react'
import { v4 as uuidv4 } from 'uuid'
import { Message, SearchSettings as SearchSettingsType, ChatProps, FileInfo, ModelInfo, HubFile, Notification } from './types'
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
    const [notification, setNotification] = useState<Notification | null>(null)
    const messagesEndRef = useRef<HTMLDivElement>(null)
    const firstRenderRef = useRef(true)
    const loadingStateRef = useRef(false)
  
    const { send, sendMessage, isConnected, requestModels } = useWebSocket(clientId, chatId, searchSettings, (data) => {
      if (data.type === 'stream') {
        setMessages(prev => processStreamMessage(prev, data.content))
      } else if (data.type === 'complete') {
        setMessages(prev => addSearchResults(prev, data.search_results, data.search_summary))
        setIsLoading(false)
        loadingStateRef.current = false
      } else if (data.type === 'models') {
        setAvailableModels(data.models || [])
      } else if (data.type === 'error') {
        setError(data.message)
        setIsLoading(false)
        loadingStateRef.current = false
      } else if (data.type === 'hub_import_response') {
        handleHubImportResponse(data)
      } else if (data.type === 'hub_export_response') {
        handleHubExportResponse(data)
      } else if (data.type === 'conversation_history') {
        if (data.messages) {
          setMessages(data.messages.map((msg: any) => ({
            id: uuidv4(),
            role: msg.role,
            content: msg.content,
            timestamp: new Date(msg.metadata?.timestamp || new Date()),
            thinkingContent: msg.metadata?.thinkingContent || '',
            searchResults: msg.metadata?.searchResults || [],
            searchSummary: msg.metadata?.searchSummary || '',
            files: msg.metadata?.files || [],
            model: msg.metadata?.model || selectedModel
          })))
        }
      }
    })

    useEffect(() => {
      if (isConnected && firstRenderRef.current) {
        requestModels()
        firstRenderRef.current = false
      }
    }, [isConnected, requestModels])

    useEffect(() => {
      if (availableModels.length > 0 && !selectedModel) {
        setSelectedModel(availableModels[0].name)
      }
    }, [availableModels])

    const showNotification = (type: 'success' | 'error' | 'info', message: string) => {
      setNotification({ type, message })
      setTimeout(() => setNotification(null), 3000)
    }

    const handleHubImportResponse = async (data: { success: boolean, error?: string }) => {
      if (data.success) {
        // Request conversation history after successful import
        sendMessage({
          type: 'get_conversation_history',
          chatId
        })
        showNotification('success', 'Chat session imported successfully')
      } else {
        showNotification('error', data.error || 'Failed to import chat session')
      }
    }

    const handleHubExportResponse = (data: { success: boolean, data?: HubFile, error?: string }) => {
      if (data.success && data.data) {
        const hubFile = data.data
        const blob = new Blob([JSON.stringify(hubFile, null, 2)], { type: 'application/json' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `chat-${new Date().toISOString()}.hub`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
        showNotification('success', 'Chat session exported successfully')
      } else {
        showNotification('error', data.error || 'Failed to export chat session')
      }
    }

    useEffect(() => {
      // Request conversation history when chat ID changes
      if (chatId && isConnected) {
        sendMessage({
          type: 'get_conversation_history',
          chatId
        })
      }
    }, [chatId, isConnected])

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

    const handleSendMessage = (input: string, files?: FileInfo[]) => {
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
        loadingStateRef.current = true
        setError("")
        send(input, files, selectedModel)
    }

    const saveSession = () => {
      if (loadingStateRef.current) {
        showNotification('error', 'Please wait for the current response to complete')
        return
      }
      sendMessage({
        type: 'hub_export',
        chatId
      })
    }

    const loadSession = async (file: File) => {
      if (loadingStateRef.current) {
        showNotification('error', 'Please wait for the current response to complete')
        return
      }
      try {
        const content = await file.text()
        const hubFile: HubFile = JSON.parse(content)
        
        if (!hubFile.version || !hubFile.messages) {
          throw new Error('Invalid .hub file format')
        }

        // Update hubFile with current chatId
        hubFile.chatId = chatId

        sendMessage({
          type: 'hub_import',
          hubFile,
          chatId
        })
      } catch (error) {
        showNotification('error', 'Failed to load chat session')
      }
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
                onSend={handleSendMessage}
                onSaveHub={saveSession}
                onLoadHub={loadSession}
                disabled={!isConnected || isLoading || !selectedModel}
              />

              <div className="mt-2 text-xs">
                {!isConnected && <span className="text-red-500">{MESSAGES.disconnected}</span>}
                {isLoading && <span className="text-blue-500">{MESSAGES.generating}</span>}
                {error && <span className="text-red-500">{error}</span>}
              </div>
            </div>
          </div>

          {notification && (
            <div className={`fixed bottom-4 right-4 px-4 py-2 rounded-lg shadow-lg ${
              notification.type === 'success' 
                ? 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300'
                : notification.type === 'error'
                ? 'bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300'
                : 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300'
            }`}>
              {notification.message}
            </div>
          )}
        </div>
    )
}