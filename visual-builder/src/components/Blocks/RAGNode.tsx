import { memo } from 'react';
import { type NodeProps } from '@xyflow/react';
import { BookOpen } from 'lucide-react';
import { BaseNode } from './BaseNode';
import type { RAGBlockData } from '../../types/blocks';

type RAGNodeProps = NodeProps & {
  data: RAGBlockData & { label?: string };
};

export const RAGNode = memo(function RAGNode({ data, selected }: RAGNodeProps) {
  const docCount = data.documents?.length || 0;

  return (
    <BaseNode color="#8B5CF6" selected={selected}>
      <div className="p-3" aria-label={`RAG node: ${data.name || 'Unnamed RAG'}`}>
        <div className="flex items-center gap-2 mb-2">
          <div className="p-1.5 rounded bg-violet-100">
            <BookOpen className="w-4 h-4 text-violet-600" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-medium text-sm truncate">
              {data.name || 'Unnamed RAG'}
            </div>
            <div className="text-xs text-muted-foreground">
              {docCount} document{docCount !== 1 ? 's' : ''}
            </div>
          </div>
        </div>
        {data.systemPrompt && (
          <div className="text-xs text-muted-foreground line-clamp-2">
            {data.systemPrompt}
          </div>
        )}
      </div>
    </BaseNode>
  );
});
