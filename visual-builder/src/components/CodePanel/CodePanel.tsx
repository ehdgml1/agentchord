import { memo, useMemo, useState, useCallback } from 'react';
import { Copy, Check, ChevronUp, ChevronDown } from 'lucide-react';
import { Button } from '../ui/button';
import { useWorkflowStore } from '../../stores/workflowStore';
import { generateCode } from '../../utils/codeGenerator';
import { cn } from '../../lib/utils';

interface CodePanelProps {
  className?: string;
}

export const CodePanel = memo(function CodePanel({ className }: CodePanelProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [copied, setCopied] = useState(false);

  const nodes = useWorkflowStore((state) => state.nodes);
  const edges = useWorkflowStore((state) => state.edges);

  const code = useMemo(() => {
    if (nodes.length === 0) {
      return '# Add agents to the canvas to generate code';
    }
    return generateCode(nodes, edges);
  }, [nodes, edges]);

  const handleCopy = useCallback(async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [code]);

  const toggleExpanded = useCallback(() => {
    setIsExpanded((prev) => !prev);
  }, []);

  return (
    <div
      className={cn(
        'border-t bg-[#1e1e1e] text-white transition-all duration-200',
        isExpanded ? 'h-48' : 'h-10',
        className
      )}
    >
      <div className="flex items-center justify-between px-4 h-10 border-b border-gray-700">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">Python Code</span>
          <span className="text-xs text-gray-400">(AgentWeave)</span>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-gray-400 hover:text-white hover:bg-gray-700"
            onClick={handleCopy}
          >
            {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-gray-400 hover:text-white hover:bg-gray-700"
            onClick={toggleExpanded}
          >
            {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
          </Button>
        </div>
      </div>

      {isExpanded && (
        <div className="p-4 h-[calc(100%-40px)] overflow-auto">
          <pre className="text-sm font-mono text-gray-300 whitespace-pre-wrap">
            {code}
          </pre>
        </div>
      )}
    </div>
  );
});
