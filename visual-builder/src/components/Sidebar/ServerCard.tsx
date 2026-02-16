import { Star, ShieldCheck, AlertCircle, Download } from 'lucide-react';
import { Button, Badge, Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../ui';
import { type MCPServerInfo } from '../../data/mcpCatalog';

interface ServerCardProps {
  server: MCPServerInfo;
  isInstalled: boolean;
  onInstall: (server: MCPServerInfo) => void;
}

export function ServerCard({ server, isInstalled, onInstall }: ServerCardProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <CardTitle className="flex items-center gap-2 text-base">
              {server.name}
              {server.official && (
                <Badge variant="default" className="gap-1">
                  <ShieldCheck className="w-3 h-3" />
                  Official
                </Badge>
              )}
            </CardTitle>
            <div className="flex items-center gap-3 mt-1">
              <Badge variant="outline" className="text-xs">
                {server.category}
              </Badge>
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <Star className="w-3 h-3 fill-current" />
                {server.stars}
              </div>
            </div>
          </div>
        </div>
        <CardDescription className="mt-2">{server.description}</CardDescription>
      </CardHeader>

      {server.requiredSecrets && server.requiredSecrets.length > 0 && (
        <CardContent>
          <div className="flex items-start gap-2 p-2 rounded-md bg-amber-500/10 border border-amber-500/20">
            <AlertCircle className="w-4 h-4 text-amber-600 mt-0.5 flex-shrink-0" />
            <div className="text-xs text-amber-900 dark:text-amber-100">
              <div className="font-medium mb-1">Required secrets:</div>
              <div className="font-mono text-xs space-y-0.5">
                {server.requiredSecrets.map((secret) => (
                  <div key={secret}>{secret}</div>
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      )}

      <CardFooter>
        <Button
          size="sm"
          className="w-full"
          onClick={() => onInstall(server)}
          disabled={isInstalled}
        >
          {isInstalled ? (
            'Installed'
          ) : (
            <>
              <Download className="w-4 h-4 mr-2" />
              Install
            </>
          )}
        </Button>
      </CardFooter>
    </Card>
  );
}
