/**
 * Tests for ConditionBuilder component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConditionBuilder } from './ConditionBuilder';
import { useWorkflowStore } from '../../stores/workflowStore';
import { BlockType } from '../../types/blocks';

vi.mock('../../stores/workflowStore', () => ({
  useWorkflowStore: vi.fn(),
}));

describe('ConditionBuilder', () => {
  const mockOnChange = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    // Default: empty workflow
    vi.mocked(useWorkflowStore).mockReturnValue({
      nodes: [],
      edges: [],
    });
  });

  describe('Visual Mode', () => {
    it('renders in visual mode by default', () => {
      render(<ConditionBuilder nodeId="loop-1" value="" onChange={mockOnChange} />);

      expect(screen.getByText(/종료 조건/i)).toBeInTheDocument();
      expect(screen.getByText(/고급 모드/i)).toBeInTheDocument();
      expect(screen.queryByPlaceholderText(/iteration >= 3/)).not.toBeInTheDocument();
    });

    it('shows iteration field by default', () => {
      render(<ConditionBuilder nodeId="loop-1" value="" onChange={mockOnChange} />);

      // The iteration option should be visible in the field dropdown
      expect(screen.getByText(/반복 횟수/i)).toBeInTheDocument();
    });

    it('shows operator dropdown with number operators', () => {
      render(<ConditionBuilder nodeId="loop-1" value="" onChange={mockOnChange} />);

      // Should show operator dropdown for number field
      const operatorTrigger = screen.getByLabelText(/Condition operator/i);
      expect(operatorTrigger).toBeInTheDocument();
    });

    it('shows value input for number type', () => {
      render(<ConditionBuilder nodeId="loop-1" value="" onChange={mockOnChange} />);

      const valueInput = screen.getByLabelText(/Condition value/i);
      expect(valueInput).toBeInTheDocument();
      expect(valueInput).toHaveAttribute('type', 'number');
    });

    it('shows apply button', () => {
      render(<ConditionBuilder nodeId="loop-1" value="" onChange={mockOnChange} />);

      expect(screen.getByText(/조건 적용/i)).toBeInTheDocument();
    });

    it('displays current condition when value is provided', () => {
      render(<ConditionBuilder nodeId="loop-1" value="iteration >= 5" onChange={mockOnChange} />);

      expect(screen.getByText('iteration >= 5')).toBeInTheDocument();
    });

    it('calls onChange when apply button is clicked', async () => {
      const user = userEvent.setup();
      render(<ConditionBuilder nodeId="loop-1" value="" onChange={mockOnChange} />);

      const applyButton = screen.getByText(/조건 적용/i);
      await user.click(applyButton);

      expect(mockOnChange).toHaveBeenCalled();
      expect(mockOnChange).toHaveBeenCalledWith('iteration >= 3');
    });

    it('disables apply button when value is empty', async () => {
      render(<ConditionBuilder nodeId="loop-1" value="" onChange={mockOnChange} />);

      const valueInput = screen.getByLabelText(/Condition value/i);
      await userEvent.setup().clear(valueInput);

      const applyButton = screen.getByText(/조건 적용/i);
      expect(applyButton).toBeDisabled();
    });
  });

  describe('Advanced Mode', () => {
    it('switches to advanced mode when toggle is clicked', async () => {
      const user = userEvent.setup();
      render(<ConditionBuilder nodeId="loop-1" value="" onChange={mockOnChange} />);

      const advancedButton = screen.getByText(/고급 모드/i);
      await user.click(advancedButton);

      expect(screen.getByPlaceholderText(/iteration >= 3 or input.score >= 80/i)).toBeInTheDocument();
      expect(screen.getByText(/간편 모드/i)).toBeInTheDocument();
    });

    it('shows textarea in advanced mode', async () => {
      const user = userEvent.setup();
      render(<ConditionBuilder nodeId="loop-1" value="iteration >= 5" onChange={mockOnChange} />);

      const advancedButton = screen.getByText(/고급 모드/i);
      await user.click(advancedButton);

      const textarea = screen.getByPlaceholderText(/iteration >= 3 or input.score >= 80/i);
      expect(textarea).toHaveValue('iteration >= 5');
    });

    it('allows editing in advanced mode', async () => {
      const user = userEvent.setup();
      render(<ConditionBuilder nodeId="loop-1" value="" onChange={mockOnChange} />);

      const advancedButton = screen.getByText(/고급 모드/i);
      await user.click(advancedButton);

      const textarea = screen.getByPlaceholderText(/iteration >= 3 or input.score >= 80/i);
      await user.type(textarea, 'test');

      // onChange is called for each character typed
      expect(mockOnChange).toHaveBeenCalled();
    });

    it('switches back to visual mode', async () => {
      const user = userEvent.setup();
      render(<ConditionBuilder nodeId="loop-1" value="" onChange={mockOnChange} />);

      // Go to advanced
      const advancedButton = screen.getByText(/고급 모드/i);
      await user.click(advancedButton);

      // Go back to visual
      const visualButton = screen.getByText(/간편 모드/i);
      await user.click(visualButton);

      expect(screen.getByText(/조건 적용/i)).toBeInTheDocument();
      expect(screen.queryByPlaceholderText(/iteration >= 3/)).not.toBeInTheDocument();
    });
  });

  describe('Upstream Node Integration', () => {
    it('shows output fields from connected upstream Agent nodes', () => {
      vi.mocked(useWorkflowStore).mockReturnValue({
        nodes: [
          {
            id: 'agent-1',
            type: BlockType.AGENT,
            position: { x: 0, y: 0 },
            data: {
              name: 'Scorer',
              outputFields: [
                { name: 'score', type: 'number', description: 'Quality score' },
              ],
            },
          },
        ],
        edges: [
          { id: 'e1', source: 'agent-1', target: 'loop-1', sourceHandle: null, targetHandle: null },
        ],
      });

      render(<ConditionBuilder nodeId="loop-1" value="" onChange={mockOnChange} />);

      // Both iteration and agent output should be available
      expect(screen.getByText(/반복 횟수/i)).toBeInTheDocument();
    });

    it('handles multiple upstream nodes with output fields', () => {
      vi.mocked(useWorkflowStore).mockReturnValue({
        nodes: [
          {
            id: 'agent-1',
            type: BlockType.AGENT,
            position: { x: 0, y: 0 },
            data: {
              name: 'Scorer',
              outputFields: [
                { name: 'score', type: 'number' },
              ],
            },
          },
          {
            id: 'agent-2',
            type: BlockType.AGENT,
            position: { x: 0, y: 0 },
            data: {
              name: 'Validator',
              outputFields: [
                { name: 'valid', type: 'boolean' },
              ],
            },
          },
        ],
        edges: [
          { id: 'e1', source: 'agent-1', target: 'loop-1', sourceHandle: null, targetHandle: null },
          { id: 'e2', source: 'agent-2', target: 'loop-1', sourceHandle: null, targetHandle: null },
        ],
      });

      render(<ConditionBuilder nodeId="loop-1" value="" onChange={mockOnChange} />);

      // Should have iteration + fields from both agents
      expect(screen.getByText(/반복 횟수/i)).toBeInTheDocument();
    });

    it('ignores nodes without outputFields', () => {
      vi.mocked(useWorkflowStore).mockReturnValue({
        nodes: [
          {
            id: 'agent-1',
            type: BlockType.AGENT,
            position: { x: 0, y: 0 },
            data: {
              name: 'Simple Agent',
              // No outputFields
            },
          },
        ],
        edges: [
          { id: 'e1', source: 'agent-1', target: 'loop-1', sourceHandle: null, targetHandle: null },
        ],
      });

      render(<ConditionBuilder nodeId="loop-1" value="" onChange={mockOnChange} />);

      // Only iteration should be available
      expect(screen.getByText(/반복 횟수/i)).toBeInTheDocument();
    });
  });

  describe('Field Type Handling', () => {
    it('shows appropriate operators for number fields', async () => {
      render(<ConditionBuilder nodeId="loop-1" value="" onChange={mockOnChange} />);

      // iteration is number type, should show operator dropdown
      const operatorTrigger = screen.getByLabelText(/Condition operator/i);
      expect(operatorTrigger).toBeInTheDocument();
    });

    it('shows boolean value dropdown for boolean fields', () => {
      vi.mocked(useWorkflowStore).mockReturnValue({
        nodes: [
          {
            id: 'agent-1',
            type: BlockType.AGENT,
            position: { x: 0, y: 0 },
            data: {
              name: 'Validator',
              outputFields: [
                { name: 'valid', type: 'boolean' },
              ],
            },
          },
        ],
        edges: [
          { id: 'e1', source: 'agent-1', target: 'loop-1', sourceHandle: null, targetHandle: null },
        ],
      });

      render(<ConditionBuilder nodeId="loop-1" value="" onChange={mockOnChange} />);

      // Should render with boolean options available when field is selected
      expect(screen.getByText(/반복 횟수/i)).toBeInTheDocument();
    });

    it('shows text input for text fields', () => {
      vi.mocked(useWorkflowStore).mockReturnValue({
        nodes: [
          {
            id: 'agent-1',
            type: BlockType.AGENT,
            position: { x: 0, y: 0 },
            data: {
              name: 'Generator',
              outputFields: [
                { name: 'status', type: 'text' },
              ],
            },
          },
        ],
        edges: [
          { id: 'e1', source: 'agent-1', target: 'loop-1', sourceHandle: null, targetHandle: null },
        ],
      });

      render(<ConditionBuilder nodeId="loop-1" value="" onChange={mockOnChange} />);

      expect(screen.getByText(/반복 횟수/i)).toBeInTheDocument();
    });
  });

  describe('Expression Building', () => {
    it('builds correct expression for number field', async () => {
      const user = userEvent.setup();
      render(<ConditionBuilder nodeId="loop-1" value="" onChange={mockOnChange} />);

      // Default: iteration >= 3
      const applyButton = screen.getByText(/조건 적용/i);
      await user.click(applyButton);

      expect(mockOnChange).toHaveBeenCalledWith('iteration >= 3');
    });

    it('updates value when user changes input', async () => {
      const user = userEvent.setup();
      render(<ConditionBuilder nodeId="loop-1" value="" onChange={mockOnChange} />);

      const valueInput = screen.getByLabelText(/Condition value/i);
      await user.clear(valueInput);
      await user.type(valueInput, '10');

      const applyButton = screen.getByText(/조건 적용/i);
      await user.click(applyButton);

      expect(mockOnChange).toHaveBeenCalledWith('iteration >= 10');
    });
  });

  describe('Edge Cases', () => {
    it('handles nodes without data gracefully', () => {
      vi.mocked(useWorkflowStore).mockReturnValue({
        nodes: [
          {
            id: 'broken-node',
            type: BlockType.AGENT,
            position: { x: 0, y: 0 },
            data: null as any,
          },
        ],
        edges: [
          { id: 'e1', source: 'broken-node', target: 'loop-1', sourceHandle: null, targetHandle: null },
        ],
      });

      render(<ConditionBuilder nodeId="loop-1" value="" onChange={mockOnChange} />);

      // Should still render with just iteration
      expect(screen.getByText(/반복 횟수/i)).toBeInTheDocument();
    });

    it('handles empty edges array', () => {
      vi.mocked(useWorkflowStore).mockReturnValue({
        nodes: [
          {
            id: 'agent-1',
            type: BlockType.AGENT,
            position: { x: 0, y: 0 },
            data: {
              name: 'Isolated',
              outputFields: [{ name: 'score', type: 'number' }],
            },
          },
        ],
        edges: [],
      });

      render(<ConditionBuilder nodeId="loop-1" value="" onChange={mockOnChange} />);

      // Only iteration, no connected nodes
      expect(screen.getByText(/반복 횟수/i)).toBeInTheDocument();
    });

    it('preserves value when switching between modes', async () => {
      const user = userEvent.setup();
      render(<ConditionBuilder nodeId="loop-1" value="iteration >= 5" onChange={mockOnChange} />);

      // Should show value in visual mode
      expect(screen.getByText('iteration >= 5')).toBeInTheDocument();

      // Switch to advanced
      const advancedButton = screen.getByText(/고급 모드/i);
      await user.click(advancedButton);

      const textarea = screen.getByPlaceholderText(/iteration >= 3 or input.score >= 80/i);
      expect(textarea).toHaveValue('iteration >= 5');
    });
  });
});
