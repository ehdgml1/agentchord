export { AgentWeaveGenerator } from './agentweave';
export type { CodeGenerator, GeneratedCode, GeneratorContext } from './types';

import { AgentWeaveGenerator } from './agentweave';
import type { WorkflowNode, WorkflowEdge } from '../../types/workflow';

const defaultGenerator = new AgentWeaveGenerator();

export function generateCode(nodes: WorkflowNode[], edges: WorkflowEdge[]): string {
  return defaultGenerator.generate(nodes, edges);
}
