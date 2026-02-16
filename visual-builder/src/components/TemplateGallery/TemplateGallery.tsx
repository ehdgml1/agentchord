/**
 * Template Gallery Component
 *
 * Provides a gallery of predefined workflow templates that users can
 * apply to quickly start with common workflow patterns.
 */

import { memo, useState, useCallback } from 'react';
import {
  Box,
  GitBranch,
  Workflow,
  Repeat,
  Wrench,
  Network,
} from 'lucide-react';
import { useShallow } from 'zustand/react/shallow';
import { useWorkflowStore } from '../../stores/workflowStore';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '../ui/card';
import { toast } from 'sonner';
import { BlockType } from '../../types/blocks';
import type { WorkflowNode, WorkflowEdge } from '../../types/workflow';

/**
 * Template definition structure
 */
interface WorkflowTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  icon: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
}

/**
 * Predefined workflow templates
 */
const TEMPLATES: WorkflowTemplate[] = [
  {
    id: 'simple-chain',
    name: 'Simple Chain',
    description: 'Two agents in sequence for basic data processing pipeline',
    category: 'Basic',
    icon: 'box',
    nodes: [
      {
        id: 'start-1',
        type: BlockType.START,
        position: { x: 100, y: 100 },
        data: { label: 'Start' },
      },
      {
        id: 'agent-1',
        type: BlockType.AGENT,
        position: { x: 100, y: 200 },
        data: {
          name: 'Data Extractor',
          role: 'Extract and structure data from input',
          model: 'claude-sonnet-4-5-20250929' as const,
          temperature: 0.3,
          maxTokens: 2000,
          label: 'Data Extractor',
        },
      },
      {
        id: 'agent-2',
        type: BlockType.AGENT,
        position: { x: 100, y: 350 },
        data: {
          name: 'Data Analyzer',
          role: 'Analyze and summarize extracted data',
          model: 'claude-sonnet-4-5-20250929' as const,
          temperature: 0.5,
          maxTokens: 2000,
          label: 'Data Analyzer',
        },
      },
      {
        id: 'end-1',
        type: BlockType.END,
        position: { x: 100, y: 500 },
        data: { label: 'End' },
      },
    ],
    edges: [
      { id: 'e-start-agent1', source: 'start-1', target: 'agent-1' },
      { id: 'e-agent1-agent2', source: 'agent-1', target: 'agent-2' },
      { id: 'e-agent2-end', source: 'agent-2', target: 'end-1' },
    ],
  },
  {
    id: 'conditional-router',
    name: 'Conditional Router',
    description: 'Route data to different agents based on condition',
    category: 'Control Flow',
    icon: 'git-branch',
    nodes: [
      {
        id: 'start-1',
        type: BlockType.START,
        position: { x: 250, y: 50 },
        data: { label: 'Start' },
      },
      {
        id: 'agent-1',
        type: BlockType.AGENT,
        position: { x: 250, y: 150 },
        data: {
          name: 'Classifier',
          role: 'Classify input type and set classification flag',
          model: 'claude-sonnet-4-5-20250929' as const,
          temperature: 0.2,
          maxTokens: 1000,
          label: 'Classifier',
        },
      },
      {
        id: 'condition-1',
        type: BlockType.CONDITION,
        position: { x: 250, y: 300 },
        data: {
          condition: 'input.classification === "complex"',
          trueLabel: 'Complex',
          falseLabel: 'Simple',
          label: 'Route by Type',
        },
      },
      {
        id: 'agent-2',
        type: BlockType.AGENT,
        position: { x: 100, y: 450 },
        data: {
          name: 'Complex Handler',
          role: 'Handle complex requests with detailed analysis',
          model: 'claude-sonnet-4-5-20250929' as const,
          temperature: 0.7,
          maxTokens: 3000,
          label: 'Complex Handler',
        },
      },
      {
        id: 'agent-3',
        type: BlockType.AGENT,
        position: { x: 400, y: 450 },
        data: {
          name: 'Simple Handler',
          role: 'Handle simple requests quickly',
          model: 'claude-haiku-4-5-20251001' as const,
          temperature: 0.3,
          maxTokens: 1000,
          label: 'Simple Handler',
        },
      },
      {
        id: 'end-1',
        type: BlockType.END,
        position: { x: 250, y: 600 },
        data: { label: 'End' },
      },
    ],
    edges: [
      { id: 'e-start-agent1', source: 'start-1', target: 'agent-1' },
      { id: 'e-agent1-condition', source: 'agent-1', target: 'condition-1' },
      {
        id: 'e-condition-agent2',
        source: 'condition-1',
        target: 'agent-2',
        sourceHandle: 'true',
        data: { condition: 'true' },
      },
      {
        id: 'e-condition-agent3',
        source: 'condition-1',
        target: 'agent-3',
        sourceHandle: 'false',
        data: { condition: 'false' },
      },
      { id: 'e-agent2-end', source: 'agent-2', target: 'end-1' },
      { id: 'e-agent3-end', source: 'agent-3', target: 'end-1' },
    ],
  },
  {
    id: 'parallel-processing',
    name: 'Parallel Processing',
    description: 'Process data with multiple agents in parallel',
    category: 'Performance',
    icon: 'workflow',
    nodes: [
      {
        id: 'start-1',
        type: BlockType.START,
        position: { x: 250, y: 50 },
        data: { label: 'Start' },
      },
      {
        id: 'parallel-1',
        type: BlockType.PARALLEL,
        position: { x: 250, y: 150 },
        data: {
          mergeStrategy: 'concat' as const,
          label: 'Parallel Split',
        },
      },
      {
        id: 'agent-1',
        type: BlockType.AGENT,
        position: { x: 100, y: 300 },
        data: {
          name: 'Sentiment Analyzer',
          role: 'Analyze sentiment and emotional tone',
          model: 'claude-sonnet-4-5-20250929' as const,
          temperature: 0.4,
          maxTokens: 1500,
          label: 'Sentiment Analyzer',
        },
      },
      {
        id: 'agent-2',
        type: BlockType.AGENT,
        position: { x: 400, y: 300 },
        data: {
          name: 'Entity Extractor',
          role: 'Extract named entities and keywords',
          model: 'claude-sonnet-4-5-20250929' as const,
          temperature: 0.2,
          maxTokens: 1500,
          label: 'Entity Extractor',
        },
      },
      {
        id: 'end-1',
        type: BlockType.END,
        position: { x: 250, y: 450 },
        data: { label: 'End' },
      },
    ],
    edges: [
      { id: 'e-start-parallel', source: 'start-1', target: 'parallel-1' },
      { id: 'e-parallel-agent1', source: 'parallel-1', target: 'agent-1' },
      { id: 'e-parallel-agent2', source: 'parallel-1', target: 'agent-2' },
      { id: 'e-agent1-end', source: 'agent-1', target: 'end-1' },
      { id: 'e-agent2-end', source: 'agent-2', target: 'end-1' },
    ],
  },
  {
    id: 'feedback-loop',
    name: 'Feedback Loop',
    description: 'Iteratively refine output until quality criteria are met',
    category: 'Quality',
    icon: 'repeat',
    nodes: [
      {
        id: 'start-1',
        type: BlockType.START,
        position: { x: 250, y: 50 },
        data: { label: 'Start' },
      },
      {
        id: 'agent-1',
        type: BlockType.AGENT,
        position: { x: 250, y: 150 },
        data: {
          name: 'Content Generator',
          role: 'Generate content based on input requirements',
          model: 'claude-sonnet-4-5-20250929' as const,
          temperature: 0.7,
          maxTokens: 3000,
          label: 'Content Generator',
        },
      },
      {
        id: 'feedback-1',
        type: BlockType.FEEDBACK_LOOP,
        position: { x: 250, y: 300 },
        data: {
          maxIterations: 3,
          stopCondition: 'output.quality >= 0.8',
          label: 'Quality Check',
        },
      },
      {
        id: 'end-1',
        type: BlockType.END,
        position: { x: 250, y: 450 },
        data: { label: 'End' },
      },
    ],
    edges: [
      { id: 'e-start-agent1', source: 'start-1', target: 'agent-1' },
      { id: 'e-agent1-feedback', source: 'agent-1', target: 'feedback-1' },
      { id: 'e-feedback-end', source: 'feedback-1', target: 'end-1' },
    ],
  },
  {
    id: 'mcp-tool-pipeline',
    name: 'MCP Tool Pipeline',
    description: 'Use MCP tool output as input for agent analysis',
    category: 'Integration',
    icon: 'wrench',
    nodes: [
      {
        id: 'start-1',
        type: BlockType.START,
        position: { x: 250, y: 50 },
        data: { label: 'Start' },
      },
      {
        id: 'mcp-1',
        type: BlockType.MCP_TOOL,
        position: { x: 250, y: 150 },
        data: {
          serverId: 'example-server',
          serverName: 'Example Server',
          toolName: 'fetch_data',
          description: 'Fetch data from external source',
          parameters: {},
          label: 'Fetch Data',
        },
      },
      {
        id: 'agent-1',
        type: BlockType.AGENT,
        position: { x: 250, y: 300 },
        data: {
          name: 'Data Interpreter',
          role: 'Interpret and explain the fetched data',
          model: 'claude-sonnet-4-5-20250929' as const,
          temperature: 0.5,
          maxTokens: 2000,
          label: 'Data Interpreter',
        },
      },
      {
        id: 'end-1',
        type: BlockType.END,
        position: { x: 250, y: 450 },
        data: { label: 'End' },
      },
    ],
    edges: [
      { id: 'e-start-mcp', source: 'start-1', target: 'mcp-1' },
      { id: 'e-mcp-agent1', source: 'mcp-1', target: 'agent-1' },
      { id: 'e-agent1-end', source: 'agent-1', target: 'end-1' },
    ],
  },
  {
    id: 'full-pipeline',
    name: 'Full Pipeline',
    description: 'Complete workflow with conditional routing and parallel processing',
    category: 'Advanced',
    icon: 'network',
    nodes: [
      {
        id: 'start-1',
        type: BlockType.START,
        position: { x: 350, y: 50 },
        data: { label: 'Start' },
      },
      {
        id: 'agent-1',
        type: BlockType.AGENT,
        position: { x: 350, y: 150 },
        data: {
          name: 'Intake Processor',
          role: 'Process and validate input data',
          model: 'claude-sonnet-4-5-20250929' as const,
          temperature: 0.3,
          maxTokens: 1500,
          label: 'Intake Processor',
        },
      },
      {
        id: 'condition-1',
        type: BlockType.CONDITION,
        position: { x: 350, y: 280 },
        data: {
          condition: 'input.requiresDeepAnalysis === true',
          trueLabel: 'Deep Analysis',
          falseLabel: 'Quick Process',
          label: 'Analysis Type',
        },
      },
      {
        id: 'parallel-1',
        type: BlockType.PARALLEL,
        position: { x: 150, y: 410 },
        data: {
          mergeStrategy: 'concat' as const,
          label: 'Parallel Analysis',
        },
      },
      {
        id: 'agent-2',
        type: BlockType.AGENT,
        position: { x: 50, y: 540 },
        data: {
          name: 'Technical Analyzer',
          role: 'Perform technical analysis',
          model: 'claude-sonnet-4-5-20250929' as const,
          temperature: 0.4,
          maxTokens: 2500,
          label: 'Technical Analyzer',
        },
      },
      {
        id: 'agent-3',
        type: BlockType.AGENT,
        position: { x: 250, y: 540 },
        data: {
          name: 'Context Analyzer',
          role: 'Analyze contextual information',
          model: 'claude-sonnet-4-5-20250929' as const,
          temperature: 0.5,
          maxTokens: 2500,
          label: 'Context Analyzer',
        },
      },
      {
        id: 'agent-4',
        type: BlockType.AGENT,
        position: { x: 550, y: 410 },
        data: {
          name: 'Quick Processor',
          role: 'Perform quick processing for simple cases',
          model: 'claude-haiku-4-5-20251001' as const,
          temperature: 0.3,
          maxTokens: 1000,
          label: 'Quick Processor',
        },
      },
      {
        id: 'agent-5',
        type: BlockType.AGENT,
        position: { x: 350, y: 670 },
        data: {
          name: 'Final Synthesizer',
          role: 'Synthesize all analysis into final output',
          model: 'claude-sonnet-4-5-20250929' as const,
          temperature: 0.6,
          maxTokens: 3000,
          label: 'Final Synthesizer',
        },
      },
      {
        id: 'end-1',
        type: BlockType.END,
        position: { x: 350, y: 800 },
        data: { label: 'End' },
      },
    ],
    edges: [
      { id: 'e-start-agent1', source: 'start-1', target: 'agent-1' },
      { id: 'e-agent1-condition', source: 'agent-1', target: 'condition-1' },
      {
        id: 'e-condition-parallel',
        source: 'condition-1',
        target: 'parallel-1',
        sourceHandle: 'true',
        data: { condition: 'true' },
      },
      {
        id: 'e-condition-agent4',
        source: 'condition-1',
        target: 'agent-4',
        sourceHandle: 'false',
        data: { condition: 'false' },
      },
      { id: 'e-parallel-agent2', source: 'parallel-1', target: 'agent-2' },
      { id: 'e-parallel-agent3', source: 'parallel-1', target: 'agent-3' },
      { id: 'e-agent2-agent5', source: 'agent-2', target: 'agent-5' },
      { id: 'e-agent3-agent5', source: 'agent-3', target: 'agent-5' },
      { id: 'e-agent4-agent5', source: 'agent-4', target: 'agent-5' },
      { id: 'e-agent5-end', source: 'agent-5', target: 'end-1' },
    ],
  },
];

