import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { WorkflowEditor } from './WorkflowEditor';

const mockNavigate = vi.fn();
const mockLoadFromBackend = vi.fn();
const mockUseParams = vi.fn();

vi.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
  useParams: () => mockUseParams(),
}));

vi.mock('../stores/workflowStore', () => ({
  useWorkflowStore: vi.fn((selector) => {
    const state = { loadFromBackend: mockLoadFromBackend };
    return selector ? selector(state) : state;
  }),
}));

vi.mock('../hooks/useUnsavedChanges', () => ({
  useUnsavedChanges: vi.fn(),
}));

vi.mock('../hooks/useAutoSave', () => ({
  useAutoSave: vi.fn(),
}));

vi.mock('@xyflow/react', () => ({
  ReactFlowProvider: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="react-flow-provider">{children}</div>
  ),
}));

vi.mock('../components/Canvas/Canvas', () => ({
  Canvas: () => <div data-testid="canvas">Canvas Component</div>,
}));

vi.mock('../components/Layout', () => ({
  Layout: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="layout">{children}</div>
  ),
}));

describe('WorkflowEditor', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockLoadFromBackend.mockResolvedValue(undefined);
  });

  describe('Rendering', () => {
    it('renders editor with Canvas for new workflow', () => {
      mockUseParams.mockReturnValue({ id: 'new' });

      render(<WorkflowEditor />);

      expect(screen.getByTestId('react-flow-provider')).toBeInTheDocument();
      expect(screen.getByTestId('layout')).toBeInTheDocument();
      expect(screen.getByTestId('canvas')).toBeInTheDocument();
    });

    it('renders editor with Canvas for existing workflow', () => {
      mockUseParams.mockReturnValue({ id: 'workflow-123' });

      render(<WorkflowEditor />);

      expect(screen.getByTestId('react-flow-provider')).toBeInTheDocument();
      expect(screen.getByTestId('layout')).toBeInTheDocument();
      expect(screen.getByTestId('canvas')).toBeInTheDocument();
    });

    it('wraps Canvas in Layout', () => {
      mockUseParams.mockReturnValue({ id: 'new' });

      render(<WorkflowEditor />);

      const layout = screen.getByTestId('layout');
      const canvas = screen.getByTestId('canvas');

      expect(layout).toContainElement(canvas);
    });

    it('wraps Layout in ReactFlowProvider', () => {
      mockUseParams.mockReturnValue({ id: 'new' });

      render(<WorkflowEditor />);

      const provider = screen.getByTestId('react-flow-provider');
      const layout = screen.getByTestId('layout');

      expect(provider).toContainElement(layout);
    });
  });

  describe('Data loading', () => {
    it('does not load workflow data when id is "new"', () => {
      mockUseParams.mockReturnValue({ id: 'new' });

      render(<WorkflowEditor />);

      expect(mockLoadFromBackend).not.toHaveBeenCalled();
    });

    it('does not load workflow data when no id provided', () => {
      mockUseParams.mockReturnValue({});

      render(<WorkflowEditor />);

      expect(mockLoadFromBackend).not.toHaveBeenCalled();
    });
  });
});
