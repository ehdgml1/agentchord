import type { WorkflowNode, WorkflowEdge } from '../../types/workflow';
import {
  BlockType,
  type AgentBlockData,
  type MCPToolBlockData,
  type ConditionBlockData,
  type ParallelBlockData,
  type FeedbackLoopBlockData,
  type TriggerBlockData,
  type MultiAgentBlockData,
} from '../../types/blocks';
import type { CodeGenerator, GeneratedCode } from './types';

// Topological sort to get execution order
function topologicalSort(nodes: WorkflowNode[], edges: WorkflowEdge[]): string[] {
  const inDegree = new Map<string, number>();
  const adjacency = new Map<string, string[]>();

  nodes.forEach((n) => {
    inDegree.set(n.id, 0);
    adjacency.set(n.id, []);
  });

  edges.forEach((e) => {
    inDegree.set(e.target, (inDegree.get(e.target) || 0) + 1);
    adjacency.get(e.source)?.push(e.target);
  });

  const queue = nodes.filter((n) => inDegree.get(n.id) === 0).map((n) => n.id);
  const result: string[] = [];

  while (queue.length > 0) {
    const nodeId = queue.shift()!;
    result.push(nodeId);

    adjacency.get(nodeId)?.forEach((neighbor) => {
      const degree = (inDegree.get(neighbor) || 0) - 1;
      inDegree.set(neighbor, degree);
      if (degree === 0) {
        queue.push(neighbor);
      }
    });
  }

  return result;
}

export class AgentChordGenerator implements CodeGenerator {
  private nodeMap: Map<string, WorkflowNode> = new Map();
  private edgeMap: Map<string, WorkflowEdge[]> = new Map();
  private processedNodes: Set<string> = new Set();
  private indent = '    '; // 4 spaces

  generate(nodes: WorkflowNode[], edges: WorkflowEdge[]): string {
    const code = this.generateParts(nodes, edges);
    return [code.imports, code.agents, code.workflow, code.main]
      .filter(Boolean)
      .join('\n\n');
  }

  private generateParts(nodes: WorkflowNode[], edges: WorkflowEdge[]): GeneratedCode {
    // Build lookup maps
    this.nodeMap.clear();
    this.edgeMap.clear();
    this.processedNodes.clear();

    nodes.forEach((n) => this.nodeMap.set(n.id, n));
    edges.forEach((e) => {
      if (!this.edgeMap.has(e.source)) {
        this.edgeMap.set(e.source, []);
      }
      this.edgeMap.get(e.source)!.push(e);
    });

    const agentNodes = nodes.filter((n) => n.type === BlockType.AGENT);
    const complexNodes = nodes.filter(
      (n) =>
        n.type === BlockType.CONDITION ||
        n.type === BlockType.PARALLEL ||
        n.type === BlockType.FEEDBACK_LOOP ||
        n.type === BlockType.MCP_TOOL ||
        n.type === BlockType.TRIGGER ||
        n.type === BlockType.MULTI_AGENT
    );

    const useComplexFormat = complexNodes.length > 0;

    if (useComplexFormat) {
      return this.generateComplexWorkflow(nodes, edges, agentNodes);
    } else {
      return this.generateSimpleWorkflow(nodes, edges, agentNodes);
    }
  }

  private generateSimpleWorkflow(
    nodes: WorkflowNode[],
    edges: WorkflowEdge[],
    agentNodes: WorkflowNode[]
  ): GeneratedCode {
    const order = topologicalSort(nodes, edges);

    return {
      imports: this.generateImports(agentNodes.length > 0, agentNodes.length > 1),
      agents: this.generateAgents(agentNodes),
      workflow: this.generateWorkflow(agentNodes, order, edges, nodes),
      main: this.generateSimpleMain(agentNodes.length > 1),
    };
  }

