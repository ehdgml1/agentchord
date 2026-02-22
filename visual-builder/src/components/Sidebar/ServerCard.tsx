import { useState } from 'react';
import { Star, ShieldCheck, Key, Download, Loader2, Eye, EyeOff } from 'lucide-react';
import { Button, Badge, Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../ui';
import { Input } from '../ui';
import { type MCPServerInfo } from '../../data/mcpCatalog';

interface ServerCardProps {
  server: MCPServerInfo;
  isInstalled: boolean;
  isInstalling?: boolean;
  onInstall: (server: MCPServerInfo, env: Record<string, string>) => void;
}

export function ServerCard({ server, isInstalled, isInstalling, onInstall }: ServerCardProps) {
  const hasSecrets = server.requiredSecrets && server.requiredSecrets.length > 0;
  const [secrets, setSecrets] = useState<Record<string, string>>({});
  const [showSecrets, setShowSecrets] = useState<Record<string, boolean>>({});

  const allSecretsFilled = !hasSecrets || server.requiredSecrets!.every((s) => secrets[s]?.trim());

  const handleSecretChange = (key: string, value: string) => {
    setSecrets((prev) => ({ ...prev, [key]: value }));
  };

  const toggleShowSecret = (key: string) => {
    setShowSecrets((prev) => ({ ...prev, [key]: !prev[key] }));
  };

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

      {hasSecrets && !isInstalled && (
        <CardContent>
          <div className="space-y-2">
            <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
              <Key className="w-3.5 h-3.5" />
              API Keys
            </div>
            {server.requiredSecrets!.map((secret) => (
              <div key={secret} className="space-y-1">
                <label className="text-xs font-mono text-muted-foreground">{secret}</label>
                <div className="relative">
                  <Input
                    type={showSecrets[secret] ? 'text' : 'password'}
                    placeholder={`Enter ${secret}`}
                    value={secrets[secret] || ''}
                    onChange={(e) => handleSecretChange(secret, e.target.value)}
                    className="pr-8 text-xs font-mono h-8"
                  />
                  <button
                    type="button"
                    onClick={() => toggleShowSecret(secret)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  >
                    {showSecrets[secret] ? (
                      <EyeOff className="w-3.5 h-3.5" />
                    ) : (
                      <Eye className="w-3.5 h-3.5" />
                    )}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      )}

      <CardFooter>
        <Button
          size="sm"
          className="w-full"
          onClick={() => onInstall(server, secrets)}
          disabled={isInstalled || isInstalling || !allSecretsFilled}
        >
          {isInstalling ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Installing...
            </>
          ) : isInstalled ? (
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
