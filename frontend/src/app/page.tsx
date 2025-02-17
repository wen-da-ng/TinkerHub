// frontend/src/app/page.tsx

'use client'

import { useState, useEffect } from 'react'
import Chat from '../components/Chat'
import { v4 as uuidv4 } from 'uuid'
import { FiPlus, FiTrash2 } from 'react-icons/fi'

interface ChatSession {
  id: string
  name: string
  created: Date
}

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
    setChats(prev => prev.filter(chat => chat.id !== chatId))
    if (currentChat.id === chatId) {
      setCurrentChat(chats[0])
    }
  }

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
      {/* Sidebar */}
      <div className={`${isSidebarOpen ? 'w-64' : 'w-0'} transition-all duration-300 ease-in-out`}>
        <div className="h-full bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 p-4">
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
                  onClick={() => setCurrentChat(chat)}
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
      </div>

      {/* Toggle Sidebar Button */}
      <button
        onClick={() => setIsSidebarOpen(!isSidebarOpen)}
        className="fixed left-0 top-4 z-10 p-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-r-lg shadow-md"
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

      {/* Main Content */}
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