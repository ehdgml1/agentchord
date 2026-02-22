/**
 * MCPToolSelector - Multi-select component for attaching MCP tools to agents.
 * Displays catalog servers as checkboxes grouped by category.
 */
import { memo, useCallback, useMemo } from 'react';
import { Wrench } from 'lucide-react';
import { MCP_CATALOG } from '../../data/mcpCatalog';
import { useMCPStore } from '../../stores/mcpStore';

interface MCPToolSelectorProps {
  selectedTools: string[];
  onChange: (tools: string[]) => void;
}

export const MCPToolSelector = memo(function MCPToolSelector({
  selectedTools,
  onChange,
}: MCPToolSelectorProps) {
  const servers = useMCPStore((state) => state.servers);

  const grouped = useMemo(() => {
    const filtered = MCP_CATALOG.filter((server) =>
      servers.some((s) => s.name.toLowerCase() === server.name.toLowerCase())
    );

    const map = new Map<string, typeof MCP_CATALOG>();
    for (const server of filtered) {
      const list = map.get(server.category) || [];
      list.push(server);
      map.set(server.category, list);
    }
    return map;
  }, [servers]);

  const handleToggle = useCallback(
    (serverId: string) => {
      const next = selectedTools.includes(serverId)
        ? selectedTools.filter((id) => id !== serverId)
        : [...selectedTools, serverId];
      onChange(next);
    },
    [selectedTools, onChange]
  );

  return (
    <div className="space-y-3">
      <label className="text-sm font-medium flex items-center gap-1.5">
        <Wrench className="w-3.5 h-3.5" />
        MCP Tools
      </label>
      {grouped.size === 0 ? (
        <div className="border rounded-md p-4 text-sm text-muted-foreground text-center">
          설치된 MCP 서버가 없습니다. Add Server에서 서버를 추가해주세요.
        </div>
      ) : (
        <div className="border rounded-md max-h-48 overflow-y-auto">
          {Array.from(grouped.entries()).map(([category, servers]) => (
            <div key={category}>
              <div className="px-2 py-1 text-xs font-semibold text-muted-foreground bg-muted/50 sticky top-0">
                {category}
              </div>
              {servers.map((server) => (
                <label
                  key={server.id}
                  className="flex items-center gap-2 px-2 py-1.5 hover:bg-accent cursor-pointer text-sm"
                >
                  <input
                    type="checkbox"
                    checked={selectedTools.includes(server.id)}
                    onChange={() => handleToggle(server.id)}
                    className="rounded border-gray-300"
                  />
                  <span className="truncate">{server.name}</span>
                </label>
              ))}
            </div>
          ))}
        </div>
      )}
      {selectedTools.length > 0 && (
        <p className="text-xs text-muted-foreground">
          {selectedTools.length} tool{selectedTools.length > 1 ? 's' : ''} selected
        </p>
      )}
    </div>
  );
});
