import type { WorkflowNode, WorkflowEdge } from '../../types/workflow';

export interface GeneratorContext {
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  indentLevel: number;
}

export interface CodeGenerator {
  generate(nodes: WorkflowNode[], edges: WorkflowEdge[]): string;
}

export interface GeneratedCode {
  imports: string;
  agents: string;
  workflow: string;
  main: string;
}
