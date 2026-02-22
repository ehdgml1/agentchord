import { useState, useMemo } from 'react';
import { Search } from 'lucide-react';
import { Input, Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui';
import { MCP_CATALOG, MCP_CATEGORIES, type MCPServerInfo } from '../../data/mcpCatalog';
import { useMCPStore } from '../../stores/mcpStore';
import { ServerCard } from './ServerCard';

interface MCPMarketplaceProps {
  onClose?: () => void;
}

export function MCPMarketplace({ onClose: _onClose }: MCPMarketplaceProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [installingIds, setInstallingIds] = useState<Set<string>>(new Set());
  const { servers, connectServer, error, clearError } = useMCPStore();

  const filteredServers = useMemo(() => {
    return MCP_CATALOG.filter((server) => {
      const matchesSearch =
        server.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        server.description.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesCategory =
        selectedCategory === 'all' || server.category === selectedCategory;

      return matchesSearch && matchesCategory;
    }).sort((a, b) => b.stars - a.stars);
  }, [searchQuery, selectedCategory]);

  const handleInstall = async (server: MCPServerInfo, env: Record<string, string>) => {
    setInstallingIds(prev => new Set(prev).add(server.id));
    try {
      await connectServer({
        name: server.name,
        command: server.command,
        args: server.args,
        env,
      });
    } finally {
      setInstallingIds(prev => {
        const next = new Set(prev);
        next.delete(server.id);
        return next;
      });
    }
  };

  const isInstalled = (serverName: string) => {
    return servers.some(s => s.name.toLowerCase() === serverName.toLowerCase());
  };

  return (
    <div className="flex flex-col h-full min-h-0">
      <div className="p-4 border-b">
        <h2 className="text-lg font-semibold mb-4">MCP Marketplace</h2>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded text-sm flex justify-between items-center mb-4">
            <span>{error}</span>
            <button onClick={clearError} className="text-red-500 hover:text-red-700 ml-2">×</button>
          </div>
        )}

        <div className="space-y-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Search servers..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>

          <Select value={selectedCategory} onValueChange={setSelectedCategory}>
            <SelectTrigger>
              <SelectValue placeholder="All categories" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All categories</SelectItem>
              {MCP_CATEGORIES.map((category) => (
                <SelectItem key={category} value={category}>
                  {category}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        <div className="grid gap-4">
          {filteredServers.map((server) => (
            <ServerCard
              key={server.id}
              server={server}
              isInstalled={isInstalled(server.name)}
              isInstalling={installingIds.has(server.id)}
              onInstall={handleInstall}
            />
          ))}
        </div>

        {filteredServers.length === 0 && (
          <div className="text-center py-8 text-muted-foreground">
            No servers found matching your criteria
          </div>
        )}
      </div>
    </div>
  );
}
