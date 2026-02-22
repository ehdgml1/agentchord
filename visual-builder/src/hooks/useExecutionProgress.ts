import { useState, useEffect, useCallback } from 'react';
import { useAuthStore } from '../stores/authStore';
import { useExecutionStore } from '../stores/executionStore';

export interface ExecutionEvent {
  type: 'started' | 'node_started' | 'node_completed' | 'completed' | 'failed' | 'done';
  data: Record<string, unknown>;
  timestamp: string;
}

export function useExecutionProgress(executionId: string | null) {
  const [events, setEvents] = useState<ExecutionEvent[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [connectedId, setConnectedId] = useState<string | null>(null);
  const token = useAuthStore(s => s.token);
  const setNodeStatus = useExecutionStore(s => s.setNodeStatus);
  const resetNodeStatuses = useExecutionStore(s => s.resetNodeStatuses);

  const connect = useCallback(() => {
    if (!executionId || !token) {
      setConnectedId(null);
      return;
    }

    // EventSource doesn't support custom headers, use fetch-based SSE
    const controller = new AbortController();

    setConnectedId(executionId);
    setEvents([]);
    resetNodeStatuses();
    setIsStreaming(true);

    const fetchSSE = async () => {
      try {
        const response = await fetch(`/api/executions/${executionId}/stream`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Accept': 'text/event-stream',
          },
          signal: controller.signal,
        });

        if (!response.ok || !response.body) {
          setIsStreaming(false);
          return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const event: ExecutionEvent = JSON.parse(line.slice(6));
                setEvents(prev => [...prev, event]);

                // Update node execution statuses for real-time visualization
                if (event.type === 'node_started' && event.data?.node_id) {
                  setNodeStatus(event.data.node_id as string, 'running');
                } else if (event.type === 'node_completed' && event.data?.node_id) {
                  const status = event.data.status === 'completed' ? 'completed' : 'failed';
                  setNodeStatus(event.data.node_id as string, status);
                } else if (event.type === 'started') {
                  resetNodeStatuses();
                }

                if (event.type === 'done' || event.type === 'completed' || event.type === 'failed') {
                  setIsStreaming(false);
                  return;
                }
              } catch {
                // ignore parse errors
              }
            }
          }
        }
      } catch (err: any) {
        if (err.name !== 'AbortError') {
          setIsStreaming(false);
        }
      }
    };

    fetchSSE();

    return () => {
      controller.abort();
      setIsStreaming(false);
    };
  }, [executionId, token]);

  useEffect(() => {
    const cleanup = connect();
    return cleanup;
  }, [connect]);

  return { events, isStreaming, connectedId };
}
