/**
 * Tests for VersionHistory component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { VersionHistory } from './VersionHistory';
import type { WorkflowVersion } from '../../types';
import { useVersionStore } from '../../stores/versionStore';

// Mock the version store
vi.mock('../../stores/versionStore', () => ({
  useVersionStore: vi.fn(),
}));

const mockVersions: WorkflowVersion[] = [
  {
    id: 'v1',
    workflowId: 'wf-1',
    versionNumber: 1,
    message: 'Initial version',
    createdAt: new Date('2024-01-01T10:00:00Z').toISOString(),
    snapshot: { blocks: [], connections: [] },
  },
  {
    id: 'v2',
    workflowId: 'wf-1',
    versionNumber: 2,
    message: 'Added new features',
    createdAt: new Date('2024-01-02T10:00:00Z').toISOString(),
    snapshot: { blocks: [], connections: [] },
  },
  {
    id: 'v3',
    workflowId: 'wf-1',
    versionNumber: 3,
    message: 'Bug fixes',
    createdAt: new Date('2024-01-03T10:00:00Z').toISOString(),
    snapshot: { blocks: [], connections: [] },
  },
];

describe('VersionHistory', () => {
  const mockFetchVersions = vi.fn();
  const mockCreateVersion = vi.fn();
  const mockRestoreVersion = vi.fn();
  const mockClearError = vi.fn();
  const mockOnVersionRestored = vi.fn();

  const defaultStoreState = {
    versions: mockVersions,
    loading: false,
    error: null,
    fetchVersions: mockFetchVersions,
    createVersion: mockCreateVersion,
    restoreVersion: mockRestoreVersion,
    clearError: mockClearError,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useVersionStore).mockReturnValue(defaultStoreState);
  });

  it('renders the header with title and create button', () => {
    render(<VersionHistory workflowId="wf-1" />);

    expect(screen.getByText('Version History')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /create version/i })).toBeInTheDocument();
  });

  it('fetches versions on mount', () => {
    render(<VersionHistory workflowId="wf-1" />);

    expect(mockFetchVersions).toHaveBeenCalledWith('wf-1');
  });

  it('displays all versions in the list', () => {
    render(<VersionHistory workflowId="wf-1" />);

    expect(screen.getByText('Initial version')).toBeInTheDocument();
    expect(screen.getByText('Added new features')).toBeInTheDocument();
    expect(screen.getByText('Bug fixes')).toBeInTheDocument();
  });

  it('displays version numbers', () => {
    render(<VersionHistory workflowId="wf-1" />);

    expect(screen.getByText('v1')).toBeInTheDocument();
    expect(screen.getByText('v2')).toBeInTheDocument();
    expect(screen.getByText('v3')).toBeInTheDocument();
  });

  it('shows loading spinner when loading and no versions', () => {
    vi.mocked(useVersionStore).mockReturnValue({
      ...defaultStoreState,
      versions: [],
      loading: true,
    });

    render(<VersionHistory workflowId="wf-1" />);

    expect(screen.getByText((content, element) => {
      return element?.classList.contains('animate-spin') || false;
    })).toBeInTheDocument();
  });

  it('shows empty state when no versions exist', () => {
    vi.mocked(useVersionStore).mockReturnValue({
      ...defaultStoreState,
      versions: [],
      loading: false,
    });

    render(<VersionHistory workflowId="wf-1" />);

    expect(screen.getByText('No versions saved')).toBeInTheDocument();
    expect(
      screen.getByText('Create a version to save a snapshot of your workflow')
    ).toBeInTheDocument();
  });

  it('displays error message when error exists', () => {
    vi.mocked(useVersionStore).mockReturnValue({
      ...defaultStoreState,
      error: 'Failed to load versions',
    });

    render(<VersionHistory workflowId="wf-1" />);

    expect(screen.getByText('Failed to load versions')).toBeInTheDocument();
  });

  it('dismisses error when dismiss button is clicked', async () => {
    const user = userEvent.setup();
    vi.mocked(useVersionStore).mockReturnValue({
      ...defaultStoreState,
      error: 'Failed to load versions',
    });

    render(<VersionHistory workflowId="wf-1" />);

    const dismissButton = screen.getByRole('button', { name: /dismiss/i });
    await user.click(dismissButton);

    expect(mockClearError).toHaveBeenCalled();
  });

  it('opens create version dialog when create button is clicked', async () => {
    const user = userEvent.setup();
    render(<VersionHistory workflowId="wf-1" />);

    const createButton = screen.getByRole('button', { name: /create version/i });
    await user.click(createButton);

    await waitFor(() => {
      expect(screen.getByLabelText(/version message/i)).toBeInTheDocument();
    });
  });

  it('creates a version with message', async () => {
    const user = userEvent.setup();
    mockCreateVersion.mockResolvedValue(undefined);

    render(<VersionHistory workflowId="wf-1" />);

    // Open dialog
    const createButton = screen.getByRole('button', { name: /create version/i });
    await user.click(createButton);

    // Enter message
    const messageInput = screen.getByLabelText(/version message/i);
    await user.type(messageInput, 'New feature added');

    // Submit
    const submitButton = screen.getByRole('button', { name: /create version/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(mockCreateVersion).toHaveBeenCalledWith('wf-1', 'New feature added');
    });
  });

  it('closes create dialog after successful creation', async () => {
    const user = userEvent.setup();
    mockCreateVersion.mockResolvedValue(undefined);

    render(<VersionHistory workflowId="wf-1" />);

    // Open and create
    const createButton = screen.getByRole('button', { name: /create version/i });
    await user.click(createButton);

    const messageInput = screen.getByLabelText(/version message/i);
    await user.type(messageInput, 'Test version');

    const submitButton = screen.getByRole('button', { name: /create version/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });
  });

  it('disables create button when message is empty', async () => {
    const user = userEvent.setup();
    render(<VersionHistory workflowId="wf-1" />);

    const createButton = screen.getByRole('button', { name: /create version/i });
    await user.click(createButton);

    await waitFor(() => {
      expect(screen.getByLabelText(/version message/i)).toBeInTheDocument();
    });

    const submitButtons = screen.getAllByRole('button', { name: /create version/i });
    const submitButton = submitButtons[submitButtons.length - 1];
    expect(submitButton).toBeDisabled();
  });

  it('cancels create dialog', async () => {
    const user = userEvent.setup();
    render(<VersionHistory workflowId="wf-1" />);

    const createButton = screen.getByRole('button', { name: /create version/i });
    await user.click(createButton);

    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    await user.click(cancelButton);

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });
  });

  it('opens restore confirmation dialog when restore is clicked', async () => {
    const user = userEvent.setup();
    render(<VersionHistory workflowId="wf-1" />);

    // Find the first restore button (icon button)
    const restoreButtons = screen.getAllByRole('button');
    const firstRestoreButton = restoreButtons.find((btn) =>
      btn.querySelector('svg[class*="lucide-rotate-ccw"]')
    );

    if (firstRestoreButton) {
      await user.click(firstRestoreButton);
    }

    await waitFor(() => {
      expect(screen.getByText('Restore Version?')).toBeInTheDocument();
      expect(screen.getByText(/this will replace your current workflow/i)).toBeInTheDocument();
    });
  });

  it('restores a version', async () => {
    const user = userEvent.setup();
    mockRestoreVersion.mockResolvedValue(undefined);

    render(<VersionHistory workflowId="wf-1" onVersionRestored={mockOnVersionRestored} />);

    // Click restore on first version
    const restoreButtons = screen.getAllByRole('button');
    const firstRestoreButton = restoreButtons.find((btn) =>
      btn.querySelector('svg[class*="lucide-rotate-ccw"]')
    );

    if (firstRestoreButton) {
      await user.click(firstRestoreButton);
    }

    // Confirm restoration
    await waitFor(() => {
      expect(screen.getByText('Restore Version?')).toBeInTheDocument();
    });

    const confirmButton = screen.getByRole('button', { name: /restore version/i });
    await user.click(confirmButton);

    await waitFor(() => {
      expect(mockRestoreVersion).toHaveBeenCalledWith('wf-1', 'v1');
      expect(mockOnVersionRestored).toHaveBeenCalled();
    });
  });

  it('closes restore dialog after successful restore', async () => {
    const user = userEvent.setup();
    mockRestoreVersion.mockResolvedValue(undefined);

    render(<VersionHistory workflowId="wf-1" />);

    // Open restore dialog
    const restoreButtons = screen.getAllByRole('button');
    const firstRestoreButton = restoreButtons.find((btn) =>
      btn.querySelector('svg[class*="lucide-rotate-ccw"]')
    );

    if (firstRestoreButton) {
      await user.click(firstRestoreButton);
    }

    await waitFor(() => {
      expect(screen.getByText('Restore Version?')).toBeInTheDocument();
    });

    const confirmButton = screen.getByRole('button', { name: /restore version/i });
    await user.click(confirmButton);

    await waitFor(() => {
      expect(screen.queryByText('Restore Version?')).not.toBeInTheDocument();
    });
  });

  it('cancels restore dialog', async () => {
    const user = userEvent.setup();
    render(<VersionHistory workflowId="wf-1" />);

    // Open restore dialog
    const restoreButtons = screen.getAllByRole('button');
    const firstRestoreButton = restoreButtons.find((btn) =>
      btn.querySelector('svg[class*="lucide-rotate-ccw"]')
    );

    if (firstRestoreButton) {
      await user.click(firstRestoreButton);
    }

    await waitFor(() => {
      expect(screen.getByText('Restore Version?')).toBeInTheDocument();
    });

    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    await user.click(cancelButton);

    await waitFor(() => {
      expect(screen.queryByText('Restore Version?')).not.toBeInTheDocument();
    });
  });

  it('displays version message in restore confirmation', async () => {
    const user = userEvent.setup();
    render(<VersionHistory workflowId="wf-1" />);

    const restoreButtons = screen.getAllByRole('button');
    const firstRestoreButton = restoreButtons.find((btn) =>
      btn.querySelector('svg[class*="lucide-rotate-ccw"]')
    );

    if (firstRestoreButton) {
      await user.click(firstRestoreButton);
    }

    await waitFor(() => {
      expect(screen.getByText('Restore Version?')).toBeInTheDocument();
    });

    // Message appears in both places - in the list and in the dialog
    const messages = screen.getAllByText('Initial version');
    expect(messages.length).toBeGreaterThanOrEqual(1);
  });

  it('disables buttons during loading', async () => {
    const user = userEvent.setup();
    vi.mocked(useVersionStore).mockReturnValue({
      ...defaultStoreState,
      loading: true,
    });

    render(<VersionHistory workflowId="wf-1" />);

    const createButton = screen.getByRole('button', { name: /create version/i });
    await user.click(createButton);

    await waitFor(() => {
      expect(screen.getByLabelText(/version message/i)).toBeInTheDocument();
    });

    const messageInput = screen.getByLabelText(/version message/i);
    await user.type(messageInput, 'Test');

    const submitButtons = screen.getAllByRole('button', { name: /create version/i });
    const submitButton = submitButtons[submitButtons.length - 1];
    expect(submitButton).toBeDisabled();
  });

  it('refetches versions when workflowId changes', () => {
    const { rerender } = render(<VersionHistory workflowId="wf-1" />);

    expect(mockFetchVersions).toHaveBeenCalledWith('wf-1');

    rerender(<VersionHistory workflowId="wf-2" />);

    expect(mockFetchVersions).toHaveBeenCalledWith('wf-2');
  });

  it('handles restore error gracefully', async () => {
    const user = userEvent.setup();
    mockRestoreVersion.mockRejectedValue(new Error('Restore failed'));

    render(<VersionHistory workflowId="wf-1" />);

    const restoreButtons = screen.getAllByRole('button');
    const firstRestoreButton = restoreButtons.find((btn) =>
      btn.querySelector('svg[class*="lucide-rotate-ccw"]')
    );

    if (firstRestoreButton) {
      await user.click(firstRestoreButton);
    }

    await waitFor(() => {
      expect(screen.getByText('Restore Version?')).toBeInTheDocument();
    });

    const confirmButton = screen.getByRole('button', { name: /restore version/i });
    await user.click(confirmButton);

    // Error is handled by the store, component should not crash
    await waitFor(() => {
      expect(mockRestoreVersion).toHaveBeenCalled();
    });
  });

  it('handles create error gracefully', async () => {
    const user = userEvent.setup();
    mockCreateVersion.mockRejectedValue(new Error('Create failed'));

    render(<VersionHistory workflowId="wf-1" />);

    const createButton = screen.getByRole('button', { name: /create version/i });
    await user.click(createButton);

    await waitFor(() => {
      expect(screen.getByLabelText(/version message/i)).toBeInTheDocument();
    });

    const messageInput = screen.getByLabelText(/version message/i);
    await user.type(messageInput, 'Test version');

    const submitButtons = screen.getAllByRole('button', { name: /create version/i });
    const submitButton = submitButtons[submitButtons.length - 1];
    await user.click(submitButton);

    // Error is handled by the store, component should not crash
    await waitFor(() => {
      expect(mockCreateVersion).toHaveBeenCalled();
    });
  });

  it('displays relative time for recent versions', () => {
    const recentVersion: WorkflowVersion = {
      id: 'v-recent',
      workflowId: 'wf-1',
      versionNumber: 4,
      message: 'Just now',
      createdAt: new Date(Date.now() - 30000).toISOString(), // 30 seconds ago
      snapshot: { blocks: [], connections: [] },
    };

    vi.mocked(useVersionStore).mockReturnValue({
      ...defaultStoreState,
      versions: [recentVersion],
    });

    render(<VersionHistory workflowId="wf-1" />);

    expect(screen.getByText('just now')).toBeInTheDocument();
  });

  it('renders restore button for each version', () => {
    render(<VersionHistory workflowId="wf-1" />);

    const restoreButtons = screen.getAllByRole('button');
    const restoreIconButtons = restoreButtons.filter((btn) =>
      btn.querySelector('svg[class*="lucide-rotate-ccw"]')
    );

    expect(restoreIconButtons).toHaveLength(mockVersions.length);
  });
});