/**
 * Icon map for template categories
 */
const ICON_MAP = {
  box: Box,
  'git-branch': GitBranch,
  workflow: Workflow,
  repeat: Repeat,
  wrench: Wrench,
  network: Network,
} as const;

/**
 * Template Gallery Component
 */
export const TemplateGallery = memo(function TemplateGallery() {
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [applying, setApplying] = useState(false);
  const { clearWorkflow, loadWorkflow } = useWorkflowStore(
    useShallow(s => ({
      clearWorkflow: s.clearWorkflow,
      loadWorkflow: s.loadWorkflow,
    }))
  );

  // Get unique categories
  const categories = ['all', ...new Set(TEMPLATES.map((t) => t.category))];

  // Filter templates by category
  const filteredTemplates =
    selectedCategory === 'all'
      ? TEMPLATES
      : TEMPLATES.filter((t) => t.category === selectedCategory);

  /**
   * Apply a template to the workflow
   */
  const handleApplyTemplate = useCallback(
    (template: WorkflowTemplate) => {
      if (applying) return;
      setApplying(true);

      // Clear current workflow
      clearWorkflow();

      // Load template as a workflow
      const workflow = {
        id: `template-${template.id}-${Date.now()}`,
        name: template.name,
        description: template.description,
        nodes: template.nodes,
        edges: template.edges,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };

      loadWorkflow(workflow);
      toast.success(`Template "${template.name}" applied successfully`);

      // Reset after a tick to prevent immediate re-click
      setTimeout(() => setApplying(false), 500);
    },
    [applying, clearWorkflow, loadWorkflow]
  );

  return (
    <div className="p-4 space-y-4">
      <div className="space-y-2">
        <h2 className="text-lg font-semibold">Workflow Templates</h2>
        <p className="text-sm text-muted-foreground">
          Start with a predefined template to quickly build common workflow patterns
        </p>
      </div>

      {/* Category filter */}
      <div className="flex gap-2 flex-wrap">
        {categories.map((category) => (
          <Button
            key={category}
            variant={selectedCategory === category ? 'default' : 'outline'}
            size="sm"
            onClick={() => setSelectedCategory(category)}
          >
            {category.charAt(0).toUpperCase() + category.slice(1)}
          </Button>
        ))}
      </div>

      {/* Template grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" role="list">
        {filteredTemplates.map((template) => {
          const Icon = ICON_MAP[template.icon as keyof typeof ICON_MAP] || Box;

          return (
            <Card key={template.id} role="listitem" aria-label={`${template.name} template`}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <Icon className="h-5 w-5" />
                    <CardTitle className="text-base">{template.name}</CardTitle>
                  </div>
                  <Badge variant="secondary" className="text-xs">
                    {template.category}
                  </Badge>
                </div>
                <CardDescription className="text-xs">
                  {template.description}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex gap-4 text-xs text-muted-foreground">
                  <div>
                    <span className="font-medium">{template.nodes.length}</span> nodes
                  </div>
                  <div>
                    <span className="font-medium">{template.edges.length}</span> connections
                  </div>
                </div>
              </CardContent>
              <CardFooter>
                <Button
                  className="w-full"
                  size="sm"
                  onClick={() => handleApplyTemplate(template)}
                  disabled={applying}
                  aria-label={`Apply ${template.name} template`}
                >
                  Apply Template
                </Button>
              </CardFooter>
            </Card>
          );
        })}
      </div>

      {filteredTemplates.length === 0 && (
        <div className="text-center py-8 text-muted-foreground">
          No templates found in this category
        </div>
      )}
    </div>
  );
});
