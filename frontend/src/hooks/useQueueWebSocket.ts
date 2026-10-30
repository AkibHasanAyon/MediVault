import { useState, useEffect, useRef, useCallback } from 'react';

export interface QueueWebSocketEvent {
  event: string;
  clinic_id: string;
  doctor_id?: string | null;
  timestamp: string;
  data: any;
}

export function useQueueWebSocket(
  clinicId?: string,
  doctorId?: string,
  onEvent?: (event: QueueWebSocketEvent) => void
) {
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [lastEvent, setLastEvent] = useState<QueueWebSocketEvent | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);

  const connect = useCallback(() => {
    if (!clinicId) return;

    // Build URL with JWT token if available
    const token = localStorage.getItem('access_token');
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;

    let wsUrl = `${protocol}//${host}/ws/queue/${clinicId}/`;
    if (doctorId) {
      wsUrl = `${protocol}//${host}/ws/queue/${clinicId}/doctor/${doctorId}/`;
    }
    if (token) {
      wsUrl += `?token=${encodeURIComponent(token)}`;
    }

    try {
      const socket = new WebSocket(wsUrl);
      socketRef.current = socket;

      socket.onopen = () => {
        setIsConnected(true);
      };

      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.event) {
            setLastEvent(payload);
            if (onEvent) {
              onEvent(payload);
            }
          }
        } catch {
          // Non-JSON message or ping response
        }
      };

      socket.onclose = () => {
        setIsConnected(false);
        // Exponential reconnect attempt
        reconnectTimeoutRef.current = window.setTimeout(() => {
          connect();
        }, 3000);
      };

      socket.onerror = () => {
        socket.close();
      };
    } catch {
      setIsConnected(false);
    }
  }, [clinicId, doctorId, onEvent]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, [connect]);

  const sendAction = useCallback((action: string, payload: Record<string, any> = {}) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ action, ...payload }));
    }
  }, []);

  return { isConnected, lastEvent, sendAction };
}

