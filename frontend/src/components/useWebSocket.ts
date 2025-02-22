// frontend/src/components/useWebSocket.ts
import { useEffect, useRef, useState } from 'react'
import { SearchSettings, FileInfo, WebSocketMessage, GetModelsRequest } from './types'

export const useWebSocket = (
  clientId: string,
  chatId: string,
  searchSettings: SearchSettings,
  onMessage: (data: WebSocketMessage) => void
) => {
  const wsRef = useRef<WebSocket | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>()

  useEffect(() => {
    const connect = () => {
      const ws = new WebSocket(`ws://localhost:8000/ws/${clientId}/${chatId}`)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('WebSocket connected')
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

      ws.onclose = () => {
        console.log('WebSocket closed, reconnecting...')
        setIsConnected(false)
        wsRef.current = null
        
        // Clear any existing reconnection timeout
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current)
        }
        
        // Set up reconnection attempt
        reconnectTimeoutRef.current = setTimeout(connect, 3000)
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        ws.close()
      }
    }

    connect()
    
    // Cleanup function
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [clientId, chatId])

  const send = (message: string, files?: FileInfo[], model?: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        message,
        files,
        model,
        ...searchSettings
      }))
    } else {
      console.warn('WebSocket is not connected')
    }
  }

  const requestModels = () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const getModelsRequest: GetModelsRequest = { type: 'get_models' }
      wsRef.current.send(JSON.stringify(getModelsRequest))
    }
  }

  return { 
    send, 
    isConnected,
    requestModels 
  }
}