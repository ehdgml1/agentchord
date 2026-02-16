import { create } from 'zustand';
import type { DebugEvent } from '../types/debug';

interface DebugState {
  isDebugging: boolean;
  isPaused: boolean;
  currentNode: string | null;
  breakpoints: Set<string>;
  events: DebugEvent[];
  startDebug: (workflowId: string, input: string) => void;
  continueExecution: () => void;
  step: () => void;
  stop: () => void;
  toggleBreakpoint: (nodeId: string) => void;
  addEvent: (event: DebugEvent) => void;
  setPaused: (isPaused: boolean, nodeId?: string) => void;
  reset: () => void;
}

export const useDebugStore = create<DebugState>((set, get) => ({
  isDebugging: false,
  isPaused: false,
  currentNode: null,
  breakpoints: new Set<string>(),
  events: [],

  startDebug: (_workflowId: string, _input: string) => {
    set({
      isDebugging: true,
      isPaused: false,
      currentNode: null,
      events: [],
    });
  },

  continueExecution: () => {
    set({ isPaused: false, currentNode: null });
  },

  step: () => {
    set({ isPaused: false });
  },

  stop: () => {
    set({
      isDebugging: false,
      isPaused: false,
      currentNode: null,
    });
  },

  toggleBreakpoint: (nodeId: string) => {
    const breakpoints = new Set(get().breakpoints);
    if (breakpoints.has(nodeId)) {
      breakpoints.delete(nodeId);
    } else {
      breakpoints.add(nodeId);
    }
    set({ breakpoints });
  },

  addEvent: (event: DebugEvent) => {
    set((state) => ({
      events: [...state.events, event],
    }));
  },

  setPaused: (isPaused: boolean, nodeId?: string) => {
    set({ isPaused, currentNode: nodeId || null });
  },

  reset: () => {
    set({
      isDebugging: false,
      isPaused: false,
      currentNode: null,
      events: [],
    });
  },
}));
