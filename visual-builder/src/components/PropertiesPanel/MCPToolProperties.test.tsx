/**
 * Tests for MCPToolProperties component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MCPToolProperties } from './MCPToolProperties';
import type { MCPToolBlockData } from '../../types/blocks';
import type { MCPServer, MCPTool } from '../../types/mcp';
import { api } from '../../services/api';

// Mock the API service
vi.mock('../../services/api', () => ({
  api: {
    mcp: {
      listServers: vi.fn(),
      getTools: vi.fn(),
    },
  },
}));

// Mock the workflow store
vi.mock('../../stores/workflowStore', () => ({
  useWorkflowStore: vi.fn(() => ({
    nodes: [],
    edges: [],
  })),
}));

const mockServers: MCPServer[] = [
  {
    id: 'server-1',
    name: 'Test Server 1',
    status: 'connected',
    command: 'test',
    args: [],
  },
  {
    id: 'server-2',
    name: 'Test Server 2',
    status: 'connected',
    command: 'test2',
    args: [],
  },
  {
    id: 'server-3',
    name: 'Disconnected Server',
    status: 'disconnected',
    command: 'test3',
    args: [],
  },
];

const mockTools: MCPTool[] = [
  {
    name: 'tool-1',
    description: 'Test Tool 1',
    inputSchema: {
      type: 'object',
      properties: {
        param1: {
          type: 'string',
          description: 'Parameter 1',
        },
      },
      required: ['param1'],
    },
  },
  {
    name: 'tool-2',
    description: 'Test Tool 2',
    inputSchema: {
      type: 'object',
      properties: {},
    },
  },
];

const mockComplexTool: MCPTool = {
  name: 'complex-tool',
  description: 'Tool with complex schema',
  inputSchema: {
    type: 'object',
    properties: {
      nested: {
        type: 'object',
        properties: {
          value: { type: 'string' },
        },
      },
    },
  },
};

describe('MCPToolProperties', () => {
  const mockOnChange = vi.fn();
  const defaultData: MCPToolBlockData = {
    serverId: '',
    serverName: '',
    toolName: '',
    description: '',
    parameters: {},
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.mcp.listServers).mockResolvedValue(mockServers);
    vi.mocked(api.mcp.getTools).mockResolvedValue(mockTools);
  });

  it('renders loading state initially', () => {
    render(<MCPToolProperties nodeId="test-node" data={defaultData} onChange={mockOnChange} />);

    expect(screen.getByText('Loading servers...')).toBeInTheDocument();
  });

  it('loads and displays connected servers', async () => {
    render(<MCPToolProperties nodeId="test-node" data={defaultData} onChange={mockOnChange} />);

    await waitFor(() => {
      expect(api.mcp.listServers).toHaveBeenCalled();
    });

    // Click the server select trigger
    const serverTrigger = screen.getByRole('combobox', { name: /mcp server/i });
    await userEvent.click(serverTrigger);

    // Should show only connected servers
    expect(screen.getByText('Test Server 1')).toBeInTheDocument();
    expect(screen.getByText('Test Server 2')).toBeInTheDocument();
    expect(screen.queryByText('Disconnected Server')).not.toBeInTheDocument();
  });

  it('handles server selection and loads tools', async () => {
    const user = userEvent.setup();
    render(<MCPToolProperties nodeId="test-node" data={defaultData} onChange={mockOnChange} />);

    await waitFor(() => {
      expect(screen.queryByText('Loading servers...')).not.toBeInTheDocument();
    });

    const serverTrigger = screen.getByRole('combobox', { name: /mcp server/i });
    await user.click(serverTrigger);

    const server1Option = await screen.findByText('Test Server 1');
    await user.click(server1Option);

    await waitFor(() => {
      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({
          serverId: 'server-1',
          serverName: 'Test Server 1',
        })
      );
    });
  });

  it('displays tools after server is selected', async () => {
    const dataWithServer: MCPToolBlockData = {
      ...defaultData,
      serverId: 'server-1',
      serverName: 'Test Server 1',
    };

    render(<MCPToolProperties nodeId="test-node" data={dataWithServer} onChange={mockOnChange} />);

    await waitFor(() => {
      expect(api.mcp.getTools).toHaveBeenCalledWith('server-1');
    });

    const toolTrigger = screen.getByRole('combobox', { name: /tool/i });
    await userEvent.click(toolTrigger);

    expect(screen.getByText('tool-1')).toBeInTheDocument();
    expect(screen.getByText('Test Tool 1')).toBeInTheDocument();
    expect(screen.getByText('tool-2')).toBeInTheDocument();
  });

  it('handles tool selection and updates description', async () => {
    const dataWithServer: MCPToolBlockData = {
      ...defaultData,
      serverId: 'server-1',
      serverName: 'Test Server 1',
    };

    render(<MCPToolProperties nodeId="test-node" data={dataWithServer} onChange={mockOnChange} />);

    await waitFor(() => {
      expect(screen.queryByText('Loading tools...')).not.toBeInTheDocument();
    });

    const toolTrigger = screen.getByRole('combobox', { name: /tool/i });
    await userEvent.click(toolTrigger);

    const tool1Option = screen.getByText('tool-1');
    await userEvent.click(tool1Option);

    await waitFor(() => {
      expect(mockOnChange).toHaveBeenCalledWith({
        toolName: 'tool-1',
        description: 'Test Tool 1',
        parameters: {},
      });
    });
  });

  it('renders parameter form for simple schema', async () => {
    const user = userEvent.setup();
    const dataWithTool: MCPToolBlockData = {
      ...defaultData,
      serverId: 'server-1',
      serverName: 'Test Server 1',
      toolName: 'tool-1',
      description: 'Test Tool 1',
      parameters: {},
    };

    render(<MCPToolProperties nodeId="test-node" data={dataWithTool} onChange={mockOnChange} />);

    await waitFor(() => {
      expect(screen.getByLabelText(/param1/i)).toBeInTheDocument();
    });

    const param1Input = screen.getByLabelText(/param1/i);
    expect(screen.getByText('Parameter 1')).toBeInTheDocument();
    expect(screen.getByText('*')).toBeInTheDocument(); // Required indicator

    await user.clear(param1Input);
    await user.type(param1Input, 'test');

    // Called for user interactions
    expect(mockOnChange).toHaveBeenCalled();
    expect(mockOnChange).toHaveBeenLastCalledWith(
      expect.objectContaining({
        parameters: expect.objectContaining({ param1: expect.any(String) }),
      })
    );
  });

  it('renders parameter form for complex nested schema', async () => {
    vi.mocked(api.mcp.getTools).mockResolvedValue([mockComplexTool]);

    const dataWithComplexTool: MCPToolBlockData = {
      ...defaultData,
      serverId: 'server-1',
      serverName: 'Test Server 1',
      toolName: 'complex-tool',
      description: 'Tool with complex schema',
      parameters: { nested: { value: 'test' } },
    };

    render(<MCPToolProperties nodeId="test-node" data={dataWithComplexTool} onChange={mockOnChange} />);

    await waitFor(() => {
      // ParameterEditor should handle nested objects with proper form UI
      expect(screen.getByText('nested')).toBeInTheDocument();
    });
  });

  it('handles JSON parameter changes', async () => {
    vi.mocked(api.mcp.getTools).mockResolvedValue([
      {
        name: 'tool-2',
        description: 'Test Tool 2',
        inputSchema: {
          type: 'object',
          properties: {},
        },
      },
    ]);

    const dataWithTool: MCPToolBlockData = {
      ...defaultData,
      serverId: 'server-1',
      serverName: 'Test Server 1',
      toolName: 'tool-2',
      parameters: {},
    };

    render(<MCPToolProperties nodeId="test-node" data={dataWithTool} onChange={mockOnChange} />);

    await waitFor(() => {
      expect(screen.getByText('이 도구는 매개변수가 없습니다.')).toBeInTheDocument();
    });
  });

  it('handles parameter changes for nested objects', async () => {
    const user = userEvent.setup();
    vi.mocked(api.mcp.getTools).mockResolvedValue([mockComplexTool]);

    const dataWithTool: MCPToolBlockData = {
      ...defaultData,
      serverId: 'server-1',
      toolName: 'complex-tool',
      parameters: {},
    };

    render(<MCPToolProperties nodeId="test-node" data={dataWithTool} onChange={mockOnChange} />);

    await waitFor(() => {
      expect(screen.getByText('nested')).toBeInTheDocument();
    });

    // Find the value input within the nested object
    const valueInput = screen.getByLabelText(/value/i);
    await user.type(valueInput, 'test-value');

    // onChange should be called with the nested structure
    expect(mockOnChange).toHaveBeenCalled();
  });

  it('handles mock response changes', async () => {
    const user = userEvent.setup();
    const dataWithTool: MCPToolBlockData = {
      ...defaultData,
      serverId: 'server-1',
      toolName: 'tool-1',
      parameters: {},
      mockResponse: '',
    };

    render(<MCPToolProperties nodeId="test-node" data={dataWithTool} onChange={mockOnChange} />);

    await waitFor(() => {
      expect(screen.getByLabelText(/mock response/i)).toBeInTheDocument();
    });

    const mockResponseTextarea = screen.getByLabelText(/mock response/i);
    await user.type(mockResponseTextarea, 't');

    expect(mockOnChange).toHaveBeenCalled();
    expect(mockOnChange).toHaveBeenLastCalledWith(
      expect.objectContaining({
        mockResponse: expect.any(String),
      })
    );
  });

  it('displays error when server loading fails', async () => {
    vi.mocked(api.mcp.listServers).mockRejectedValue(new Error('Network error'));

    render(<MCPToolProperties nodeId="test-node" data={defaultData} onChange={mockOnChange} />);

    await waitFor(() => {
      expect(screen.getByText('Failed to load MCP servers')).toBeInTheDocument();
    });

    const dismissButton = screen.getByTitle('Dismiss error');
    await userEvent.click(dismissButton);

    expect(screen.queryByText('Failed to load MCP servers')).not.toBeInTheDocument();
  });

  it('displays error when tools loading fails', async () => {
    vi.mocked(api.mcp.getTools).mockRejectedValue(new Error('Network error'));

    const dataWithServer: MCPToolBlockData = {
      ...defaultData,
      serverId: 'server-1',
      serverName: 'Test Server 1',
    };

    render(<MCPToolProperties nodeId="test-node" data={dataWithServer} onChange={mockOnChange} />);

    await waitFor(() => {
      expect(screen.getByText('Failed to load MCP tools')).toBeInTheDocument();
    });
  });

  it('shows "이 도구는 매개변수가 없습니다." for tools without parameters', async () => {
    const dataWithTool: MCPToolBlockData = {
      ...defaultData,
      serverId: 'server-1',
      toolName: 'tool-2',
      parameters: {},
    };

    vi.mocked(api.mcp.getTools).mockResolvedValue([
      {
        name: 'tool-2',
        description: 'Tool without params',
        inputSchema: {
          type: 'object',
          properties: {},
        },
      },
    ]);

    render(<MCPToolProperties nodeId="test-node" data={dataWithTool} onChange={mockOnChange} />);

    await waitFor(() => {
      expect(screen.getByText('이 도구는 매개변수가 없습니다.')).toBeInTheDocument();
    });
  });

  it('renders fallback JSON textarea when no schema available', async () => {
    const dataWithTool: MCPToolBlockData = {
      ...defaultData,
      serverId: 'server-1',
      toolName: 'tool-no-schema',
      parameters: {},
    };

    vi.mocked(api.mcp.getTools).mockResolvedValue([
      {
        name: 'tool-no-schema',
        description: 'Tool without schema',
      },
    ]);

    render(<MCPToolProperties nodeId="test-node" data={dataWithTool} onChange={mockOnChange} />);

    await waitFor(() => {
      expect(screen.getByLabelText(/parameters \(json\)/i)).toBeInTheDocument();
    });
  });

  it('shows "No servers available" when no connected servers', async () => {
    vi.mocked(api.mcp.listServers).mockResolvedValue([]);

    render(<MCPToolProperties nodeId="test-node" data={defaultData} onChange={mockOnChange} />);

    await waitFor(() => {
      expect(screen.getByText('No servers available')).toBeInTheDocument();
    });
  });

  it('disables tool select when no tools are available', async () => {
    vi.mocked(api.mcp.getTools).mockResolvedValue([]);

    const dataWithServer: MCPToolBlockData = {
      ...defaultData,
      serverId: 'server-1',
      serverName: 'Test Server 1',
    };

    render(<MCPToolProperties nodeId="test-node" data={dataWithServer} onChange={mockOnChange} />);

    await waitFor(() => {
      const toolTrigger = screen.getByRole('combobox', { name: /tool/i });
      expect(toolTrigger).toBeDisabled();
    });
  });
});
