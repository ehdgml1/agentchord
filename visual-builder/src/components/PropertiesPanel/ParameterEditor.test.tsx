/**
 * Tests for ParameterEditor component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ParameterEditor } from './ParameterEditor';

describe('ParameterEditor', () => {
  const mockOnChange = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Empty Schema', () => {
    it('shows no parameters message for empty schema', () => {
      const emptySchema = { properties: {} };
      render(
        <ParameterEditor
          schema={emptySchema}
          value={{}}
          onChange={mockOnChange}
        />
      );

      expect(screen.getByText('이 도구는 매개변수가 없습니다.')).toBeInTheDocument();
    });

    it('shows no parameters message when properties is undefined', () => {
      const emptySchema = {};
      render(
        <ParameterEditor
          schema={emptySchema}
          value={{}}
          onChange={mockOnChange}
        />
      );

      expect(screen.getByText('이 도구는 매개변수가 없습니다.')).toBeInTheDocument();
    });
  });

  describe('String Input', () => {
    it('renders string input from schema', () => {
      const schema = {
        properties: {
          message: {
            type: 'string',
            title: 'Message',
            description: 'Enter your message',
          },
        },
      };

      render(
        <ParameterEditor
          schema={schema}
          value={{ message: '' }}
          onChange={mockOnChange}
        />
      );

      expect(screen.getByText('Message')).toBeInTheDocument();
      expect(screen.getByText('Enter your message')).toBeInTheDocument();
      expect(screen.getByDisplayValue('')).toBeInTheDocument();
    });

    it('handles string input changes', async () => {
      const user = userEvent.setup();
      const schema = {
        properties: {
          message: { type: 'string', title: 'Message' },
        },
      };

      render(
        <ParameterEditor
          schema={schema}
          value={{ message: '' }}
          onChange={mockOnChange}
        />
      );

      const input = screen.getByDisplayValue('');
      await user.type(input, 'Hello');

      expect(mockOnChange).toHaveBeenCalled();
      // Check that onChange was called with a message containing characters
      const calls = mockOnChange.mock.calls;
      expect(calls.some(call => call[0].message.includes('H'))).toBe(true);
    });
  });

  describe('Number Input', () => {
    it('renders number input with correct type', () => {
      const schema = {
        properties: {
          count: {
            type: 'number',
            title: 'Count',
          },
        },
      };

      render(
        <ParameterEditor
          schema={schema}
          value={{ count: 0 }}
          onChange={mockOnChange}
        />
      );

      expect(screen.getByText('Count')).toBeInTheDocument();
      const input = screen.getByDisplayValue('0') as HTMLInputElement;
      expect(input.type).toBe('number');
      expect(input.step).toBe('any');
    });

    it('renders integer input with step 1', () => {
      const schema = {
        properties: {
          age: {
            type: 'integer',
            title: 'Age',
          },
        },
      };

      render(
        <ParameterEditor
          schema={schema}
          value={{ age: 0 }}
          onChange={mockOnChange}
        />
      );

      const input = screen.getByDisplayValue('0') as HTMLInputElement;
      expect(input.step).toBe('1');
    });

    it('coerces number input to number type', async () => {
      const user = userEvent.setup();
      const schema = {
        properties: {
          amount: { type: 'number', title: 'Amount' },
        },
      };

      render(
        <ParameterEditor
          schema={schema}
          value={{ amount: 0 }}
          onChange={mockOnChange}
        />
      );

      const input = screen.getByDisplayValue('0');
      await user.clear(input);
      await user.type(input, '42');

      expect(mockOnChange).toHaveBeenCalled();
      // Find a call where amount is a number
      const calls = mockOnChange.mock.calls;
      const numberCall = calls.find(call => typeof call[0].amount === 'number' && call[0].amount > 0);
      expect(numberCall).toBeDefined();
      expect(typeof numberCall[0].amount).toBe('number');
    });
  });

  describe('Boolean Switch', () => {
    it('renders boolean as switch toggle', () => {
      const schema = {
        properties: {
          enabled: {
            type: 'boolean',
            title: 'Enabled',
          },
        },
      };

      render(
        <ParameterEditor
          schema={schema}
          value={{ enabled: false }}
          onChange={mockOnChange}
        />
      );

      expect(screen.getByText('Enabled')).toBeInTheDocument();
      const switchElement = screen.getByRole('switch');
      expect(switchElement).toBeInTheDocument();
      expect(switchElement).not.toBeChecked();
    });

    it('handles boolean toggle changes', async () => {
      const user = userEvent.setup();
      const schema = {
        properties: {
          enabled: { type: 'boolean', title: 'Enabled' },
        },
      };

      render(
        <ParameterEditor
          schema={schema}
          value={{ enabled: false }}
          onChange={mockOnChange}
        />
      );

      const switchElement = screen.getByRole('switch');
      await user.click(switchElement);

      expect(mockOnChange).toHaveBeenCalledWith({ enabled: true });
    });
  });

  describe('Enum Select', () => {
    it('renders enum as select dropdown', () => {
      const schema = {
        properties: {
          size: {
            type: 'string',
            title: 'Size',
            enum: ['small', 'medium', 'large'],
            description: 'Choose a size',
          },
        },
      };

      render(
        <ParameterEditor
          schema={schema}
          value={{ size: '' }}
          onChange={mockOnChange}
        />
      );

      expect(screen.getByText('Size')).toBeInTheDocument();
      expect(screen.getByText('Choose a size')).toBeInTheDocument();
      const select = screen.getByRole('combobox');
      expect(select).toBeInTheDocument();
    });

    it('handles enum selection changes', async () => {
      const user = userEvent.setup();
      const schema = {
        properties: {
          size: {
            type: 'string',
            title: 'Size',
            enum: ['small', 'medium', 'large'],
          },
        },
      };

      render(
        <ParameterEditor
          schema={schema}
          value={{ size: '' }}
          onChange={mockOnChange}
        />
      );

      const trigger = screen.getByRole('combobox');
      await user.click(trigger);

      const mediumOption = await screen.findByText('medium');
      await user.click(mediumOption);

      expect(mockOnChange).toHaveBeenCalledWith({ size: 'medium' });
    });
  });

  describe('Array Fields', () => {
    it('renders array field with add button', () => {
      const schema = {
        properties: {
          tags: {
            type: 'array',
            title: 'Tags',
            description: 'List of tags',
            items: { type: 'string' },
          },
        },
      };

      render(
        <ParameterEditor
          schema={schema}
          value={{ tags: [] }}
          onChange={mockOnChange}
        />
      );

      expect(screen.getByText('Tags')).toBeInTheDocument();
      expect(screen.getByText('List of tags')).toBeInTheDocument();
      expect(screen.getByText('+ 항목 추가')).toBeInTheDocument();
    });

    it('adds array items when add button clicked', async () => {
      const user = userEvent.setup();
      const schema = {
        properties: {
          tags: {
            type: 'array',
            title: 'Tags',
            items: { type: 'string' },
          },
        },
      };

      render(
        <ParameterEditor
          schema={schema}
          value={{ tags: [] }}
          onChange={mockOnChange}
        />
      );

      const addButton = screen.getByText('+ 항목 추가');
      await user.click(addButton);

      expect(mockOnChange).toHaveBeenCalledWith({ tags: [''] });
    });

    it('removes array items when remove button clicked', async () => {
      const user = userEvent.setup();
      const schema = {
        properties: {
          tags: {
            type: 'array',
            title: 'Tags',
            items: { type: 'string' },
          },
        },
      };

      render(
        <ParameterEditor
          schema={schema}
          value={{ tags: ['tag1', 'tag2', 'tag3'] }}
          onChange={mockOnChange}
        />
      );

      const removeButtons = screen.getAllByText('삭제');
      expect(removeButtons).toHaveLength(3);

      // Remove second item
      await user.click(removeButtons[1]);

      expect(mockOnChange).toHaveBeenCalledWith({ tags: ['tag1', 'tag3'] });
    });

    it('displays array items with correct indices', () => {
      const schema = {
        properties: {
          items: {
            type: 'array',
            title: 'Items',
            items: { type: 'string' },
          },
        },
      };

      render(
        <ParameterEditor
          schema={schema}
          value={{ items: ['first', 'second', 'third'] }}
          onChange={mockOnChange}
        />
      );

      expect(screen.getByText('[1]')).toBeInTheDocument();
      expect(screen.getByText('[2]')).toBeInTheDocument();
      expect(screen.getByText('[3]')).toBeInTheDocument();
    });

    it('handles array of numbers with type coercion', async () => {
      const user = userEvent.setup();
      const schema = {
        properties: {
          numbers: {
            type: 'array',
            title: 'Numbers',
            items: { type: 'number' },
          },
        },
      };

      render(
        <ParameterEditor
          schema={schema}
          value={{ numbers: [] }}
          onChange={mockOnChange}
        />
      );

      const addButton = screen.getByText('+ 항목 추가');
      await user.click(addButton);

      expect(mockOnChange).toHaveBeenCalledWith({ numbers: [''] });

      // Now render with the added item
      render(
        <ParameterEditor
          schema={schema}
          value={{ numbers: [0] }}
          onChange={mockOnChange}
        />
      );

      const input = screen.getByDisplayValue('0') as HTMLInputElement;
      expect(input.type).toBe('number');
    });
  });

  describe('Array of Objects', () => {
    it('renders array of objects with nested properties', () => {
      const schema = {
        properties: {
          attachments: {
            type: 'array',
            title: 'Email Attachments',
            items: {
              type: 'object',
              properties: {
                filename: { type: 'string', title: 'Filename' },
                content: { type: 'string', title: 'Content' },
              },
            },
          },
        },
      };

      render(
        <ParameterEditor
          schema={schema}
          value={{
            attachments: [
              { filename: 'doc.pdf', content: 'base64...' },
            ],
          }}
          onChange={mockOnChange}
        />
      );

      expect(screen.getByText('Email Attachments')).toBeInTheDocument();
      expect(screen.getByText('[1]')).toBeInTheDocument();
      expect(screen.getByText('Filename')).toBeInTheDocument();
      expect(screen.getByText('Content')).toBeInTheDocument();
      expect(screen.getByDisplayValue('doc.pdf')).toBeInTheDocument();
      expect(screen.getByDisplayValue('base64...')).toBeInTheDocument();
    });

    it('adds array of objects items correctly', async () => {
      const user = userEvent.setup();
      const schema = {
        properties: {
          items: {
            type: 'array',
            title: 'Items',
            items: {
              type: 'object',
              properties: {
                name: { type: 'string' },
              },
            },
          },
        },
      };

      render(
        <ParameterEditor
          schema={schema}
          value={{ items: [] }}
          onChange={mockOnChange}
        />
      );

      const addButton = screen.getByText('+ 항목 추가');
      await user.click(addButton);

      expect(mockOnChange).toHaveBeenCalledWith({ items: [{}] });
    });

    it('updates nested object properties in array', async () => {
      const user = userEvent.setup();
      const schema = {
        properties: {
          items: {
            type: 'array',
            title: 'Items',
            items: {
              type: 'object',
              properties: {
                name: { type: 'string', title: 'Name' },
                value: { type: 'number', title: 'Value' },
              },
            },
          },
        },
      };

      render(
        <ParameterEditor
          schema={schema}
          value={{ items: [{ name: 'test', value: 0 }] }}
          onChange={mockOnChange}
        />
      );

      const nameInput = screen.getByDisplayValue('test');
      await user.type(nameInput, 'X');

      expect(mockOnChange).toHaveBeenCalled();
      const lastCall = mockOnChange.mock.calls[mockOnChange.mock.calls.length - 1][0];
      expect(lastCall.items[0].name).toBe('testX');
    });
  });

  describe('Nested Object Properties', () => {
    it('renders nested object properties', () => {
      const schema = {
        properties: {
          config: {
            type: 'object',
            title: 'Configuration',
            description: 'App configuration',
            properties: {
              host: { type: 'string', title: 'Host' },
              port: { type: 'number', title: 'Port' },
            },
          },
        },
      };

      render(
        <ParameterEditor
          schema={schema}
          value={{ config: { host: 'localhost', port: 3000 } }}
          onChange={mockOnChange}
        />
      );

      expect(screen.getByText('Configuration')).toBeInTheDocument();
      expect(screen.getByText('App configuration')).toBeInTheDocument();
      expect(screen.getByText('Host')).toBeInTheDocument();
      expect(screen.getByText('Port')).toBeInTheDocument();
      expect(screen.getByDisplayValue('localhost')).toBeInTheDocument();
      expect(screen.getByDisplayValue('3000')).toBeInTheDocument();
    });

    it('updates nested object property values', async () => {
      const user = userEvent.setup();
      const schema = {
        properties: {
          config: {
            type: 'object',
            title: 'Config',
            properties: {
              apiKey: { type: 'string', title: 'API Key' },
            },
          },
        },
      };

      render(
        <ParameterEditor
          schema={schema}
          value={{ config: { apiKey: 'initial' } }}
          onChange={mockOnChange}
        />
      );

      const input = screen.getByDisplayValue('initial');
      await user.type(input, 'X');

      expect(mockOnChange).toHaveBeenCalled();
      const lastCall = mockOnChange.mock.calls[mockOnChange.mock.calls.length - 1][0];
      expect(lastCall.config.apiKey).toBe('initialX');
    });
  });

  describe('Required Fields', () => {
    it('shows required indicator for required fields', () => {
      const schema = {
        properties: {
          email: { type: 'string', title: 'Email' },
          password: { type: 'string', title: 'Password' },
        },
        required: ['email', 'password'],
      };

      render(
        <ParameterEditor
          schema={schema}
          value={{ email: '', password: '' }}
          onChange={mockOnChange}
        />
      );

      const requiredIndicators = screen.getAllByText('*');
      expect(requiredIndicators).toHaveLength(2);
    });

    it('shows required indicator for nested required fields', () => {
      const schema = {
        properties: {
          config: {
            type: 'object',
            title: 'Config',
            properties: {
              apiKey: { type: 'string', title: 'API Key' },
              secret: { type: 'string', title: 'Secret' },
            },
            required: ['apiKey'],
          },
        },
      };

      render(
        <ParameterEditor
          schema={schema}
          value={{ config: { apiKey: '', secret: '' } }}
          onChange={mockOnChange}
        />
      );

      const requiredIndicators = screen.getAllByText('*');
      expect(requiredIndicators).toHaveLength(1);
    });

    it('shows required indicator in array object items', () => {
      const schema = {
        properties: {
          users: {
            type: 'array',
            title: 'Users',
            items: {
              type: 'object',
              properties: {
                name: { type: 'string', title: 'Name' },
                email: { type: 'string', title: 'Email' },
              },
              required: ['email'],
            },
          },
        },
      };

      render(
        <ParameterEditor
          schema={schema}
          value={{ users: [{ name: '', email: '' }] }}
          onChange={mockOnChange}
        />
      );

      expect(screen.getByText('Email')).toBeInTheDocument();
      expect(screen.getAllByText('*')).toHaveLength(1);
    });
  });

  describe('Property Descriptions', () => {
    it('shows property descriptions', () => {
      const schema = {
        properties: {
          username: {
            type: 'string',
            title: 'Username',
            description: 'Your unique username',
          },
          age: {
            type: 'number',
            title: 'Age',
            description: 'Your age in years',
          },
        },
      };

      render(
        <ParameterEditor
          schema={schema}
          value={{ username: '', age: 0 }}
          onChange={mockOnChange}
        />
      );

      expect(screen.getByText('Your unique username')).toBeInTheDocument();
      expect(screen.getByText('Your age in years')).toBeInTheDocument();
    });

    it('shows description for array fields', () => {
      const schema = {
        properties: {
          tags: {
            type: 'array',
            title: 'Tags',
            description: 'Add tags to categorize',
            items: { type: 'string' },
          },
        },
      };

      render(
        <ParameterEditor
          schema={schema}
          value={{ tags: [] }}
          onChange={mockOnChange}
        />
      );

      expect(screen.getByText('Add tags to categorize')).toBeInTheDocument();
    });
  });

  describe('Template Variables', () => {
    it('shows template hint when value contains {{', () => {
      const schema = {
        properties: {
          message: { type: 'string', title: 'Message' },
        },
      };

      render(
        <ParameterEditor
          schema={schema}
          value={{ message: 'Hello {{user.name}}' }}
          onChange={mockOnChange}
        />
      );

      expect(screen.getByText(/템플릿 사용 가능:/)).toBeInTheDocument();
      expect(screen.getByText(/노드ID\.필드/)).toBeInTheDocument();
    });

    it('applies monospace font class for template values', () => {
      const schema = {
        properties: {
          query: { type: 'string', title: 'Query' },
        },
      };

      render(
        <ParameterEditor
          schema={schema}
          value={{ query: '{{node1.output}}' }}
          onChange={mockOnChange}
        />
      );

      const input = screen.getByDisplayValue('{{node1.output}}') as HTMLInputElement;
      expect(input.className).toContain('font-mono');
    });

    it('does not show template hint for regular values', () => {
      const schema = {
        properties: {
          message: { type: 'string', title: 'Message' },
        },
      };

      render(
        <ParameterEditor
          schema={schema}
          value={{ message: 'Regular text' }}
          onChange={mockOnChange}
        />
      );

      expect(screen.queryByText(/템플릿 사용 가능:/)).not.toBeInTheDocument();
    });

    it('shows template hint in array string items', () => {
      const schema = {
        properties: {
          paths: {
            type: 'array',
            title: 'Paths',
            items: { type: 'string' },
          },
        },
      };

      render(
        <ParameterEditor
          schema={schema}
          value={{ paths: ['{{node1.path}}', 'static/path'] }}
          onChange={mockOnChange}
        />
      );

      const templateInputs = screen.getAllByDisplayValue(/{{.*}}/);
      expect(templateInputs).toHaveLength(1);
      expect(templateInputs[0].className).toContain('font-mono');
    });
  });

  describe('Field Titles', () => {
    it('uses schema title when provided', () => {
      const schema = {
        properties: {
          user_email: { type: 'string', title: 'User Email Address' },
        },
      };

      render(
        <ParameterEditor
          schema={schema}
          value={{ user_email: '' }}
          onChange={mockOnChange}
        />
      );

      expect(screen.getByText('User Email Address')).toBeInTheDocument();
    });

    it('uses field name as fallback when no title', () => {
      const schema = {
        properties: {
          username: { type: 'string' },
        },
      };

      render(
        <ParameterEditor
          schema={schema}
          value={{ username: '' }}
          onChange={mockOnChange}
        />
      );

      expect(screen.getByText('username')).toBeInTheDocument();
    });
  });

  describe('Complex Scenarios', () => {
    it('handles deeply nested structures', async () => {
      const user = userEvent.setup();
      const schema = {
        properties: {
          email: {
            type: 'object',
            title: 'Email',
            properties: {
              to: { type: 'string', title: 'To' },
              attachments: {
                type: 'array',
                title: 'Attachments',
                items: {
                  type: 'object',
                  properties: {
                    filename: { type: 'string', title: 'Filename' },
                    size: { type: 'number', title: 'Size' },
                  },
                  required: ['filename'],
                },
              },
            },
            required: ['to'],
          },
        },
      };

      render(
        <ParameterEditor
          schema={schema}
          value={{
            email: {
              to: 'test@example.com',
              attachments: [{ filename: 'report.pdf', size: 1024 }],
            },
          }}
          onChange={mockOnChange}
        />
      );

      expect(screen.getByText('Email')).toBeInTheDocument();
      expect(screen.getByText('To')).toBeInTheDocument();
      expect(screen.getByText('Attachments')).toBeInTheDocument();
      expect(screen.getByText('Filename')).toBeInTheDocument();
      expect(screen.getByText('Size')).toBeInTheDocument();
      expect(screen.getByDisplayValue('test@example.com')).toBeInTheDocument();
      expect(screen.getByDisplayValue('report.pdf')).toBeInTheDocument();
      expect(screen.getByDisplayValue('1024')).toBeInTheDocument();

      // Verify required indicators
      const requiredMarkers = screen.getAllByText('*');
      expect(requiredMarkers.length).toBeGreaterThan(0);
    });

    it('maintains proper value structure on changes', async () => {
      const user = userEvent.setup();
      const schema = {
        properties: {
          name: { type: 'string', title: 'Name' },
          age: { type: 'number', title: 'Age' },
          active: { type: 'boolean', title: 'Active' },
        },
      };

      render(
        <ParameterEditor
          schema={schema}
          value={{ name: 'John', age: 30, active: true }}
          onChange={mockOnChange}
        />
      );

      const nameInput = screen.getByDisplayValue('John');
      await user.type(nameInput, 'X');

      const lastCall = mockOnChange.mock.calls[mockOnChange.mock.calls.length - 1][0];
      expect(lastCall.name).toContain('John');
      expect(lastCall.age).toBe(30);
      expect(lastCall.active).toBe(true);
    });
  });
});
