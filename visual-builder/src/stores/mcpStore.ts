/**
 * Zustand store for MCP server state
 *
 * Manages MCP server connections, tool discovery, and server
 * lifecycle operations.
 */

import { create } from 'zustand';
import type { MCPServer, MCPServerCreate } from '../types';
import { api, ApiError } from '../services/api';

/**
 * MCP store state and actions interface
 */
interface MCPState {
  /** List of configured MCP servers */
  servers: MCPServer[];
  /** Loading state for async operations */
  isLoading: boolean;
  /** Error message from last failed operation */
  error: string | null;

  /** Fetch all MCP servers */
  fetchServers: () => Promise<void>;
  /** Connect a new MCP server */
  connectServer: (data: MCPServerCreate) => Promise<void>;
  /** Disconnect an MCP server */
  disconnectServer: (id: string) => Promise<void>;
  /** Refresh tools for a specific server */
  refreshTools: (serverId: string) => Promise<void>;
  /** Clear error message */
  clearError: () => void;
}

/**
 * Main MCP store
 */
export const useMCPStore = create<MCPState>((set) => ({
  servers: [],
  isLoading: false,
  error: null,

  fetchServers: async () => {
    set({ isLoading: true, error: null });

    try {
      const servers = await api.mcp.listServers();
      set({ servers, isLoading: false });
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : 'Failed to fetch MCP servers';
      set({ error: message, isLoading: false });
    }
  },

  connectServer: async (data: MCPServerCreate) => {
    set({ isLoading: true, error: null });

    try {
      const server = await api.mcp.connectServer(data);

      set((state) => ({
        servers: [...state.servers, server],
        isLoading: false,
      }));
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : 'Failed to connect MCP server';
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  disconnectServer: async (id: string) => {
    set({ isLoading: true, error: null });

    try {
      await api.mcp.disconnectServer(id);

      set((state) => ({
        servers: state.servers.filter((s) => s.id !== id),
        isLoading: false,
      }));
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : 'Failed to disconnect MCP server';
      set({ error: message, isLoading: false });
    }
  },

  refreshTools: async (serverId: string) => {
    set({ isLoading: true, error: null });

    try {
      const tools = await api.mcp.getTools(serverId);

      set((state) => ({
        servers: state.servers.map((s) =>
          s.id === serverId
            ? { ...s, tools, toolCount: tools.length }
            : s
        ),
        isLoading: false,
      }));
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : 'Failed to refresh tools';
      set({ error: message, isLoading: false });
    }
  },

  clearError: () => {
    set({ error: null });
  },
}));

/**
 * Selector hook for servers list
 */
export const useMCPServers = () => useMCPStore((state) => state.servers);

/**
 * Selector hook for connected servers only
 */
export const useConnectedServers = () =>
  useMCPStore(
    (state) => state.servers.filter((s) => s.status === 'connected'),
    (a, b) => a.length === b.length && a.every((server, i) => server.id === b[i]?.id)
  );

/**
 * Selector hook for loading state
 */
export const useMCPLoading = () => useMCPStore((state) => state.isLoading);

/**
 * Selector hook for error state
 */
export const useMCPError = () => useMCPStore((state) => state.error);