  private generateComplexWorkflow(
    nodes: WorkflowNode[],
    edges: WorkflowEdge[],
    agentNodes: WorkflowNode[]
  ): GeneratedCode {
    const mcpToolNodes = nodes.filter((n) => n.type === BlockType.MCP_TOOL);
    const hasAsyncNodes = mcpToolNodes.length > 0 || agentNodes.length > 0;

    return {
      imports: this.generateComplexImports(nodes, hasAsyncNodes),
      agents: this.generateAgents(agentNodes),
      workflow: this.generateWorkflowFunction(nodes, edges, hasAsyncNodes),
      main: this.generateAsyncMain(hasAsyncNodes),
    };
  }

  private generateImports(hasAgents: boolean, hasMultipleAgents: boolean): string {
    if (!hasAgents) {
      return 'from agentchord import Agent';
    }

    if (hasMultipleAgents) {
      return 'from agentchord import Agent, Workflow';
    }

    return 'from agentchord import Agent';
  }

  private generateComplexImports(nodes: WorkflowNode[], hasAsyncNodes: boolean): string {
    const imports: string[] = [];

    if (hasAsyncNodes) {
      imports.push('import asyncio');
    }

    const hasAgents = nodes.some((n) => n.type === BlockType.AGENT);
    const hasMCPTools = nodes.some((n) => n.type === BlockType.MCP_TOOL);
    const hasMultiAgent = nodes.some((n) => n.type === BlockType.MULTI_AGENT);

    if (hasMultiAgent) {
      imports.push('from agentchord import Agent, AgentTeam');
    } else if (hasAgents) {
      imports.push('from agentchord import Agent');
    } else {
      // Always include Agent import even if no agents (for consistency)
      imports.push('from agentchord import Agent');
    }

    if (hasMCPTools) {
      imports.push('# from agentchord.protocols.mcp import MCPClient');
    }

    return imports.join('\n');
  }

  private generateAgents(agents: WorkflowNode[]): string {
    return agents
      .map((node, index) => {
        const data = node.data as AgentBlockData;
        const varName = this.getVariableName(data.name, index);
        const displayName = data.name || `agent_${index + 1}`;
        const lines = [
          `${varName} = Agent(`,
          `    name="${displayName}",`,
          `    role="${data.role || 'AI Assistant'}",`,
          `    model="${data.model}",`,
          `    temperature=${data.temperature ?? 0.7},`,
        ];

        if (data.systemPrompt) {
          lines.push(`    system_prompt="""${data.systemPrompt}""",`);
        }

        lines.push(')');
        return lines.join('\n');
      })
      .join('\n\n');
  }

  private generateWorkflowFunction(
    nodes: WorkflowNode[],
    edges: WorkflowEdge[],
    isAsync: boolean
  ): string {
    const startNodes = this.findStartNodes(nodes, edges);
    if (startNodes.length === 0) {
      return `# No start node found. Define entry point.`;
    }

    const funcDef = isAsync
      ? 'async def workflow_main(input_text: str):'
      : 'def workflow_main(input_text: str):';

    const body = this.generateNodeSequence(startNodes, 1);

    const returnStmt = `${this.indent}return result`;

    return `# --- Workflow Logic ---\n${funcDef}\n${body}\n${returnStmt}`;
  }

  private findStartNodes(nodes: WorkflowNode[], edges: WorkflowEdge[]): WorkflowNode[] {
    const hasIncoming = new Set(edges.map((e) => e.target));
    return nodes.filter((n) => !hasIncoming.has(n.id) && n.type !== BlockType.END);
  }

  private generateNodeSequence(startNodes: WorkflowNode[], level: number): string {
    const lines: string[] = [];
    const indent = this.indent.repeat(level);

    lines.push(`${indent}result = input_text`);

    for (const node of startNodes) {
      lines.push(...this.generateNodeExecution(node, level, 'result'));
    }

    return lines.join('\n');
  }

