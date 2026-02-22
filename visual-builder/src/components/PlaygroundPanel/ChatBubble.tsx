import { memo, useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { cn } from '../../lib/utils';
import type { ChatMessage } from '../../stores/playgroundStore';

interface ChatBubbleProps {
  message: ChatMessage;
}

const formatRelativeTime = (isoString: string): string => {
  const now = new Date();
  const timestamp = new Date(isoString);
  const diffMs = now.getTime() - timestamp.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (diffSec < 60) return '방금 전';
  if (diffMin < 60) return `${diffMin}분 전`;
  if (diffHour < 24) return `${diffHour}시간 전`;
  return `${diffDay}일 전`;
};

export const ChatBubble = memo(function ChatBubble({ message }: ChatBubbleProps) {
  const [isResultsExpanded, setIsResultsExpanded] = useState(false);
  const isUser = message.role === 'user';
  const isAssistant = message.role === 'assistant';

  // Show streaming dots if streaming and no content yet
  const showStreamingDots = message.isStreaming && !message.content;

  return (
    <div className={cn('flex flex-col', isUser && 'items-end')}>
      <div
        className={cn(
          'rounded-2xl px-4 py-2.5 max-w-[85%] break-words',
          isUser && 'bg-blue-600 text-white rounded-br-sm ml-auto',
          isAssistant && 'bg-zinc-100 dark:bg-zinc-800 text-foreground rounded-bl-sm',
          message.role === 'system' && 'bg-zinc-50 dark:bg-zinc-900 text-muted-foreground'
        )}
      >
        {showStreamingDots ? (
          <div className="flex items-center gap-1 py-1">
            <span className="w-2 h-2 bg-current rounded-full animate-pulse" style={{ animationDelay: '0ms' }} />
            <span className="w-2 h-2 bg-current rounded-full animate-pulse" style={{ animationDelay: '200ms' }} />
            <span className="w-2 h-2 bg-current rounded-full animate-pulse" style={{ animationDelay: '400ms' }} />
          </div>
        ) : (
          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        )}
      </div>

      <div className={cn('mt-1 px-1 flex items-center gap-2', isUser && 'flex-row-reverse')}>
        <span className="text-[10px] text-muted-foreground">
          {formatRelativeTime(message.timestamp)}
        </span>

        {message.tokenUsage && (
          <span className="text-[10px] text-muted-foreground bg-zinc-100 dark:bg-zinc-800 rounded px-1.5 py-0.5">
            🔤 {message.tokenUsage.total} 토큰
          </span>
        )}
      </div>

      {isAssistant && message.nodeResults && Object.keys(message.nodeResults).length > 0 && (
        <div className="mt-2 w-full max-w-[85%]">
          <button
            onClick={() => setIsResultsExpanded(!isResultsExpanded)}
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            {isResultsExpanded ? (
              <ChevronDown className="w-3.5 h-3.5" />
            ) : (
              <ChevronRight className="w-3.5 h-3.5" />
            )}
            <span>노드 실행 결과</span>
          </button>

          {isResultsExpanded && (
            <pre className="mt-1.5 text-xs font-mono bg-zinc-50 dark:bg-zinc-900 p-2 rounded overflow-auto max-h-40 border border-zinc-200 dark:border-zinc-700">
              {JSON.stringify(message.nodeResults, null, 2)}
            </pre>
          )}
        </div>
      )}
    </div>
  );
});
