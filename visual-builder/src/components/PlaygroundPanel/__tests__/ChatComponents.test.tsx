import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChatBubble } from '../ChatBubble';
import { ChatInput } from '../ChatInput';
import { ChatMessageList } from '../ChatMessageList';
import type { ChatMessage } from '../../../stores/playgroundStore';

describe('ChatBubble', () => {
  const createMessage = (overrides?: Partial<ChatMessage>): ChatMessage => ({
    id: 'msg-1',
    role: 'user',
    content: 'Test message',
    timestamp: new Date().toISOString(),
    ...overrides,
  });

  it('renders user message with correct styling', () => {
    const message = createMessage({ role: 'user', content: 'Hello' });

    render(<ChatBubble message={message} />);

    const bubble = screen.getByText('Hello').closest('div');
    expect(bubble).toHaveClass('bg-blue-600');
    expect(bubble).toHaveClass('text-white');
  });

  it('renders assistant message with correct styling', () => {
    const message = createMessage({ role: 'assistant', content: 'Hi there' });

    render(<ChatBubble message={message} />);

    const bubble = screen.getByText('Hi there').closest('div');
    expect(bubble).toHaveClass('bg-zinc-100');
  });

  it('renders system message with correct styling', () => {
    const message = createMessage({ role: 'system', content: 'System message' });

    render(<ChatBubble message={message} />);

    const bubble = screen.getByText('System message').closest('div');
    expect(bubble).toHaveClass('bg-zinc-50');
  });

  it('shows streaming dots when isStreaming=true and no content', () => {
    const message = createMessage({
      role: 'assistant',
      content: '',
      isStreaming: true,
    });

    const { container } = render(<ChatBubble message={message} />);

    // Check for animated dots
    const dots = container.querySelectorAll('.animate-pulse');
    expect(dots).toHaveLength(3);
  });

  it('shows content text when not streaming', () => {
    const message = createMessage({
      role: 'assistant',
      content: 'Full response',
      isStreaming: false,
    });

    render(<ChatBubble message={message} />);

    expect(screen.getByText('Full response')).toBeInTheDocument();
  });

  it('shows content even when isStreaming is true if content exists', () => {
    const message = createMessage({
      role: 'assistant',
      content: 'Partial content...',
      isStreaming: true,
    });

    render(<ChatBubble message={message} />);

    expect(screen.getByText('Partial content...')).toBeInTheDocument();
  });

  it('shows relative timestamp', () => {
    const message = createMessage({ timestamp: new Date().toISOString() });

    render(<ChatBubble message={message} />);

    expect(screen.getByText('방금 전')).toBeInTheDocument();
  });

  it('shows token usage badge when tokenUsage exists', () => {
    const message = createMessage({
      role: 'assistant',
      tokenUsage: { prompt: 10, completion: 20, total: 30 },
    });

    render(<ChatBubble message={message} />);

    expect(screen.getByText(/30 토큰/)).toBeInTheDocument();
  });

  it('does not show token usage when tokenUsage is undefined', () => {
    const message = createMessage({ role: 'assistant' });

    render(<ChatBubble message={message} />);

    expect(screen.queryByText(/토큰/)).not.toBeInTheDocument();
  });

  it('shows node results toggle when nodeResults exists', () => {
    const message = createMessage({
      role: 'assistant',
      nodeResults: { 'node-1': { output: 'result' } },
    });

    render(<ChatBubble message={message} />);

    expect(screen.getByText('노드 실행 결과')).toBeInTheDocument();
  });

  it('does not show node results toggle for user messages', () => {
    const message = createMessage({
      role: 'user',
      nodeResults: { 'node-1': { output: 'result' } },
    });

    render(<ChatBubble message={message} />);

    expect(screen.queryByText('노드 실행 결과')).not.toBeInTheDocument();
  });

  it('toggles node results on click', async () => {
    const user = userEvent.setup();
    const message = createMessage({
      role: 'assistant',
      nodeResults: { 'node-1': { output: 'test result' } },
    });

    render(<ChatBubble message={message} />);

    const toggle = screen.getByText('노드 실행 결과');

    // Results should not be visible initially
    expect(screen.queryByText(/"node-1"/)).not.toBeInTheDocument();

    // Click to expand
    await user.click(toggle);

    // Results should be visible
    expect(screen.getByText(/"node-1"/)).toBeInTheDocument();

    // Click to collapse
    await user.click(toggle);

    // Results should be hidden again
    expect(screen.queryByText(/"node-1"/)).not.toBeInTheDocument();
  });

  it('does not show node results toggle when nodeResults is empty', () => {
    const message = createMessage({
      role: 'assistant',
      nodeResults: {},
    });

    render(<ChatBubble message={message} />);

    expect(screen.queryByText('노드 실행 결과')).not.toBeInTheDocument();
  });
});

