export type DebugEventType = 'breakpoint' | 'node_start' | 'node_complete' | 'complete' | 'error' | 'timeout';

export interface DebugEvent {
  type: DebugEventType;
  nodeId?: string;
  data?: Record<string, unknown>;
  timestamp: string;
}

export interface DebugCommand {
  action: 'start' | 'continue' | 'step' | 'stop';
  input?: string;
  breakpoints?: string[];
}
