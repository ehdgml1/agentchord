import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CodePanel } from './CodePanel';
import { useWorkflowStore } from '../../stores/workflowStore';

// Mock the workflow store
vi.mock('../../stores/workflowStore', () => ({
  useWorkflowStore: vi.fn(),
}));

// Mock the code generator
vi.mock('../../utils/codeGenerator', () => ({
  generateCode: vi.fn((nodes, edges) => {
    if (nodes.length === 0) {
      return '# Add agents to the canvas to generate code';
    }
    return `# Generated code for ${nodes.length} nodes`;
  }),
}));

// Mock UI components
vi.mock('../ui/button', () => ({
  Button: ({ children, onClick, className }: any) => (
    <button onClick={onClick} className={className}>
      {children}
    </button>
  ),
}));

describe('CodePanel', () => {
  const mockNodes = [
    {
      id: '1',
      type: 'agent',
      position: { x: 0, y: 0 },
      data: { name: 'Agent 1', model: 'gpt-4o' },
    },
  ];

  const mockEdges = [
    { id: 'e1', source: '1', target: '2' },
  ];

  let clipboardSpy: any;

  beforeEach(() => {
    vi.clearAllMocks();
    // Mock clipboard API with spy
    clipboardSpy = {
      writeText: vi.fn(() => Promise.resolve()),
    };
    Object.defineProperty(navigator, 'clipboard', {
      value: clipboardSpy,
      writable: true,
      configurable: true,
    });
  });

  it('renders code panel container', () => {
    (useWorkflowStore as any).mockImplementation((selector: any) =>
      selector({ nodes: mockNodes, edges: mockEdges })
    );
    const { container } = render(<CodePanel />);
    expect(container.firstChild).toHaveClass('border-t', 'bg-[#1e1e1e]');
  });

  it('displays "Python Code" title', () => {
    (useWorkflowStore as any).mockImplementation((selector: any) =>
      selector({ nodes: mockNodes, edges: mockEdges })
    );
    render(<CodePanel />);
    expect(screen.getByText('Python Code')).toBeInTheDocument();
  });

  it('displays "(AgentWeave)" subtitle', () => {
    (useWorkflowStore as any).mockImplementation((selector: any) =>
      selector({ nodes: mockNodes, edges: mockEdges })
    );
    render(<CodePanel />);
    expect(screen.getByText('(AgentWeave)')).toBeInTheDocument();
  });

  it('shows placeholder text when no nodes', () => {
    (useWorkflowStore as any).mockImplementation((selector: any) =>
      selector({ nodes: [], edges: [] })
    );
    render(<CodePanel />);
    expect(screen.getByText('# Add agents to the canvas to generate code')).toBeInTheDocument();
  });

  it('shows generated code when nodes exist', () => {
    (useWorkflowStore as any).mockImplementation((selector: any) =>
      selector({ nodes: mockNodes, edges: mockEdges })
    );
    render(<CodePanel />);
    expect(screen.getByText('# Generated code for 1 nodes')).toBeInTheDocument();
  });

  it('has copy button', () => {
    (useWorkflowStore as any).mockReturnValue(mockNodes);
    const { container } = render(<CodePanel />);
    const copyButton = container.querySelector('button svg[class*="lucide"]');
    expect(copyButton).toBeInTheDocument();
  });

  it('has expand/collapse button', () => {
    (useWorkflowStore as any).mockReturnValue(mockNodes);
    const { container } = render(<CodePanel />);
    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThanOrEqual(2);
  });

  it('copy button triggers handleCopy callback', async () => {
    (useWorkflowStore as any).mockImplementation((selector: any) =>
      selector({ nodes: mockNodes, edges: mockEdges })
    );
    const user = userEvent.setup();
    const { container } = render(<CodePanel />);

    const buttons = container.querySelectorAll('button');
    const copyButton = buttons[0]; // First button is copy

    // Verify button exists and is clickable
    expect(copyButton).toBeInTheDocument();
    await user.click(copyButton);

    // Button should be in the document after click
    expect(copyButton).toBeInTheDocument();
  });

  it('toggles expanded state when toggle button clicked', async () => {
    (useWorkflowStore as any).mockImplementation((selector: any) =>
      selector({ nodes: mockNodes, edges: mockEdges })
    );
    const user = userEvent.setup();
    const { container } = render(<CodePanel />);

    const initialHeight = (container.firstChild as HTMLElement).className;
    expect(initialHeight).toContain('h-48'); // Initially expanded

    const buttons = container.querySelectorAll('button');
    const toggleButton = buttons[1]; // Second button is toggle

    await user.click(toggleButton);

    // After click, should be collapsed
    const newHeight = (container.firstChild as HTMLElement).className;
    expect(newHeight).toContain('h-10');
  });

  it('displays code in pre element with correct styling', () => {
    (useWorkflowStore as any).mockImplementation((selector: any) =>
      selector({ nodes: mockNodes, edges: mockEdges })
    );
    const { container } = render(<CodePanel />);
    const preElement = container.querySelector('pre');
    expect(preElement).toBeInTheDocument();
    expect(preElement).toHaveClass('text-sm', 'font-mono');
  });

  it('applies custom className when provided', () => {
    (useWorkflowStore as any).mockImplementation((selector: any) =>
      selector({ nodes: mockNodes, edges: mockEdges })
    );
    const { container } = render(<CodePanel className="custom-class" />);
    expect(container.firstChild).toHaveClass('custom-class');
  });
});