describe('ChatInput', () => {
  it('renders textarea with placeholder', () => {
    render(<ChatInput onSend={vi.fn()} />);

    expect(screen.getByPlaceholderText('메시지를 입력하세요...')).toBeInTheDocument();
  });

  it('calls onSend when Enter pressed', async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();

    render(<ChatInput onSend={onSend} />);

    const textarea = screen.getByPlaceholderText('메시지를 입력하세요...');
    await user.type(textarea, 'Hello world{Enter}');

    expect(onSend).toHaveBeenCalledWith('Hello world');
  });

  it('does NOT call onSend when Shift+Enter pressed', async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();

    render(<ChatInput onSend={onSend} />);

    const textarea = screen.getByPlaceholderText('메시지를 입력하세요...');
    await user.type(textarea, 'Line 1{Shift>}{Enter}{/Shift}Line 2');

    expect(onSend).not.toHaveBeenCalled();
  });

  it('does NOT call onSend when empty', async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();

    render(<ChatInput onSend={onSend} />);

    const textarea = screen.getByPlaceholderText('메시지를 입력하세요...');
    await user.type(textarea, '{Enter}');

    expect(onSend).not.toHaveBeenCalled();
  });

  it('does NOT call onSend when only whitespace', async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();

    render(<ChatInput onSend={onSend} />);

    const textarea = screen.getByPlaceholderText('메시지를 입력하세요...');
    await user.type(textarea, '   {Enter}');

    expect(onSend).not.toHaveBeenCalled();
  });

  it('clears input after send', async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();

    render(<ChatInput onSend={onSend} />);

    const textarea = screen.getByPlaceholderText('메시지를 입력하세요...') as HTMLTextAreaElement;
    await user.type(textarea, 'Test message{Enter}');

    await waitFor(() => {
      expect(textarea.value).toBe('');
    });
  });

  it('shows loader icon when disabled', () => {
    render(<ChatInput onSend={vi.fn()} disabled={true} />);

    // Loader2 icon should be present
    const button = screen.getByRole('button', { name: '메시지 보내기' });
    expect(button).toBeInTheDocument();
    expect(button.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('textarea is disabled when disabled prop is true', () => {
    render(<ChatInput onSend={vi.fn()} disabled={true} />);

    const textarea = screen.getByPlaceholderText('메시지를 입력하세요...');
    expect(textarea).toBeDisabled();
  });

  it('send button is disabled when disabled prop is true', () => {
    render(<ChatInput onSend={vi.fn()} disabled={true} />);

    const button = screen.getByRole('button', { name: '메시지 보내기' });
    expect(button).toBeDisabled();
  });

  it('send button is disabled when input is empty', () => {
    render(<ChatInput onSend={vi.fn()} />);

    const button = screen.getByRole('button', { name: '메시지 보내기' });
    expect(button).toBeDisabled();
  });

  it('send button is enabled when input has content', async () => {
    const user = userEvent.setup();
    render(<ChatInput onSend={vi.fn()} />);

    const textarea = screen.getByPlaceholderText('메시지를 입력하세요...');
    const button = screen.getByRole('button', { name: '메시지 보내기' });

    // Initially disabled
    expect(button).toBeDisabled();

    // Type content
    await user.type(textarea, 'Hello');

    // Should be enabled
    expect(button).not.toBeDisabled();
  });

  it('calls onSend when send button clicked', async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();

    render(<ChatInput onSend={onSend} />);

    const textarea = screen.getByPlaceholderText('메시지를 입력하세요...');
    await user.type(textarea, 'Click test');

    const button = screen.getByRole('button', { name: '메시지 보내기' });
    await user.click(button);

    expect(onSend).toHaveBeenCalledWith('Click test');
  });

  it('trims whitespace before sending', async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();

    render(<ChatInput onSend={onSend} />);

    const textarea = screen.getByPlaceholderText('메시지를 입력하세요...');
    await user.type(textarea, '  Trimmed message  {Enter}');

    expect(onSend).toHaveBeenCalledWith('Trimmed message');
  });
});

