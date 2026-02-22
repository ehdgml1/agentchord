import { describe, it, expect, beforeEach, vi } from 'vitest';
import { usePlaygroundStore } from './playgroundStore';

// Create a counter that can be reset
let uuidCounter = 0;

// Mock crypto.randomUUID for predictable IDs
vi.stubGlobal('crypto', {
  randomUUID: () => `test-uuid-${uuidCounter++}`,
});

describe('playgroundStore', () => {
  beforeEach(() => {
    // Reset UUID counter
    uuidCounter = 0;

    // Reset store to initial state before each test
    usePlaygroundStore.setState({
      isOpen: false,
      messages: [],
      isStreaming: false,
      activeExecutionId: null,
    });
  });

  describe('toggle', () => {
    it('toggles isOpen from false to true', () => {
      const { toggle } = usePlaygroundStore.getState();

      expect(usePlaygroundStore.getState().isOpen).toBe(false);

      toggle();

      expect(usePlaygroundStore.getState().isOpen).toBe(true);
    });

    it('toggles isOpen from true to false', () => {
      const { toggle } = usePlaygroundStore.getState();

      usePlaygroundStore.setState({ isOpen: true });
      expect(usePlaygroundStore.getState().isOpen).toBe(true);

      toggle();

      expect(usePlaygroundStore.getState().isOpen).toBe(false);
    });
  });

  describe('open', () => {
    it('sets isOpen to true', () => {
      const { open } = usePlaygroundStore.getState();

      expect(usePlaygroundStore.getState().isOpen).toBe(false);

      open();

      expect(usePlaygroundStore.getState().isOpen).toBe(true);
    });

    it('keeps isOpen true when called multiple times', () => {
      const { open } = usePlaygroundStore.getState();

      open();
      open();

      expect(usePlaygroundStore.getState().isOpen).toBe(true);
    });
  });

  describe('close', () => {
    it('sets isOpen to false', () => {
      const { close } = usePlaygroundStore.getState();

      usePlaygroundStore.setState({ isOpen: true });

      close();

      expect(usePlaygroundStore.getState().isOpen).toBe(false);
    });

    it('keeps isOpen false when called multiple times', () => {
      const { close } = usePlaygroundStore.getState();

      close();
      close();

      expect(usePlaygroundStore.getState().isOpen).toBe(false);
    });
  });

  describe('addUserMessage', () => {
    it('adds user message with correct fields', () => {
      const { addUserMessage } = usePlaygroundStore.getState();

      const messageId = addUserMessage('Hello world');

      const state = usePlaygroundStore.getState();
      expect(state.messages).toHaveLength(1);
      expect(state.messages[0]).toMatchObject({
        id: messageId,
        role: 'user',
        content: 'Hello world',
      });
      expect(state.messages[0].timestamp).toBeTruthy();
    });

    it('returns valid UUID as message ID', () => {
      const { addUserMessage } = usePlaygroundStore.getState();

      const messageId = addUserMessage('Test message');

      expect(messageId).toBe('test-uuid-0');
      expect(typeof messageId).toBe('string');
      expect(messageId.length).toBeGreaterThan(0);
    });

    it('adds message with valid ISO timestamp', () => {
      const { addUserMessage } = usePlaygroundStore.getState();

      addUserMessage('Test message');

      const state = usePlaygroundStore.getState();
      const timestamp = new Date(state.messages[0].timestamp);
      expect(timestamp).toBeInstanceOf(Date);
      expect(timestamp.toISOString()).toBe(state.messages[0].timestamp);
    });

    it('accumulates multiple messages correctly', () => {
      const { addUserMessage } = usePlaygroundStore.getState();

      addUserMessage('Message 1');
      addUserMessage('Message 2');
      addUserMessage('Message 3');

      const state = usePlaygroundStore.getState();
      expect(state.messages).toHaveLength(3);
      expect(state.messages[0].content).toBe('Message 1');
      expect(state.messages[1].content).toBe('Message 2');
      expect(state.messages[2].content).toBe('Message 3');
    });
  });

  describe('addAssistantMessage', () => {
    it('adds assistant message with correct fields', () => {
      const { addAssistantMessage } = usePlaygroundStore.getState();

      addAssistantMessage({ content: 'Assistant response' });

      const state = usePlaygroundStore.getState();
      expect(state.messages).toHaveLength(1);
      expect(state.messages[0]).toMatchObject({
        role: 'assistant',
        content: 'Assistant response',
      });
      expect(state.messages[0].id).toBe('test-uuid-0');
      expect(state.messages[0].timestamp).toBeTruthy();
    });

    it('includes optional nodeResults when provided', () => {
      const { addAssistantMessage } = usePlaygroundStore.getState();
      const nodeResults = { 'node-1': { output: 'result' } };

      addAssistantMessage({ content: 'Response', nodeResults });

      const state = usePlaygroundStore.getState();
      expect(state.messages[0].nodeResults).toEqual(nodeResults);
    });

    it('includes optional tokenUsage when provided', () => {
      const { addAssistantMessage } = usePlaygroundStore.getState();
      const tokenUsage = { prompt: 10, completion: 20, total: 30 };

      addAssistantMessage({ content: 'Response', tokenUsage });

      const state = usePlaygroundStore.getState();
      expect(state.messages[0].tokenUsage).toEqual(tokenUsage);
    });

    it('includes optional executionId when provided', () => {
      const { addAssistantMessage } = usePlaygroundStore.getState();

      addAssistantMessage({ content: 'Response', executionId: 'exec-123' });

      const state = usePlaygroundStore.getState();
      expect(state.messages[0].executionId).toBe('exec-123');
    });
  });

  describe('setStreaming', () => {
    it('sets streaming to true and adds placeholder message', () => {
      const { setStreaming } = usePlaygroundStore.getState();

      setStreaming(true, 'exec-123');

      const state = usePlaygroundStore.getState();
      expect(state.isStreaming).toBe(true);
      expect(state.activeExecutionId).toBe('exec-123');
      expect(state.messages).toHaveLength(1);
      expect(state.messages[0]).toMatchObject({
        role: 'assistant',
        content: '',
        isStreaming: true,
      });
    });

    it('sets streaming to true without executionId', () => {
      const { setStreaming } = usePlaygroundStore.getState();

      setStreaming(true);

      const state = usePlaygroundStore.getState();
      expect(state.isStreaming).toBe(true);
      expect(state.activeExecutionId).toBeNull();
      expect(state.messages).toHaveLength(1);
      expect(state.messages[0].isStreaming).toBe(true);
    });

    it('sets streaming to false and removes isStreaming flag from last message', () => {
      const { setStreaming } = usePlaygroundStore.getState();

      // Start streaming
      setStreaming(true, 'exec-123');

      // Stop streaming
      setStreaming(false);

      const state = usePlaygroundStore.getState();
      expect(state.isStreaming).toBe(false);
      expect(state.activeExecutionId).toBeNull();
      expect(state.messages).toHaveLength(1);
      expect(state.messages[0].isStreaming).toBe(false);
    });

    it('does not modify messages if last message is not streaming when stopping', () => {
      const { addUserMessage, setStreaming } = usePlaygroundStore.getState();

      // Add normal message
      addUserMessage('Test');

      // Try to stop streaming (should not crash)
      setStreaming(false);

      const state = usePlaygroundStore.getState();
      expect(state.isStreaming).toBe(false);
      expect(state.messages).toHaveLength(1);
      expect(state.messages[0].content).toBe('Test');
    });
  });

  describe('updateStreamingMessage', () => {
    it('updates content of the last streaming message', () => {
      const { setStreaming, updateStreamingMessage } = usePlaygroundStore.getState();

      setStreaming(true);
      updateStreamingMessage('Partial response...');

      const state = usePlaygroundStore.getState();
      expect(state.messages[0].content).toBe('Partial response...');
      expect(state.messages[0].isStreaming).toBe(true);
    });

    it('accumulates content updates', () => {
      const { setStreaming, updateStreamingMessage } = usePlaygroundStore.getState();

      setStreaming(true);
      updateStreamingMessage('Part 1');
      updateStreamingMessage('Part 1 and 2');
      updateStreamingMessage('Complete response');

      const state = usePlaygroundStore.getState();
      expect(state.messages[0].content).toBe('Complete response');
    });

    it('does not modify messages if last message is not streaming', () => {
      const { addUserMessage, updateStreamingMessage } = usePlaygroundStore.getState();

      addUserMessage('User message');
      updateStreamingMessage('This should not appear');

      const state = usePlaygroundStore.getState();
      expect(state.messages[0].content).toBe('User message');
    });

    it('does not crash when no messages exist', () => {
      const { updateStreamingMessage } = usePlaygroundStore.getState();

      // Should not crash
      updateStreamingMessage('No messages yet');

      const state = usePlaygroundStore.getState();
      expect(state.messages).toHaveLength(0);
    });
  });

  describe('clearMessages', () => {
    it('resets all message state', () => {
      const { addUserMessage, setStreaming, clearMessages } = usePlaygroundStore.getState();

      // Add some state
      addUserMessage('Message 1');
      addUserMessage('Message 2');
      setStreaming(true, 'exec-123');

      clearMessages();

      const state = usePlaygroundStore.getState();
      expect(state.messages).toHaveLength(0);
      expect(state.isStreaming).toBe(false);
      expect(state.activeExecutionId).toBeNull();
    });

    it('works when messages are already empty', () => {
      const { clearMessages } = usePlaygroundStore.getState();

      clearMessages();

      const state = usePlaygroundStore.getState();
      expect(state.messages).toHaveLength(0);
      expect(state.isStreaming).toBe(false);
      expect(state.activeExecutionId).toBeNull();
    });

    it('preserves isOpen state', () => {
      const { addUserMessage, open, clearMessages } = usePlaygroundStore.getState();

      open();
      addUserMessage('Message');

      clearMessages();

      const state = usePlaygroundStore.getState();
      expect(state.isOpen).toBe(true);
      expect(state.messages).toHaveLength(0);
    });
  });

  describe('conversation flow integration', () => {
    it('simulates a complete conversation flow', () => {
      const {
        open,
        addUserMessage,
        setStreaming,
        updateStreamingMessage,
        addAssistantMessage,
        clearMessages,
      } = usePlaygroundStore.getState();

      // 1. Open panel
      open();
      expect(usePlaygroundStore.getState().isOpen).toBe(true);

      // 2. User sends message
      addUserMessage('What is the weather?');
      expect(usePlaygroundStore.getState().messages).toHaveLength(1);

      // 3. Start streaming response
      setStreaming(true, 'exec-123');
      expect(usePlaygroundStore.getState().isStreaming).toBe(true);
      expect(usePlaygroundStore.getState().messages).toHaveLength(2);

      // 4. Stream partial content
      updateStreamingMessage('The weather is...');
      updateStreamingMessage('The weather is sunny and warm.');

      // 5. Stop streaming
      setStreaming(false);
      expect(usePlaygroundStore.getState().isStreaming).toBe(false);
      expect(usePlaygroundStore.getState().messages[1].content).toBe('The weather is sunny and warm.');

      // 6. User sends follow-up
      addUserMessage('What about tomorrow?');

      // 7. Clear conversation
      clearMessages();
      expect(usePlaygroundStore.getState().messages).toHaveLength(0);
      expect(usePlaygroundStore.getState().isOpen).toBe(true);
    });
  });
});
