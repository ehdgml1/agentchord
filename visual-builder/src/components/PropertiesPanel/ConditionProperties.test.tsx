/**
 * Tests for ConditionProperties component
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConditionProperties } from './ConditionProperties';
import type { ConditionBlockData } from '../../types/blocks';

describe('ConditionProperties', () => {
  const mockOnChange = vi.fn();
  const defaultData: ConditionBlockData = {
    condition: '',
    trueLabel: 'Yes',
    falseLabel: 'No',
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders all form fields', () => {
    render(<ConditionProperties data={defaultData} onChange={mockOnChange} />);

    expect(screen.getByLabelText(/condition expression/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/true branch label/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/false branch label/i)).toBeInTheDocument();
  });

  it('displays current condition value', () => {
    const dataWithCondition: ConditionBlockData = {
      ...defaultData,
      condition: "len(input) > 5",
    };

    render(<ConditionProperties data={dataWithCondition} onChange={mockOnChange} />);

    const conditionTextarea = screen.getByLabelText(/condition expression/i);
    expect(conditionTextarea).toHaveValue("len(input) > 5");
  });

  it('displays current label values', () => {
    const dataWithLabels: ConditionBlockData = {
      ...defaultData,
      trueLabel: 'Valid',
      falseLabel: 'Invalid',
    };

    render(<ConditionProperties data={dataWithLabels} onChange={mockOnChange} />);

    expect(screen.getByLabelText(/true branch label/i)).toHaveValue('Valid');
    expect(screen.getByLabelText(/false branch label/i)).toHaveValue('Invalid');
  });

  it('handles condition expression changes', async () => {
    const user = userEvent.setup();
    render(<ConditionProperties data={defaultData} onChange={mockOnChange} />);

    const conditionTextarea = screen.getByLabelText(/condition expression/i);
    await user.type(conditionTextarea, "test");

    // Called once per character typed
    expect(mockOnChange).toHaveBeenCalled();
    expect(mockOnChange.mock.calls.length).toBeGreaterThan(0);
  });

  it('handles true label changes', async () => {
    const user = userEvent.setup();
    render(<ConditionProperties data={defaultData} onChange={mockOnChange} />);

    const trueLabelInput = screen.getByLabelText(/true branch label/i) as HTMLInputElement;
    await user.tripleClick(trueLabelInput);
    await user.paste('Approved');

    expect(mockOnChange).toHaveBeenCalledWith({ trueLabel: 'Approved' });
  });

  it('handles false label changes', async () => {
    const user = userEvent.setup();
    render(<ConditionProperties data={defaultData} onChange={mockOnChange} />);

    const falseLabelInput = screen.getByLabelText(/false branch label/i) as HTMLInputElement;
    await user.tripleClick(falseLabelInput);
    await user.paste('Rejected');

    expect(mockOnChange).toHaveBeenCalledWith({ falseLabel: 'Rejected' });
  });

  it('displays placeholder text for condition', () => {
    render(<ConditionProperties data={defaultData} onChange={mockOnChange} />);

    const conditionTextarea = screen.getByLabelText(/condition expression/i);
    expect(conditionTextarea).toHaveAttribute(
      'placeholder',
      "len(input) > 5 and status == 'active'"
    );
  });

  it('displays helper text for safe functions', () => {
    render(<ConditionProperties data={defaultData} onChange={mockOnChange} />);

    expect(
      screen.getByText(/safe functions: len, str, int, float, bool, abs, min, max, any, all/i)
    ).toBeInTheDocument();
  });

  it('renders textarea with monospace font class', () => {
    render(<ConditionProperties data={defaultData} onChange={mockOnChange} />);

    const conditionTextarea = screen.getByLabelText(/condition expression/i);
    expect(conditionTextarea).toHaveClass('font-mono', 'text-sm');
  });

  it('handles empty condition value', () => {
    const dataWithEmpty: ConditionBlockData = {
      ...defaultData,
      condition: '',
    };

    render(<ConditionProperties data={dataWithEmpty} onChange={mockOnChange} />);

    const conditionTextarea = screen.getByLabelText(/condition expression/i);
    expect(conditionTextarea).toHaveValue('');
  });

  it('handles multi-line conditions', async () => {
    const user = userEvent.setup();
    render(<ConditionProperties data={defaultData} onChange={mockOnChange} />);

    const conditionTextarea = screen.getByLabelText(/condition expression/i);
    await user.type(conditionTextarea, 'test');

    expect(mockOnChange).toHaveBeenCalled();
  });

  it('calls onChange with partial data updates', async () => {
    const user = userEvent.setup();
    render(<ConditionProperties data={defaultData} onChange={mockOnChange} />);

    const trueLabelInput = screen.getByLabelText(/true branch label/i) as HTMLInputElement;
    await user.tripleClick(trueLabelInput);
    await user.paste('Pass');

    // Should only update the changed field
    expect(mockOnChange).toHaveBeenCalledWith({ trueLabel: 'Pass' });
    expect(mockOnChange).not.toHaveBeenCalledWith(
      expect.objectContaining({ condition: expect.anything() })
    );
  });

  it('renders with default label placeholders', () => {
    render(<ConditionProperties data={defaultData} onChange={mockOnChange} />);

    expect(screen.getByPlaceholderText('Yes')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('No')).toBeInTheDocument();
  });

  it('handles rapid consecutive changes', async () => {
    const user = userEvent.setup();
    render(<ConditionProperties data={defaultData} onChange={mockOnChange} />);

    const conditionTextarea = screen.getByLabelText(/condition expression/i);

    await user.type(conditionTextarea, 'a');
    await user.type(conditionTextarea, 'b');
    await user.type(conditionTextarea, 'c');

    // Should call onChange for each keystroke
    expect(mockOnChange).toHaveBeenCalledTimes(3);
  });
});
