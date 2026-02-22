import { describe, it, expect } from 'vitest';
import { AgentChordGenerator } from './agentchord';
import { generateCode } from './index';
import { BlockType } from '../../types/blocks';
import type { WorkflowNode, WorkflowEdge } from '../../types/workflow';
import type { AgentBlockData } from '../../types/blocks';

// Helper functions for creating test data
const agentNode = (
  id: string,
  name: string,
  model: 'gpt-4o-mini' | 'gpt-4o' = 'gpt-4o-mini',
  systemPrompt?: string
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
    ...(systemPrompt && { systemPrompt }),
  } as AgentBlockData,
});

const edge = (source: string, target: string): WorkflowEdge => ({
  id: `e-${source}-${target}`,
  source,
  target,
});

describe('AgentChordGenerator', () => {
  describe('generateCode wrapper', () => {
    it('should return a string', () => {
      const nodes = [agentNode('agent1', 'TestAgent')];
      const edges: WorkflowEdge[] = [];
      const result = generateCode(nodes, edges);
      expect(typeof result).toBe('string');
    });

    it('should return minimal string with empty nodes/edges', () => {
      const result = generateCode([], []);
      expect(result).toBeDefined();
      expect(result.length).toBeGreaterThan(0);
    });
  });

  describe('Single agent', () => {
    it('should generate import line with Agent', () => {
      const generator = new AgentChordGenerator();
      const nodes = [agentNode('agent1', 'TestAgent')];
      const result = generator.generate(nodes, []);
      expect(result).toContain('from agentchord import Agent');
    });

    it('should include agent name in output', () => {
      const generator = new AgentChordGenerator();
      const nodes = [agentNode('agent1', 'My Test Agent')];
      const result = generator.generate(nodes, []);
      expect(result).toContain('My Test Agent');
    });

    it('should include model name', () => {
      const generator = new AgentChordGenerator();
      const nodes = [agentNode('agent1', 'TestAgent', 'gpt-4o')];
      const result = generator.generate(nodes, []);
      expect(result).toContain('model="gpt-4o"');
    });

    it('should include temperature', () => {
      const generator = new AgentChordGenerator();
      const nodes = [agentNode('agent1', 'TestAgent')];
      const result = generator.generate(nodes, []);
      expect(result).toContain('temperature=0.7');
    });

    it('should include role', () => {
      const generator = new AgentChordGenerator();
      const nodes = [agentNode('agent1', 'TestAgent')];
      const result = generator.generate(nodes, []);
      expect(result).toContain('role="Assistant"');
    });

    it('should include systemPrompt when provided', () => {
      const generator = new AgentChordGenerator();
      const systemPrompt = 'You are a helpful assistant';
      const nodes = [agentNode('agent1', 'TestAgent', 'gpt-4o-mini', systemPrompt)];
      const result = generator.generate(nodes, []);
      expect(result).toContain('system_prompt="""You are a helpful assistant"""');
    });

    it('should use fallback agent_1 variable name for empty name', () => {
      const generator = new AgentChordGenerator();
      const nodes = [agentNode('agent1', '')];
      const result = generator.generate(nodes, []);
      expect(result).toContain('agent_1 = Agent(');
    });
  });

  describe('Multiple agents', () => {
    it('should generate import with Agent and Workflow', () => {
      const generator = new AgentChordGenerator();
      const nodes = [agentNode('agent1', 'Agent1'), agentNode('agent2', 'Agent2')];
      const result = generator.generate(nodes, [edge('agent1', 'agent2')]);
      expect(result).toContain('from agentchord import Agent, Workflow');
    });

    it('should generate workflow section', () => {
      const generator = new AgentChordGenerator();
      const nodes = [agentNode('agent1', 'Agent1'), agentNode('agent2', 'Agent2')];
      const result = generator.generate(nodes, [edge('agent1', 'agent2')]);
      expect(result).toContain('workflow = Workflow(');
    });

    it('should generate flow string with ->', () => {
      const generator = new AgentChordGenerator();
      const nodes = [agentNode('agent1', 'Agent1'), agentNode('agent2', 'Agent2')];
      const result = generator.generate(nodes, [edge('agent1', 'agent2')]);
      expect(result).toContain('->');
    });

    it('should generate main section with if __name__', () => {
      const generator = new AgentChordGenerator();
      const nodes = [agentNode('agent1', 'Agent1'), agentNode('agent2', 'Agent2')];
      const result = generator.generate(nodes, [edge('agent1', 'agent2')]);
      expect(result).toContain('if __name__ == "__main__"');
    });
  });

  describe('Topological sort (tested through generate)', () => {
    it('should produce correct order for linear chain A→B→C', () => {
      const generator = new AgentChordGenerator();
      const nodes = [
        agentNode('agent1', 'AgentA'),
        agentNode('agent2', 'AgentB'),
        agentNode('agent3', 'AgentC'),
      ];
      const edges = [edge('agent1', 'agent2'), edge('agent2', 'agent3')];
      const result = generator.generate(nodes, edges);

      // Check flow string contains correct order
      expect(result).toContain('agent_a -> agent_b -> agent_c');
    });

    it('should produce both agents with no edges', () => {
      const generator = new AgentChordGenerator();
      const nodes = [agentNode('agent1', 'Agent1'), agentNode('agent2', 'Agent2')];
      const result = generator.generate(nodes, []);

      // Both agents should be defined (variable names based on agent name, not id)
      expect(result).toContain('agent1 = Agent(');
      expect(result).toContain('agent2 = Agent(');
    });
  });

  describe('toSnakeCase (tested through generated variable names)', () => {
    it('should convert "My Agent" to my_agent', () => {
      const generator = new AgentChordGenerator();
      const nodes = [agentNode('agent1', 'My Agent')];
      const result = generator.generate(nodes, []);
      expect(result).toContain('my_agent = Agent(');
    });

    it('should convert "camelCase" to camel_case', () => {
      const generator = new AgentChordGenerator();
      const nodes = [agentNode('agent1', 'camelCase')];
      const result = generator.generate(nodes, []);
      expect(result).toContain('camel_case = Agent(');
    });

    it('should use fallback agent_N for empty name', () => {
      const generator = new AgentChordGenerator();
      const nodes = [
        agentNode('agent1', ''),
        agentNode('agent2', '   '), // whitespace-only
      ];
      const result = generator.generate(nodes, []);
      expect(result).toContain('agent_1 = Agent(');
      expect(result).toContain('agent_2 = Agent(');
    });
  });

  describe('Edge cases', () => {
    it('should only include agents in code with mixed node types', () => {
      const generator = new AgentChordGenerator();
      const nodes: WorkflowNode[] = [
        agentNode('agent1', 'Agent1'),
        {
          id: 'condition1',
          type: BlockType.CONDITION,
          position: { x: 0, y: 0 },
          data: { condition: 'true' },
        },
        agentNode('agent2', 'Agent2'),
      ];
      const result = generator.generate(nodes, []);

      // Should contain both agents
      expect(result).toContain('Agent1');
      expect(result).toContain('Agent2');
      // Should not reference condition node
      expect(result).not.toContain('condition1');
    });

    it('should handle agent with special characters in name', () => {
      const generator = new AgentChordGenerator();
      const nodes = [agentNode('agent1', 'Agent-Name-123')];
      const result = generator.generate(nodes, []);
      expect(result).toContain('agent_name_123 = Agent(');
    });

    it('should produce minimal output with no agent nodes', () => {
      const generator = new AgentChordGenerator();
      const nodes: WorkflowNode[] = [
        {
          id: 'condition1',
          type: BlockType.CONDITION,
          position: { x: 0, y: 0 },
          data: { condition: 'true' },
        },
      ];
      const result = generator.generate(nodes, []);

      // Should still have import
      expect(result).toContain('from agentchord import Agent');
      // Should not have workflow
      expect(result).not.toContain('workflow = Workflow');
    });
  });
});
