/**
 * Tests for FeedbackLoopProperties component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FeedbackLoopProperties } from './FeedbackLoopProperties';
import type { FeedbackLoopBlockData } from '../../types/blocks';
import { useWorkflowStore } from '../../stores/workflowStore';

vi.mock('../../stores/workflowStore', () => ({
  useWorkflowStore: vi.fn(),
}));

describe('FeedbackLoopProperties', () => {
  const mockOnChange = vi.fn();
  const defaultData: FeedbackLoopBlockData = {
    maxIterations: 10,
    stopCondition: '',
  };

  beforeEach(() => {
    vi.clearAllMocks();
    // Mock the workflow store with empty nodes and edges
    vi.mocked(useWorkflowStore).mockReturnValue({
      nodes: [],
      edges: [],
    });
  });

  it('renders all form fields', () => {
    render(<FeedbackLoopProperties nodeId="loop-1" data={defaultData} onChange={mockOnChange} />);

    expect(screen.getByLabelText(/최대 반복 횟수/i)).toBeInTheDocument();
    expect(screen.getByText(/종료 조건/i)).toBeInTheDocument();
  });

  it('displays current maxIterations value', () => {
    render(<FeedbackLoopProperties nodeId="loop-1" data={defaultData} onChange={mockOnChange} />);

    const maxIterationsInput = screen.getByLabelText(/최대 반복 횟수/i);
    expect(maxIterationsInput).toHaveValue(10);
  });

  it('displays current stopCondition value in visual builder', () => {
    const dataWithCondition: FeedbackLoopBlockData = {
      ...defaultData,
      stopCondition: "iteration >= 3",
    };

    render(<FeedbackLoopProperties nodeId="loop-1" data={dataWithCondition} onChange={mockOnChange} />);

    expect(screen.getByText('iteration >= 3')).toBeInTheDocument();
  });

  it('handles maxIterations changes', async () => {
    const user = userEvent.setup();
    render(<FeedbackLoopProperties nodeId="loop-1" data={defaultData} onChange={mockOnChange} />);

    const maxIterationsInput = screen.getByLabelText(/최대 반복 횟수/i) as HTMLInputElement;
    await user.tripleClick(maxIterationsInput);
    await user.paste('25');

    expect(mockOnChange).toHaveBeenCalled();
    expect(mockOnChange).toHaveBeenCalledWith({ maxIterations: 25 });
  });

  it('handles stopCondition changes via apply button', async () => {
    const user = userEvent.setup();
    render(<FeedbackLoopProperties nodeId="loop-1" data={defaultData} onChange={mockOnChange} />);

    const applyButton = screen.getByText(/조건 적용/i);
    await user.click(applyButton);

    expect(mockOnChange).toHaveBeenCalled();
  });

  it('renders maxIterations input with correct attributes', () => {
    render(<FeedbackLoopProperties nodeId="loop-1" data={defaultData} onChange={mockOnChange} />);

    const maxIterationsInput = screen.getByLabelText(/최대 반복 횟수/i);
    expect(maxIterationsInput).toHaveAttribute('type', 'number');
    expect(maxIterationsInput).toHaveAttribute('min', '1');
    expect(maxIterationsInput).toHaveAttribute('max', '1000');
    expect(maxIterationsInput).toHaveAttribute('placeholder', '10');
  });

  it('shows advanced mode toggle button', () => {
    render(<FeedbackLoopProperties nodeId="loop-1" data={defaultData} onChange={mockOnChange} />);

    expect(screen.getByText(/고급 모드/i)).toBeInTheDocument();
  });

  it('switches to advanced mode showing raw textarea', async () => {
    const user = userEvent.setup();
    render(<FeedbackLoopProperties nodeId="loop-1" data={defaultData} onChange={mockOnChange} />);

    const advancedButton = screen.getByText(/고급 모드/i);
    await user.click(advancedButton);

    const textarea = screen.getByPlaceholderText(/iteration >= 3 or input.score >= 80/i);
    expect(textarea).toBeInTheDocument();
    expect(screen.getByText(/간편 모드/i)).toBeInTheDocument();
  });

  it('ignores invalid number input for maxIterations', async () => {
    const user = userEvent.setup();
    render(<FeedbackLoopProperties nodeId="loop-1" data={defaultData} onChange={mockOnChange} />);

    const maxIterationsInput = screen.getByLabelText(/최대 반복 횟수/i);
    await user.clear(maxIterationsInput);
    await user.type(maxIterationsInput, 'abc');

    // Should not call onChange with NaN
    expect(mockOnChange).not.toHaveBeenCalled();
  });

  it('handles empty stopCondition', () => {
    const dataWithEmpty: FeedbackLoopBlockData = {
      ...defaultData,
      stopCondition: '',
    };

    render(<FeedbackLoopProperties nodeId="loop-1" data={dataWithEmpty} onChange={mockOnChange} />);

    // In visual mode, no condition display when empty
    expect(screen.queryByText(/iteration >=/)).not.toBeInTheDocument();
  });

  it('handles large maxIterations values within range', async () => {
    const user = userEvent.setup();
    render(<FeedbackLoopProperties nodeId="loop-1" data={defaultData} onChange={mockOnChange} />);

    const maxIterationsInput = screen.getByLabelText(/최대 반복 횟수/i) as HTMLInputElement;
    await user.tripleClick(maxIterationsInput);
    await user.paste('999');

    expect(mockOnChange).toHaveBeenCalledWith({ maxIterations: 999 });
  });

  it('handles minimum maxIterations value', async () => {
    const user = userEvent.setup();
    render(<FeedbackLoopProperties nodeId="loop-1" data={defaultData} onChange={mockOnChange} />);

    const maxIterationsInput = screen.getByLabelText(/최대 반복 횟수/i) as HTMLInputElement;
    await user.tripleClick(maxIterationsInput);
    await user.paste('1');

    expect(mockOnChange).toHaveBeenCalledWith({ maxIterations: 1 });
  });

  it('shows field dropdown with iteration option', () => {
    render(<FeedbackLoopProperties nodeId="loop-1" data={defaultData} onChange={mockOnChange} />);

    // Check that the dropdown shows the iteration option (appears in multiple places)
    const iterationOptions = screen.getAllByText(/반복 횟수/i);
    expect(iterationOptions.length).toBeGreaterThan(0);
  });

  it('renders with proper spacing', () => {
    const { container } = render(
      <FeedbackLoopProperties nodeId="loop-1" data={defaultData} onChange={mockOnChange} />
    );

    const spacingDiv = container.querySelector('.space-y-4');
    expect(spacingDiv).toBeInTheDocument();
  });

  it('calls onChange with partial data updates', async () => {
    const user = userEvent.setup();
    render(<FeedbackLoopProperties nodeId="loop-1" data={defaultData} onChange={mockOnChange} />);

    const maxIterationsInput = screen.getByLabelText(/최대 반복 횟수/i) as HTMLInputElement;
    await user.tripleClick(maxIterationsInput);
    await user.paste('50');

    // Should only update maxIterations
    expect(mockOnChange).toHaveBeenCalledWith({ maxIterations: 50 });
    expect(mockOnChange).not.toHaveBeenCalledWith(
      expect.objectContaining({ stopCondition: expect.anything() })
    );
  });

  it('defaults to 10 iterations when no value provided', () => {
    const dataWithoutIterations: FeedbackLoopBlockData = {
      maxIterations: undefined as any,
      stopCondition: '',
    };

    render(
      <FeedbackLoopProperties nodeId="loop-1" data={dataWithoutIterations} onChange={mockOnChange} />
    );

    const maxIterationsInput = screen.getByLabelText(/최대 반복 횟수/i);
    expect(maxIterationsInput).toHaveValue(10);
  });

  it('handles rapid consecutive changes to maxIterations', async () => {
    const user = userEvent.setup();
    render(<FeedbackLoopProperties nodeId="loop-1" data={defaultData} onChange={mockOnChange} />);

    const maxIterationsInput = screen.getByLabelText(/최대 반복 횟수/i) as HTMLInputElement;

    await user.tripleClick(maxIterationsInput);
    await user.paste('5');
    await user.tripleClick(maxIterationsInput);
    await user.paste('15');

    expect(mockOnChange).toHaveBeenCalled();
    expect(mockOnChange).toHaveBeenCalledWith({ maxIterations: 15 });
  });

  it('parses integer values correctly', async () => {
    const user = userEvent.setup();
    render(<FeedbackLoopProperties nodeId="loop-1" data={defaultData} onChange={mockOnChange} />);

    const maxIterationsInput = screen.getByLabelText(/최대 반복 횟수/i) as HTMLInputElement;
    await user.tripleClick(maxIterationsInput);
    await user.paste('42');

    expect(mockOnChange).toHaveBeenCalledWith({ maxIterations: 42 });
  });
});