describe('ChatMessageList', () => {
  const createMessage = (id: string, content: string): ChatMessage => ({
    id,
    role: 'user',
    content,
    timestamp: new Date().toISOString(),
  });

  it('shows empty state when no messages', () => {
    render(<ChatMessageList messages={[]} />);

    expect(screen.getByText('워크플로우를 테스트해보세요')).toBeInTheDocument();
    expect(screen.getByText('메시지를 보내면 워크플로우가 실행됩니다')).toBeInTheDocument();
  });

  it('renders messages when provided', () => {
    const messages = [
      createMessage('msg-1', 'First message'),
      createMessage('msg-2', 'Second message'),
    ];

    render(<ChatMessageList messages={messages} />);

    expect(screen.getByText('First message')).toBeInTheDocument();
    expect(screen.getByText('Second message')).toBeInTheDocument();
  });

  it('does not show empty state when messages exist', () => {
    const messages = [createMessage('msg-1', 'Test')];

    render(<ChatMessageList messages={messages} />);

    expect(screen.queryByText('워크플로우를 테스트해보세요')).not.toBeInTheDocument();
  });

  it('shows empty state text in Korean', () => {
    render(<ChatMessageList messages={[]} />);

    // Verify Korean text is present (use exact text to avoid multiple matches)
    expect(screen.getByText('워크플로우를 테스트해보세요')).toBeInTheDocument();
    expect(screen.getByText('메시지를 보내면 워크플로우가 실행됩니다')).toBeInTheDocument();
  });

  it('renders multiple messages in order', () => {
    const messages = [
      createMessage('msg-1', 'Message 1'),
      createMessage('msg-2', 'Message 2'),
      createMessage('msg-3', 'Message 3'),
    ];

    const { container } = render(<ChatMessageList messages={messages} />);

    const bubbles = container.querySelectorAll('.text-sm.whitespace-pre-wrap');
    expect(bubbles).toHaveLength(3);
    expect(bubbles[0].textContent).toBe('Message 1');
    expect(bubbles[1].textContent).toBe('Message 2');
    expect(bubbles[2].textContent).toBe('Message 3');
  });

  it('shows MessageSquare icon in empty state', () => {
    const { container } = render(<ChatMessageList messages={[]} />);

    // Check for icon presence
    const icon = container.querySelector('.text-muted-foreground.opacity-30');
    expect(icon).toBeInTheDocument();
  });

  it('auto-scrolls to bottom when messages change', () => {
    const messages = [createMessage('msg-1', 'Message 1')];

    const { rerender } = render(<ChatMessageList messages={messages} />);

    const updatedMessages = [
      ...messages,
      createMessage('msg-2', 'Message 2'),
    ];

    // Mock scrollIntoView
    const scrollIntoViewMock = vi.fn();
    Element.prototype.scrollIntoView = scrollIntoViewMock;

    rerender(<ChatMessageList messages={updatedMessages} />);

    // scrollIntoView should be called for auto-scroll
    expect(scrollIntoViewMock).toHaveBeenCalled();
  });
});
