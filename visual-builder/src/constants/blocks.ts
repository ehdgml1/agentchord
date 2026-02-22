/**
 * Block definitions for the visual workflow builder
 *
 * This module provides metadata for all block types including their visual
 * appearance, default configurations, and behavior hints.
 */

import { BlockType, type BlockDefinition, type RAGBlockData, type MultiAgentBlockData } from '../types/blocks';

/**
 * Complete definitions for all available block types
 *
 * Each definition includes:
 * - Visual properties (icon, color, label)
 * - Descriptive metadata
 * - Default configuration values
 */
export const BLOCK_DEFINITIONS: BlockDefinition[] = [
  {
    type: BlockType.TRIGGER,
    label: 'Trigger',
    description: 'Start workflow via schedule or webhook',
    icon: 'Zap',
    color: '#EF4444', // red-500
    defaultData: {
      triggerType: 'webhook',
      webhookPath: '',
      cronExpression: '',
    },
  },
  {
    type: BlockType.AGENT,
    label: 'Agent',
    description: 'AI agent that processes inputs',
    icon: 'Bot',
    color: '#3B82F6', // blue-500
    defaultData: {
      name: '',
      role: '',
      model: 'gpt-4o-mini',
      temperature: 0.7,
      maxTokens: 4096,
    },
  },
  {
    type: BlockType.MCP_TOOL,
    label: 'MCP Tool',
    description: 'External tool via MCP protocol',
    icon: 'Wrench',
    color: '#8B5CF6', // violet-500
    defaultData: {
      serverId: '',
      serverName: '',
      toolName: '',
      description: '',
      parameters: {},
    },
  },
  {
    type: BlockType.PARALLEL,
    label: 'Parallel',
    description: 'Execute multiple agents in parallel',
    icon: 'GitBranch',
    color: '#10B981', // emerald-500
    defaultData: {
      mergeStrategy: 'concat',
    },
  },
  {
    type: BlockType.CONDITION,
    label: 'Condition',
    description: 'Branch based on condition',
    icon: 'GitFork',
    color: '#F59E0B', // amber-500
    defaultData: {
      condition: '',
      trueLabel: 'Yes',
      falseLabel: 'No',
    },
  },
  {
    type: BlockType.FEEDBACK_LOOP,
    label: 'Feedback Loop',
    description: 'Iterate until condition met',
    icon: 'RefreshCw',
    color: '#EC4899', // pink-500
    defaultData: {
      maxIterations: 3,
      stopCondition: '',
    },
  },
  {
    type: BlockType.RAG,
    label: 'RAG',
    description: 'Retrieve and generate answers from documents',
    icon: 'BookOpen',
    color: '#8B5CF6', // violet-500
    defaultData: {
      name: 'RAG Node',
      documents: [],
      searchLimit: 5,
      enableBm25: true,
      chunkSize: 500,
      chunkOverlap: 50,
      systemPrompt: '',
      model: '',
      temperature: 0.3,
      maxTokens: 1024,
      embeddingProvider: undefined,
      embeddingModel: undefined,
      embeddingDimensions: undefined,
    } satisfies RAGBlockData,
  },
  {
    type: BlockType.MULTI_AGENT,
    label: 'Multi-Agent Team',
    description: 'Coordinate multiple AI agents as a team',
    icon: 'Users',
    color: '#6366F1', // indigo-500
    defaultData: {
      name: '',
      strategy: 'coordinator',
      members: [],
      maxRounds: 10,
      costBudget: 0,
    } satisfies MultiAgentBlockData,
  },
];

/**
 * Retrieve block definition by type
 *
 * @param type - The block type to look up
 * @returns Block definition or undefined if not found
 */
export const getBlockDefinition = (
  type: BlockType
): BlockDefinition | undefined =>
  BLOCK_DEFINITIONS.find((def) => def.type === type);

/**
 * Get all block definitions suitable for the palette
 *
 * Filters out special blocks like START and END that shouldn't
 * be user-creatable.
 *
 * @returns Array of palette-displayable block definitions
 */
export const getPaletteBlocks = (): BlockDefinition[] =>
  BLOCK_DEFINITIONS.filter(
    (def) => def.type !== BlockType.START && def.type !== BlockType.END
  );

/**
 * Check if a block type supports multiple inputs
 *
 * @param type - The block type to check
 * @returns True if block can accept multiple inputs
 */
export const supportsMultipleInputs = (type: BlockType): boolean => {
  switch (type) {
    case BlockType.PARALLEL:
    case BlockType.FEEDBACK_LOOP:
      return false;
    case BlockType.AGENT:
    case BlockType.MCP_TOOL:
    case BlockType.CONDITION:
      return true;
    default:
      return true;
  }
};

/**
 * Check if a block type supports multiple outputs
 *
 * @param type - The block type to check
 * @returns True if block can produce multiple outputs
 */
export const supportsMultipleOutputs = (type: BlockType): boolean => {
  switch (type) {
    case BlockType.CONDITION:
      return true; // true/false branches
    case BlockType.PARALLEL:
      return true; // multiple parallel branches
    default:
      return false;
  }
};
