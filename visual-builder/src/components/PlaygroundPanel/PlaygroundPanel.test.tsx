import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PlaygroundPanel } from './PlaygroundPanel';
import { usePlaygroundStore } from '../../stores/playgroundStore';
import { useWorkflowStore } from '../../stores/workflowStore';
import { api } from '../../services/api';
import type { ExecutionEvent } from '../../hooks/useExecutionProgress';

// Mock API
vi.mock('../../services/api', () => ({
  api: {
    playground: {
      chat: vi.fn(),
    },
  },
}));

// Mock hooks - use getter function to allow dynamic updates
const mockEventsStore = { current: [] as ExecutionEvent[] };
vi.mock('../../hooks/useExecutionProgress', () => ({
  useExecutionProgress: vi.fn((executionId: string | null) => ({
    events: mockEventsStore.current,
    isStreaming: false,
    connectedId: executionId,
  })),
}));

describe('PlaygroundPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockEventsStore.current = [];
    usePlaygroundStore.getState().clearMessages();
    useWorkflowStore.setState({ backendId: 'test-workflow-123' });
  });

  it('renders the panel with title and controls', () => {
    render(<PlaygroundPanel />);

    expect(screen.getByText('플레이그라운드')).toBeInTheDocument();
    expect(screen.getByTitle('초기화')).toBeInTheDocument();
    expect(screen.getByTitle('닫기')).toBeInTheDocument();
  });

  it('shows empty state when no messages', () => {
    render(<PlaygroundPanel />);

    expect(screen.getByText('워크플로우를 테스트해보세요')).toBeInTheDocument();
    expect(screen.getByText('메시지를 보내면 워크플로우가 실행됩니다')).toBeInTheDocument();
  });

  it('shows warning when workflow is not saved', () => {
    useWorkflowStore.setState({ backendId: null });
    render(<PlaygroundPanel />);

    expect(screen.getByText('워크플로우를 먼저 저장해주세요.')).toBeInTheDocument();
  });

  it('disables input when workflow is not saved', () => {
    useWorkflowStore.setState({ backendId: null });
    render(<PlaygroundPanel />);

    const textarea = screen.getByPlaceholderText('메시지를 입력하세요...');
    expect(textarea).toBeDisabled();
  });

  it('enables input when workflow is saved', () => {
    useWorkflowStore.setState({ backendId: 'test-workflow-123' });
    render(<PlaygroundPanel />);

    const textarea = screen.getByPlaceholderText('메시지를 입력하세요...');
    expect(textarea).not.toBeDisabled();
  });

  it('sends message and starts streaming on submit', async () => {
    const user = userEvent.setup();
    const mockChat = vi.mocked(api.playground.chat);
    mockChat.mockResolvedValue({ executionId: 'exec-123', status: 'running' });

    useWorkflowStore.setState({ backendId: 'test-workflow-123' });
    render(<PlaygroundPanel />);

    const textarea = screen.getByPlaceholderText('메시지를 입력하세요...');
    await user.type(textarea, 'Hello world');

    const sendButton = screen.getByLabelText('메시지 보내기');
    await user.click(sendButton);

    // Verify API was called (history includes the new user message via getState())
    await waitFor(() => {
      expect(mockChat).toHaveBeenCalledWith(
        'test-workflow-123',
        'Hello world',
        [{ role: 'user', content: 'Hello world' }]
      );
    });

    // Verify user message was added
    const state = usePlaygroundStore.getState();
    expect(state.messages).toHaveLength(2); // user + streaming placeholder
    expect(state.messages[0].role).toBe('user');
    expect(state.messages[0].content).toBe('Hello world');
    expect(state.isStreaming).toBe(true);
  });

  it('handles API error gracefully', async () => {
    const user = userEvent.setup();
    const mockChat = vi.mocked(api.playground.chat);
    mockChat.mockRejectedValue(new Error('Network error'));

    useWorkflowStore.setState({ backendId: 'test-workflow-123' });
    render(<PlaygroundPanel />);

    const textarea = screen.getByPlaceholderText('메시지를 입력하세요...');
    await user.type(textarea, 'Test');

    const sendButton = screen.getByLabelText('메시지 보내기');
    await user.click(sendButton);

    // Verify error message was added
    await waitFor(() => {
      const state = usePlaygroundStore.getState();
      expect(state.messages).toHaveLength(2);
      expect(state.messages[1].content).toContain('Network error');
    });
  });

  it('clears messages when clear button clicked', async () => {
    const user = userEvent.setup();

    // Add some messages first
    usePlaygroundStore.getState().addUserMessage('Message 1');
    usePlaygroundStore.getState().addAssistantMessage({ content: 'Response 1' });

    render(<PlaygroundPanel />);

    const clearButton = screen.getByTitle('초기화');
    await user.click(clearButton);

    const state = usePlaygroundStore.getState();
    expect(state.messages).toHaveLength(0);
  });

  it('closes panel when close button clicked', async () => {
    const user = userEvent.setup();

    usePlaygroundStore.getState().open();
    expect(usePlaygroundStore.getState().isOpen).toBe(true);

    render(<PlaygroundPanel />);

    const closeButton = screen.getByTitle('닫기');
    await user.click(closeButton);

    expect(usePlaygroundStore.getState().isOpen).toBe(false);
  });

  it('disables send button when streaming', () => {
    useWorkflowStore.setState({ backendId: 'test-workflow-123' });
    usePlaygroundStore.setState({ isStreaming: true });

    render(<PlaygroundPanel />);

    const sendButton = screen.getByLabelText('메시지 보내기');
    expect(sendButton).toBeDisabled();
  });

  it('builds conversation history correctly', async () => {
    const user = userEvent.setup();
    const mockChat = vi.mocked(api.playground.chat);
    mockChat.mockResolvedValue({ executionId: 'exec-123', status: 'running' });

    // Add existing messages
    usePlaygroundStore.getState().addUserMessage('First message');
    usePlaygroundStore.getState().addAssistantMessage({ content: 'First response' });

    useWorkflowStore.setState({ backendId: 'test-workflow-123' });
    render(<PlaygroundPanel />);

    const textarea = screen.getByPlaceholderText('메시지를 입력하세요...');
    await user.type(textarea, 'Second message');

    const sendButton = screen.getByLabelText('메시지 보내기');
    await user.click(sendButton);

    // Verify history was sent correctly (includes the new user message via getState())
    await waitFor(() => {
      expect(mockChat).toHaveBeenCalledWith(
        'test-workflow-123',
        'Second message',
        [
          { role: 'user', content: 'First message' },
          { role: 'assistant', content: 'First response' },
          { role: 'user', content: 'Second message' },
        ]
      );
    });
  });

  describe('SSE Event Processing', () => {
    it('handles batched SSE events correctly', async () => {
      // Start streaming to create placeholder message
      usePlaygroundStore.getState().setStreaming(true, 'exec-123');

      // Simulate batched events arriving together
      mockEventsStore.current = [
        {
          type: 'started',
          data: { executionId: 'exec-123' },
        },
        {
          type: 'node_completed',
          data: { nodeId: 'node-1', output: 'Processing...' },
        },
        {
          type: 'completed',
          data: { output: 'Final result', status: 'completed' },
        },
      ];

      const { rerender } = render(<PlaygroundPanel />);
      rerender(<PlaygroundPanel />);

      // Verify the completed event was processed
      await waitFor(() => {
        const state = usePlaygroundStore.getState();
        const lastMessage = state.messages[state.messages.length - 1];
        expect(lastMessage.content).toBe('Final result');
        expect(state.isStreaming).toBe(false);
      });
    });

    it('handles completed event with output', async () => {
      // Start streaming to create placeholder message
      usePlaygroundStore.getState().setStreaming(true, 'exec-456');

      mockEventsStore.current = [
        {
          type: 'completed',
          data: { output: 'Success response', status: 'completed' },
        },
      ];

      const { rerender } = render(<PlaygroundPanel />);
      rerender(<PlaygroundPanel />);

      await waitFor(() => {
        const state = usePlaygroundStore.getState();
        const lastMessage = state.messages[state.messages.length - 1];
        expect(lastMessage.content).toBe('Success response');
        expect(state.isStreaming).toBe(false);
      });
    });

    it('processes events incrementally', async () => {
      // This test verifies that when events arrive one-at-a-time,
      // each is processed correctly without skipping
      usePlaygroundStore.getState().setStreaming(true, 'exec-789');

      // Start with first event
      mockEventsStore.current = [
        {
          type: 'started',
          data: { executionId: 'exec-789' },
        },
      ];

      const { rerender, unmount } = render(<PlaygroundPanel />);

      // Unmount and remount with second event to trigger fresh useEffect
      unmount();
      mockEventsStore.current = [
        {
          type: 'started',
          data: { executionId: 'exec-789' },
        },
        {
          type: 'node_completed',
          data: { nodeId: 'node-1', output: 'Step 1 done' },
        },
      ];
      usePlaygroundStore.getState().setStreaming(true, 'exec-789');
      render(<PlaygroundPanel />);

      await waitFor(() => {
        const state = usePlaygroundStore.getState();
        const lastMessage = state.messages[state.messages.length - 1];
        expect(lastMessage.content).toBe('Step 1 done');
      });
    });

    it('resets event processing on new execution', async () => {
      // First execution
      usePlaygroundStore.getState().setStreaming(true, 'exec-first');

      mockEventsStore.current = [
        {
          type: 'completed',
          data: { output: 'First execution result', status: 'completed' },
        },
      ];

      const { rerender } = render(<PlaygroundPanel />);
      rerender(<PlaygroundPanel />);

      await waitFor(() => {
        const state = usePlaygroundStore.getState();
        expect(state.messages[state.messages.length - 1].content).toBe('First execution result');
      });

      // New execution with reset - must call setStreaming to create new placeholder
      usePlaygroundStore.getState().setStreaming(true, 'exec-second');

      mockEventsStore.current = [
        {
          type: 'completed',
          data: { output: 'Second execution result', status: 'completed' },
        },
      ];

      rerender(<PlaygroundPanel />);

      await waitFor(() => {
        const state = usePlaygroundStore.getState();
        const lastMessage = state.messages[state.messages.length - 1];
        expect(lastMessage.content).toBe('Second execution result');
      });
    });

    it('handles failed event correctly', async () => {
      // Start streaming to create placeholder message
      usePlaygroundStore.getState().setStreaming(true, 'exec-fail');

      mockEventsStore.current = [
        {
          type: 'started',
          data: { executionId: 'exec-fail' },
        },
        {
          type: 'failed',
          data: { error: 'Execution failed due to timeout' },
        },
      ];

      const { rerender } = render(<PlaygroundPanel />);
      rerender(<PlaygroundPanel />);

      await waitFor(() => {
        const state = usePlaygroundStore.getState();
        const lastMessage = state.messages[state.messages.length - 1];
        expect(lastMessage.content).toContain('Execution failed due to timeout');
        expect(state.isStreaming).toBe(false);
      });
    });

    it('collects node results across all events', async () => {
      // Start streaming to create placeholder message
      usePlaygroundStore.getState().setStreaming(true, 'exec-multi');

      mockEventsStore.current = [
        {
          type: 'node_completed',
          data: { nodeId: 'node-1', output: 'Result 1' },
        },
        {
          type: 'node_completed',
          data: { nodeId: 'node-2', output: 'Result 2' },
        },
        {
          type: 'completed',
          data: { output: 'Final output', status: 'completed' },
        },
      ];

      const { rerender } = render(<PlaygroundPanel />);
      rerender(<PlaygroundPanel />);

      await waitFor(() => {
        const state = usePlaygroundStore.getState();
        const lastMessage = state.messages[state.messages.length - 1];
        expect(lastMessage.content).toBe('Final output');
        expect(lastMessage.nodeResults).toEqual({
          'node-1': 'Result 1',
          'node-2': 'Result 2',
        });
        expect(state.isStreaming).toBe(false);
      });
    });
  });
});
