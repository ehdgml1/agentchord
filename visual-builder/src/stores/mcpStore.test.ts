import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useMCPStore } from './mcpStore';

vi.mock('../services/api', () => ({
  api: {
    mcp: {
      listServers: vi.fn(),
      connectServer: vi.fn(),
      disconnectServer: vi.fn(),
      getTools: vi.fn(),
    },
  },
  ApiError: class extends Error {
    statusCode: number;
    constructor(message: string, statusCode: number) {
      super(message);
      this.name = 'ApiError';
      this.statusCode = statusCode;
    }
  },
}));

import { api } from '../services/api';
import type { MCPServer, MCPTool } from '../types';

const mockServers: MCPServer[] = [
  {
    id: 's1',
    name: 'Filesystem',
    command: 'npx',
    args: ['-y', '@modelcontextprotocol/server-filesystem', '/tmp'],
    status: 'connected',
    toolCount: 3,
    lastConnectedAt: '2024-01-01T00:00:00Z',
    tools: [],
  },
  {
    id: 's2',
    name: 'Git',
    command: 'npx',
    args: ['-y', '@modelcontextprotocol/server-git'],
    status: 'disconnected',
    toolCount: 0,
    lastConnectedAt: null,
    tools: [],
  },
];

describe('mcpStore', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useMCPStore.setState({
      servers: [],
      isLoading: false,
      error: null,
    });
  });

  describe('fetchServers', () => {
    it('loads servers from API', async () => {
      vi.mocked(api.mcp.listServers).mockResolvedValueOnce(mockServers);

      await useMCPStore.getState().fetchServers();

      expect(useMCPStore.getState().servers).toEqual(mockServers);
      expect(useMCPStore.getState().isLoading).toBe(false);
    });

    it('handles fetch error', async () => {
      vi.mocked(api.mcp.listServers).mockRejectedValueOnce(new Error('Network'));

      await useMCPStore.getState().fetchServers();

      expect(useMCPStore.getState().error).toBe('Failed to fetch MCP servers');
    });

    it('sets loading state during fetch', async () => {
      let resolvePromise: (value: MCPServer[]) => void;
      const promise = new Promise<MCPServer[]>((resolve) => { resolvePromise = resolve; });
      vi.mocked(api.mcp.listServers).mockReturnValueOnce(promise);

      const fetchPromise = useMCPStore.getState().fetchServers();
      expect(useMCPStore.getState().isLoading).toBe(true);

      resolvePromise!([]);
      await fetchPromise;
      expect(useMCPStore.getState().isLoading).toBe(false);
    });
  });

  describe('connectServer', () => {
    it('adds new server to list', async () => {
      const newServer: MCPServer = {
        id: 's3',
        name: 'New Server',
        command: 'node',
        args: ['server.js'],
        status: 'connected',
        toolCount: 0,
        lastConnectedAt: '2024-01-01T00:00:00Z',
        tools: [],
      };
      vi.mocked(api.mcp.connectServer).mockResolvedValueOnce(newServer);

      await useMCPStore.getState().connectServer({ name: 'New Server', command: 'node', args: ['server.js'] });

      expect(useMCPStore.getState().servers).toHaveLength(1);
      expect(useMCPStore.getState().servers[0].name).toBe('New Server');
    });

    it('throws on connect failure', async () => {
      vi.mocked(api.mcp.connectServer).mockRejectedValueOnce(new Error('Bad command'));

      await expect(
        useMCPStore.getState().connectServer({ name: 'Bad', command: 'bad', args: [] })
      ).rejects.toThrow();

      expect(useMCPStore.getState().error).toBe('Failed to connect MCP server');
    });
  });

  describe('disconnectServer', () => {
    it('removes server from list', async () => {
      useMCPStore.setState({ servers: mockServers });
      vi.mocked(api.mcp.disconnectServer).mockResolvedValueOnce(undefined);

      await useMCPStore.getState().disconnectServer('s1');

      expect(useMCPStore.getState().servers).toHaveLength(1);
      expect(useMCPStore.getState().servers[0].id).toBe('s2');
    });

    it('handles disconnect error', async () => {
      useMCPStore.setState({ servers: mockServers });
      vi.mocked(api.mcp.disconnectServer).mockRejectedValueOnce(new Error('Server not found'));

      await useMCPStore.getState().disconnectServer('s1');

      expect(useMCPStore.getState().error).toBe('Failed to disconnect MCP server');
      expect(useMCPStore.getState().servers).toHaveLength(2);
    });
  });

  describe('refreshTools', () => {
    it('updates server tools', async () => {
      useMCPStore.setState({ servers: [mockServers[0]] });
      const mockTools: MCPTool[] = [
        { serverId: 's1', name: 'read', description: 'Read file', inputSchema: { type: 'object', properties: { path: { type: 'string' } } } },
        { serverId: 's1', name: 'write', description: 'Write file', inputSchema: { type: 'object', properties: { path: { type: 'string' }, content: { type: 'string' } } } },
      ];
      vi.mocked(api.mcp.getTools).mockResolvedValueOnce(mockTools);

      await useMCPStore.getState().refreshTools('s1');

      const server = useMCPStore.getState().servers[0];
      expect(server.tools).toEqual(mockTools);
      expect(server.toolCount).toBe(2);
    });

    it('handles refresh error', async () => {
      useMCPStore.setState({ servers: [mockServers[0]] });
      vi.mocked(api.mcp.getTools).mockRejectedValueOnce(new Error('Server disconnected'));

      await useMCPStore.getState().refreshTools('s1');

      expect(useMCPStore.getState().error).toBe('Failed to refresh tools');
    });

    it('only updates the target server', async () => {
      useMCPStore.setState({ servers: mockServers });
      const mockTools: MCPTool[] = [
        { serverId: 's1', name: 'read', description: 'Read file', inputSchema: {} },
      ];
      vi.mocked(api.mcp.getTools).mockResolvedValueOnce(mockTools);

      await useMCPStore.getState().refreshTools('s1');

      const servers = useMCPStore.getState().servers;
      expect(servers[0].tools).toEqual(mockTools);
      expect(servers[0].toolCount).toBe(1);
      expect(servers[1].tools).toEqual([]);
      expect(servers[1].toolCount).toBe(0);
    });
  });

  describe('clearError', () => {
    it('clears error state', () => {
      useMCPStore.setState({ error: 'Some error' });
      useMCPStore.getState().clearError();
      expect(useMCPStore.getState().error).toBeNull();
    });
  });
});