  private generateNodeExecution(
    node: WorkflowNode,
    level: number,
    inputVar: string
  ): string[] {
    if (this.processedNodes.has(node.id)) {
      return [];
    }
    this.processedNodes.add(node.id);

    const indent = this.indent.repeat(level);
    const lines: string[] = [];

    switch (node.type) {
      case BlockType.TRIGGER:
        lines.push(...this.generateTrigger(node, level));
        break;
      case BlockType.AGENT:
        lines.push(...this.generateAgent(node, level, inputVar));
        break;
      case BlockType.MCP_TOOL:
        lines.push(...this.generateMCPTool(node, level, inputVar));
        break;
      case BlockType.CONDITION:
        lines.push(...this.generateCondition(node, level, inputVar));
        return lines; // Condition handles its own children
      case BlockType.PARALLEL:
        lines.push(...this.generateParallel(node, level, inputVar));
        return lines; // Parallel handles its own children
      case BlockType.FEEDBACK_LOOP:
        lines.push(...this.generateFeedbackLoop(node, level, inputVar));
        return lines; // Loop handles its own children
      case BlockType.MULTI_AGENT:
        lines.push(...this.generateMultiAgent(node, level, inputVar));
        break;
      case BlockType.START:
        lines.push(`${indent}# Start node`);
        break;
      case BlockType.END:
        lines.push(`${indent}# End node`);
        return lines; // Don't process children
      default:
        lines.push(`${indent}# Unknown node type: ${node.type}`);
    }

    // Process next nodes
    const nextEdges = this.edgeMap.get(node.id) || [];
    for (const edge of nextEdges) {
      const nextNode = this.nodeMap.get(edge.target);
      if (nextNode) {
        lines.push(...this.generateNodeExecution(nextNode, level, 'result'));
      }
    }

    return lines;
  }

  private generateTrigger(node: WorkflowNode, level: number): string[] {
    const indent = this.indent.repeat(level);
    const data = node.data as TriggerBlockData;
    const lines: string[] = [];

    if (data.triggerType === 'cron') {
      lines.push(`${indent}# Trigger: Cron schedule (${data.cronExpression || 'not set'})`);
    } else if (data.triggerType === 'webhook') {
      lines.push(`${indent}# Trigger: Webhook (${data.webhookPath || 'not set'})`);
    } else {
      lines.push(`${indent}# Trigger: ${data.triggerType}`);
    }

    return lines;
  }

  private generateAgent(node: WorkflowNode, level: number, inputVar: string): string[] {
    const indent = this.indent.repeat(level);
    const varName = this.getAgentVarName(node.id);
    const data = node.data as AgentBlockData;

    return [
      `${indent}# Agent: ${data.name || 'Unnamed'}`,
      `${indent}result = await ${varName}.complete(${inputVar})`,
    ];
  }

  private generateMCPTool(node: WorkflowNode, level: number, inputVar: string): string[] {
    const indent = this.indent.repeat(level);
    const data = node.data as MCPToolBlockData;
    const params = JSON.stringify(data.parameters || {}, null, 2)
      .split('\n')
      .map((line, idx) => (idx === 0 ? line : `${indent}    ${line}`))
      .join('\n');

    return [
      `${indent}# MCP Tool: ${data.toolName} (${data.serverName})`,
      `${indent}# result = await mcp_client.call_tool(`,
      `${indent}#     server_id="${data.serverId}",`,
      `${indent}#     tool_name="${data.toolName}",`,
      `${indent}#     parameters=${params}`,
      `${indent}# )`,
    ];
  }

  private generateCondition(
    node: WorkflowNode,
    level: number,
    inputVar: string
  ): string[] {
    const indent = this.indent.repeat(level);
    const data = node.data as ConditionBlockData;
    const lines: string[] = [];

    const edges = this.edgeMap.get(node.id) || [];
    const trueEdge = edges.find((e) => e.data?.condition === 'true');
    const falseEdge = edges.find((e) => e.data?.condition === 'false');

    lines.push(`${indent}# Condition: ${data.condition}`);
    lines.push(`${indent}if ${data.condition}:`);

    if (trueEdge) {
      const trueNode = this.nodeMap.get(trueEdge.target);
      if (trueNode) {
        lines.push(...this.generateNodeExecution(trueNode, level + 1, inputVar));
      }
    } else {
      lines.push(`${indent}${this.indent}pass  # No true branch`);
    }

    if (falseEdge) {
      lines.push(`${indent}else:`);
      const falseNode = this.nodeMap.get(falseEdge.target);
      if (falseNode) {
        lines.push(...this.generateNodeExecution(falseNode, level + 1, inputVar));
      }
    }

    return lines;
  }

