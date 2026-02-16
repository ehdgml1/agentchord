/**
 * Tests for ParallelProperties component
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ParallelProperties } from './ParallelProperties';
import type { ParallelBlockData } from '../../types/blocks';

describe('ParallelProperties', () => {
  const mockOnChange = vi.fn();
  const defaultData: ParallelBlockData = {
    mergeStrategy: 'concat',
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders merge strategy select', () => {
    render(<ParallelProperties data={defaultData} onChange={mockOnChange} />);

    expect(screen.getByText(/merge strategy/i)).toBeInTheDocument();
    expect(screen.getByRole('combobox')).toBeInTheDocument();
  });

  it('displays current merge strategy value', () => {
    render(<ParallelProperties data={defaultData} onChange={mockOnChange} />);

    const selectTrigger = screen.getByRole('combobox');
    expect(selectTrigger).toHaveTextContent('Collect all');
  });

  it('displays description for current strategy', () => {
    render(<ParallelProperties data={defaultData} onChange={mockOnChange} />);

    expect(screen.getByText('Combine all results into an array')).toBeInTheDocument();
  });

  it('shows all merge strategy options when opened', async () => {
    const user = userEvent.setup();
    render(<ParallelProperties data={defaultData} onChange={mockOnChange} />);

    const selectTrigger = screen.getByRole('combobox');
    await user.click(selectTrigger);

    await waitFor(() => {
      expect(screen.getAllByText('Collect all').length).toBeGreaterThan(0);
    });
    expect(screen.getByText('First result')).toBeInTheDocument();
    expect(screen.getByText('Last result')).toBeInTheDocument();
    expect(screen.getByText('Custom merge')).toBeInTheDocument();
  });

  it('handles merge strategy change to "first"', async () => {
    const user = userEvent.setup();
    render(<ParallelProperties data={defaultData} onChange={mockOnChange} />);

    const selectTrigger = screen.getByRole('combobox');
    await user.click(selectTrigger);

    const firstOption = screen.getByText('First result');
    await user.click(firstOption);

    expect(mockOnChange).toHaveBeenCalledWith({ mergeStrategy: 'first' });
  });

  it('handles merge strategy change to "last"', async () => {
    const user = userEvent.setup();
    render(<ParallelProperties data={defaultData} onChange={mockOnChange} />);

    const selectTrigger = screen.getByRole('combobox');
    await user.click(selectTrigger);

    const lastOption = screen.getByText('Last result');
    await user.click(lastOption);

    expect(mockOnChange).toHaveBeenCalledWith({ mergeStrategy: 'last' });
  });

  it('handles merge strategy change to "custom"', async () => {
    const user = userEvent.setup();
    render(<ParallelProperties data={defaultData} onChange={mockOnChange} />);

    const selectTrigger = screen.getByRole('combobox');
    await user.click(selectTrigger);

    const customOption = screen.getByText('Custom merge');
    await user.click(customOption);

    expect(mockOnChange).toHaveBeenCalledWith({ mergeStrategy: 'custom' });
  });

  it('displays "first" strategy with correct description', async () => {
    const dataWithFirst: ParallelBlockData = {
      mergeStrategy: 'first',
    };

    render(<ParallelProperties data={dataWithFirst} onChange={mockOnChange} />);

    expect(screen.getByText('Use the first completed result')).toBeInTheDocument();
  });

  it('displays "last" strategy with correct description', async () => {
    const dataWithLast: ParallelBlockData = {
      mergeStrategy: 'last',
    };

    render(<ParallelProperties data={dataWithLast} onChange={mockOnChange} />);

    expect(screen.getByText('Use the last completed result')).toBeInTheDocument();
  });

  it('displays "custom" strategy with correct description', async () => {
    const dataWithCustom: ParallelBlockData = {
      mergeStrategy: 'custom',
    };

    render(<ParallelProperties data={dataWithCustom} onChange={mockOnChange} />);

    expect(screen.getByText('Define custom merge logic')).toBeInTheDocument();
  });

  it('defaults to "concat" when no strategy is provided', () => {
    const dataWithoutStrategy: ParallelBlockData = {
      mergeStrategy: undefined as any,
    };

    render(<ParallelProperties data={dataWithoutStrategy} onChange={mockOnChange} />);

    const selectTrigger = screen.getByRole('combobox');
    expect(selectTrigger).toHaveTextContent('Collect all');
  });

  it('updates description when strategy changes', async () => {
    const user = userEvent.setup();
    const { rerender } = render(
      <ParallelProperties data={{ mergeStrategy: 'concat' }} onChange={mockOnChange} />
    );

    expect(screen.getByText('Combine all results into an array')).toBeInTheDocument();

    rerender(
      <ParallelProperties data={{ mergeStrategy: 'first' }} onChange={mockOnChange} />
    );

    expect(screen.getByText('Use the first completed result')).toBeInTheDocument();
    expect(
      screen.queryByText('Combine all results into an array')
    ).not.toBeInTheDocument();
  });

  it('renders with proper spacing classes', () => {
    const { container } = render(
      <ParallelProperties data={defaultData} onChange={mockOnChange} />
    );

    const spacingDiv = container.querySelector('.space-y-4');
    expect(spacingDiv).toBeInTheDocument();
  });

  it('calls onChange with correct strategy type', async () => {
    const user = userEvent.setup();
    render(<ParallelProperties data={defaultData} onChange={mockOnChange} />);

    const selectTrigger = screen.getByRole('combobox');
    await user.click(selectTrigger);

    const lastOption = screen.getByText('Last result');
    await user.click(lastOption);

    expect(mockOnChange).toHaveBeenCalledTimes(1);
    expect(mockOnChange).toHaveBeenCalledWith({ mergeStrategy: 'last' });
  });

  it('handles multiple strategy changes in sequence', async () => {
    const user = userEvent.setup();
    render(<ParallelProperties data={defaultData} onChange={mockOnChange} />);

    // Change to first
    let selectTrigger = screen.getByRole('combobox');
    await user.click(selectTrigger);
    await user.click(screen.getByText('First result'));

    expect(mockOnChange).toHaveBeenCalledWith({ mergeStrategy: 'first' });

    // Change to custom
    selectTrigger = screen.getByRole('combobox');
    await user.click(selectTrigger);
    await user.click(screen.getByText('Custom merge'));

    expect(mockOnChange).toHaveBeenCalledWith({ mergeStrategy: 'custom' });

    expect(mockOnChange).toHaveBeenCalledTimes(2);
  });

  it('renders select placeholder', () => {
    render(<ParallelProperties data={defaultData} onChange={mockOnChange} />);

    const select = screen.getByRole('combobox');
    expect(select).toBeInTheDocument();
  });
});
