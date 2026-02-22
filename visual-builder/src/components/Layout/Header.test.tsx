import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Header } from './Header';
import { useWorkflowStore } from '../../stores/workflowStore';

// Mock react-router-dom
const mockNavigate = vi.fn();
vi.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
}));

// Mock workflowStore
const mockSaveWorkflow = vi.fn().mockResolvedValue(undefined);
const mockSetWorkflowName = vi.fn();
const mockClearWorkflow = vi.fn();
const mockGetWorkflow = vi.fn(() => ({
  name: 'Test Workflow',
  nodes: [],
  edges: [],
}));

vi.mock('../../stores/workflowStore', () => ({
  useWorkflowStore: vi.fn((selector) => {
    const state = {
      workflowName: 'Test Workflow',
      setWorkflowName: mockSetWorkflowName,
      clearWorkflow: mockClearWorkflow,
      getWorkflow: mockGetWorkflow,
      saveWorkflow: mockSaveWorkflow,
      loadWorkflow: vi.fn(),
      isSaving: false,
      isDirty: false,
      backendId: null,
      nodes: [],
      edges: [],
      undo: vi.fn(),
      redo: vi.fn(),
      canUndo: () => false,
      canRedo: () => false,
    };
    return typeof selector === 'function' ? selector(state) : state;
  }),
}));

// Mock authStore
const mockLogout = vi.fn();

vi.mock('../../stores/authStore', () => ({
  useAuthStore: vi.fn((selector) => {
    const state = {
      user: { email: 'test@example.com' },
      logout: mockLogout,
    };
    return typeof selector === 'function' ? selector(state) : state;
  }),
}));

// Mock RunDialog
vi.mock('../RunDialog', () => ({
  RunDialog: ({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) => (
    <div data-testid="run-dialog" data-open={open}>
      Run Dialog Mock
    </div>
  ),
}));

// Mock codeGenerator
vi.mock('../../utils/codeGenerator', () => ({
  generateCode: vi.fn(() => 'print("generated code")'),
}));

// Mock ImportDialog
vi.mock('../ImportDialog/ImportDialog', () => ({
  ImportDialog: ({ open }: { open: boolean }) => (
    <div data-testid="import-dialog" data-open={open}>Import Dialog Mock</div>
  ),
}));

// Mock sonner
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
  },
}));

// Mock api
vi.mock('../../services/api', () => ({
  api: {
    workflows: {
      validate: vi.fn().mockResolvedValue({ valid: true, errors: [] }),
    },
  },
}));

// Mock confirm dialog
vi.mock('../ui/confirm-dialog', () => ({
  useConfirm: () => vi.fn().mockResolvedValue(true),
}));