  private generateParallel(node: WorkflowNode, level: number, inputVar: string): string[] {
    const indent = this.indent.repeat(level);
    const data = node.data as ParallelBlockData;
    const lines: string[] = [];

    const edges = this.edgeMap.get(node.id) || [];
    if (edges.length === 0) {
      lines.push(`${indent}# Parallel: No branches defined`);
      return lines;
    }

    lines.push(`${indent}# Parallel execution (merge: ${data.mergeStrategy})`);

    const branchCalls = edges.map((edge, idx) => {
      const targetNode = this.nodeMap.get(edge.target);
      if (!targetNode) return `${indent}${this.indent}None  # Missing target`;

      if (targetNode.type === BlockType.AGENT) {
        const varName = this.getAgentVarName(targetNode.id);
        return `${indent}${this.indent}${varName}.complete(${inputVar})`;
      }
      return `${indent}${this.indent}# Branch ${idx + 1}: ${targetNode.type}`;
    });

    lines.push(`${indent}results = await asyncio.gather(`);
    lines.push(branchCalls.join(',\n'));
    lines.push(`${indent})`);

    // Apply merge strategy
    if (data.mergeStrategy === 'concat') {
      lines.push(`${indent}result = ' '.join(str(r) for r in results)`);
    } else if (data.mergeStrategy === 'first') {
      lines.push(`${indent}result = results[0] if results else ""`);
    } else if (data.mergeStrategy === 'last') {
      lines.push(`${indent}result = results[-1] if results else ""`);
    } else {
      lines.push(`${indent}result = results  # Custom merge strategy`);
    }

    // Mark branches as processed to avoid duplication
    edges.forEach((edge) => {
      if (edge.target) {
        this.processedNodes.add(edge.target);
      }
    });

    return lines;
  }

  private generateMultiAgent(
    node: WorkflowNode,
    level: number,
    inputVar: string
  ): string[] {
    const indent = this.indent.repeat(level);
    const data = node.data as MultiAgentBlockData;
    const lines: string[] = [];
    const teamName = data.name || 'team';
    const teamVar = this.toSnakeCase(teamName);

    lines.push(`${indent}# Multi-Agent Team: ${teamName}`);

    // Generate member agents
    const memberVars: string[] = [];
    for (const member of data.members || []) {
      const memberVar = this.toSnakeCase(member.name || `member_${memberVars.length + 1}`);
      memberVars.push(memberVar);
      lines.push(`${indent}${memberVar} = Agent(`);
      lines.push(`${indent}    name="${member.name || memberVar}",`);
      lines.push(`${indent}    role="${member.role}",`);
      lines.push(`${indent}    model="${member.model}",`);
      lines.push(`${indent}    temperature=${member.temperature ?? 0.7},`);
      if (member.systemPrompt) {
        lines.push(`${indent}    system_prompt="""${member.systemPrompt}""",`);
      }
      lines.push(`${indent})`);
    }

    // Generate team
    lines.push(`${indent}${teamVar} = AgentTeam(`);
    lines.push(`${indent}    name="${teamName}",`);
    if (memberVars.length > 0) {
      lines.push(`${indent}    members=[${memberVars.join(', ')}],`);
    } else {
      lines.push(`${indent}    members=[],`);
    }
    lines.push(`${indent}    strategy="${data.strategy}",`);
    lines.push(`${indent}    max_rounds=${data.maxRounds || 10},`);
    lines.push(`${indent})`);
    lines.push(`${indent}result = await ${teamVar}.run(${inputVar})`);

    return lines;
  }

