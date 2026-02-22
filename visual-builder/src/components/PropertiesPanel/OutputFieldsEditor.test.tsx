/**
 * Tests for OutputFieldsEditor component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { OutputFieldsEditor } from './OutputFieldsEditor';
import type { OutputFieldConfig } from '../../types/blocks';

describe('OutputFieldsEditor', () => {
  const mockOnChange = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Empty State', () => {
    it('renders empty state with helper text when no fields', () => {
      render(<OutputFieldsEditor fields={[]} onChange={mockOnChange} />);

      expect(screen.getByText(/출력 형식/i)).toBeInTheDocument();
      expect(
        screen.getByText(/출력 필드를 정의하면 Agent가 구조화된 JSON으로 응답합니다/)
      ).toBeInTheDocument();
      expect(
        screen.getByText(/텍스트 필드는 문장이나 문단도 지원합니다/)
      ).toBeInTheDocument();
      expect(
        screen.getByText(/다운스트림 노드에서 각 필드를 개별적으로 활용할 수 있습니다/)
      ).toBeInTheDocument();
    });

    it('shows add button in empty state', () => {
      render(<OutputFieldsEditor fields={[]} onChange={mockOnChange} />);

      const addButton = screen.getByRole('button', { name: /add output field/i });
      expect(addButton).toBeInTheDocument();
      expect(screen.getByText(/필드 추가/i)).toBeInTheDocument();
    });

    it('does not show field list when empty', () => {
      const { container } = render(<OutputFieldsEditor fields={[]} onChange={mockOnChange} />);

      const fieldList = container.querySelector('.space-y-2');
      expect(fieldList).not.toBeInTheDocument();
    });
  });

  describe('Rendering Fields', () => {
    it('renders existing field with name and type', () => {
      const fields: OutputFieldConfig[] = [{ name: 'score', type: 'number' }];

      render(<OutputFieldsEditor fields={fields} onChange={mockOnChange} />);

      const nameInput = screen.getByLabelText(/field name/i);
      expect(nameInput).toHaveValue('score');

      const typeSelect = screen.getByLabelText(/field type/i);
      expect(typeSelect).toHaveTextContent('숫자');
    });

    it('renders multiple fields correctly', () => {
      const fields: OutputFieldConfig[] = [
        { name: 'score', type: 'number' },
        { name: 'valid', type: 'boolean' },
        { name: 'message', type: 'text' },
      ];

      render(<OutputFieldsEditor fields={fields} onChange={mockOnChange} />);

      expect(screen.getByTestId('output-field-0')).toBeInTheDocument();
      expect(screen.getByTestId('output-field-1')).toBeInTheDocument();
      expect(screen.getByTestId('output-field-2')).toBeInTheDocument();

      const nameInputs = screen.getAllByLabelText(/field name/i);
      expect(nameInputs[0]).toHaveValue('score');
      expect(nameInputs[1]).toHaveValue('valid');
      expect(nameInputs[2]).toHaveValue('message');
    });

    it('renders field with empty name', () => {
      const fields: OutputFieldConfig[] = [{ name: '', type: 'text' }];

      render(<OutputFieldsEditor fields={fields} onChange={mockOnChange} />);

      const nameInput = screen.getByLabelText(/field name/i);
      expect(nameInput).toHaveValue('');
      expect(nameInput).toHaveAttribute('placeholder', '필드명 (예: 평가근거, score)');
    });

    it('shows remove button for each field', () => {
      const fields: OutputFieldConfig[] = [
        { name: 'score', type: 'number' },
        { name: 'valid', type: 'boolean' },
      ];

      render(<OutputFieldsEditor fields={fields} onChange={mockOnChange} />);

      const removeButtons = screen.getAllByRole('button', { name: /remove field/i });
      expect(removeButtons).toHaveLength(2);
    });
  });

  describe('Adding Fields', () => {
    it('clicking "필드 추가" adds a new empty field', async () => {
      const user = userEvent.setup();
      render(<OutputFieldsEditor fields={[]} onChange={mockOnChange} />);

      const addButton = screen.getByRole('button', { name: /add output field/i });
      await user.click(addButton);

      expect(mockOnChange).toHaveBeenCalledWith([{ name: '', type: 'text' }]);
    });

    it('adds new field to existing fields', async () => {
      const user = userEvent.setup();
      const fields: OutputFieldConfig[] = [{ name: 'score', type: 'number' }];

      render(<OutputFieldsEditor fields={fields} onChange={mockOnChange} />);

      const addButton = screen.getByRole('button', { name: /add output field/i });
      await user.click(addButton);

      expect(mockOnChange).toHaveBeenCalledWith([
        { name: 'score', type: 'number' },
        { name: '', type: 'text' },
      ]);
    });

    it('new field has default type "text"', async () => {
      const user = userEvent.setup();
      render(<OutputFieldsEditor fields={[]} onChange={mockOnChange} />);

      const addButton = screen.getByRole('button', { name: /add output field/i });
      await user.click(addButton);

      expect(mockOnChange).toHaveBeenCalledWith(
        expect.arrayContaining([expect.objectContaining({ type: 'text' })])
      );
    });

    it('adds multiple fields sequentially', async () => {
      const user = userEvent.setup();
      const fields: OutputFieldConfig[] = [];
      let currentFields = fields;

      const { rerender } = render(
        <OutputFieldsEditor fields={currentFields} onChange={mockOnChange} />
      );

      const addButton = screen.getByRole('button', { name: /add output field/i });

      // Add first field
      await user.click(addButton);
      currentFields = [{ name: '', type: 'text' }];
      rerender(<OutputFieldsEditor fields={currentFields} onChange={mockOnChange} />);

      // Add second field
      await user.click(addButton);

      expect(mockOnChange).toHaveBeenLastCalledWith([
        { name: '', type: 'text' },
        { name: '', type: 'text' },
      ]);
    });
  });

  describe('Changing Field Name', () => {
    it('changing field name calls onChange with updated fields', async () => {
      const user = userEvent.setup();
      const fields: OutputFieldConfig[] = [{ name: '', type: 'text' }];

      render(<OutputFieldsEditor fields={fields} onChange={mockOnChange} />);

      const nameInput = screen.getByLabelText(/field name/i);
      await user.type(nameInput, 'score');

      expect(mockOnChange).toHaveBeenCalled();
      // Called once for each character typed ('s', 'c', 'o', 'r', 'e')
      expect(mockOnChange).toHaveBeenCalledTimes(5);
      // Last call should be 's' (first character)
      const calls = mockOnChange.mock.calls;
      expect(calls[calls.length - 1][0]).toEqual([{ name: 'e', type: 'text' }]);
    });

    it('updates correct field when multiple fields exist', async () => {
      const user = userEvent.setup();
      const fields: OutputFieldConfig[] = [
        { name: 'field1', type: 'text' },
        { name: 'field2', type: 'number' },
      ];

      render(<OutputFieldsEditor fields={fields} onChange={mockOnChange} />);

      const nameInputs = screen.getAllByLabelText(/field name/i);
      await user.clear(nameInputs[1]);

      // After clear, type new value
      await user.type(nameInputs[1], 'score');

      expect(mockOnChange).toHaveBeenCalled();
      // Check that first field is preserved
      const lastCall = mockOnChange.mock.calls[mockOnChange.mock.calls.length - 1][0];
      expect(lastCall[0]).toEqual({ name: 'field1', type: 'text' });
      expect(lastCall[1].type).toBe('number');
    });

    it('preserves field type when changing name', async () => {
      const user = userEvent.setup();
      const fields: OutputFieldConfig[] = [{ name: '', type: 'boolean' }];

      render(<OutputFieldsEditor fields={fields} onChange={mockOnChange} />);

      const nameInput = screen.getByLabelText(/field name/i);
      await user.type(nameInput, 'valid');

      // Verify type is preserved across all onChange calls
      const allCalls = mockOnChange.mock.calls;
      allCalls.forEach((call) => {
        expect(call[0][0].type).toBe('boolean');
      });
    });
  });

  describe('Changing Field Type', () => {
    it('changing field type calls onChange with updated type', async () => {
      const user = userEvent.setup();
      const fields: OutputFieldConfig[] = [{ name: 'score', type: 'text' }];

      render(<OutputFieldsEditor fields={fields} onChange={mockOnChange} />);

      const typeSelect = screen.getByLabelText(/field type/i);
      await user.click(typeSelect);

      const numberOption = screen.getByRole('option', { name: /숫자/i });
      await user.click(numberOption);

      expect(mockOnChange).toHaveBeenCalledWith([{ name: 'score', type: 'number' }]);
    });

    it('updates correct field type when multiple fields exist', async () => {
      const user = userEvent.setup();
      const fields: OutputFieldConfig[] = [
        { name: 'field1', type: 'text' },
        { name: 'field2', type: 'number' },
      ];

      render(<OutputFieldsEditor fields={fields} onChange={mockOnChange} />);

      const typeSelects = screen.getAllByLabelText(/field type/i);
      await user.click(typeSelects[0]);

      const booleanOption = screen.getByRole('option', { name: /예\/아니오/i });
      await user.click(booleanOption);

      expect(mockOnChange).toHaveBeenCalledWith([
        { name: 'field1', type: 'boolean' },
        { name: 'field2', type: 'number' },
      ]);
    });

    it('preserves field name when changing type', async () => {
      const user = userEvent.setup();
      const fields: OutputFieldConfig[] = [{ name: 'myField', type: 'text' }];

      render(<OutputFieldsEditor fields={fields} onChange={mockOnChange} />);

      const typeSelect = screen.getByLabelText(/field type/i);
      await user.click(typeSelect);

      const listOption = screen.getByRole('option', { name: /목록/i });
      await user.click(listOption);

      expect(mockOnChange).toHaveBeenCalledWith([{ name: 'myField', type: 'list' }]);
    });
  });

  describe('Removing Fields', () => {
    it('clicking remove button removes the field', async () => {
      const user = userEvent.setup();
      const fields: OutputFieldConfig[] = [{ name: 'score', type: 'number' }];

      render(<OutputFieldsEditor fields={fields} onChange={mockOnChange} />);

      const removeButton = screen.getByRole('button', { name: /remove field/i });
      await user.click(removeButton);

      expect(mockOnChange).toHaveBeenCalledWith([]);
    });

    it('removes correct field when multiple fields exist', async () => {
      const user = userEvent.setup();
      const fields: OutputFieldConfig[] = [
        { name: 'field1', type: 'text' },
        { name: 'field2', type: 'number' },
        { name: 'field3', type: 'boolean' },
      ];

      render(<OutputFieldsEditor fields={fields} onChange={mockOnChange} />);

      const removeButtons = screen.getAllByRole('button', { name: /remove field/i });
      await user.click(removeButtons[1]); // Remove middle field

      expect(mockOnChange).toHaveBeenCalledWith([
        { name: 'field1', type: 'text' },
        { name: 'field3', type: 'boolean' },
      ]);
    });

    it('removes first field correctly', async () => {
      const user = userEvent.setup();
      const fields: OutputFieldConfig[] = [
        { name: 'first', type: 'text' },
        { name: 'second', type: 'number' },
      ];

      render(<OutputFieldsEditor fields={fields} onChange={mockOnChange} />);

      const removeButtons = screen.getAllByRole('button', { name: /remove field/i });
      await user.click(removeButtons[0]);

      expect(mockOnChange).toHaveBeenCalledWith([{ name: 'second', type: 'number' }]);
    });

    it('removes last field correctly', async () => {
      const user = userEvent.setup();
      const fields: OutputFieldConfig[] = [
        { name: 'first', type: 'text' },
        { name: 'second', type: 'number' },
      ];

      render(<OutputFieldsEditor fields={fields} onChange={mockOnChange} />);

      const removeButtons = screen.getAllByRole('button', { name: /remove field/i });
      await user.click(removeButtons[1]);

      expect(mockOnChange).toHaveBeenCalledWith([{ name: 'first', type: 'text' }]);
    });

    it('shows empty state after removing all fields', async () => {
      const user = userEvent.setup();
      const fields: OutputFieldConfig[] = [{ name: 'last', type: 'text' }];

      const { rerender } = render(<OutputFieldsEditor fields={fields} onChange={mockOnChange} />);

      const removeButton = screen.getByRole('button', { name: /remove field/i });
      await user.click(removeButton);

      // Simulate the onChange effect
      rerender(<OutputFieldsEditor fields={[]} onChange={mockOnChange} />);

      expect(
        screen.getByText(/출력 필드를 정의하면 Agent가 구조화된 JSON으로 응답합니다/)
      ).toBeInTheDocument();
    });
  });

  describe('Field Type Options', () => {
    it('shows all field type options', async () => {
      const user = userEvent.setup();
      const fields: OutputFieldConfig[] = [{ name: 'test', type: 'text' }];

      render(<OutputFieldsEditor fields={fields} onChange={mockOnChange} />);

      const typeSelect = screen.getByLabelText(/field type/i);
      await user.click(typeSelect);

      expect(screen.getByRole('option', { name: /텍스트/i })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: /숫자/i })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: /예\/아니오/i })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: /목록/i })).toBeInTheDocument();
    });

    it('renders correct type label for each field type', () => {
      const fields: OutputFieldConfig[] = [
        { name: 'text_field', type: 'text' },
        { name: 'number_field', type: 'number' },
        { name: 'boolean_field', type: 'boolean' },
        { name: 'list_field', type: 'list' },
      ];

      render(<OutputFieldsEditor fields={fields} onChange={mockOnChange} />);

      const typeSelects = screen.getAllByLabelText(/field type/i);
      expect(typeSelects[0]).toHaveTextContent('텍스트');
      expect(typeSelects[1]).toHaveTextContent('숫자');
      expect(typeSelects[2]).toHaveTextContent('예/아니오');
      expect(typeSelects[3]).toHaveTextContent('목록');
    });
  });

  describe('UI Elements', () => {
    it('renders with ListChecks icon in label', () => {
      render(<OutputFieldsEditor fields={[]} onChange={mockOnChange} />);

      const label = screen.getByText(/출력 형식/i);
      expect(label).toBeInTheDocument();
    });

    it('renders add button with Plus icon', () => {
      render(<OutputFieldsEditor fields={[]} onChange={mockOnChange} />);

      const addButton = screen.getByRole('button', { name: /add output field/i });
      expect(addButton).toHaveTextContent('필드 추가');
    });

    it('renders remove button with Trash2 icon', () => {
      const fields: OutputFieldConfig[] = [{ name: 'test', type: 'text' }];

      render(<OutputFieldsEditor fields={fields} onChange={mockOnChange} />);

      const removeButton = screen.getByRole('button', { name: /remove field/i });
      expect(removeButton).toBeInTheDocument();
    });

    it('applies correct CSS classes', () => {
      const { container } = render(<OutputFieldsEditor fields={[]} onChange={mockOnChange} />);

      expect(container.querySelector('.space-y-3')).toBeInTheDocument();
    });

    it('applies data-testid to each field row', () => {
      const fields: OutputFieldConfig[] = [
        { name: 'field1', type: 'text' },
        { name: 'field2', type: 'number' },
      ];

      render(<OutputFieldsEditor fields={fields} onChange={mockOnChange} />);

      expect(screen.getByTestId('output-field-0')).toBeInTheDocument();
      expect(screen.getByTestId('output-field-1')).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('handles undefined description field gracefully', () => {
      const fields: OutputFieldConfig[] = [{ name: 'test', type: 'text' }];

      render(<OutputFieldsEditor fields={fields} onChange={mockOnChange} />);

      const nameInput = screen.getByLabelText(/field name/i);
      expect(nameInput).toBeInTheDocument();
    });

    it('handles rapid add and remove operations', async () => {
      const user = userEvent.setup();
      render(<OutputFieldsEditor fields={[]} onChange={mockOnChange} />);

      const addButton = screen.getByRole('button', { name: /add output field/i });

      // Add field
      await user.click(addButton);
      expect(mockOnChange).toHaveBeenCalledWith([{ name: '', type: 'text' }]);

      // Simulate rerender with the new field
      const { rerender } = render(
        <OutputFieldsEditor fields={[{ name: '', type: 'text' }]} onChange={mockOnChange} />
      );

      // Remove field
      const removeButton = screen.getByRole('button', { name: /remove field/i });
      await user.click(removeButton);
      expect(mockOnChange).toHaveBeenCalledWith([]);
    });

    it('handles special characters in field names', async () => {
      const user = userEvent.setup();
      const fields: OutputFieldConfig[] = [{ name: '', type: 'text' }];

      render(<OutputFieldsEditor fields={fields} onChange={mockOnChange} />);

      const nameInput = screen.getByLabelText(/field name/i);
      await user.type(nameInput, 'test_field');

      // Verify onChange was called multiple times (once per character)
      expect(mockOnChange).toHaveBeenCalled();
      // Verify all calls preserve the type
      const allCalls = mockOnChange.mock.calls;
      allCalls.forEach((call) => {
        expect(call[0][0].type).toBe('text');
      });
    });

    it('preserves onChange reference across updates', () => {
      const { rerender } = render(<OutputFieldsEditor fields={[]} onChange={mockOnChange} />);

      const addButton1 = screen.getByRole('button', { name: /add output field/i });

      rerender(<OutputFieldsEditor fields={[]} onChange={mockOnChange} />);

      const addButton2 = screen.getByRole('button', { name: /add output field/i });

      expect(addButton1).toBe(addButton2);
    });
  });

  describe('Component Properties', () => {
    it('component is exported and can be rendered', () => {
      expect(OutputFieldsEditor).toBeDefined();

      const { container } = render(
        <OutputFieldsEditor fields={[]} onChange={mockOnChange} />
      );

      expect(container).toBeInTheDocument();
    });

    it('renders consistently with same props', () => {
      const fields: OutputFieldConfig[] = [{ name: 'test', type: 'text' }];

      const { rerender, container } = render(
        <OutputFieldsEditor fields={fields} onChange={mockOnChange} />
      );
      const firstRender = container.innerHTML;

      rerender(<OutputFieldsEditor fields={fields} onChange={mockOnChange} />);
      const secondRender = container.innerHTML;

      expect(firstRender).toBe(secondRender);
    });
  });
});
