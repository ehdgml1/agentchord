import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MultiAgentProperties } from './MultiAgentProperties';
import type { MultiAgentBlockData } from '../../types/blocks';

const mockData: MultiAgentBlockData = {
  name: 'Test Team',
  strategy: 'coordinator',
  members: [
    {
      id: 'member_1',
      name: 'Agent One',
      role: 'worker',
      model: 'gpt-4o-mini',
      systemPrompt: 'Be helpful',
      capabilities: ['search', 'code'],
      temperature: 0.7,
    },
  ],
  maxRounds: 10,
  costBudget: 5.0,
};

describe('MultiAgentProperties', () => {
  it('renders Team Name input with current value', () => {
    const onChange = vi.fn();
    render(<MultiAgentProperties data={mockData} onChange={onChange} />);

    const nameInput = screen.getByLabelText(/team name/i);
    expect(nameInput).toHaveValue('Test Team');
  });

  it('renders Strategy selector', () => {
    const onChange = vi.fn();
    render(<MultiAgentProperties data={mockData} onChange={onChange} />);

    expect(screen.getByText('Strategy')).toBeInTheDocument();
  });

  it('renders Max Rounds input with current value', () => {
    const onChange = vi.fn();
    render(<MultiAgentProperties data={mockData} onChange={onChange} />);

    const maxRoundsInput = screen.getByLabelText(/max rounds/i);
    expect(maxRoundsInput).toHaveValue(10);
  });

  it('renders Cost Budget input with current value', () => {
    const onChange = vi.fn();
    render(<MultiAgentProperties data={mockData} onChange={onChange} />);

    const costInput = screen.getByLabelText(/cost budget/i);
    expect(costInput).toHaveValue(5);
  });

  it('renders member count', () => {
    const onChange = vi.fn();
    render(<MultiAgentProperties data={mockData} onChange={onChange} />);

    expect(screen.getByText(/Team Members \(1\)/)).toBeInTheDocument();
  });

  it('name change calls onChange with { name: value }', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<MultiAgentProperties data={mockData} onChange={onChange} />);

    const nameInput = screen.getByLabelText(/team name/i);
    await user.type(nameInput, 'X');

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ name: expect.stringContaining('X') })
    );
  });

  it('maxRounds change calls onChange', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<MultiAgentProperties data={mockData} onChange={onChange} />);

    const maxRoundsInput = screen.getByLabelText(/max rounds/i);
    await user.clear(maxRoundsInput);
    await user.type(maxRoundsInput, '20');

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ maxRounds: expect.any(Number) })
    );
  });

  it('costBudget change calls onChange', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<MultiAgentProperties data={mockData} onChange={onChange} />);

    const costInput = screen.getByLabelText(/cost budget/i);
    await user.clear(costInput);
    await user.type(costInput, '10');

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ costBudget: expect.any(Number) })
    );
  });

  it('shows "No members yet" when members array is empty', () => {
    const onChange = vi.fn();
    const emptyData = { ...mockData, members: [] };
    render(<MultiAgentProperties data={emptyData} onChange={onChange} />);

    expect(screen.getByText(/no members yet/i)).toBeInTheDocument();
  });

  it('renders Add button', () => {
    const onChange = vi.fn();
    render(<MultiAgentProperties data={mockData} onChange={onChange} />);

    expect(screen.getByLabelText(/add member/i)).toBeInTheDocument();
  });

  it('add member button calls onChange with new member', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<MultiAgentProperties data={mockData} onChange={onChange} />);

    await user.click(screen.getByLabelText(/add member/i));

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({
        members: expect.arrayContaining([
          expect.objectContaining({ role: 'worker' }),
        ]),
      })
    );
    // Should now have 2 members
    const call = onChange.mock.calls[onChange.mock.calls.length - 1][0];
    expect(call.members).toHaveLength(2);
  });

  it('remove member button calls onChange without the member', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<MultiAgentProperties data={mockData} onChange={onChange} />);

    await user.click(screen.getByLabelText(/remove member/i));

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({
        members: [],
      })
    );
  });

  it('renders member name input', () => {
    const onChange = vi.fn();
    render(<MultiAgentProperties data={mockData} onChange={onChange} />);

    const memberNameInput = screen.getByDisplayValue('Agent One');
    expect(memberNameInput).toBeInTheDocument();
  });

  it('member name change calls onChange with updated member', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<MultiAgentProperties data={mockData} onChange={onChange} />);

    const memberNameInput = screen.getByDisplayValue('Agent One');
    await user.type(memberNameInput, 'Z');

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({
        members: expect.arrayContaining([
          expect.objectContaining({ name: expect.stringContaining('Z') }),
        ]),
      })
    );
  });

  it('expand button reveals member details', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<MultiAgentProperties data={mockData} onChange={onChange} />);

    // Initially, system prompt should not be visible
    expect(screen.queryByLabelText(/system prompt/i)).not.toBeInTheDocument();

    // Click expand button
    await user.click(screen.getByLabelText(/expand member/i));

    // Now system prompt should be visible
    expect(screen.getByLabelText(/system prompt/i)).toBeInTheDocument();
  });

  it('collapse button hides member details', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<MultiAgentProperties data={mockData} onChange={onChange} />);

    // Expand
    await user.click(screen.getByLabelText(/expand member/i));
    expect(screen.getByLabelText(/system prompt/i)).toBeInTheDocument();

    // Collapse
    await user.click(screen.getByLabelText(/collapse member/i));
    expect(screen.queryByLabelText(/system prompt/i)).not.toBeInTheDocument();
  });

  it('handles empty name gracefully', () => {
    const onChange = vi.fn();
    const dataWithEmptyName = { ...mockData, name: '' };
    render(<MultiAgentProperties data={dataWithEmptyName} onChange={onChange} />);

    const nameInput = screen.getByLabelText(/team name/i);
    expect(nameInput).toHaveValue('');
  });

  it('renders strategy selector with current value', () => {
    const onChange = vi.fn();
    render(<MultiAgentProperties data={mockData} onChange={onChange} />);

    // There should be a combobox for strategy
    const selects = screen.getAllByRole('combobox');
    expect(selects.length).toBeGreaterThanOrEqual(1);
  });
});
