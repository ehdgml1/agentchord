/**
 * Zustand store for Playground Chat Panel state
 *
 * Manages chat messages, streaming state, and chat interactions
 * for the workflow playground panel.
 */

import { create } from 'zustand';

/**
 * Chat message interface
 */
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  nodeResults?: Record<string, unknown>;
  tokenUsage?: { prompt: number; completion: number; total: number };
  executionId?: string;
  timestamp: string;
  isStreaming?: boolean;
}

/**
 * Playground store state and actions interface
 */
interface PlaygroundState {
  /** Whether the playground panel is open */
  isOpen: boolean;
  /** Chat message history */
  messages: ChatMessage[];
  /** Whether a message is currently streaming */
  isStreaming: boolean;
  /** ID of the active execution during streaming */
  activeExecutionId: string | null;

  /** Toggle panel open/closed */
  toggle: () => void;
  /** Open the panel */
  open: () => void;
  /** Close the panel */
  close: () => void;
  /** Add a user message and return its ID */
  addUserMessage: (content: string) => string;
  /** Add an assistant message */
  addAssistantMessage: (message: Omit<ChatMessage, 'id' | 'role' | 'timestamp'>) => void;
  /** Set streaming state and optionally track execution ID */
  setStreaming: (streaming: boolean, executionId?: string | null) => void;
  /** Update the content of the currently streaming message */
  updateStreamingMessage: (content: string, options?: { nodeResults?: Record<string, unknown> }) => void;
  /** Clear all messages */
  clearMessages: () => void;
}

/**
 * Main playground store
 */
export const usePlaygroundStore = create<PlaygroundState>((set) => ({
  isOpen: false,
  messages: [],
  isStreaming: false,
  activeExecutionId: null,

  toggle: () => {
    set((state) => ({ isOpen: !state.isOpen }));
  },

  open: () => {
    set({ isOpen: true });
  },

  close: () => {
    set({ isOpen: false });
  },

  addUserMessage: (content: string) => {
    const id = crypto.randomUUID();
    const message: ChatMessage = {
      id,
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    };

    set((state) => ({
      messages: [...state.messages, message],
    }));

    return id;
  },

  addAssistantMessage: (message) => {
    const fullMessage: ChatMessage = {
      ...message,
      id: crypto.randomUUID(),
      role: 'assistant',
      timestamp: new Date().toISOString(),
    };

    set((state) => ({
      messages: [...state.messages, fullMessage],
    }));
  },

  setStreaming: (streaming: boolean, executionId?: string | null) => {
    if (streaming) {
      // Start streaming: add placeholder message
      const placeholderMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: '',
        timestamp: new Date().toISOString(),
        isStreaming: true,
      };

      set((state) => ({
        isStreaming: true,
        activeExecutionId: executionId || null,
        messages: [...state.messages, placeholderMessage],
      }));
    } else {
      // Stop streaming: remove streaming flag from last message
      set((state) => {
        const messages = [...state.messages];
        if (messages.length > 0 && messages[messages.length - 1].isStreaming) {
          messages[messages.length - 1] = {
            ...messages[messages.length - 1],
            isStreaming: false,
          };
        }

        return {
          isStreaming: false,
          activeExecutionId: null,
          messages,
        };
      });
    }
  },

  updateStreamingMessage: (content: string, options?: { nodeResults?: Record<string, unknown> }) => {
    set((state) => {
      const messages = [...state.messages];
      const lastIndex = messages.length - 1;

      if (lastIndex >= 0 && messages[lastIndex].isStreaming) {
        messages[lastIndex] = {
          ...messages[lastIndex],
          content,
          ...(options?.nodeResults && { nodeResults: options.nodeResults }),
        };
      }

      return { messages };
    });
  },

  clearMessages: () => {
    set({
      messages: [],
      isStreaming: false,
      activeExecutionId: null,
    });
  },
}));
