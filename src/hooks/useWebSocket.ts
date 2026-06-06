import { useEffect, useRef, useCallback } from 'react'
import { WS_URL } from '../services/api'

// eslint-disable-next-line @typescript-eslint/no-explicit-any

export function useWebSocket(
  userId: string | null,
  onMessage: (data: Record<string, unknown>) => void
) {
  const ws = useRef<WebSocket | null>(null)
  const reconnectTimeout = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const isMounted = useRef(true)

  const connect = useCallback(() => {
    if (!userId || !isMounted.current) return

    const token = localStorage.getItem('access_token')
    if (!token) return

    const url = `${WS_URL}/ws/${userId}?token=${token}`

    try {
      ws.current = new WebSocket(url)

      ws.current.onopen = () => {
        clearTimeout(reconnectTimeout.current)
      }

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          onMessage(data)
        } catch {
          // ignore malformed messages
        }
      }

      ws.current.onclose = () => {
        if (isMounted.current) {
          reconnectTimeout.current = setTimeout(connect, 3000)
        }
      }

      ws.current.onerror = () => {
        ws.current?.close()
      }
    } catch {
      reconnectTimeout.current = setTimeout(connect, 5000)
    }
  }, [userId, onMessage])

  useEffect(() => {
    isMounted.current = true
    connect()
    return () => {
      isMounted.current = false
      clearTimeout(reconnectTimeout.current)
      ws.current?.close()
    }
  }, [connect])
}
