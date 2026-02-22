/**
 * Properties editor for MCP Tool blocks
 *
 * Provides form controls for configuring MCP server connection,
 * tool selection, and parameters.
 */

import { memo, useCallback, useEffect, useState, useMemo } from 'react';
import { useShallow } from 'zustand/react/shallow';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import type { MCPToolBlockData } from '../../types/blocks';
import type { MCPServer, MCPTool } from '../../types/mcp';
import { api } from '../../services/api';
import { ParameterEditor } from './ParameterEditor';
import { useWorkflowStore } from '../../stores/workflowStore';

interface MCPToolPropertiesProps {
  nodeId: string;
  data: MCPToolBlockData;
  onChange: (data: Partial<MCPToolBlockData>) => void;
}

export const MCPToolProperties = memo(function MCPToolProperties({
  nodeId,
  data,
  onChange,
}: MCPToolPropertiesProps) {
  const { nodes, edges } = useWorkflowStore(
    useShallow(s => ({
      nodes: s.nodes,
      edges: s.edges,
    }))
  );

  const [servers, setServers] = useState<MCPServer[]>([]);
  const [tools, setTools] = useState<MCPTool[]>([]);
  const [loadingServers, setLoadingServers] = useState(false);
  const [loadingTools, setLoadingTools] = useState(false);
  const [selectedTool, setSelectedTool] = useState<MCPTool | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Compute upstream template variables — label must match canvas display name
  const templateVars = useMemo(() => {
    const upstreamEdges = edges.filter(e => e.target === nodeId);
    const vars: { label: string; value: string }[] = [];
    for (const edge of upstreamEdges) {
      const sourceNode = nodes.find(n => n.id === edge.source);
      if (!sourceNode) continue;
      // Match the display name shown on the canvas for each node type
      const nodeType = sourceNode.type;
      const d = sourceNode.data;
      const nodeName = nodeType === 'mcp_tool'
        ? (d?.toolName || d?.name || d?.label || sourceNode.id)
        : (d?.name || d?.label || sourceNode.id);
      // Add .output reference for all upstream nodes
      vars.push({ label: `${nodeName}.output`, value: `{{${sourceNode.id}.output}}` });
      // If it's an Agent with outputFields, add field-level vars
      if (d?.outputFields && Array.isArray(d.outputFields)) {
        for (const field of d.outputFields) {
          vars.push({ label: `${nodeName}.${field.name}`, value: `{{${sourceNode.id}.${field.name}}}` });
        }
      }
    }
    return vars;
  }, [nodes, edges, nodeId]);

  // Fetch servers on mount
  useEffect(() => {
    const fetchServers = async () => {
      setLoadingServers(true);
      setError(null);
      try {
        const serverList = await api.mcp.listServers();
        setServers(serverList.filter((s) => s.status === 'connected'));
      } catch (err) {
        const message = 'Failed to load MCP servers';
        setError(message);
        if (import.meta.env.DEV) console.error(message, err);
      } finally {
        setLoadingServers(false);
      }
    };

    fetchServers();
  }, []);

  // Fetch tools when server changes
  useEffect(() => {
    if (!data.serverId) {
      setTools([]);
      setError(null);
      return;
    }

    const fetchTools = async () => {
      setLoadingTools(true);
      setError(null);
      try {
        const toolList = await api.mcp.getTools(data.serverId);
        setTools(toolList);
      } catch (err) {
        const message = 'Failed to load MCP tools';
        setError(message);
        if (import.meta.env.DEV) console.error(message, err);
        setTools([]);
      } finally {
        setLoadingTools(false);
      }
    };

    fetchTools();
  }, [data.serverId]);

  // Update selected tool when tool name changes
  useEffect(() => {
    if (data.toolName && tools.length > 0) {
      const tool = tools.find((t) => t.name === data.toolName);
      setSelectedTool(tool || null);
    } else {
      setSelectedTool(null);
    }
  }, [data.toolName, tools]);

  const handleServerChange = useCallback(
    (serverId: string) => {
      const server = servers.find((s) => s.id === serverId);
      onChange({
        serverId,
        serverName: server?.name || '',
        toolName: '',
        description: '',
        parameters: {},
      });
    },
    [onChange, servers]
  );

  const handleToolChange = useCallback(
    (toolName: string) => {
      const tool = tools.find((t) => t.name === toolName);
      onChange({
        toolName,
        description: tool?.description || '',
        parameters: {},
      });
    },
    [onChange, tools]
  );

  const handleParametersChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      try {
        const parsed = JSON.parse(e.target.value);
        onChange({ parameters: parsed });
      } catch {
        // Invalid JSON, don't update
      }
    },
    [onChange]
  );

  const handleMockResponseChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      onChange({ mockResponse: e.target.value });
    },
    [onChange]
  );

  const renderParameterForm = () => {
    if (!selectedTool?.inputSchema) {
      return (
        <div className="space-y-2">
          <Label htmlFor="parameters">Parameters (JSON)</Label>
          <Textarea
            id="parameters"
            value={JSON.stringify(data.parameters || {}, null, 2)}
            onChange={handleParametersChange}
            placeholder='{\n  "key": "value"\n}'
            rows={6}
            className="font-mono text-sm"
          />
        </div>
      );
    }

    return (
      <ParameterEditor
        schema={selectedTool.inputSchema}
        value={data.parameters || {}}
        onChange={(params) => onChange({ parameters: params })}
        templateVars={templateVars}
      />
    );
  };

  return (
    <div className="space-y-4">
      {/* Error display */}
      {error && (
        <div className="flex items-start gap-2 p-3 rounded-md bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800">
          <div className="flex-1">
            <p className="text-sm text-red-700 dark:text-red-400">{error}</p>
          </div>
          <button
            onClick={() => setError(null)}
            className="text-red-500 hover:text-red-700 text-sm font-medium"
            title="Dismiss error"
          >
            Dismiss
          </button>
        </div>
      )}

      <div className="space-y-2">
        <Label htmlFor="server">MCP Server</Label>
        <Select
          value={data.serverId || ''}
          onValueChange={handleServerChange}
          disabled={loadingServers || servers.length === 0}
        >
          <SelectTrigger id="server">
            <SelectValue
              placeholder={
                loadingServers
                  ? 'Loading servers...'
                  : servers.length === 0
                  ? 'No servers available'
                  : 'Select a server'
              }
            />
          </SelectTrigger>
          <SelectContent>
            {servers.map((server) => (
              <SelectItem key={server.id} value={server.id}>
                {server.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {data.serverId && (
        <div className="space-y-2">
          <Label htmlFor="tool">Tool</Label>
          <Select
            value={data.toolName || ''}
            onValueChange={handleToolChange}
            disabled={loadingTools || tools.length === 0}
          >
            <SelectTrigger id="tool">
              <SelectValue
                placeholder={
                  loadingTools
                    ? 'Loading tools...'
                    : tools.length === 0
                    ? 'No tools available'
                    : 'Select a tool'
                }
              />
            </SelectTrigger>
            <SelectContent>
              {tools.map((tool) => (
                <SelectItem key={tool.name} value={tool.name}>
                  <div className="flex flex-col">
                    <span>{tool.name}</span>
                    {tool.description && (
                      <span className="text-xs text-muted-foreground">
                        {tool.description}
                      </span>
                    )}
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

      {data.toolName && selectedTool && (
        <>
          {renderParameterForm()}

          <div className="space-y-2">
            <Label htmlFor="mockResponse">Mock Response (Optional)</Label>
            <Textarea
              id="mockResponse"
              value={(data.mockResponse as string) || ''}
              onChange={handleMockResponseChange}
              placeholder='{\n  "result": "mock data"\n}'
              rows={4}
              className="font-mono text-sm"
            />
            <p className="text-xs text-muted-foreground">
              Custom mock response for testing (JSON format)
            </p>
          </div>
        </>
      )}
    </div>
  );
});
