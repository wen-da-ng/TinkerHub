// frontend/src/components/useWebSocket.ts
import { useEffect, useRef, useState, useCallback } from 'react'
import { SearchSettings, FileInfo, WebSocketMessage, GetModelsRequest } from './types'

// Keep track of active connections globally to prevent duplicates
const activeConnections = new Map<string, WebSocket>()

export const useWebSocket = (
  clientId: string,
  chatId: string,
  searchSettings: SearchSettings,
  onMessage: (data: WebSocketMessage) => void
) => {
  const wsRef = useRef<WebSocket | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>()
  const connectionKey = `${clientId}-${chatId}`

  useEffect(() => {
    const connect = () => {
      // Check if a connection already exists for this client/chat pair
      if (activeConnections.has(connectionKey)) {
        console.log(`Reusing existing WebSocket for ${connectionKey}`)
        wsRef.current = activeConnections.get(connectionKey)!
        setIsConnected(wsRef.current.readyState === WebSocket.OPEN)
        return
      }

      console.log(`Creating new WebSocket for ${connectionKey}`)
      const ws = new WebSocket(`ws://localhost:8000/ws/${clientId}/${chatId}`)
      wsRef.current = ws
      activeConnections.set(connectionKey, ws)

      ws.onopen = () => {
        console.log(`WebSocket connected for ${connectionKey}`)
        setIsConnected(true)
        // Request available models when connection is established
        const getModelsRequest: GetModelsRequest = { type: 'get_models' }
        ws.send(JSON.stringify(getModelsRequest))
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          onMessage(data)
        } catch (error) {
          console.error('Error parsing message:', error)
        }
      }

      ws.onclose = (event) => {
        console.log(`WebSocket closed for ${connectionKey}, code: ${event.code}, reason: ${event.reason}`)
        setIsConnected(false)
        wsRef.current = null
        
        // Remove from active connections
        activeConnections.delete(connectionKey)
        
        // Only reconnect if this wasn't a clean close
        if (event.code !== 1000) {
          // Clear any existing reconnection timeout
          if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current)
          }
          
          // Set up reconnection attempt
          reconnectTimeoutRef.current = setTimeout(connect, 3000)
        }
      }

      ws.onerror = (event) => {
        console.error('WebSocket error:', event)
        // Don't close here, let the onclose handler handle it
      }
    }

    connect()
    
    // Cleanup function
    return () => {
      console.log(`Cleanup for ${connectionKey}`)
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      // Don't close the WebSocket here, it might be used by other components
      // Just remove our reference to it
      wsRef.current = null
    }
  }, [clientId, chatId, connectionKey, onMessage])

  const send = useCallback((message: string, files?: FileInfo[], model?: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        message,
        files,
        model,
        ...searchSettings
      }))
    } else {
      console.warn(`WebSocket not connected for ${connectionKey}`)
    }
  }, [connectionKey, searchSettings])

  const sendMessage = useCallback((data: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data))
    } else {
      console.warn(`WebSocket not connected for ${connectionKey}`)
    }
  }, [connectionKey])

  const requestModels = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const getModelsRequest: GetModelsRequest = { type: 'get_models' }
      wsRef.current.send(JSON.stringify(getModelsRequest))
    } else {
      console.warn(`WebSocket not connected for ${connectionKey}`)
    }
  }, [connectionKey])

  return { 
    send, 
    sendMessage,
    isConnected,
    requestModels 
  }
}