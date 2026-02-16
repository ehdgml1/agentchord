import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MCPHub } from './MCPHub';
import { useMCPStore } from '../../stores/mcpStore';
import type { MCPServer } from '../../types/mcp';

const mockFetchServers = vi.fn();
const mockDisconnectServer = vi.fn();

vi.mock('../../stores/mcpStore', () => ({
  useMCPStore: vi.fn((selector) => {
    const state = {
      servers: [],
      disconnectServer: mockDisconnectServer,
      fetchServers: mockFetchServers,
    };
    return typeof selector === 'function' ? selector(state) : state;
  }),
}));

// Mock MCPMarketplace
vi.mock('./MCPMarketplace', () => ({
  MCPMarketplace: ({ onClose }: { onClose: () => void }) => (
    <div data-testid="mcp-marketplace">
      MCP Marketplace
      <button onClick={onClose}>Close</button>
    </div>
  ),
}));

describe('MCPHub', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders MCP Servers heading', () => {
    render(<MCPHub />);
    expect(screen.getByText('MCP Servers')).toBeInTheDocument();
  });

  it('shows empty state when no servers', () => {
    render(<MCPHub />);
    expect(screen.getByText('No servers connected')).toBeInTheDocument();
  });

  it('shows Add Server button', () => {
    render(<MCPHub />);
    expect(screen.getByText('Add Server')).toBeInTheDocument();
  });

  it('calls fetchServers on mount', () => {
    render(<MCPHub />);
    expect(mockFetchServers).toHaveBeenCalled();
  });

  it('displays connected servers', () => {
    const mockServers: MCPServer[] = [
      {
        id: 'srv-1',
        name: 'Test Server',
        command: 'test-cmd',
        args: [],
        status: 'connected',
        toolCount: 2,
        lastConnectedAt: null,
        tools: [
          { serverId: 'srv-1', name: 'tool_a', description: 'Tool A desc', inputSchema: {} },
          { serverId: 'srv-1', name: 'tool_b', description: 'Tool B desc', inputSchema: {} },
        ],
      },
    ];

    vi.mocked(useMCPStore).mockImplementation((selector: any) => {
      const state = {
        servers: mockServers,
        disconnectServer: mockDisconnectServer,
        fetchServers: mockFetchServers,
      };
      return typeof selector === 'function' ? selector(state) : state;
    });

    render(<MCPHub />);
    expect(screen.getByText('Test Server')).toBeInTheDocument();
    expect(screen.getByText('2 tools')).toBeInTheDocument();
  });

  it('displays singular "tool" for single tool', () => {
    const mockServers: MCPServer[] = [
      {
        id: 'srv-1',
        name: 'Single Tool Server',
        command: 'test-cmd',
        args: [],
        status: 'connected',
        toolCount: 1,
        lastConnectedAt: null,
        tools: [
          { serverId: 'srv-1', name: 'only_tool', description: 'Only tool', inputSchema: {} },
        ],
      },
    ];

    vi.mocked(useMCPStore).mockImplementation((selector: any) => {
      const state = {
        servers: mockServers,
        disconnectServer: mockDisconnectServer,
        fetchServers: mockFetchServers,
      };
      return typeof selector === 'function' ? selector(state) : state;
    });

    render(<MCPHub />);
    expect(screen.getByText('1 tool')).toBeInTheDocument();
  });

  it('shows connected status icon', () => {
    const mockServers: MCPServer[] = [
      {
        id: 'srv-1',
        name: 'Connected Server',
        command: 'test-cmd',
        args: [],
        status: 'connected',
        toolCount: 0,
        lastConnectedAt: null,
        tools: [],
      },
    ];

    vi.mocked(useMCPStore).mockImplementation((selector: any) => {
      const state = {
        servers: mockServers,
        disconnectServer: mockDisconnectServer,
        fetchServers: mockFetchServers,
      };
      return typeof selector === 'function' ? selector(state) : state;
    });

    const { container } = render(<MCPHub />);
    expect(container.querySelector('.bg-green-500')).toBeInTheDocument();
  });

  it('shows connecting status icon with pulse', () => {
    const mockServers: MCPServer[] = [
      {
        id: 'srv-1',
        name: 'Connecting Server',
        command: 'test-cmd',
        args: [],
        status: 'connecting',
        toolCount: 0,
        lastConnectedAt: null,
        tools: [],
      },
    ];

    vi.mocked(useMCPStore).mockImplementation((selector: any) => {
      const state = {
        servers: mockServers,
        disconnectServer: mockDisconnectServer,
        fetchServers: mockFetchServers,
      };
      return typeof selector === 'function' ? selector(state) : state;
    });

    const { container } = render(<MCPHub />);
    const icon = container.querySelector('.bg-yellow-500');
    expect(icon).toBeInTheDocument();
    expect(icon).toHaveClass('animate-pulse');
  });

  it('shows error status icon', () => {
    const mockServers: MCPServer[] = [
      {
        id: 'srv-1',
        name: 'Error Server',
        command: 'test-cmd',
        args: [],
        status: 'error',
        toolCount: 0,
        lastConnectedAt: null,
        tools: [],
      },
    ];

    vi.mocked(useMCPStore).mockImplementation((selector: any) => {
      const state = {
        servers: mockServers,
        disconnectServer: mockDisconnectServer,
        fetchServers: mockFetchServers,
      };
      return typeof selector === 'function' ? selector(state) : state;
    });

    const { container } = render(<MCPHub />);
    expect(container.querySelector('.bg-red-500')).toBeInTheDocument();
  });

  it('shows disconnected status icon', () => {
    const mockServers: MCPServer[] = [
      {
        id: 'srv-1',
        name: 'Disconnected Server',
        command: 'test-cmd',
        args: [],
        status: 'disconnected',
        toolCount: 0,
        lastConnectedAt: null,
        tools: [],
      },
    ];

    vi.mocked(useMCPStore).mockImplementation((selector: any) => {
      const state = {
        servers: mockServers,
        disconnectServer: mockDisconnectServer,
        fetchServers: mockFetchServers,
      };
      return typeof selector === 'function' ? selector(state) : state;
    });

    const { container } = render(<MCPHub />);
    expect(container.querySelector('.bg-gray-400')).toBeInTheDocument();
  });

  it('expands server to show tools', async () => {
    const user = userEvent.setup();
    const mockServers: MCPServer[] = [
      {
        id: 'srv-1',
        name: 'Test Server',
        command: 'test-cmd',
        args: [],
        status: 'connected',
        toolCount: 2,
        lastConnectedAt: null,
        tools: [
          { serverId: 'srv-1', name: 'tool_a', description: 'Tool A desc', inputSchema: {} },
          { serverId: 'srv-1', name: 'tool_b', description: 'Tool B desc', inputSchema: {} },
        ],
      },
    ];

    vi.mocked(useMCPStore).mockImplementation((selector: any) => {
      const state = {
        servers: mockServers,
        disconnectServer: mockDisconnectServer,
        fetchServers: mockFetchServers,
      };
      return typeof selector === 'function' ? selector(state) : state;
    });

    render(<MCPHub />);

    const serverButton = screen.getByText('Test Server');
    await user.click(serverButton);

    expect(screen.getByText('tool_a')).toBeInTheDocument();
    expect(screen.getByText('tool_b')).toBeInTheDocument();
  });

  it('collapses server when clicked again', async () => {
    const user = userEvent.setup();
    const mockServers: MCPServer[] = [
      {
        id: 'srv-1',
        name: 'Test Server',
        command: 'test-cmd',
        args: [],
        status: 'connected',
        toolCount: 2,
        lastConnectedAt: null,
        tools: [
          { serverId: 'srv-1', name: 'tool_a', description: 'Tool A desc', inputSchema: {} },
          { serverId: 'srv-1', name: 'tool_b', description: 'Tool B desc', inputSchema: {} },
        ],
      },
    ];

    vi.mocked(useMCPStore).mockImplementation((selector: any) => {
      const state = {
        servers: mockServers,
        disconnectServer: mockDisconnectServer,
        fetchServers: mockFetchServers,
      };
      return typeof selector === 'function' ? selector(state) : state;
    });

    render(<MCPHub />);

    const serverButton = screen.getByText('Test Server');
    await user.click(serverButton);
    expect(screen.getByText('tool_a')).toBeInTheDocument();

    await user.click(serverButton);
    expect(screen.queryByText('tool_a')).not.toBeInTheDocument();
  });

  it('shows "No tools available" when server has no tools', async () => {
    const user = userEvent.setup();
    const mockServers: MCPServer[] = [
      {
        id: 'srv-1',
        name: 'Empty Server',
        command: 'test-cmd',
        args: [],
        status: 'connected',
        toolCount: 0,
        lastConnectedAt: null,
        tools: [],
      },
    ];

    vi.mocked(useMCPStore).mockImplementation((selector: any) => {
      const state = {
        servers: mockServers,
        disconnectServer: mockDisconnectServer,
        fetchServers: mockFetchServers,
      };
      return typeof selector === 'function' ? selector(state) : state;
    });

    render(<MCPHub />);

    const serverButton = screen.getByText('Empty Server');
    await user.click(serverButton);

    expect(screen.getByText('No tools available')).toBeInTheDocument();
  });

  it('opens marketplace when Add Server button clicked', async () => {
    const user = userEvent.setup();
    render(<MCPHub />);

    const addButton = screen.getByText('Add Server');
    await user.click(addButton);

    expect(await screen.findByTestId('mcp-marketplace')).toBeInTheDocument();
  });

  it('opens marketplace when plus icon clicked', async () => {
    const user = userEvent.setup();
    render(<MCPHub />);

    // Find the plus icon button at the top
    const buttons = screen.getAllByRole('button');
    const plusButton = buttons[0]; // First button should be the plus icon

    await user.click(plusButton);

    expect(await screen.findByTestId('mcp-marketplace')).toBeInTheDocument();
  });

  it('renders tools as draggable', async () => {
    const user = userEvent.setup();
    const mockServers: MCPServer[] = [
      {
        id: 'srv-1',
        name: 'Test Server',
        command: 'test-cmd',
        args: [],
        status: 'connected',
        toolCount: 1,
        lastConnectedAt: null,
        tools: [
          { serverId: 'srv-1', name: 'draggable_tool', description: 'A draggable tool', inputSchema: {} },
        ],
      },
    ];

    vi.mocked(useMCPStore).mockImplementation((selector: any) => {
      const state = {
        servers: mockServers,
        disconnectServer: mockDisconnectServer,
        fetchServers: mockFetchServers,
      };
      return typeof selector === 'function' ? selector(state) : state;
    });

    render(<MCPHub />);

    const serverButton = screen.getByText('Test Server');
    await user.click(serverButton);

    const toolElement = screen.getByText('draggable_tool').parentElement;
    expect(toolElement).toHaveAttribute('draggable');
  });
});
