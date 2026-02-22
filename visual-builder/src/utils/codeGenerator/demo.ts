/**
 * Demo: AgentChord Code Generator Examples
 *
 * This file demonstrates various workflow patterns and their generated Python code.
 * Run this file to see console output of generated code.
 */

import { AgentChordGenerator } from './agentchord';
import { BlockType } from '../../types/blocks';
import type { WorkflowNode, WorkflowEdge } from '../../types/workflow';
import type {
  AgentBlockData,
  ConditionBlockData,
  ParallelBlockData,
  FeedbackLoopBlockData,
  TriggerBlockData,
} from '../../types/blocks';

// Helper functions
const agent = (id: string, name: string, model = 'gpt-4o-mini'): WorkflowNode => ({
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

const condition = (id: string, expr: string): WorkflowNode => ({
  id,
  type: BlockType.CONDITION,
  position: { x: 0, y: 0 },
  data: { condition: expr } as ConditionBlockData,
});

const parallel = (id: string, merge: 'concat' | 'first' | 'last' = 'concat'): WorkflowNode => ({
  id,
  type: BlockType.PARALLEL,
  position: { x: 0, y: 0 },
  data: { mergeStrategy: merge } as ParallelBlockData,
});

const loop = (id: string, max: number, stop: string): WorkflowNode => ({
  id,
  type: BlockType.FEEDBACK_LOOP,
  position: { x: 0, y: 0 },
  data: { maxIterations: max, stopCondition: stop } as FeedbackLoopBlockData,
});

const trigger = (id: string, type: 'cron' | 'webhook', config: string): WorkflowNode => ({
  id,
  type: BlockType.TRIGGER,
  position: { x: 0, y: 0 },
  data: {
    triggerType: type,
    ...(type === 'cron' ? { cronExpression: config } : { webhookPath: config }),
  } as TriggerBlockData,
});

const edge = (from: string, to: string, cond?: 'true' | 'false'): WorkflowEdge => ({
  id: `e-${from}-${to}`,
  source: from,
  target: to,
  ...(cond && { data: { condition: cond } }),
});

// Demo workflows
const generator = new AgentChordGenerator();

const demo1 = generator.generate(
  [agent('a1', 'Analyzer'), agent('a2', 'Processor'), agent('a3', 'Summarizer')],
  [edge('a1', 'a2'), edge('a2', 'a3')]
);

const demo2 = generator.generate(
  [
    trigger('t1', 'webhook', '/api/process'),
    agent('a1', 'Validator'),
    condition('c1', 'result.is_valid'),
    agent('a2', 'SuccessHandler'),
    agent('a3', 'ErrorHandler'),
  ],
  [
    edge('t1', 'a1'),
    edge('a1', 'c1'),
    edge('c1', 'a2', 'true'),
    edge('c1', 'a3', 'false'),
  ]
);

const demo3 = generator.generate(
  [
    agent('a1', 'DataLoader'),
    parallel('p1', 'concat'),
    agent('a2', 'Analyzer'),
    agent('a3', 'Classifier'),
    agent('a4', 'Extractor'),
    agent('a5', 'Aggregator'),
  ],
  [
    edge('a1', 'p1'),
    edge('p1', 'a2'),
    edge('p1', 'a3'),
    edge('p1', 'a4'),
    edge('a2', 'a5'),
  ]
);

const demo4 = generator.generate(
  [
    agent('a1', 'InitialDraft'),
    loop('l1', 5, 'result.quality > 0.9'),
    agent('a2', 'Refiner'),
    agent('a3', 'FinalReview'),
  ],
  [edge('a1', 'l1'), edge('l1', 'a2'), edge('a2', 'a3')]
);

const demo5 = generator.generate(
  [
    trigger('t1', 'cron', '0 */6 * * *'),
    agent('a1', 'DataCollector'),
    condition('c1', 'len(result.data) > 0'),
    parallel('p1', 'concat'),
    agent('a2', 'Processor_A'),
    agent('a3', 'Processor_B'),
    agent('a4', 'Merger'),
    loop('l1', 3, 'result.stable'),
    agent('a5', 'Optimizer'),
    agent('a6', 'Publisher'),
  ],
  [
    edge('t1', 'a1'),
    edge('a1', 'c1'),
    edge('c1', 'p1', 'true'),
    edge('p1', 'a2'),
    edge('p1', 'a3'),
    edge('a2', 'a4'),
    edge('a3', 'a4'),
    edge('a4', 'l1'),
    edge('l1', 'a5'),
    edge('a5', 'a6'),
  ]
);

const demo6 = generator.generate(
  [
    agent('a1', 'InputValidator'),
    condition('c1', 'result.error'),
    condition('c2', 'result.error.critical'),
    agent('a2', 'CriticalErrorHandler'),
    agent('a3', 'MinorErrorHandler'),
    agent('a4', 'SuccessProcessor'),
  ],
  [
    edge('a1', 'c1'),
    edge('c1', 'c2', 'true'),
    edge('c2', 'a2', 'true'),
    edge('c2', 'a3', 'false'),
    edge('c1', 'a4', 'false'),
  ]
);

// Export demos for use in other modules
export { demo1, demo2, demo3, demo4, demo5, demo6 };
