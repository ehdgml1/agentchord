export { AgentChordGenerator } from './agentchord';
export type { CodeGenerator, GeneratedCode, GeneratorContext } from './types';

import { AgentChordGenerator } from './agentchord';
import type { WorkflowNode, WorkflowEdge } from '../../types/workflow';

const defaultGenerator = new AgentChordGenerator();

export function generateCode(nodes: WorkflowNode[], edges: WorkflowEdge[]): string {
  return defaultGenerator.generate(nodes, edges);
}
