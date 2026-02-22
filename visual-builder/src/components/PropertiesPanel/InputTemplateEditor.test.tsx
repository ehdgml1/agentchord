import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { InputTemplateEditor } from './InputTemplateEditor';

// Mock workflowStore
const mockNodes: Array<{
  id: string;
  type: string;
  position: { x: number; y: number };
  data: Record<string, unknown>;
}> = [];
const mockEdges: Array<{
  id: string;
  source: string;
  target: string;
}> = [];

vi.mock('../../stores/workflowStore', () => ({
  useWorkflowStore: vi.fn((selector: (s: Record<string, unknown>) => unknown) =>
    selector({ nodes: mockNodes, edges: mockEdges })
  ),
}));

describe('InputTemplateEditor', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockNodes.length = 0;
    mockEdges.length = 0;
  });

  it('does not render when node has no incoming edges', () => {
    mockNodes.push({
      id: 'rag-1',
      type: 'rag',
      position: { x: 0, y: 0 },
      data: { name: 'RAG Node' },
    });
    // No edges targeting rag-1

    const onChange = vi.fn();
    const { container } = render(
      <InputTemplateEditor nodeId="rag-1" value="" onChange={onChange} />
    );

    expect(container.innerHTML).toBe('');
  });

  it('renders when node has incoming edges', () => {
    mockNodes.push(
      {
        id: 'agent-1',
        type: 'agent',
        position: { x: 0, y: 0 },
        data: { name: 'Classifier' },
      },
      {
        id: 'rag-1',
        type: 'rag',
        position: { x: 200, y: 0 },
        data: { name: 'RAG Node' },
      }
    );
    mockEdges.push({ id: 'e1', source: 'agent-1', target: 'rag-1' });

    const onChange = vi.fn();
    render(
      <InputTemplateEditor nodeId="rag-1" value="" onChange={onChange} />
    );

    expect(screen.getByText('입력 템플릿')).toBeInTheDocument();
    expect(screen.getByText('상위 노드의 출력 필드를 참조할 수 있습니다')).toBeInTheDocument();
  });

  it('shows upstream output fields as clickable badges', () => {
    mockNodes.push(
      {
        id: 'agent-1',
        type: 'agent',
        position: { x: 0, y: 0 },
        data: {
          name: 'Classifier',
          outputFields: [
            { name: 'query', type: 'text' },
            { name: 'category', type: 'text' },
          ],
        },
      },
      {
        id: 'rag-1',
        type: 'rag',
        position: { x: 200, y: 0 },
        data: { name: 'RAG Node' },
      }
    );
    mockEdges.push({ id: 'e1', source: 'agent-1', target: 'rag-1' });

    const onChange = vi.fn();
    render(
      <InputTemplateEditor nodeId="rag-1" value="" onChange={onChange} />
    );

    // Should show field badges
    expect(screen.getByText('사용 가능한 필드:')).toBeInTheDocument();
    expect(screen.getByText('query (Classifier)')).toBeInTheDocument();
    expect(screen.getByText('category (Classifier)')).toBeInTheDocument();
    // Should NOT show .output when outputFields exist
    expect(screen.queryByText('output (Classifier)')).not.toBeInTheDocument();
  });

  it('clicking a field badge inserts template expression', async () => {
    const user = userEvent.setup();
    mockNodes.push(
      {
        id: 'agent-1',
        type: 'agent',
        position: { x: 0, y: 0 },
        data: {
          name: 'Classifier',
          outputFields: [{ name: 'query', type: 'text' }],
        },
      },
      {
        id: 'rag-1',
        type: 'rag',
        position: { x: 200, y: 0 },
        data: { name: 'RAG Node' },
      }
    );
    mockEdges.push({ id: 'e1', source: 'agent-1', target: 'rag-1' });

    const onChange = vi.fn();
    render(
      <InputTemplateEditor nodeId="rag-1" value="" onChange={onChange} />
    );

    const queryBadge = screen.getByText('query (Classifier)');
    await user.click(queryBadge);

    expect(onChange).toHaveBeenCalledWith('{{agent-1.query}}');
  });

  it('shows current value in textarea', () => {
    mockNodes.push(
      {
        id: 'agent-1',
        type: 'agent',
        position: { x: 0, y: 0 },
        data: { name: 'Classifier' },
      },
      {
        id: 'rag-1',
        type: 'rag',
        position: { x: 200, y: 0 },
        data: { name: 'RAG Node' },
      }
    );
    mockEdges.push({ id: 'e1', source: 'agent-1', target: 'rag-1' });

    const onChange = vi.fn();
    render(
      <InputTemplateEditor
        nodeId="rag-1"
        value="{{agent-1.query}} 검색"
        onChange={onChange}
      />
    );

    const textarea = screen.getByRole('textbox');
    expect(textarea).toHaveValue('{{agent-1.query}} 검색');
  });

  it('calls onChange when typing in textarea', async () => {
    const user = userEvent.setup();
    mockNodes.push(
      {
        id: 'agent-1',
        type: 'agent',
        position: { x: 0, y: 0 },
        data: { name: 'Classifier' },
      },
      {
        id: 'rag-1',
        type: 'rag',
        position: { x: 200, y: 0 },
        data: { name: 'RAG Node' },
      }
    );
    mockEdges.push({ id: 'e1', source: 'agent-1', target: 'rag-1' });

    const onChange = vi.fn();
    render(
      <InputTemplateEditor nodeId="rag-1" value="" onChange={onChange} />
    );

    const textarea = screen.getByRole('textbox');
    await user.type(textarea, 'test');

    expect(onChange).toHaveBeenCalled();
  });

  it('shows fields from multiple upstream nodes', () => {
    mockNodes.push(
      {
        id: 'agent-1',
        type: 'agent',
        position: { x: 0, y: 0 },
        data: {
          name: 'Classifier',
          outputFields: [{ name: 'query', type: 'text' }],
        },
      },
      {
        id: 'agent-2',
        type: 'agent',
        position: { x: 0, y: 100 },
        data: {
          name: 'Enricher',
          outputFields: [{ name: 'context', type: 'text' }],
        },
      },
      {
        id: 'rag-1',
        type: 'rag',
        position: { x: 200, y: 50 },
        data: { name: 'RAG Node' },
      }
    );
    mockEdges.push(
      { id: 'e1', source: 'agent-1', target: 'rag-1' },
      { id: 'e2', source: 'agent-2', target: 'rag-1' }
    );

    const onChange = vi.fn();
    render(
      <InputTemplateEditor nodeId="rag-1" value="" onChange={onChange} />
    );

    expect(screen.getByText('query (Classifier)')).toBeInTheDocument();
    expect(screen.queryByText('output (Classifier)')).not.toBeInTheDocument();
    expect(screen.getByText('context (Enricher)')).toBeInTheDocument();
    expect(screen.queryByText('output (Enricher)')).not.toBeInTheDocument();
  });

  it('shows generic output reference even without outputFields', () => {
    mockNodes.push(
      {
        id: 'agent-1',
        type: 'agent',
        position: { x: 0, y: 0 },
        data: { name: 'SimpleAgent' },
      },
      {
        id: 'rag-1',
        type: 'rag',
        position: { x: 200, y: 0 },
        data: { name: 'RAG Node' },
      }
    );
    mockEdges.push({ id: 'e1', source: 'agent-1', target: 'rag-1' });

    const onChange = vi.fn();
    render(
      <InputTemplateEditor nodeId="rag-1" value="" onChange={onChange} />
    );

    // Should show the generic .output reference
    expect(screen.getByText('output (SimpleAgent)')).toBeInTheDocument();
  });

  it('textarea has correct placeholder text', () => {
    mockNodes.push(
      {
        id: 'agent-1',
        type: 'agent',
        position: { x: 0, y: 0 },
        data: { name: 'Agent' },
      },
      {
        id: 'rag-1',
        type: 'rag',
        position: { x: 200, y: 0 },
        data: {},
      }
    );
    mockEdges.push({ id: 'e1', source: 'agent-1', target: 'rag-1' });

    const onChange = vi.fn();
    render(
      <InputTemplateEditor nodeId="rag-1" value="" onChange={onChange} />
    );

    const textarea = screen.getByRole('textbox');
    expect(textarea).toHaveAttribute(
      'placeholder',
      '예: {{agent-classifier.query}} 에 대해 검색하세요'
    );
  });

  it('appends to existing value when clicking badge with non-empty value', async () => {
    const user = userEvent.setup();
    mockNodes.push(
      {
        id: 'agent-1',
        type: 'agent',
        position: { x: 0, y: 0 },
        data: {
          name: 'Classifier',
          outputFields: [{ name: 'query', type: 'text' }],
        },
      },
      {
        id: 'rag-1',
        type: 'rag',
        position: { x: 200, y: 0 },
        data: {},
      }
    );
    mockEdges.push({ id: 'e1', source: 'agent-1', target: 'rag-1' });

    const onChange = vi.fn();
    render(
      <InputTemplateEditor
        nodeId="rag-1"
        value="검색: "
        onChange={onChange}
      />
    );

    const queryBadge = screen.getByText('query (Classifier)');
    await user.click(queryBadge);

    // Should insert at cursor (start of textarea since no focus yet) or append
    const calledValue = onChange.mock.calls[0][0];
    expect(calledValue).toContain('{{agent-1.query}}');
  });

  it('uses node ID as fallback name when node name is empty', () => {
    mockNodes.push(
      {
        id: 'agent-1',
        type: 'agent',
        position: { x: 0, y: 0 },
        data: {
          outputFields: [{ name: 'result', type: 'text' }],
        },
      },
      {
        id: 'rag-1',
        type: 'rag',
        position: { x: 200, y: 0 },
        data: {},
      }
    );
    mockEdges.push({ id: 'e1', source: 'agent-1', target: 'rag-1' });

    const onChange = vi.fn();
    render(
      <InputTemplateEditor nodeId="rag-1" value="" onChange={onChange} />
    );

    // Falls back to node ID when name is not set
    expect(screen.getByText('result (agent-1)')).toBeInTheDocument();
  });

  it('shows only individual fields when outputFields defined (no .output badge)', () => {
    mockNodes.push(
      {
        id: 'agent-1',
        type: 'agent',
        position: { x: 0, y: 0 },
        data: {
          name: 'Classifier',
          outputFields: [
            { name: 'category', type: 'text' },
            { name: 'query', type: 'text' },
            { name: 'urgency', type: 'text' },
          ],
        },
      },
      {
        id: 'rag-1',
        type: 'rag',
        position: { x: 200, y: 0 },
        data: { name: 'RAG' },
      }
    );
    mockEdges.push({ id: 'e1', source: 'agent-1', target: 'rag-1' });

    const onChange = vi.fn();
    render(
      <InputTemplateEditor nodeId="rag-1" value="" onChange={onChange} />
    );

    // Should show individual fields
    expect(screen.getByText('category (Classifier)')).toBeInTheDocument();
    expect(screen.getByText('query (Classifier)')).toBeInTheDocument();
    expect(screen.getByText('urgency (Classifier)')).toBeInTheDocument();

    // Should NOT show .output badge when outputFields exist
    expect(screen.queryByText('output (Classifier)')).not.toBeInTheDocument();
  });

  it('shows only .output badge when no outputFields defined', () => {
    mockNodes.push(
      {
        id: 'agent-1',
        type: 'agent',
        position: { x: 0, y: 0 },
        data: {
          name: 'SimpleAgent',
          // No outputFields
        },
      },
      {
        id: 'rag-1',
        type: 'rag',
        position: { x: 200, y: 0 },
        data: { name: 'RAG' },
      }
    );
    mockEdges.push({ id: 'e1', source: 'agent-1', target: 'rag-1' });

    const onChange = vi.fn();
    render(
      <InputTemplateEditor nodeId="rag-1" value="" onChange={onChange} />
    );

    // Should show only the .output badge
    expect(screen.getByText('output (SimpleAgent)')).toBeInTheDocument();

    // Should not show any specific field badges
    expect(screen.queryByText(/category|query|urgency/)).not.toBeInTheDocument();
  });

  it('handles mixed upstream nodes (some with outputFields, some without)', () => {
    mockNodes.push(
      {
        id: 'agent-1',
        type: 'agent',
        position: { x: 0, y: 0 },
        data: {
          name: 'Classifier',
          outputFields: [{ name: 'category', type: 'text' }],
        },
      },
      {
        id: 'agent-2',
        type: 'agent',
        position: { x: 0, y: 100 },
        data: {
          name: 'SimpleAgent',
          // No outputFields
        },
      },
      {
        id: 'rag-1',
        type: 'rag',
        position: { x: 200, y: 50 },
        data: { name: 'RAG' },
      }
    );
    mockEdges.push(
      { id: 'e1', source: 'agent-1', target: 'rag-1' },
      { id: 'e2', source: 'agent-2', target: 'rag-1' }
    );

    const onChange = vi.fn();
    render(
      <InputTemplateEditor nodeId="rag-1" value="" onChange={onChange} />
    );

    // Classifier has outputFields - show individual field, no .output
    expect(screen.getByText('category (Classifier)')).toBeInTheDocument();
    expect(screen.queryByText('output (Classifier)')).not.toBeInTheDocument();

    // SimpleAgent has no outputFields - show .output only
    expect(screen.getByText('output (SimpleAgent)')).toBeInTheDocument();
  });

  it('shows {{input}} badge for original workflow input', () => {
    mockNodes.push(
      {
        id: 'agent-1',
        type: 'agent',
        position: { x: 0, y: 0 },
        data: { name: 'Classifier' },
      },
      {
        id: 'rag-1',
        type: 'rag',
        position: { x: 200, y: 0 },
        data: { name: 'RAG' },
      }
    );
    mockEdges.push({ id: 'e1', source: 'agent-1', target: 'rag-1' });

    const onChange = vi.fn();
    render(
      <InputTemplateEditor nodeId="rag-1" value="" onChange={onChange} />
    );

    // Should show {{input}} badge
    expect(screen.getByText('원본 입력 (사용자 질문)')).toBeInTheDocument();
  });

  it('discovers multi-hop ancestor fields (3-node chain)', () => {
    mockNodes.push(
      {
        id: 'agent-classifier',
        type: 'agent',
        position: { x: 0, y: 0 },
        data: {
          name: 'Classifier',
          outputFields: [{ name: 'query', type: 'text' }],
        },
      },
      {
        id: 'rag-kb',
        type: 'rag',
        position: { x: 200, y: 0 },
        data: {
          name: 'Knowledge Base',
          outputFields: [{ name: 'documents', type: 'text' }],
        },
      },
      {
        id: 'agent-responder',
        type: 'agent',
        position: { x: 400, y: 0 },
        data: { name: 'Responder' },
      }
    );
    mockEdges.push(
      { id: 'e1', source: 'agent-classifier', target: 'rag-kb' },
      { id: 'e2', source: 'rag-kb', target: 'agent-responder' }
    );

    const onChange = vi.fn();
    render(
      <InputTemplateEditor
        nodeId="agent-responder"
        value=""
        onChange={onChange}
      />
    );

    // Should show direct parent (rag-kb) field
    expect(screen.getByText('documents (Knowledge Base)')).toBeInTheDocument();

    // Should ALSO show ancestor (agent-classifier) field
    expect(screen.getByText('query (Classifier)')).toBeInTheDocument();

    // Should show {{input}} badge
    expect(screen.getByText('원본 입력 (사용자 질문)')).toBeInTheDocument();
  });

  it('handles cyclic graphs without infinite loop', () => {
    mockNodes.push(
      {
        id: 'agent-1',
        type: 'agent',
        position: { x: 0, y: 0 },
        data: {
          name: 'Agent1',
          outputFields: [{ name: 'result', type: 'text' }],
        },
      },
      {
        id: 'agent-2',
        type: 'agent',
        position: { x: 200, y: 0 },
        data: {
          name: 'Agent2',
          outputFields: [{ name: 'feedback', type: 'text' }],
        },
      },
      {
        id: 'agent-3',
        type: 'agent',
        position: { x: 400, y: 0 },
        data: { name: 'Agent3' },
      }
    );
    // Create cycle: agent-1 → agent-2 → agent-1, then agent-2 → agent-3
    mockEdges.push(
      { id: 'e1', source: 'agent-1', target: 'agent-2' },
      { id: 'e2', source: 'agent-2', target: 'agent-1' },
      { id: 'e3', source: 'agent-2', target: 'agent-3' }
    );

    const onChange = vi.fn();
    // Should not hang, should render
    render(
      <InputTemplateEditor nodeId="agent-3" value="" onChange={onChange} />
    );

    // Should show direct parent (agent-2) field
    expect(screen.getByText('feedback (Agent2)')).toBeInTheDocument();

    // BFS should discover agent-1 through the cycle without hanging
    expect(screen.getByText('result (Agent1)')).toBeInTheDocument();
  });

  it('clicking {{input}} badge inserts template expression', async () => {
    const user = userEvent.setup();
    mockNodes.push(
      {
        id: 'agent-1',
        type: 'agent',
        position: { x: 0, y: 0 },
        data: { name: 'Agent' },
      },
      {
        id: 'rag-1',
        type: 'rag',
        position: { x: 200, y: 0 },
        data: { name: 'RAG' },
      }
    );
    mockEdges.push({ id: 'e1', source: 'agent-1', target: 'rag-1' });

    const onChange = vi.fn();
    render(
      <InputTemplateEditor nodeId="rag-1" value="" onChange={onChange} />
    );

    const inputBadge = screen.getByText('원본 입력 (사용자 질문)');
    await user.click(inputBadge);

    expect(onChange).toHaveBeenCalledWith('{{input}}');
  });

  it('discovers fields from 4-node deep chain', () => {
    mockNodes.push(
      {
        id: 'node-1',
        type: 'agent',
        position: { x: 0, y: 0 },
        data: {
          name: 'Node1',
          outputFields: [{ name: 'field1', type: 'text' }],
        },
      },
      {
        id: 'node-2',
        type: 'agent',
        position: { x: 100, y: 0 },
        data: {
          name: 'Node2',
          outputFields: [{ name: 'field2', type: 'text' }],
        },
      },
      {
        id: 'node-3',
        type: 'agent',
        position: { x: 200, y: 0 },
        data: {
          name: 'Node3',
          outputFields: [{ name: 'field3', type: 'text' }],
        },
      },
      {
        id: 'node-4',
        type: 'agent',
        position: { x: 300, y: 0 },
        data: { name: 'Node4' },
      }
    );
    mockEdges.push(
      { id: 'e1', source: 'node-1', target: 'node-2' },
      { id: 'e2', source: 'node-2', target: 'node-3' },
      { id: 'e3', source: 'node-3', target: 'node-4' }
    );

    const onChange = vi.fn();
    render(<InputTemplateEditor nodeId="node-4" value="" onChange={onChange} />);

    // Should show all ancestor fields
    expect(screen.getByText('field1 (Node1)')).toBeInTheDocument();
    expect(screen.getByText('field2 (Node2)')).toBeInTheDocument();
    expect(screen.getByText('field3 (Node3)')).toBeInTheDocument();
  });
});
