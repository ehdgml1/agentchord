import { describe, it, expect } from 'vitest';
import { AgentWeaveGenerator } from './agentweave';
import { BlockType } from '../../types/blocks';
import type { WorkflowNode, WorkflowEdge } from '../../types/workflow';
import type {
  AgentBlockData,
  ConditionBlockData,
  ParallelBlockData,
  FeedbackLoopBlockData,
  MCPToolBlockData,
  TriggerBlockData,
} from '../../types/blocks';

// Helper functions for creating test nodes
const agentNode = (
  id: string,
  name: string,
  model: 'gpt-4o-mini' | 'gpt-4o' = 'gpt-4o-mini'
): WorkflowNode => ({
  id,
  type: BlockType.AGENT,
  position: { x: 0, y: 0 },
  data: {
    name,
    role: 'Assistant',
    model,
    temperature: 0.7,
    maxTokens: 4096,
  } as AgentBlockData,
});

const conditionNode = (id: string, condition: string): WorkflowNode => ({
  id,
  type: BlockType.CONDITION,
  position: { x: 0, y: 0 },
  data: {
    condition,
    trueLabel: 'true',
    falseLabel: 'false',
  } as ConditionBlockData,
});

const parallelNode = (
  id: string,
  mergeStrategy: 'concat' | 'first' | 'last' = 'concat'
): WorkflowNode => ({
  id,
  type: BlockType.PARALLEL,
  position: { x: 0, y: 0 },
  data: {
    mergeStrategy,
  } as ParallelBlockData,
});

const feedbackLoopNode = (
  id: string,
  maxIterations: number,
  stopCondition: string
): WorkflowNode => ({
  id,
  type: BlockType.FEEDBACK_LOOP,
  position: { x: 0, y: 0 },
  data: {
    maxIterations,
    stopCondition,
  } as FeedbackLoopBlockData,
});

const mcpToolNode = (id: string, toolName: string): WorkflowNode => ({
  id,
  type: BlockType.MCP_TOOL,
  position: { x: 0, y: 0 },
  data: {
    serverId: 'test-server',
    serverName: 'Test Server',
    toolName,
    description: 'Test tool',
    parameters: { param1: 'value1' },
  } as MCPToolBlockData,
});

const triggerNode = (
  id: string,
  triggerType: 'cron' | 'webhook',
  config?: string
): WorkflowNode => ({
  id,
  type: BlockType.TRIGGER,
  position: { x: 0, y: 0 },
  data: {
    triggerType,
    ...(triggerType === 'cron' ? { cronExpression: config } : { webhookPath: config }),
  } as TriggerBlockData,
});

const edge = (source: string, target: string, condition?: 'true' | 'false'): WorkflowEdge => ({
  id: `e-${source}-${target}`,
  source,
  target,
  ...(condition && { data: { condition } }),
});

