/**
 * Block type definitions for Visual Builder
 *
 * This module defines the core block types and their associated data structures
 * used throughout the visual workflow builder.
 */

/**
 * Available block types in the workflow builder
 */
export const BlockType = {
  TRIGGER: 'trigger',
  AGENT: 'agent',
  MCP_TOOL: 'mcp_tool',
  PARALLEL: 'parallel',
  CONDITION: 'condition',
  FEEDBACK_LOOP: 'feedback_loop',
  RAG: 'rag',
  MULTI_AGENT: 'multi_agent',
  START: 'start',
  END: 'end',
} as const;

export type BlockType = (typeof BlockType)[keyof typeof BlockType];

/**
 * Supported AI model identifiers
 */
export type ModelId =
  | 'gpt-4o'
  | 'gpt-4o-mini'
  | 'gpt-4.1'
  | 'gpt-4.1-mini'
  | 'o1'
  | 'o1-mini'
  | 'claude-sonnet-4-5-20250929'
  | 'claude-haiku-4-5-20251001'
  | 'claude-opus-4-6'
  | 'llama3.1'
  | 'llama3.1:70b'
  | 'mistral'
  | 'codellama'
  | 'gemini-2.0-flash'
  | 'gemini-2.5-pro';

/**
 * Configuration data for Agent blocks
 */
export interface AgentBlockData extends Record<string, unknown> {
  /** Display name of the agent */
  name: string;
  /** Agent's role/purpose description */
  role: string;
  /** AI model to use for this agent */
  model: ModelId;
  /** Temperature parameter (0-1) for model randomness */
  temperature: number;
  /** Maximum tokens the model can generate */
  maxTokens: number;
  /** Optional system prompt to guide agent behavior */
  systemPrompt?: string;
  /** Optional list of MCP tool IDs available to this agent */
  mcpTools?: string[];
}

/**
 * Configuration data for MCP Tool blocks
 */
export interface MCPToolBlockData extends Record<string, unknown> {
  /** Unique identifier for the MCP server */
  serverId: string;
  /** Display name of the MCP server */
  serverName: string;
  /** Name of the specific tool to invoke */
  toolName: string;
  /** Human-readable description of the tool */
  description: string;
  /** Tool-specific parameters */
  parameters: Record<string, unknown>;
}

/**
 * Configuration data for Parallel execution blocks
 */
export interface ParallelBlockData extends Record<string, unknown> {
  /** Strategy for merging results from parallel branches */
  mergeStrategy: 'concat' | 'first' | 'last' | 'custom';
}

/**
 * Configuration data for Condition blocks
 */
export interface ConditionBlockData extends Record<string, unknown> {
  /** Boolean expression to evaluate */
  condition: string;
  /** Optional label for the true branch edge */
  trueLabel?: string;
  /** Optional label for the false branch edge */
  falseLabel?: string;
}

/**
 * Configuration data for Feedback Loop blocks
 */
export interface FeedbackLoopBlockData extends Record<string, unknown> {
  /** Maximum number of loop iterations */
  maxIterations: number;
  /** Expression to evaluate for loop termination */
  stopCondition: string;
}

/**
 * Configuration data for Trigger blocks
 */
export interface TriggerBlockData extends Record<string, unknown> {
  /** Type of trigger: cron for scheduled, webhook for HTTP triggers */
  triggerType: 'cron' | 'webhook';
  /** Cron expression for scheduled triggers */
  cronExpression?: string;
  /** Webhook path for webhook triggers */
  webhookPath?: string;
}

/**
 * Configuration for an individual agent member within a multi-agent team
 */
export interface AgentMemberConfig {
  /** Unique identifier for the member */
  id: string;
  /** Display name of the member */
  name: string;
  /** Role within the team */
  role: 'coordinator' | 'worker' | 'reviewer' | 'specialist';
  /** AI model to use for this member */
  model: string;
  /** System prompt to guide member behavior */
  systemPrompt: string;
  /** List of capabilities this member has */
  capabilities: string[];
  /** Temperature parameter (0-1) for model randomness */
  temperature: number;
}

/**
 * Configuration data for Multi-Agent Team blocks
 */
export interface MultiAgentBlockData extends Record<string, unknown> {
  /** Display name of the multi-agent team */
  name: string;
  /** Collaboration strategy for the team */
  strategy: 'coordinator' | 'round_robin' | 'debate' | 'map_reduce';
  /** List of agent members in the team */
  members: AgentMemberConfig[];
  /** Maximum number of collaboration rounds */
  maxRounds: number;
  /** Optional cost budget limit */
  costBudget: number;
}

/**
 * Configuration data for RAG blocks
 */
export interface RAGBlockData extends Record<string, unknown> {
  /** Display name of the RAG node */
  name: string;
  /** List of document paths or identifiers */
  documents: string[];
  /** Number of search results to retrieve */
  searchLimit: number;
  /** Enable BM25 keyword search */
  enableBm25: boolean;
  /** Size of text chunks for processing */
  chunkSize: number;
  /** Overlap between consecutive chunks */
  chunkOverlap: number;
  /** Optional system prompt for generation */
  systemPrompt: string;
  /** AI model to use for generation */
  model: string;
  /** Temperature parameter (0-1) for model randomness */
  temperature: number;
  /** Maximum tokens the model can generate */
  maxTokens: number;
}

/**
 * Union type for all possible block data configurations
 */
export type BlockData =
  | AgentBlockData
  | MCPToolBlockData
  | ParallelBlockData
  | ConditionBlockData
  | FeedbackLoopBlockData
  | TriggerBlockData
  | RAGBlockData
  | MultiAgentBlockData
  | Record<string, unknown>;

/**
 * Block definition for the palette/toolbox
 */
export interface BlockDefinition {
  /** Type identifier for this block */
  type: BlockType;
  /** Display label in the palette */
  label: string;
  /** Description shown in tooltip/help */
  description: string;
  /** Icon identifier or path */
  icon: string;
  /** Color for visual representation */
  color: string;
  /** Default data configuration for new instances */
  defaultData: BlockData;
}
