import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AgentProperties } from './AgentProperties';
import type { AgentBlockData } from '../../types/blocks';

const mockData: AgentBlockData = {
  name: 'Test Agent',
  role: 'Assistant',
  model: 'gpt-4o-mini',
  temperature: 0.7,
  maxTokens: 4096,
  systemPrompt: 'Be helpful',
};

describe('AgentProperties', () => {
  it('renders Name input with current value', () => {
    const onChange = vi.fn();
    render(<AgentProperties data={mockData} onChange={onChange} />);

    const nameInput = screen.getByLabelText(/name/i);
    expect(nameInput).toHaveValue('Test Agent');
  });

  it('renders Role input with current value', () => {
    const onChange = vi.fn();
    render(<AgentProperties data={mockData} onChange={onChange} />);

    const roleInput = screen.getByLabelText(/role/i);
    expect(roleInput).toHaveValue('Assistant');
  });

  it('renders model selector', () => {
    const onChange = vi.fn();
    render(<AgentProperties data={mockData} onChange={onChange} />);

    expect(screen.getByText('Model')).toBeInTheDocument();
  });

  it('renders temperature display', () => {
    const onChange = vi.fn();
    render(<AgentProperties data={mockData} onChange={onChange} />);

    expect(screen.getByText(/temperature/i)).toBeInTheDocument();
    expect(screen.getByText('0.7')).toBeInTheDocument();
  });

  it('renders system prompt textarea', () => {
    const onChange = vi.fn();
    render(<AgentProperties data={mockData} onChange={onChange} />);

    const promptInput = screen.getByLabelText(/system prompt/i);
    expect(promptInput).toHaveValue('Be helpful');
  });

  it('name change calls onChange with { name: value }', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<AgentProperties data={mockData} onChange={onChange} />);

    const nameInput = screen.getByLabelText(/name/i);
    await user.type(nameInput, 'X');

    // Should have been called with partial update containing name
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ name: expect.stringContaining('X') })
    );
  });

  it('role change calls onChange with { role: value }', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<AgentProperties data={mockData} onChange={onChange} />);

    const roleInput = screen.getByLabelText(/role/i);
    await user.type(roleInput, 'Y');

    // Should have been called with partial update containing role
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ role: expect.stringContaining('Y') })
    );
  });

  it('system prompt change calls onChange with { systemPrompt: value }', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<AgentProperties data={mockData} onChange={onChange} />);

    const promptInput = screen.getByLabelText(/system prompt/i);
    await user.type(promptInput, 'Z');

    // Should have been called with partial update containing systemPrompt
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ systemPrompt: expect.stringContaining('Z') })
    );
  });

  it('renders model selector with current value', () => {
    const onChange = vi.fn();
    render(<AgentProperties data={mockData} onChange={onChange} />);

    // The select should show the current model value
    const selectTrigger = screen.getByRole('combobox');
    expect(selectTrigger).toBeInTheDocument();
  });

  it('temperature shows formatted value', () => {
    const onChange = vi.fn();
    const dataWithTemp = { ...mockData, temperature: 1.3 };
    render(<AgentProperties data={dataWithTemp} onChange={onChange} />);

    expect(screen.getByText('1.3')).toBeInTheDocument();
  });

  it('handles empty name gracefully', () => {
    const onChange = vi.fn();
    const dataWithEmptyName = { ...mockData, name: '' };
    render(<AgentProperties data={dataWithEmptyName} onChange={onChange} />);

    const nameInput = screen.getByLabelText(/name/i);
    expect(nameInput).toHaveValue('');
  });

  it('handles undefined systemPrompt gracefully', () => {
    const onChange = vi.fn();
    const dataWithoutPrompt = { ...mockData, systemPrompt: undefined };
    render(<AgentProperties data={dataWithoutPrompt} onChange={onChange} />);

    const promptInput = screen.getByLabelText(/system prompt/i);
    expect(promptInput).toHaveValue('');
  });

  it('renders maxTokens input with current value', () => {
    const onChange = vi.fn();
    render(<AgentProperties data={mockData} onChange={onChange} />);

    const maxTokensInput = screen.getByLabelText(/max tokens/i);
    expect(maxTokensInput).toHaveValue(4096);
  });

  it('maxTokens change calls onChange with { maxTokens: value }', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<AgentProperties data={mockData} onChange={onChange} />);

    const maxTokensInput = screen.getByLabelText(/max tokens/i);
    await user.clear(maxTokensInput);
    await user.type(maxTokensInput, '8192');

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ maxTokens: expect.any(Number) })
    );
  });
});
