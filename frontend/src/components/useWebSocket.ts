// frontend/src/components/useWebSocket.ts
import { useEffect, useRef, useState } from 'react'
import { SearchSettings, FileInfo } from './types'

export const useWebSocket = (
  clientId: string,
  chatId: string,
  searchSettings: SearchSettings,
  onMessage: (data: any) => void
) => {
  const wsRef = useRef<WebSocket | null>(null)
  const [isConnected, setIsConnected] = useState(false)

  useEffect(() => {
    const connect = () => {
      const ws = new WebSocket(`ws://localhost:8000/ws/${clientId}/${chatId}`)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('WebSocket connected')
        setIsConnected(true)
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
        setTimeout(connect, 3000)
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        ws.close()
      }
    }

    connect()
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [clientId, chatId])

  const send = (message: string, files?: FileInfo[]) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        message,
        files,
        ...searchSettings
      }))
    } else {
      console.warn('WebSocket is not connected')
    }
  }

  return { send, isConnected }
}