  private generateFeedbackLoop(
    node: WorkflowNode,
    level: number,
    inputVar: string
  ): string[] {
    const indent = this.indent.repeat(level);
    const data = node.data as FeedbackLoopBlockData;
    const lines: string[] = [];

    const edges = this.edgeMap.get(node.id) || [];
    const bodyEdge = edges[0]; // Assume first edge is loop body

    lines.push(
      `${indent}# Feedback loop (max ${data.maxIterations} iterations, stop: ${data.stopCondition})`
    );
    lines.push(`${indent}loop_result = ${inputVar}`);
    lines.push(`${indent}for _iteration in range(${data.maxIterations}):`);

    if (bodyEdge) {
      const bodyNode = this.nodeMap.get(bodyEdge.target);
      if (bodyNode) {
        lines.push(
          ...this.generateNodeExecution(bodyNode, level + 1, 'loop_result')
        );
        // Mark as processed
        this.processedNodes.add(bodyEdge.target);
      }
    } else {
      lines.push(`${indent}${this.indent}pass  # No loop body`);
    }

    lines.push(`${indent}${this.indent}if ${data.stopCondition}:`);
    lines.push(`${indent}${this.indent}${this.indent}break`);
    lines.push(`${indent}result = loop_result`);

    return lines;
  }

  private getVariableName(name: string, index: number): string {
    if (name && name.trim()) {
      return this.toSnakeCase(name);
    }
    return `agent_${index + 1}`;
  }

  private getAgentVarName(nodeId: string): string {
    const node = this.nodeMap.get(nodeId);
    if (!node) return `agent_${nodeId.slice(0, 8)}`;

    const data = node.data as AgentBlockData;
    if (data.name && data.name.trim()) {
      return this.toSnakeCase(data.name);
    }
    return `agent_${nodeId.slice(0, 8)}`;
  }

  private generateWorkflow(
    agents: WorkflowNode[],
    order: string[],
    edges: WorkflowEdge[],
    nodes: WorkflowNode[]
  ): string {
    if (agents.length <= 1) return '';

    const agentNames = agents.map((n, index) =>
      this.getVariableName((n.data as AgentBlockData).name, index)
    );
    const flowString = this.buildFlowStringWithFallback(order, nodes, edges, agents);

    return [
      'workflow = Workflow(',
      `    agents=[${agentNames.join(', ')}],`,
      `    flow="${flowString}",`,
      ')',
    ].join('\n');
  }

  private buildFlowStringWithFallback(
    order: string[],
    nodes: WorkflowNode[],
    _edges: WorkflowEdge[],
    agents: WorkflowNode[]
  ): string {
    const agentNodeIds = order.filter((id) => {
      const node = nodes.find((n) => n.id === id);
      return node?.type === BlockType.AGENT;
    });

    if (agentNodeIds.length === 0) return '';

    return agentNodeIds
      .map((id) => {
        const index = agents.findIndex((a) => a.id === id);
        const node = nodes.find((n) => n.id === id);
        const data = node?.data as AgentBlockData;
        return this.getVariableName(data?.name, index >= 0 ? index : 0);
      })
      .join(' -> ');
  }

  private generateSimpleMain(hasWorkflow: boolean): string {
    if (hasWorkflow) {
      return [
        'if __name__ == "__main__":',
        '    result = workflow.run_sync("Your input here")',
        '    print(result.output)',
      ].join('\n');
    } else {
      return [
        'if __name__ == "__main__":',
        '    # Add your workflow execution here',
        '    pass',
      ].join('\n');
    }
  }

  private generateAsyncMain(isAsync: boolean): string {
    if (isAsync) {
      return [
        'if __name__ == "__main__":',
        '    input_text = "Your input here"',
        '    result = asyncio.run(workflow_main(input_text))',
        '    print(result)',
      ].join('\n');
    } else {
      return [
        'if __name__ == "__main__":',
        '    input_text = "Your input here"',
        '    result = workflow_main(input_text)',
        '    print(result)',
      ].join('\n');
    }
  }

  private toSnakeCase(str: string): string {
    return str
      .replace(/([a-z])([A-Z])/g, '$1_$2')
      .replace(/[\s-]+/g, '_')
      .toLowerCase();
  }
}
