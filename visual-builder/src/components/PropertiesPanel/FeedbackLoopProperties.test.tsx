/**
 * Tests for FeedbackLoopProperties component
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FeedbackLoopProperties } from './FeedbackLoopProperties';
import type { FeedbackLoopBlockData } from '../../types/blocks';

describe('FeedbackLoopProperties', () => {
  const mockOnChange = vi.fn();
  const defaultData: FeedbackLoopBlockData = {
    maxIterations: 10,
    stopCondition: '',
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders all form fields', () => {
    render(<FeedbackLoopProperties data={defaultData} onChange={mockOnChange} />);

    expect(screen.getByLabelText(/max iterations/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/stop condition/i)).toBeInTheDocument();
  });

  it('displays current maxIterations value', () => {
    render(<FeedbackLoopProperties data={defaultData} onChange={mockOnChange} />);

    const maxIterationsInput = screen.getByLabelText(/max iterations/i);
    expect(maxIterationsInput).toHaveValue(10);
  });

  it('displays current stopCondition value', () => {
    const dataWithCondition: FeedbackLoopBlockData = {
      ...defaultData,
      stopCondition: "result == 'done'",
    };

    render(<FeedbackLoopProperties data={dataWithCondition} onChange={mockOnChange} />);

    const stopConditionTextarea = screen.getByLabelText(/stop condition/i);
    expect(stopConditionTextarea).toHaveValue("result == 'done'");
  });

  it('handles maxIterations changes', async () => {
    const user = userEvent.setup();
    render(<FeedbackLoopProperties data={defaultData} onChange={mockOnChange} />);

    const maxIterationsInput = screen.getByLabelText(/max iterations/i) as HTMLInputElement;
    await user.tripleClick(maxIterationsInput);
    await user.paste('25');

    expect(mockOnChange).toHaveBeenCalled();
    expect(mockOnChange).toHaveBeenCalledWith({ maxIterations: 25 });
  });

  it('handles stopCondition changes', async () => {
    const user = userEvent.setup();
    render(<FeedbackLoopProperties data={defaultData} onChange={mockOnChange} />);

    const stopConditionTextarea = screen.getByLabelText(/stop condition/i);
    await user.type(stopConditionTextarea, "test");

    expect(mockOnChange).toHaveBeenCalled();
  });

  it('renders maxIterations input with correct attributes', () => {
    render(<FeedbackLoopProperties data={defaultData} onChange={mockOnChange} />);

    const maxIterationsInput = screen.getByLabelText(/max iterations/i);
    expect(maxIterationsInput).toHaveAttribute('type', 'number');
    expect(maxIterationsInput).toHaveAttribute('min', '1');
    expect(maxIterationsInput).toHaveAttribute('max', '1000');
    expect(maxIterationsInput).toHaveAttribute('placeholder', '10');
  });

  it('displays placeholder for stopCondition', () => {
    render(<FeedbackLoopProperties data={defaultData} onChange={mockOnChange} />);

    const stopConditionTextarea = screen.getByLabelText(/stop condition/i);
    expect(stopConditionTextarea).toHaveAttribute(
      'placeholder',
      "iteration > 5 or result == 'done'"
    );
  });

  it('displays helper text for available variables', () => {
    render(<FeedbackLoopProperties data={defaultData} onChange={mockOnChange} />);

    expect(
      screen.getByText(/available variables: iteration \(current count\), result \(previous output\)/i)
    ).toBeInTheDocument();
  });

  it('renders stopCondition textarea with monospace font', () => {
    render(<FeedbackLoopProperties data={defaultData} onChange={mockOnChange} />);

    const stopConditionTextarea = screen.getByLabelText(/stop condition/i);
    expect(stopConditionTextarea).toHaveClass('font-mono', 'text-sm');
  });

  it('ignores invalid number input for maxIterations', async () => {
    const user = userEvent.setup();
    render(<FeedbackLoopProperties data={defaultData} onChange={mockOnChange} />);

    const maxIterationsInput = screen.getByLabelText(/max iterations/i);
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

    render(<FeedbackLoopProperties data={dataWithEmpty} onChange={mockOnChange} />);

    const stopConditionTextarea = screen.getByLabelText(/stop condition/i);
    expect(stopConditionTextarea).toHaveValue('');
  });

  it('handles large maxIterations values within range', async () => {
    const user = userEvent.setup();
    render(<FeedbackLoopProperties data={defaultData} onChange={mockOnChange} />);

    const maxIterationsInput = screen.getByLabelText(/max iterations/i) as HTMLInputElement;
    await user.tripleClick(maxIterationsInput);
    await user.paste('999');

    expect(mockOnChange).toHaveBeenCalledWith({ maxIterations: 999 });
  });

  it('handles minimum maxIterations value', async () => {
    const user = userEvent.setup();
    render(<FeedbackLoopProperties data={defaultData} onChange={mockOnChange} />);

    const maxIterationsInput = screen.getByLabelText(/max iterations/i) as HTMLInputElement;
    await user.tripleClick(maxIterationsInput);
    await user.paste('1');

    expect(mockOnChange).toHaveBeenCalledWith({ maxIterations: 1 });
  });

  it('handles multi-line stop conditions', async () => {
    const user = userEvent.setup();
    render(<FeedbackLoopProperties data={defaultData} onChange={mockOnChange} />);

    const stopConditionTextarea = screen.getByLabelText(/stop condition/i);
    await user.type(
      stopConditionTextarea,
      'iteration > 5\nor result == "complete"'
    );

    expect(mockOnChange).toHaveBeenCalled();
  });

  it('renders with proper spacing', () => {
    const { container } = render(
      <FeedbackLoopProperties data={defaultData} onChange={mockOnChange} />
    );

    const spacingDiv = container.querySelector('.space-y-4');
    expect(spacingDiv).toBeInTheDocument();
  });

  it('calls onChange with partial data updates', async () => {
    const user = userEvent.setup();
    render(<FeedbackLoopProperties data={defaultData} onChange={mockOnChange} />);

    const maxIterationsInput = screen.getByLabelText(/max iterations/i) as HTMLInputElement;
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
      <FeedbackLoopProperties data={dataWithoutIterations} onChange={mockOnChange} />
    );

    const maxIterationsInput = screen.getByLabelText(/max iterations/i);
    expect(maxIterationsInput).toHaveValue(10);
  });

  it('handles rapid consecutive changes to maxIterations', async () => {
    const user = userEvent.setup();
    render(<FeedbackLoopProperties data={defaultData} onChange={mockOnChange} />);

    const maxIterationsInput = screen.getByLabelText(/max iterations/i) as HTMLInputElement;

    await user.tripleClick(maxIterationsInput);
    await user.paste('5');
    await user.tripleClick(maxIterationsInput);
    await user.paste('15');

    expect(mockOnChange).toHaveBeenCalled();
    expect(mockOnChange).toHaveBeenCalledWith({ maxIterations: 15 });
  });

  it('parses integer values correctly', async () => {
    const user = userEvent.setup();
    render(<FeedbackLoopProperties data={defaultData} onChange={mockOnChange} />);

    const maxIterationsInput = screen.getByLabelText(/max iterations/i) as HTMLInputElement;
    await user.tripleClick(maxIterationsInput);
    await user.paste('42');

    expect(mockOnChange).toHaveBeenCalledWith({ maxIterations: 42 });
  });
});
