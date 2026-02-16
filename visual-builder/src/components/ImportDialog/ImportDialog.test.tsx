import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ImportDialog } from './ImportDialog';
import type { WorkflowExport } from '../../types';

// Mock the parseWorkflowImport function
vi.mock('../../lib/workflowExport', () => ({
  parseWorkflowImport: vi.fn(),
}));

// Mock the UI components
vi.mock('../ui/dialog', () => ({
  Dialog: ({ children, open }: any) => (open ? <div data-testid="dialog">{children}</div> : null),
  DialogContent: ({ children }: any) => <div data-testid="dialog-content">{children}</div>,
  DialogHeader: ({ children }: any) => <div data-testid="dialog-header">{children}</div>,
  DialogTitle: ({ children }: any) => <div data-testid="dialog-title">{children}</div>,
  DialogFooter: ({ children }: any) => <div data-testid="dialog-footer">{children}</div>,
}));

vi.mock('../ui/button', () => ({
  Button: ({ children, onClick, disabled, variant }: any) => (
    <button onClick={onClick} disabled={disabled} data-variant={variant}>
      {children}
    </button>
  ),
}));

describe('ImportDialog', () => {
  const mockOnOpenChange = vi.fn();
  const mockOnImport = vi.fn();

  const mockWorkflowData: WorkflowExport = {
    version: '1.0',
    exportedAt: '2024-01-01T00:00:00.000Z',
    workflow: {
      id: 'test-workflow',
      name: 'Test Workflow',
      description: 'Test Description',
      nodes: [{ id: '1', type: 'agent', position: { x: 0, y: 0 }, data: {} }],
      edges: [{ id: 'e1', source: '1', target: '2' }],
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders dialog when open', () => {
    render(
      <ImportDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        onImport={mockOnImport}
      />
    );

    expect(screen.getByTestId('dialog')).toBeInTheDocument();
    expect(screen.getByTestId('dialog-title')).toHaveTextContent('Import Workflow');
  });

  it('does not render when closed', () => {
    render(
      <ImportDialog
        open={false}
        onOpenChange={mockOnOpenChange}
        onImport={mockOnImport}
      />
    );

    expect(screen.queryByTestId('dialog')).not.toBeInTheDocument();
  });

  it('shows file selection UI initially', () => {
    render(
      <ImportDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        onImport={mockOnImport}
      />
    );

    expect(screen.getByText(/Drag and drop a workflow JSON file/i)).toBeInTheDocument();
    expect(screen.getByText('Select File')).toBeInTheDocument();
  });

  it('shows error when non-JSON file is selected', async () => {
    const { parseWorkflowImport } = await import('../../lib/workflowExport');

    render(
      <ImportDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        onImport={mockOnImport}
      />
    );

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    expect(fileInput).toBeInTheDocument();

    const file = new File(['content'], 'test.txt', { type: 'text/plain' });
    Object.defineProperty(fileInput, 'files', {
      value: [file],
      writable: false,
    });

    fireEvent.change(fileInput);

    await waitFor(() => {
      expect(screen.getByText('Please select a JSON file.')).toBeInTheDocument();
    });
  });

  it('displays import button as disabled initially', () => {
    render(
      <ImportDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        onImport={mockOnImport}
      />
    );

    const buttons = screen.getAllByText('Import Workflow');
    const importButton = buttons.find(btn => btn.tagName === 'BUTTON');
    expect(importButton).toBeDisabled();
  });

  it('calls onOpenChange when cancel is clicked', () => {
    render(
      <ImportDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        onImport={mockOnImport}
      />
    );

    const cancelButton = screen.getByText('Cancel');
    fireEvent.click(cancelButton);

    expect(mockOnOpenChange).toHaveBeenCalledWith(false);
  });

  it('handles drag and drop area', () => {
    render(
      <ImportDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        onImport={mockOnImport}
      />
    );

    const dropArea = screen.getByText(/Drag and drop/i).closest('div');
    expect(dropArea).toBeInTheDocument();

    // Test drag over
    fireEvent.dragOver(dropArea!, { preventDefault: vi.fn() });

    // Test drag leave
    fireEvent.dragLeave(dropArea!);
  });

  it('resets state when dialog closes', () => {
    const { rerender } = render(
      <ImportDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        onImport={mockOnImport}
      />
    );

    // Close the dialog
    rerender(
      <ImportDialog
        open={false}
        onOpenChange={mockOnOpenChange}
        onImport={mockOnImport}
      />
    );

    expect(screen.queryByTestId('dialog')).not.toBeInTheDocument();
  });
});
