import { TriggerNode } from './TriggerNode';
import { AgentNode } from './AgentNode';
import { MCPToolNode } from './MCPToolNode';
import { ParallelNode } from './ParallelNode';
import { ConditionNode } from './ConditionNode';
import { FeedbackLoopNode } from './FeedbackLoopNode';
import { RAGNode } from './RAGNode';
import { MultiAgentNode } from './MultiAgentNode';
import { BlockType } from '../../types/blocks';

export const nodeTypes = {
  [BlockType.TRIGGER]: TriggerNode,
  [BlockType.AGENT]: AgentNode,
  [BlockType.MCP_TOOL]: MCPToolNode,
  [BlockType.PARALLEL]: ParallelNode,
  [BlockType.CONDITION]: ConditionNode,
  [BlockType.FEEDBACK_LOOP]: FeedbackLoopNode,
  [BlockType.RAG]: RAGNode,
  [BlockType.MULTI_AGENT]: MultiAgentNode,
};

export { TriggerNode, AgentNode, MCPToolNode, ParallelNode, ConditionNode, FeedbackLoopNode, RAGNode, MultiAgentNode };