describe('Header', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders AgentChord logo', () => {
    render(<Header />);
    expect(screen.getByText('AgentChord')).toBeInTheDocument();
  });

  it('renders workflow name', () => {
    render(<Header />);
    expect(screen.getByText('Test Workflow')).toBeInTheDocument();
  });

  it('renders user email', () => {
    render(<Header />);
    expect(screen.getByText('test@example.com')).toBeInTheDocument();
  });

  it('shows save button', () => {
    render(<Header />);
    const buttons = screen.getAllByRole('button');
    const saveButton = buttons.find((b) => b.textContent?.includes('Save') && !b.textContent?.includes('JSON'));
    expect(saveButton).toBeDefined();
  });

  it('shows Save JSON button', () => {
    render(<Header />);
    expect(screen.getByText('Save JSON')).toBeInTheDocument();
  });

  it('shows Export Python button', () => {
    render(<Header />);
    expect(screen.getByText('Export Python')).toBeInTheDocument();
  });

  it('shows Clear button', () => {
    render(<Header />);
    expect(screen.getByText('Clear')).toBeInTheDocument();
  });

  it('shows Run button', () => {
    render(<Header />);
    const buttons = screen.getAllByRole('button');
    const runButton = buttons.find((b) => b.textContent?.includes('Run'));
    expect(runButton).toBeDefined();
  });

  it('shows Logout button', () => {
    render(<Header />);
    expect(screen.getByText('Logout')).toBeInTheDocument();
  });

  it('allows editing workflow name', async () => {
    const user = userEvent.setup();
    render(<Header />);

    const nameButton = screen.getByText('Test Workflow');
    await user.click(nameButton);

    const input = screen.getByDisplayValue('Test Workflow') as HTMLInputElement;
    expect(input).toBeInTheDocument();
    expect(input).toHaveFocus();
  });

  it('updates workflow name on change', async () => {
    const user = userEvent.setup();
    render(<Header />);

    const nameButton = screen.getByText('Test Workflow');
    await user.click(nameButton);

    const input = screen.getByDisplayValue('Test Workflow') as HTMLInputElement;
    await user.clear(input);
    await user.type(input, 'New Workflow Name');

    expect(mockSetWorkflowName).toHaveBeenCalled();
  });

  it('exits edit mode on blur', async () => {
    const user = userEvent.setup();
    render(<Header />);

    const nameButton = screen.getByText('Test Workflow');
    await user.click(nameButton);

    const input = screen.getByDisplayValue('Test Workflow');
    await user.tab(); // Blur the input

    // Input should no longer be in the document
    expect(screen.queryByDisplayValue('Test Workflow')).not.toBeInTheDocument();
  });

  it('exits edit mode on Enter key', async () => {
    const user = userEvent.setup();
    render(<Header />);

    const nameButton = screen.getByText('Test Workflow');
    await user.click(nameButton);

    const input = screen.getByDisplayValue('Test Workflow');
    await user.type(input, '{Enter}');

    // Input should no longer be in the document
    expect(screen.queryByDisplayValue('Test Workflow')).not.toBeInTheDocument();
  });

  it('calls saveWorkflow when save button clicked', async () => {
    const user = userEvent.setup();
    render(<Header />);

    const buttons = screen.getAllByRole('button');
    const saveButton = buttons.find((b) => b.textContent?.includes('Save') && !b.textContent?.includes('JSON'));

    if (saveButton) {
      await user.click(saveButton);
      expect(mockSaveWorkflow).toHaveBeenCalled();
    }
  });

  it('calls logout when logout button clicked', async () => {
    const user = userEvent.setup();
    render(<Header />);

    const logoutButton = screen.getByText('Logout');
    await user.click(logoutButton);

    expect(mockLogout).toHaveBeenCalled();
  });

  it('opens run dialog when run button clicked', async () => {
    const user = userEvent.setup();
    render(<Header />);

    const buttons = screen.getAllByRole('button');
    const runButton = buttons.find((b) => b.textContent?.includes('Run'));

    if (runButton) {
      await user.click(runButton);

      const dialog = screen.getByTestId('run-dialog');
      expect(dialog).toHaveAttribute('data-open', 'true');
    }
  });

  it('shows "Saving..." text when saving', () => {
    vi.mocked(useWorkflowStore).mockImplementation((selector: any) => {
      const state = {
        workflowName: 'Test Workflow',
        setWorkflowName: mockSetWorkflowName,
        clearWorkflow: mockClearWorkflow,
        getWorkflow: mockGetWorkflow,
        saveWorkflow: mockSaveWorkflow,
        loadWorkflow: vi.fn(),
        isSaving: true,
        isDirty: false,
        backendId: null,
        nodes: [],
        edges: [],
        undo: vi.fn(),
        redo: vi.fn(),
        canUndo: () => false,
        canRedo: () => false,
      };
      return typeof selector === 'function' ? selector(state) : state;
    });
    render(<Header />);
    expect(screen.getByText('Saving...')).toBeInTheDocument();
  });

  it('shows "Save*" when workflow is dirty', () => {
    vi.mocked(useWorkflowStore).mockImplementation((selector: any) => {
      const state = {
        workflowName: 'Test Workflow',
        setWorkflowName: mockSetWorkflowName,
        clearWorkflow: mockClearWorkflow,
        getWorkflow: mockGetWorkflow,
        saveWorkflow: mockSaveWorkflow,
        loadWorkflow: vi.fn(),
        isSaving: false,
        isDirty: true,
        backendId: null,
        nodes: [],
        edges: [],
        undo: vi.fn(),
        redo: vi.fn(),
        canUndo: () => false,
        canRedo: () => false,
      };
      return typeof selector === 'function' ? selector(state) : state;
    });
    render(<Header />);
    expect(screen.getByText('Save*')).toBeInTheDocument();
  });

  it('disables save button when saving', () => {
    vi.mocked(useWorkflowStore).mockImplementation((selector: any) => {
      const state = {
        workflowName: 'Test Workflow',
        setWorkflowName: mockSetWorkflowName,
        clearWorkflow: mockClearWorkflow,
        getWorkflow: mockGetWorkflow,
        saveWorkflow: mockSaveWorkflow,
        loadWorkflow: vi.fn(),
        isSaving: true,
        isDirty: false,
        backendId: null,
        nodes: [],
        edges: [],
        undo: vi.fn(),
        redo: vi.fn(),
        canUndo: () => false,
        canRedo: () => false,
      };
      return typeof selector === 'function' ? selector(state) : state;
    });
    render(<Header />);
    const buttons = screen.getAllByRole('button');
    const saveButton = buttons.find((b) => b.textContent?.includes('Saving...'));
    expect(saveButton).toBeDisabled();
  });
});
