import { lazy, memo, Suspense, useCallback, useEffect, useState } from 'react';
import { Plus, ChevronDown, ChevronRight, PowerOff } from 'lucide-react';
import { cn } from '../../lib/utils';
import { Button } from '../ui/button';
import { Dialog, DialogContent } from '../ui/dialog';
import { useMCPStore } from '../../stores/mcpStore';
import type { MCPServer } from '../../types/mcp';

const MCPMarketplace = lazy(() => import('./MCPMarketplace').then(m => ({ default: m.MCPMarketplace })));

interface MCPHubProps {
  className?: string;
}

export const MCPHub = memo(function MCPHub({ className }: MCPHubProps) {
  const { servers, disconnectServer, fetchServers } = useMCPStore();
  const [expandedServers, setExpandedServers] = useState<Set<string>>(new Set());
  const [showMarketplace, setShowMarketplace] = useState(false);

  useEffect(() => {
    fetchServers();
  }, [fetchServers]);

  const toggleServer = useCallback((serverId: string) => {
    setExpandedServers((prev) => {
      const next = new Set(prev);
      if (next.has(serverId)) {
        next.delete(serverId);
      } else {
        next.add(serverId);
      }
      return next;
    });
  }, []);

  const handleDisconnect = useCallback(
    (serverId: string, e: React.MouseEvent) => {
      e.stopPropagation();
      disconnectServer(serverId);
    },
    [disconnectServer]
  );

  const onToolDragStart = useCallback((event: React.DragEvent, tool: MCPServer['tools'][0]) => {
    event.dataTransfer.setData('application/reactflow', 'mcp_tool');
    event.dataTransfer.setData('tool', JSON.stringify(tool));
    event.dataTransfer.effectAllowed = 'move';
  }, []);

  const getStatusIcon = (status: MCPServer['status']) => {
    switch (status) {
      case 'connected':
        return <div className="w-2 h-2 rounded-full bg-green-500" />;
      case 'connecting':
        return <div className="w-2 h-2 rounded-full bg-yellow-500 animate-pulse" />;
      case 'disconnected':
        return <div className="w-2 h-2 rounded-full bg-gray-400" />;
      case 'error':
        return <div className="w-2 h-2 rounded-full bg-red-500" />;
    }
  };

  return (
    <div className={cn('border-t mt-6 pt-4', className)}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-sm text-muted-foreground uppercase tracking-wider">
          MCP Servers
        </h3>
        <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => setShowMarketplace(true)}>
          <Plus className="w-4 h-4" />
        </Button>
      </div>

      <div className="space-y-1">
        {servers.length === 0 ? (
          <p className="text-xs text-muted-foreground py-2">No servers connected</p>
        ) : (
          servers.map((server) => {
            const isExpanded = expandedServers.has(server.id);
            const isConnected = server.status === 'connected';

            return (
              <div key={server.id} className="border rounded-lg overflow-hidden">
                <button
                  onClick={() => toggleServer(server.id)}
                  className={cn(
                    'w-full flex items-center gap-2 p-2 hover:bg-accent transition-colors text-left',
                    isConnected && 'bg-accent/50'
                  )}
                >
                  <div className="flex items-center justify-center w-4 h-4">
                    {isExpanded ? (
                      <ChevronDown className="w-3 h-3" />
                    ) : (
                      <ChevronRight className="w-3 h-3" />
                    )}
                  </div>
                  {getStatusIcon(server.status)}
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium truncate">{server.name}</div>
                    <div className="text-xs text-muted-foreground">
                      {server.toolCount} tool{server.toolCount !== 1 ? 's' : ''}
                    </div>
                  </div>
                  {isConnected && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6 opacity-0 group-hover:opacity-100"
                      onClick={(e) => handleDisconnect(server.id, e)}
                    >
                      <PowerOff className="w-3 h-3" />
                    </Button>
                  )}
                </button>

                {isExpanded && (
                  <div className="border-t bg-muted/30">
                    {server.tools.length === 0 ? (
                      <div className="p-2 text-xs text-muted-foreground">No tools available</div>
                    ) : (
                      <div className="p-1 space-y-1">
                        {server.tools.map((tool) => (
                          <div
                            key={tool.name}
                            draggable
                            onDragStart={(e) => onToolDragStart(e, tool)}
                            className={cn(
                              'px-2 py-1.5 rounded text-xs cursor-grab hover:bg-accent transition-colors',
                              'active:cursor-grabbing'
                            )}
                          >
                            <div className="font-medium">{tool.name}</div>
                            {tool.description && (
                              <div className="text-muted-foreground truncate">{tool.description}</div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      <div className="mt-3">
        <Button variant="outline" size="sm" className="w-full text-xs" onClick={() => setShowMarketplace(true)}>
          <Plus className="w-3 h-3 mr-2" />
          Add Server
        </Button>
      </div>

      <Dialog open={showMarketplace} onOpenChange={setShowMarketplace}>
        <DialogContent className="max-w-3xl h-[80vh]">
          <Suspense fallback={<div className="flex items-center justify-center h-full text-muted-foreground">Loading...</div>}>
            <MCPMarketplace onClose={() => setShowMarketplace(false)} />
          </Suspense>
        </DialogContent>
      </Dialog>
    </div>
  );
});
