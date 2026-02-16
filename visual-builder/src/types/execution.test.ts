import { describe, it, expect } from 'vitest';
import type { Execution, NodeExecution } from './execution';

describe('Execution type', () => {
  it('should include token usage fields', () => {
    const execution: Execution = {
      id: 'exec-1',
      workflowId: 'wf-1',
      status: 'completed',
      mode: 'full',
      triggerType: 'manual',
      triggerId: null,
      input: '{}',
      output: null,
      error: null,
      nodeExecutions: [],
      startedAt: '2025-01-01T00:00:00Z',
      completedAt: '2025-01-01T00:01:00Z',
      durationMs: 60000,
      totalTokens: 1500,
      promptTokens: 1000,
      completionTokens: 500,
      estimatedCost: 0.0025,
      modelUsed: 'gpt-4o',
    };

    expect(execution.totalTokens).toBe(1500);
    expect(execution.promptTokens).toBe(1000);
    expect(execution.completionTokens).toBe(500);
    expect(execution.estimatedCost).toBe(0.0025);
    expect(execution.modelUsed).toBe('gpt-4o');
  });

  it('should allow null token fields', () => {
    const execution: Execution = {
      id: 'exec-2',
      workflowId: 'wf-2',
      status: 'pending',
      mode: 'mock',
      triggerType: 'manual',
      triggerId: null,
      input: '{}',
      output: null,
      error: null,
      nodeExecutions: [],
      startedAt: '2025-01-01T00:00:00Z',
      completedAt: null,
      durationMs: null,
      totalTokens: null,
      promptTokens: null,
      completionTokens: null,
      estimatedCost: null,
      modelUsed: null,
    };

    expect(execution.totalTokens).toBeNull();
    expect(execution.modelUsed).toBeNull();
  });

  it('NodeExecution should have required fields', () => {
    const nodeExec: NodeExecution = {
      nodeId: 'node-1',
      status: 'completed',
      input: { text: 'hello' },
      output: { result: 'world' },
      error: null,
      startedAt: '2025-01-01T00:00:00Z',
      completedAt: '2025-01-01T00:00:01Z',
      durationMs: 1000,
      retryCount: 0,
    };

    expect(nodeExec.nodeId).toBe('node-1');
    expect(nodeExec.retryCount).toBe(0);
  });
});
