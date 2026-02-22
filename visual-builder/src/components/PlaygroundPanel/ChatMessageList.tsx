import { memo, useRef, useEffect } from 'react';
import { MessageSquare } from 'lucide-react';
import type { ChatMessage } from '../../stores/playgroundStore';
import { ChatBubble } from './ChatBubble';

interface ChatMessageListProps {
  messages: ChatMessage[];
}

export const ChatMessageList = memo(function ChatMessageList({ messages }: ChatMessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 overflow-y-auto p-4 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3 text-center">
          <MessageSquare className="w-12 h-12 text-muted-foreground opacity-30" />
          <div>
            <p className="text-sm text-muted-foreground">워크플로우를 테스트해보세요</p>
            <p className="text-xs text-muted-foreground/70 mt-1">
              메시지를 보내면 워크플로우가 실행됩니다
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {messages.map((message) => (
        <ChatBubble key={message.id} message={message} />
      ))}
      <div ref={bottomRef} />
    </div>
  );
});
