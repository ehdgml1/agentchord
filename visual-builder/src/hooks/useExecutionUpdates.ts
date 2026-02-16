import { useState, useEffect, useRef, useCallback } from 'react';
import type { Execution } from '../types';

/**
 * WebSocket hook for real-time execution updates
 *
 * Connects to the debug WebSocket endpoint and receives live execution updates.
 * Automatically reconnects on connection loss.
 *
 * @param executionId - The execution ID to monitor, or null to disconnect
 * @returns The latest execution state from the WebSocket
 */
export function useExecutionUpdates(executionId: string | null) {
  const [execution, setExecution] = useState<Execution | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttemptsRef = useRef(0);

  const connect = useCallback(() => {
    if (!executionId) return;

    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws/debug/${executionId}`;

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        setError(null);
        reconnectAttemptsRef.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === 'execution_update' && data.execution) {
            setExecution(data.execution);
          } else if (data.type === 'node_update' && data.nodeExecution) {
            // Update specific node execution within the current execution
            setExecution((prev) => {
              if (!prev) return prev;

              const exists = prev.nodeExecutions.some(
                (ne) => ne.nodeId === data.nodeExecution.nodeId
              );

              return {
                ...prev,
                nodeExecutions: exists
                  ? prev.nodeExecutions.map((ne) =>
                      ne.nodeId === data.nodeExecution.nodeId
                        ? data.nodeExecution
                        : ne
                    )
                  : [...prev.nodeExecutions, data.nodeExecution],
              };
            });
          } else if (data.type === 'error') {
            if (import.meta.env.DEV) console.error('[WS] Server error:', data.message);
            setError(data.message);
          }
        } catch (err) {
          if (import.meta.env.DEV) console.error('[WS] Failed to parse message:', err);
        }
      };

      ws.onerror = (event) => {
        if (import.meta.env.DEV) console.error('[WS] WebSocket error:', event);
        setError('WebSocket connection error');
        setIsConnected(false);
      };

      ws.onclose = (event) => {
        setIsConnected(false);
        wsRef.current = null;

        // Attempt to reconnect with exponential backoff if not a normal closure
        if (event.code !== 1000 && executionId) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000);
          reconnectAttemptsRef.current += 1;
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        }
      };
    } catch (err) {
      if (import.meta.env.DEV) console.error('[WS] Failed to create WebSocket:', err);
      setError(err instanceof Error ? err.message : 'Failed to connect');
    }
  }, [executionId]);

  useEffect(() => {
    if (!executionId) {
      // Clean up connection if executionId becomes null
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmounted or execution changed');
        wsRef.current = null;
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      reconnectAttemptsRef.current = 0;
      setExecution(null);
      setIsConnected(false);
      setError(null);
      return;
    }

    reconnectAttemptsRef.current = 0;
    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmounted or execution changed');
        wsRef.current = null;
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
    };
  }, [executionId, connect]);

  return {
    execution,
    isConnected,
    error,
  };
}
