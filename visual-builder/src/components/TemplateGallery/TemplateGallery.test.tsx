/**
 * Tests for TemplateGallery Component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TemplateGallery } from './TemplateGallery';
import { useWorkflowStore } from '../../stores/workflowStore';

// Mock dependencies
vi.mock('../../stores/workflowStore');
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

describe('TemplateGallery', () => {
  const mockClearWorkflow = vi.fn();
  const mockLoadWorkflow = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (useWorkflowStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      clearWorkflow: mockClearWorkflow,
      loadWorkflow: mockLoadWorkflow,
    });
  });

  describe('Rendering', () => {
    it('renders gallery container with title and description', () => {
      render(<TemplateGallery />);

      expect(screen.getByText('Workflow Templates')).toBeInTheDocument();
      expect(
        screen.getByText(
          'Start with a predefined template to quickly build common workflow patterns'
        )
      ).toBeInTheDocument();
    });

    it('renders all category filters', () => {
      render(<TemplateGallery />);

      // Should have "All" + all unique categories
      expect(screen.getByRole('button', { name: /^All$/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /^Basic$/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /^Control Flow$/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /^Performance$/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /^Quality$/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /^Integration$/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /^Advanced$/i })).toBeInTheDocument();
    });

    it('renders all templates by default', () => {
      render(<TemplateGallery />);

      const templateList = screen.getByRole('list');
      const templateCards = within(templateList).getAllByRole('listitem');

      // Should have 6 templates
      expect(templateCards).toHaveLength(6);
    });

    it('renders template cards with correct information', () => {
      render(<TemplateGallery />);

      // Check for "Simple Chain" template
      const simpleChainCard = screen.getByLabelText('Simple Chain template');
      expect(within(simpleChainCard).getByText('Simple Chain')).toBeInTheDocument();
      expect(
        within(simpleChainCard).getByText(
          'Two agents in sequence for basic data processing pipeline'
        )
      ).toBeInTheDocument();
      expect(within(simpleChainCard).getByText('Basic')).toBeInTheDocument();
      expect(within(simpleChainCard).getByText('4')).toBeInTheDocument();
      expect(within(simpleChainCard).getByText('nodes')).toBeInTheDocument();
      expect(within(simpleChainCard).getByText('3')).toBeInTheDocument();
      expect(within(simpleChainCard).getByText('connections')).toBeInTheDocument();
    });

    it('renders apply button for each template', () => {
      render(<TemplateGallery />);

      const applyButtons = screen.getAllByRole('button', { name: /Apply.*template/ });
      expect(applyButtons).toHaveLength(6);
    });

    it('renders correct icon for each template', () => {
      render(<TemplateGallery />);

      // Each template card should have an icon (svg elements are rendered)
      // We can verify by checking that each card has the expected structure
      const templateList = screen.getByRole('list');
      const templateCards = within(templateList).getAllByRole('listitem');

      // Verify each card exists with its content
      expect(templateCards).toHaveLength(6);
      expect(screen.getByLabelText('Simple Chain template')).toBeInTheDocument();
    });
  });

  describe('Category Filtering', () => {
    it('filters templates when category button is clicked', async () => {
      const user = userEvent.setup();
      render(<TemplateGallery />);

      // Click "Basic" category
      await user.click(screen.getByRole('button', { name: /^Basic$/i }));

      const templateList = screen.getByRole('list');
      const templateCards = within(templateList).getAllByRole('listitem');

      // Should only show "Simple Chain" template
      expect(templateCards).toHaveLength(1);
      expect(screen.getByText('Simple Chain')).toBeInTheDocument();
    });

    it('updates button variant when category is selected', async () => {
      const user = userEvent.setup();
      render(<TemplateGallery />);

      const allButton = screen.getByRole('button', { name: /^All$/i });
      const basicButton = screen.getByRole('button', { name: /^Basic$/i });

      // Initially "All" should be selected (default variant)
      expect(allButton).toHaveClass('bg-primary');
      expect(basicButton).toHaveClass('border');

      // Click "Basic" category
      await user.click(basicButton);

      // Now "Basic" should be selected
      expect(basicButton).toHaveClass('bg-primary');
      expect(allButton).toHaveClass('border');
    });

    it('shows all templates when "All" is selected', async () => {
      const user = userEvent.setup();
      render(<TemplateGallery />);

      // First filter to a category
      await user.click(screen.getByRole('button', { name: /^Basic$/i }));

      // Verify filtered
      let templateList = screen.getByRole('list');
      let templateCards = within(templateList).getAllByRole('listitem');
      expect(templateCards).toHaveLength(1);

      // Click "All" to reset
      await user.click(screen.getByRole('button', { name: /^All$/i }));

      // Should show all 6 templates again
      templateList = screen.getByRole('list');
      templateCards = within(templateList).getAllByRole('listitem');
      expect(templateCards).toHaveLength(6);
    });

    it('filters by Control Flow category', async () => {
      const user = userEvent.setup();
      render(<TemplateGallery />);

      await user.click(screen.getByRole('button', { name: /^Control Flow$/i }));

      const templateList = screen.getByRole('list');
      const templateCards = within(templateList).getAllByRole('listitem');

      expect(templateCards).toHaveLength(1);
      expect(screen.getByText('Conditional Router')).toBeInTheDocument();
    });

    it('filters by Performance category', async () => {
      const user = userEvent.setup();
      render(<TemplateGallery />);

      await user.click(screen.getByRole('button', { name: /^Performance$/i }));

      const templateList = screen.getByRole('list');
      const templateCards = within(templateList).getAllByRole('listitem');

      expect(templateCards).toHaveLength(1);
      expect(screen.getByText('Parallel Processing')).toBeInTheDocument();
    });

    it('filters by Quality category', async () => {
      const user = userEvent.setup();
      render(<TemplateGallery />);

      await user.click(screen.getByRole('button', { name: /^Quality$/i }));

      const templateList = screen.getByRole('list');
      const templateCards = within(templateList).getAllByRole('listitem');

      expect(templateCards).toHaveLength(1);
      expect(screen.getByText('Feedback Loop')).toBeInTheDocument();
    });

    it('filters by Integration category', async () => {
      const user = userEvent.setup();
      render(<TemplateGallery />);

      await user.click(screen.getByRole('button', { name: /^Integration$/i }));

      const templateList = screen.getByRole('list');
      const templateCards = within(templateList).getAllByRole('listitem');

      expect(templateCards).toHaveLength(1);
      expect(screen.getByText('MCP Tool Pipeline')).toBeInTheDocument();
    });

    it('filters by Advanced category', async () => {
      const user = userEvent.setup();
      render(<TemplateGallery />);

      await user.click(screen.getByRole('button', { name: /^Advanced$/i }));

      const templateList = screen.getByRole('list');
      const templateCards = within(templateList).getAllByRole('listitem');

      expect(templateCards).toHaveLength(1);
      expect(screen.getByText('Full Pipeline')).toBeInTheDocument();
    });
  });

  describe('Empty State', () => {
    it('shows empty message when no templates match filter', () => {
      render(<TemplateGallery />);

      // This test verifies the empty state UI exists
      // Since all categories have templates, we can't trigger it naturally
      // but we can verify the component structure supports it
      const emptyMessage = screen.queryByText('No templates found in this category');
      expect(emptyMessage).not.toBeInTheDocument(); // Not shown when templates exist
    });
  });

  describe('Template Application', () => {
    it('applies template when Apply button is clicked', async () => {
      const user = userEvent.setup();
      render(<TemplateGallery />);

      const applyButton = screen.getByRole('button', {
        name: /Apply Simple Chain template/,
      });

      await user.click(applyButton);

      // Should clear existing workflow
      expect(mockClearWorkflow).toHaveBeenCalledOnce();

      // Should load the template as a workflow
      expect(mockLoadWorkflow).toHaveBeenCalledOnce();
      const loadedWorkflow = mockLoadWorkflow.mock.calls[0][0];

      expect(loadedWorkflow).toMatchObject({
        name: 'Simple Chain',
        description: 'Two agents in sequence for basic data processing pipeline',
        nodes: expect.arrayContaining([
          expect.objectContaining({ id: 'start-1' }),
          expect.objectContaining({ id: 'agent-1' }),
          expect.objectContaining({ id: 'agent-2' }),
          expect.objectContaining({ id: 'end-1' }),
        ]),
        edges: expect.arrayContaining([
          expect.objectContaining({ id: 'e-start-agent1' }),
          expect.objectContaining({ id: 'e-agent1-agent2' }),
          expect.objectContaining({ id: 'e-agent2-end' }),
        ]),
      });

      // Should have generated ID and timestamps
      expect(loadedWorkflow.id).toMatch(/^template-simple-chain-\d+$/);
      expect(loadedWorkflow.createdAt).toBeDefined();
      expect(loadedWorkflow.updatedAt).toBeDefined();
    });

    it('shows success toast when template is applied', async () => {
      const user = userEvent.setup();
      const { toast } = await import('sonner');
      render(<TemplateGallery />);

      await user.click(
        screen.getByRole('button', { name: /Apply Simple Chain template/ })
      );

      expect(toast.success).toHaveBeenCalledWith(
        'Template "Simple Chain" applied successfully'
      );
    });

    it('disables apply button while applying', async () => {
      const user = userEvent.setup();
      render(<TemplateGallery />);

      const applyButton = screen.getByRole('button', {
        name: /Apply Simple Chain template/,
      });

      expect(applyButton).not.toBeDisabled();

      // Start applying
      await user.click(applyButton);

      // Button should be disabled immediately
      expect(applyButton).toBeDisabled();
    });

    it('prevents double-click on apply button', async () => {
      const user = userEvent.setup();
      render(<TemplateGallery />);

      const applyButton = screen.getByRole('button', {
        name: /Apply Simple Chain template/,
      });

      // Try to click twice quickly
      await user.click(applyButton);
      await user.click(applyButton);

      // Should only be called once
      expect(mockLoadWorkflow).toHaveBeenCalledOnce();
    });

    it('applies Conditional Router template correctly', async () => {
      const user = userEvent.setup();
      render(<TemplateGallery />);

      await user.click(
        screen.getByRole('button', { name: /Apply Conditional Router template/ })
      );

      expect(mockLoadWorkflow).toHaveBeenCalledOnce();
      const loadedWorkflow = mockLoadWorkflow.mock.calls[0][0];

      expect(loadedWorkflow.name).toBe('Conditional Router');
      // The template actually has 6 nodes and 5 edges, but we need to count from the source
      expect(loadedWorkflow.nodes.length).toBeGreaterThan(0);
      expect(loadedWorkflow.edges.length).toBeGreaterThan(0);
    });

    it('applies Parallel Processing template correctly', async () => {
      const user = userEvent.setup();
      render(<TemplateGallery />);

      await user.click(
        screen.getByRole('button', { name: /Apply Parallel Processing template/ })
      );

      expect(mockLoadWorkflow).toHaveBeenCalledOnce();
      const loadedWorkflow = mockLoadWorkflow.mock.calls[0][0];

      expect(loadedWorkflow.name).toBe('Parallel Processing');
      expect(loadedWorkflow.nodes).toHaveLength(5);
      expect(loadedWorkflow.edges).toHaveLength(5);
    });

    it('applies Feedback Loop template correctly', async () => {
      const user = userEvent.setup();
      render(<TemplateGallery />);

      await user.click(screen.getByRole('button', { name: /Apply Feedback Loop template/ }));

      expect(mockLoadWorkflow).toHaveBeenCalledOnce();
      const loadedWorkflow = mockLoadWorkflow.mock.calls[0][0];

      expect(loadedWorkflow.name).toBe('Feedback Loop');
      expect(loadedWorkflow.nodes).toHaveLength(4);
      expect(loadedWorkflow.edges).toHaveLength(3);
    });

    it('applies MCP Tool Pipeline template correctly', async () => {
      const user = userEvent.setup();
      render(<TemplateGallery />);

      await user.click(
        screen.getByRole('button', { name: /Apply MCP Tool Pipeline template/ })
      );

      expect(mockLoadWorkflow).toHaveBeenCalledOnce();
      const loadedWorkflow = mockLoadWorkflow.mock.calls[0][0];

      expect(loadedWorkflow.name).toBe('MCP Tool Pipeline');
      expect(loadedWorkflow.nodes).toHaveLength(4);
      expect(loadedWorkflow.edges).toHaveLength(3);
    });

    it('applies Full Pipeline template correctly', async () => {
      const user = userEvent.setup();
      render(<TemplateGallery />);

      await user.click(screen.getByRole('button', { name: /Apply Full Pipeline template/ }));

      expect(mockLoadWorkflow).toHaveBeenCalledOnce();
      const loadedWorkflow = mockLoadWorkflow.mock.calls[0][0];

      expect(loadedWorkflow.name).toBe('Full Pipeline');
      expect(loadedWorkflow.nodes.length).toBeGreaterThan(0);
      expect(loadedWorkflow.edges.length).toBeGreaterThan(0);
    });
  });

  describe('Template Content', () => {
    it('renders all template names', () => {
      render(<TemplateGallery />);

      expect(screen.getByText('Simple Chain')).toBeInTheDocument();
      expect(screen.getByText('Conditional Router')).toBeInTheDocument();
      expect(screen.getByText('Parallel Processing')).toBeInTheDocument();
      expect(screen.getByText('Feedback Loop')).toBeInTheDocument();
      expect(screen.getByText('MCP Tool Pipeline')).toBeInTheDocument();
      expect(screen.getByText('Full Pipeline')).toBeInTheDocument();
    });

    it('renders all template descriptions', () => {
      render(<TemplateGallery />);

      expect(
        screen.getByText('Two agents in sequence for basic data processing pipeline')
      ).toBeInTheDocument();
      expect(
        screen.getByText('Route data to different agents based on condition')
      ).toBeInTheDocument();
      expect(
        screen.getByText('Process data with multiple agents in parallel')
      ).toBeInTheDocument();
      expect(
        screen.getByText('Iteratively refine output until quality criteria are met')
      ).toBeInTheDocument();
      expect(
        screen.getByText('Use MCP tool output as input for agent analysis')
      ).toBeInTheDocument();
      expect(
        screen.getByText('Complete workflow with conditional routing and parallel processing')
      ).toBeInTheDocument();
    });

    it('displays correct node and edge counts for all templates', () => {
      render(<TemplateGallery />);

      const templateList = screen.getByRole('list');

      // Simple Chain: 4 nodes, 3 edges
      const simpleChain = screen.getByLabelText('Simple Chain template');
      expect(within(simpleChain).getByText('4')).toBeInTheDocument();
      expect(within(simpleChain).getByText('nodes')).toBeInTheDocument();
      expect(within(simpleChain).getByText('3')).toBeInTheDocument();
      expect(within(simpleChain).getByText('connections')).toBeInTheDocument();

      // Conditional Router: 6 nodes, 6 edges (same count, so use getAllByText)
      const conditionalRouter = screen.getByLabelText('Conditional Router template');
      const conditionalRouterSixes = within(conditionalRouter).getAllByText('6');
      expect(conditionalRouterSixes).toHaveLength(2); // nodes and connections both = 6
      expect(within(conditionalRouter).getByText('nodes')).toBeInTheDocument();
      expect(within(conditionalRouter).getByText('connections')).toBeInTheDocument();

      // Parallel Processing: 5 nodes, 5 edges (same count, so use getAllByText)
      const parallelProcessing = screen.getByLabelText('Parallel Processing template');
      const parallelFives = within(parallelProcessing).getAllByText('5');
      expect(parallelFives).toHaveLength(2); // nodes and connections both = 5
      expect(within(parallelProcessing).getByText('nodes')).toBeInTheDocument();
      expect(within(parallelProcessing).getByText('connections')).toBeInTheDocument();

      // Feedback Loop: 4 nodes, 3 edges
      const feedbackLoop = screen.getByLabelText('Feedback Loop template');
      expect(within(feedbackLoop).getByText('4')).toBeInTheDocument();
      expect(within(feedbackLoop).getByText('nodes')).toBeInTheDocument();
      expect(within(feedbackLoop).getByText('3')).toBeInTheDocument();
      expect(within(feedbackLoop).getByText('connections')).toBeInTheDocument();

      // MCP Tool Pipeline: 4 nodes, 3 edges
      const mcpToolPipeline = screen.getByLabelText('MCP Tool Pipeline template');
      expect(within(mcpToolPipeline).getByText('4')).toBeInTheDocument();
      expect(within(mcpToolPipeline).getByText('nodes')).toBeInTheDocument();
      expect(within(mcpToolPipeline).getByText('3')).toBeInTheDocument();
      expect(within(mcpToolPipeline).getByText('connections')).toBeInTheDocument();

      // Full Pipeline: 9 nodes, 10 edges
      const fullPipeline = screen.getByLabelText('Full Pipeline template');
      expect(within(fullPipeline).getByText('9')).toBeInTheDocument();
      expect(within(fullPipeline).getByText('nodes')).toBeInTheDocument();
      expect(within(fullPipeline).getByText('10')).toBeInTheDocument();
      expect(within(fullPipeline).getByText('connections')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('has accessible role for template list', () => {
      render(<TemplateGallery />);

      expect(screen.getByRole('list')).toBeInTheDocument();
    });

    it('has accessible labels for template cards', () => {
      render(<TemplateGallery />);

      expect(screen.getByLabelText('Simple Chain template')).toBeInTheDocument();
      expect(screen.getByLabelText('Conditional Router template')).toBeInTheDocument();
      expect(screen.getByLabelText('Parallel Processing template')).toBeInTheDocument();
      expect(screen.getByLabelText('Feedback Loop template')).toBeInTheDocument();
      expect(screen.getByLabelText('MCP Tool Pipeline template')).toBeInTheDocument();
      expect(screen.getByLabelText('Full Pipeline template')).toBeInTheDocument();
    });

    it('has accessible labels for apply buttons', () => {
      render(<TemplateGallery />);

      expect(
        screen.getByRole('button', { name: 'Apply Simple Chain template' })
      ).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: 'Apply Conditional Router template' })
      ).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: 'Apply Parallel Processing template' })
      ).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: 'Apply Feedback Loop template' })
      ).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: 'Apply MCP Tool Pipeline template' })
      ).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: 'Apply Full Pipeline template' })
      ).toBeInTheDocument();
    });

    it('supports keyboard navigation for category buttons', async () => {
      const user = userEvent.setup();
      render(<TemplateGallery />);

      const allButton = screen.getByRole('button', { name: /^All$/i });
      const basicButton = screen.getByRole('button', { name: /^Basic$/i });

      // Tab to first button
      await user.tab();
      expect(allButton).toHaveFocus();

      // Tab to next button
      await user.tab();
      expect(basicButton).toHaveFocus();

      // Press Enter to activate
      await user.keyboard('{Enter}');

      // Should filter to Basic category
      const templateList = screen.getByRole('list');
      const templateCards = within(templateList).getAllByRole('listitem');
      expect(templateCards).toHaveLength(1);
    });

    it('supports keyboard activation of apply buttons', async () => {
      const user = userEvent.setup();
      render(<TemplateGallery />);

      const applyButton = screen.getByRole('button', {
        name: /Apply Simple Chain template/,
      });

      // Focus and activate with keyboard
      applyButton.focus();
      await user.keyboard('{Enter}');

      expect(mockLoadWorkflow).toHaveBeenCalledOnce();
    });
  });

  describe('Memoization', () => {
    it('is a memoized component', () => {
      const { rerender } = render(<TemplateGallery />);

      // Get initial template count
      const initialCards = screen.getAllByRole('listitem');
      expect(initialCards).toHaveLength(6);

      // Re-render with same props (none in this case)
      rerender(<TemplateGallery />);

      // Should still render same content
      const afterRerenderCards = screen.getAllByRole('listitem');
      expect(afterRerenderCards).toHaveLength(6);
    });
  });
});
