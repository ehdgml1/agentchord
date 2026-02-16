/**
 * WebSocket hook for debug mode execution
 *
 * Connects to the debug WebSocket endpoint for step-by-step workflow debugging.
 * Supports breakpoints, stepping, and real-time execution state.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useAuthStore } from '../stores/authStore';

interface DebugEvent {
  type: 'node_start' | 'breakpoint' | 'node_complete' | 'complete' | 'error' | 'timeout';
  node_id?: string;
  data: Record<string, unknown>;
  timestamp?: string;
}

interface DebugState {
  isConnected: boolean;
  isDebugging: boolean;
  isPaused: boolean;
  currentNode: string | null;
  events: DebugEvent[];
}

/**
 * Hook for managing debug WebSocket connection and execution
 *
 * @param workflowId - The workflow ID to debug, or null to disconnect
 * @returns Debug state and control functions
 */
export function useDebugWebSocket(workflowId: string | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const token = useAuthStore((s) => s.token);
  const [state, setState] = useState<DebugState>({
    isConnected: false,
    isDebugging: false,
    isPaused: false,
    currentNode: null,
    events: [],
  });

  const connect = useCallback(() => {
    if (!workflowId || wsRef.current) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/debug/${workflowId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      // Send auth token as first message (more secure than query param)
      if (token) {
        ws.send(JSON.stringify({ action: 'auth', token }));
      }
      setState((prev) => ({ ...prev, isConnected: true }));
    };

    ws.onmessage = (event) => {
      try {
        const data: DebugEvent = JSON.parse(event.data);
        setState((prev) => {
          const newState = { ...prev, events: [...prev.events, data] };

          switch (data.type) {
            case 'breakpoint':
              newState.isPaused = true;
              newState.currentNode = data.node_id || null;
              break;
            case 'node_start':
              newState.currentNode = data.node_id || null;
              newState.isPaused = false;
              break;
            case 'node_complete':
              break;
            case 'complete':
              newState.isDebugging = false;
              newState.isPaused = false;
              newState.currentNode = null;
              break;
            case 'error':
            case 'timeout':
              newState.isDebugging = false;
              newState.isPaused = false;
              break;
          }
          return newState;
        });
      } catch (err) {
        if (import.meta.env.DEV) console.error('[Debug WS] Failed to parse message:', err);
      }
    };

    ws.onerror = (event) => {
      if (import.meta.env.DEV) console.error('[Debug WS] WebSocket error:', event);
    };

    ws.onclose = () => {
      wsRef.current = null;
      setState((prev) => ({ ...prev, isConnected: false, isDebugging: false }));
    };
  }, [workflowId, token]);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setState({
      isConnected: false,
      isDebugging: false,
      isPaused: false,
      currentNode: null,
      events: [],
    });
  }, []);

  const start = useCallback(
    (input: string, breakpoints: string[] = []) => {
      if (!wsRef.current) return;
      wsRef.current.send(JSON.stringify({ action: 'start', input, breakpoints }));
      setState((prev) => ({ ...prev, isDebugging: true, events: [] }));
    },
    []
  );

  const continueExec = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.send(JSON.stringify({ action: 'continue' }));
    }
  }, []);

  const step = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.send(JSON.stringify({ action: 'step' }));
    }
  }, []);

  const stop = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.send(JSON.stringify({ action: 'stop' }));
      setState((prev) => ({ ...prev, isDebugging: false, isPaused: false }));
    }
  }, []);

  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return {
    ...state,
    connect,
    disconnect,
    start,
    continue: continueExec,
    step,
    stop,
  };
}
