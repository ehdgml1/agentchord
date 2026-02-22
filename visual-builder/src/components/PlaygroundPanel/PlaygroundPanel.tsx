import { memo, useCallback, useEffect, useRef } from 'react';
import { useShallow } from 'zustand/react/shallow';
import { MessageSquare, Trash2, X } from 'lucide-react';
import { Button } from '../ui/button';
import { usePlaygroundStore } from '../../stores/playgroundStore';
import { useWorkflowStore } from '../../stores/workflowStore';
import { useExecutionProgress } from '../../hooks/useExecutionProgress';
import { api } from '../../services/api';
import { ChatMessageList } from './ChatMessageList';
import { ChatInput } from './ChatInput';

export const PlaygroundPanel = memo(function PlaygroundPanel() {
  // Data that changes - needs useShallow
  const { messages, isStreaming, activeExecutionId } = usePlaygroundStore(
    useShallow((s) => ({
      messages: s.messages,
      isStreaming: s.isStreaming,
      activeExecutionId: s.activeExecutionId,
    }))
  );

  // Stable actions - don't need useShallow
  const close = usePlaygroundStore((s) => s.close);
  const clearMessages = usePlaygroundStore((s) => s.clearMessages);
  const addUserMessage = usePlaygroundStore((s) => s.addUserMessage);
  const setStreaming = usePlaygroundStore((s) => s.setStreaming);
  const addAssistantMessage = usePlaygroundStore((s) => s.addAssistantMessage);
  const updateStreamingMessage = usePlaygroundStore((s) => s.updateStreamingMessage);

  const backendId = useWorkflowStore((s) => s.backendId);

  // SSE streaming hook
  const { events, connectedId } = useExecutionProgress(activeExecutionId);

  // Track which execution we last processed events for
  const lastProcessedExecutionRef = useRef<string | null>(null);
  const processedCountRef = useRef(0);

  // Handle SSE events incrementally
  useEffect(() => {
    if (!events.length || !activeExecutionId) return;

    // Skip processing if events belong to a different execution (stale events from previous run)
    if (connectedId !== activeExecutionId) return;

    // Reset counter when execution changes
    if (lastProcessedExecutionRef.current !== activeExecutionId) {
      lastProcessedExecutionRef.current = activeExecutionId;
      processedCountRef.current = 0;
    }

    // Process only NEW events since last render
    const startIndex = processedCountRef.current;
    if (startIndex >= events.length) return;

    // Collect node results across all events
    const nodeResults: Record<string, unknown> = {};
    let finalContent: string | null = null;
    let hasFailed = false;
    let failedMessage = '';

    for (let i = startIndex; i < events.length; i++) {
      const event = events[i];

      if (event.type === 'node_completed' && event.data?.nodeId) {
        nodeResults[event.data.nodeId as string] = event.data.output;
        const output = event.data?.output;
        if (typeof output === 'string' && output) {
          updateStreamingMessage(output);
        }
      }

      if (event.type === 'completed') {
        const output = event.data?.output ?? '';
        const contentStr = typeof output === 'string' ? output : JSON.stringify(output, null, 2);
        finalContent = contentStr || null;
      }

      if (event.type === 'failed') {
        hasFailed = true;
        failedMessage = (event.data?.error as string) || '워크플로우 실행에 실패했습니다.';
      }
    }

    processedCountRef.current = events.length;

    // Apply final state
    if (hasFailed) {
      updateStreamingMessage(`⚠️ ${failedMessage}`);
      setStreaming(false);
    } else if (finalContent !== null) {
      // Collect ALL node results from all events for the response
      const allNodeResults: Record<string, unknown> = {};
      for (const evt of events) {
        if (evt.type === 'node_completed' && evt.data?.nodeId) {
          allNodeResults[evt.data.nodeId as string] = evt.data.output;
        }
      }
      updateStreamingMessage(finalContent || '(빈 응답)', { nodeResults: allNodeResults });
      setStreaming(false);
    }
  }, [events, activeExecutionId, connectedId, updateStreamingMessage, setStreaming]);

  // Handle sending a message
  const handleSend = useCallback(
    async (content: string) => {
      if (!backendId || isStreaming) return;

      // Add user message
      addUserMessage(content);

      // Use getState() to avoid stale closure
      const currentMessages = usePlaygroundStore.getState().messages;
      const history = currentMessages
        .filter((m) => !m.isStreaming)
        .map((m) => ({ role: m.role, content: m.content }));

      try {
        // Call backend to start workflow execution
        const result = await api.playground.chat(backendId, content, history);

        // Start streaming with execution ID
        setStreaming(true, result.executionId);
      } catch (err) {
        // Add error message
        const errorMsg = err instanceof Error ? err.message : '실행 중 오류가 발생했습니다. 워크플로우를 확인해주세요.';
        addAssistantMessage({ content: `⚠️ ${errorMsg}` });
      }
    },
    [backendId, isStreaming, addUserMessage, setStreaming, addAssistantMessage]
  );

  return (
    <div className="flex flex-col h-full border-l bg-background">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b">
        <div className="flex items-center gap-2">
          <MessageSquare className="w-4 h-4 text-muted-foreground" />
          <h2 className="text-sm font-semibold">플레이그라운드</h2>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            className="h-7 w-7 p-0"
            onClick={clearMessages}
            disabled={messages.length === 0 || isStreaming}
            title="초기화"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 w-7 p-0"
            onClick={close}
            title="닫기"
          >
            <X className="w-3.5 h-3.5" />
          </Button>
        </div>
      </div>

      {/* Workflow not saved warning */}
      {!backendId && (
        <div className="px-4 py-2 bg-amber-50 dark:bg-amber-950/20 border-b text-xs text-amber-700 dark:text-amber-400">
          워크플로우를 먼저 저장해주세요.
        </div>
      )}

      {/* Messages */}
      <ChatMessageList messages={messages} />

      {/* Input */}
      <ChatInput onSend={handleSend} disabled={isStreaming || !backendId} />
    </div>
  );
});