describe('AgentWeaveGenerator - Complex Node Types', () => {
  describe('Condition nodes', () => {
    it('should generate if/else structure for condition node', () => {
      const generator = new AgentWeaveGenerator();
      const nodes = [
        conditionNode('cond1', 'result.success'),
        agentNode('agent1', 'SuccessAgent'),
        agentNode('agent2', 'FailureAgent'),
      ];
      const edges = [
        edge('cond1', 'agent1', 'true'),
        edge('cond1', 'agent2', 'false'),
      ];

      const result = generator.generate(nodes, edges);

      expect(result).toContain('# Condition: result.success');
      expect(result).toContain('if result.success:');
      expect(result).toContain('else:');
      expect(result).toContain('async def workflow_main');
    });

    it('should handle condition with only true branch', () => {
      const generator = new AgentWeaveGenerator();
      const nodes = [conditionNode('cond1', 'x > 0'), agentNode('agent1', 'Agent1')];
      const edges = [edge('cond1', 'agent1', 'true')];

      const result = generator.generate(nodes, edges);

      expect(result).toContain('if x > 0:');
      expect(result).not.toContain('else:');
    });
  });

  describe('Parallel nodes', () => {
    it('should generate asyncio.gather for parallel execution', () => {
      const generator = new AgentWeaveGenerator();
      const nodes = [
        parallelNode('par1', 'concat'),
        agentNode('agent1', 'Agent1'),
        agentNode('agent2', 'Agent2'),
      ];
      const edges = [edge('par1', 'agent1'), edge('par1', 'agent2')];

      const result = generator.generate(nodes, edges);

      expect(result).toContain('asyncio.gather(');
      expect(result).toContain('# Parallel execution (merge: concat)');
      expect(result).toContain("result = ' '.join(str(r) for r in results)");
    });

    it('should handle "first" merge strategy', () => {
      const generator = new AgentWeaveGenerator();
      const nodes = [
        parallelNode('par1', 'first'),
        agentNode('agent1', 'Agent1'),
        agentNode('agent2', 'Agent2'),
      ];
      const edges = [edge('par1', 'agent1'), edge('par1', 'agent2')];

      const result = generator.generate(nodes, edges);

      expect(result).toContain('result = results[0] if results else ""');
    });

    it('should handle "last" merge strategy', () => {
      const generator = new AgentWeaveGenerator();
      const nodes = [
        parallelNode('par1', 'last'),
        agentNode('agent1', 'Agent1'),
        agentNode('agent2', 'Agent2'),
      ];
      const edges = [edge('par1', 'agent1'), edge('par1', 'agent2')];

      const result = generator.generate(nodes, edges);

      expect(result).toContain('result = results[-1] if results else ""');
    });
  });

  describe('Feedback Loop nodes', () => {
    it('should generate for loop with iteration limit', () => {
      const generator = new AgentWeaveGenerator();
      const nodes = [
        feedbackLoopNode('loop1', 5, 'result.done'),
        agentNode('agent1', 'LoopAgent'),
      ];
      const edges = [edge('loop1', 'agent1')];

      const result = generator.generate(nodes, edges);

      expect(result).toContain('for _iteration in range(5):');
      expect(result).toContain('if result.done:');
      expect(result).toContain('break');
      expect(result).toContain('# Feedback loop (max 5 iterations');
    });
  });

  describe('MCP Tool nodes', () => {
    it('should generate MCP tool call comment', () => {
      const generator = new AgentWeaveGenerator();
      const nodes = [mcpToolNode('mcp1', 'search')];
      const edges: WorkflowEdge[] = [];

      const result = generator.generate(nodes, edges);

      expect(result).toContain('# MCP Tool: search');
      expect(result).toContain('# result = await mcp_client.call_tool(');
      expect(result).toContain('server_id="test-server"');
      expect(result).toContain('tool_name="search"');
    });

    it('should include asyncio import for MCP tools', () => {
      const generator = new AgentWeaveGenerator();
      const nodes = [mcpToolNode('mcp1', 'search')];
      const edges: WorkflowEdge[] = [];

      const result = generator.generate(nodes, edges);

      expect(result).toContain('import asyncio');
    });
  });

  describe('Trigger nodes', () => {
    it('should generate comment for cron trigger', () => {
      const generator = new AgentWeaveGenerator();
      const nodes = [
        triggerNode('trigger1', 'cron', '0 0 * * *'),
        agentNode('agent1', 'Agent1'),
      ];
      const edges = [edge('trigger1', 'agent1')];

      const result = generator.generate(nodes, edges);

      expect(result).toContain('# Trigger: Cron schedule (0 0 * * *)');
    });

    it('should generate comment for webhook trigger', () => {
      const generator = new AgentWeaveGenerator();
      const nodes = [
        triggerNode('trigger1', 'webhook', '/api/webhook'),
        agentNode('agent1', 'Agent1'),
      ];
      const edges = [edge('trigger1', 'agent1')];

      const result = generator.generate(nodes, edges);

      expect(result).toContain('# Trigger: Webhook (/api/webhook)');
    });
  });

  describe('Complex workflows', () => {
    it('should handle workflow with multiple node types', () => {
      const generator = new AgentWeaveGenerator();
      const nodes = [
        triggerNode('trigger1', 'webhook', '/start'),
        agentNode('agent1', 'InputAgent'),
        conditionNode('cond1', 'result.valid'),
        parallelNode('par1', 'concat'),
        agentNode('agent2', 'ProcessorA'),
        agentNode('agent3', 'ProcessorB'),
        agentNode('agent4', 'OutputAgent'),
      ];
      const edges = [
        edge('trigger1', 'agent1'),
        edge('agent1', 'cond1'),
        edge('cond1', 'par1', 'true'),
        edge('par1', 'agent2'),
        edge('par1', 'agent3'),
        edge('cond1', 'agent4', 'false'),
      ];

      const result = generator.generate(nodes, edges);

      // Should use complex format
      expect(result).toContain('async def workflow_main');
      expect(result).toContain('import asyncio');
      expect(result).toContain('# Trigger: Webhook');
      expect(result).toContain('# Condition:');
      expect(result).toContain('asyncio.gather(');
      expect(result).toContain('if result.valid:');
      expect(result).toContain('else:');
    });

    it('should use simple format for agent-only workflows', () => {
      const generator = new AgentWeaveGenerator();
      const nodes = [
        agentNode('agent1', 'Agent1'),
        agentNode('agent2', 'Agent2'),
        agentNode('agent3', 'Agent3'),
      ];
      const edges = [edge('agent1', 'agent2'), edge('agent2', 'agent3')];

      const result = generator.generate(nodes, edges);

      // Should use simple Workflow format
      expect(result).toContain('workflow = Workflow(');
      expect(result).toContain('agent1 -> agent2 -> agent3');
      expect(result).not.toContain('async def workflow_main');
    });

    it('should nest conditions within loops', () => {
      const generator = new AgentWeaveGenerator();
      const nodes = [
        feedbackLoopNode('loop1', 10, 'result.converged'),
        conditionNode('cond1', 'result.error'),
        agentNode('agent1', 'RetryAgent'),
        agentNode('agent2', 'SuccessAgent'),
      ];
      const edges = [
        edge('loop1', 'cond1'),
        edge('cond1', 'agent1', 'true'),
        edge('cond1', 'agent2', 'false'),
      ];

      const result = generator.generate(nodes, edges);

      expect(result).toContain('for _iteration in range(10):');
      expect(result).toContain('if result.error:');
      expect(result).toContain('if result.converged:');
      expect(result).toContain('break');
    });
  });

  describe('Edge cases', () => {
    it('should handle empty parallel branches', () => {
      const generator = new AgentWeaveGenerator();
      const nodes = [parallelNode('par1', 'concat')];
      const edges: WorkflowEdge[] = [];

      const result = generator.generate(nodes, edges);

      expect(result).toContain('# Parallel: No branches defined');
    });

    it('should handle feedback loop with no body', () => {
      const generator = new AgentWeaveGenerator();
      const nodes = [feedbackLoopNode('loop1', 5, 'False')];
      const edges: WorkflowEdge[] = [];

      const result = generator.generate(nodes, edges);

      expect(result).toContain('for _iteration in range(5):');
      expect(result).toContain('pass  # No loop body');
    });

    it('should handle condition with no branches', () => {
      const generator = new AgentWeaveGenerator();
      const nodes = [conditionNode('cond1', 'True')];
      const edges: WorkflowEdge[] = [];

      const result = generator.generate(nodes, edges);

      expect(result).toContain('if True:');
      expect(result).toContain('pass  # No true branch');
    });
  });
});
