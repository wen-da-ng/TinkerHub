'use client'

import { useState, useEffect } from 'react'
import Chat from '../components/Chat'
import { SystemInfo } from '../components/SystemInfo'
import { v4 as uuidv4 } from 'uuid'
import { FiPlus, FiTrash2 } from 'react-icons/fi'
import { ChatSession, HubFile } from '../components/types'

export default function Home() {
  const [clientId] = useState(() => uuidv4())
  const [chats, setChats] = useState<ChatSession[]>(() => {
    const initial = { id: uuidv4(), name: 'New Chat', created: new Date() }
    return [initial]
  })
  const [currentChat, setCurrentChat] = useState<ChatSession>(chats[0])
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)

  const createNewChat = () => {
    const newChat = { 
      id: uuidv4(), 
      name: `Chat ${chats.length + 1}`,
      created: new Date()
    }
    setChats(prev => [...prev, newChat])
    setCurrentChat(newChat)
  }

  const deleteChat = (chatId: string) => {
    setChats(prev => {
      const updatedChats = prev.filter(chat => chat.id !== chatId)
      if (currentChat.id === chatId && updatedChats.length > 0) {
        setCurrentChat(updatedChats[0])
      }
      return updatedChats
    })
  }

  const switchChat = (chat: ChatSession) => {
    setCurrentChat(chat)
  }

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()

    const files = Array.from(e.dataTransfer.files)
    const hubFile = files.find(file => file.name.endsWith('.hub'))

    if (hubFile) {
      try {
        const content = await hubFile.text()
        const data: HubFile = JSON.parse(content)
        
        // Generate a new chat ID for the imported chat
        const importedChatId = uuidv4()
        
        // Create new chat with loaded data
        const newChat: ChatSession = {
          id: importedChatId,
          name: data.metadata?.title || hubFile.name.replace('.hub', '') || `Imported Chat ${chats.length + 1}`,
          created: new Date(data.metadata?.created || Date.now()),
          hubFile: {
            ...data,
            chatId: importedChatId // Update the chatId in the hubFile
          }
        }

        setChats(prev => [...prev, newChat])
        setCurrentChat(newChat)
      } catch (error) {
        console.error('Error loading .hub file:', error)
      }
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
  }

  return (
    <div 
      className="flex h-screen bg-gray-50 dark:bg-gray-900"
      onDrop={handleDrop}
      onDragOver={handleDragOver}
    >
      <div className={`${isSidebarOpen ? 'w-64' : 'w-0'} transition-all duration-300 ease-in-out overflow-hidden`}>
        <div className="h-full flex flex-col bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700">
          <div className="flex-1 p-4">
            <button
              onClick={createNewChat}
              className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white p-2 rounded-lg mb-4 transition-colors"
            >
              <FiPlus className="w-4 h-4" />
              <span>New Chat</span>
            </button>
            <div className="space-y-2">
              {chats.map((chat) => (
                <div
                  key={chat.id}
                  className={`group flex items-center justify-between p-2 rounded-lg cursor-pointer transition-colors ${
                    currentChat.id === chat.id 
                      ? 'bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200' 
                      : 'hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-800 dark:text-gray-200'
                  }`}
                >
                  <div
                    className="flex-1"
                    onClick={() => switchChat(chat)}
                  >
                    {chat.name}
                  </div>
                  {chats.length > 1 && (
                    <button
                      onClick={() => deleteChat(chat.id)}
                      className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-gray-200 dark:hover:bg-gray-600 rounded"
                    >
                      <FiTrash2 className="w-4 h-4 text-gray-500 dark:text-gray-400" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
          
          <SystemInfo />
        </div>
      </div>

      <button
        onClick={() => setIsSidebarOpen(!isSidebarOpen)}
        className="fixed left-0 top-4 z-10 p-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-r-lg shadow-md"
        style={{ transform: isSidebarOpen ? 'translateX(256px)' : 'translateX(0)' }}
      >
        <svg
          className={`w-4 h-4 transition-transform ${isSidebarOpen ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 5l7 7-7 7"
          />
        </svg>
      </button>

      <div className="flex-1">
        <Chat 
          chatId={currentChat.id} 
          clientId={clientId}
          isSidebarOpen={isSidebarOpen}
        />
      </div>
    </div>
  )
}