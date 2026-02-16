/**
 * MCP (Model Context Protocol) type definitions
 *
 * This module defines types for MCP server connections, tools,
 * and server management operations.
 */

/**
 * MCP server connection status
 */
export type MCPServerStatus = 'connected' | 'disconnected' | 'connecting' | 'error';

/**
 * MCP tool definition
 *
 * Represents a single tool provided by an MCP server
 * with its metadata and input requirements.
 */
export interface MCPTool {
  /** ID of the server providing this tool */
  serverId: string;
  /** Tool name identifier */
  name: string;
  /** Human-readable description of what the tool does */
  description: string;
  /** JSON Schema defining the tool's input parameters */
  inputSchema: Record<string, unknown>;
}

/**
 * MCP server configuration and state
 *
 * Contains all information about an MCP server connection
 * including its configuration, status, and available tools.
 */
export interface MCPServer {
  /** Unique server ID */
  id: string;
  /** Human-readable server name */
  name: string;
  /** Command to execute to start the server */
  command: string;
  /** Command-line arguments for the server */
  args: string[];
  /** Current connection status */
  status: MCPServerStatus;
  /** Number of tools provided by this server */
  toolCount: number;
  /** ISO timestamp of last successful connection, null if never connected */
  lastConnectedAt: string | null;
  /** Array of tools provided by this server */
  tools: MCPTool[];
}

/**
 * MCP server creation request
 *
 * Data required to configure and connect a new MCP server.
 */
export interface MCPServerCreate {
  /** Human-readable server name */
  name: string;
  /** Command to execute to start the server */
  command: string;
  /** Command-line arguments for the server */
  args: string[];
  /** Optional environment variables for the server process */
  env?: Record<string, string>;
}
