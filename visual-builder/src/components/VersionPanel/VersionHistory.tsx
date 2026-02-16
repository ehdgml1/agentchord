/**
 * VersionHistory component for Visual Builder
 *
 * Panel to manage workflow version history including viewing,
 * creating, and restoring versions.
 */

import { useState, useEffect, useCallback, memo } from 'react';
import {
  History,
  Plus,
  RotateCcw,
  AlertCircle,
  Loader2,
  Clock,
} from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '../ui/dialog';
import { useVersionStore } from '../../stores/versionStore';
import type { WorkflowVersion } from '../../types';

interface VersionHistoryProps {
  /** Workflow ID to manage versions for */
  workflowId: string;
  /** Callback when a version is restored */
  onVersionRestored?: () => void;
}

export const VersionHistory = memo(function VersionHistory({ workflowId, onVersionRestored }: VersionHistoryProps) {
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isRestoreOpen, setIsRestoreOpen] = useState(false);
  const [versionMessage, setVersionMessage] = useState('');
  const [selectedVersion, setSelectedVersion] = useState<WorkflowVersion | null>(null);

  const {
    versions,
    loading,
    error,
    fetchVersions,
    createVersion,
    restoreVersion,
    clearError,
  } = useVersionStore();

  // Fetch versions on mount or workflow change
  useEffect(() => {
    fetchVersions(workflowId);
  }, [workflowId, fetchVersions]);

  // Handle creating a new version
  const handleCreate = useCallback(async () => {
    if (!versionMessage.trim()) return;

    try {
      await createVersion(workflowId, versionMessage);
      setIsCreateOpen(false);
      setVersionMessage('');
    } catch {
      // Error is handled by the store
    }
  }, [workflowId, versionMessage, createVersion]);

  // Handle restore confirmation
  const handleRestoreConfirm = useCallback(async () => {
    if (!selectedVersion) return;

    try {
      await restoreVersion(workflowId, selectedVersion.id);
      setIsRestoreOpen(false);
      setSelectedVersion(null);
      onVersionRestored?.();
    } catch {
      // Error is handled by the store
    }
  }, [workflowId, selectedVersion, restoreVersion, onVersionRestored]);

  // Open restore dialog
  const handleRestore = useCallback((version: WorkflowVersion) => {
    setSelectedVersion(version);
    setIsRestoreOpen(true);
  }, []);

  return (
    <div className="h-full flex flex-col bg-background">
      {/* Header */}
      <div className="p-4 border-b flex items-center justify-between">
        <div className="flex items-center gap-2">
          <History className="w-5 h-5 text-indigo-600" />
          <h2 className="font-semibold">Version History</h2>
        </div>
        <Button size="sm" onClick={() => setIsCreateOpen(true)}>
          <Plus className="w-4 h-4 mr-1" />
          Create Version
        </Button>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="mx-4 mt-4 p-3 bg-red-50 border border-red-200 rounded-md flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
          <span className="text-sm text-red-700 flex-1">{error}</span>
          <Button variant="ghost" size="sm" onClick={clearError}>
            Dismiss
          </Button>
        </div>
      )}

      {/* Version List */}
      <div className="flex-1 overflow-auto p-4">
        {loading && versions.length === 0 ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
          </div>
        ) : versions.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <History className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>No versions saved</p>
            <p className="text-sm">
              Create a version to save a snapshot of your workflow
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {versions.map((version) => (
              <VersionItem
                key={version.id}
                version={version}
                onRestore={() => handleRestore(version)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Create Version Dialog */}
      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>Create Version</DialogTitle>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-1.5">
              <Label htmlFor="message">Version Message</Label>
              <Input
                id="message"
                value={versionMessage}
                onChange={(e) => setVersionMessage(e.target.value)}
                placeholder="Describe the changes in this version..."
                autoFocus
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleCreate}
              disabled={loading || !versionMessage.trim()}
            >
              {loading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              Create Version
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Restore Confirmation Dialog */}
      <Dialog open={isRestoreOpen} onOpenChange={setIsRestoreOpen}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>Restore Version?</DialogTitle>
          </DialogHeader>

          <div className="py-4">
            <p className="text-sm text-muted-foreground mb-4">
              This will replace your current workflow with version{' '}
              <strong>#{selectedVersion?.versionNumber}</strong>. Your current work
              will not be saved.
            </p>
            {selectedVersion && (
              <div className="p-3 bg-gray-50 rounded-md space-y-1">
                <div className="text-sm font-medium">{selectedVersion.message}</div>
                <div className="text-xs text-muted-foreground">
                  {formatRelativeTime(new Date(selectedVersion.createdAt))}
                </div>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setIsRestoreOpen(false)}
            >
              Cancel
            </Button>
            <Button
              onClick={handleRestoreConfirm}
              disabled={loading}
              variant="default"
            >
              {loading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              Restore Version
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
});

/**
 * Individual version item component
 */
interface VersionItemProps {
  version: WorkflowVersion;
  onRestore: () => void;
}

function VersionItem({ version, onRestore }: VersionItemProps) {
  const relativeTime = formatRelativeTime(new Date(version.createdAt));

  return (
    <div className="border rounded-lg p-3 space-y-2 hover:bg-gray-50 transition-colors">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono bg-indigo-100 text-indigo-700 px-1.5 py-0.5 rounded">
              v{version.versionNumber}
            </span>
            <span className="text-xs text-muted-foreground flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {relativeTime}
            </span>
          </div>
          <p className="text-sm font-medium break-words">{version.message}</p>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={onRestore}
          className="flex-shrink-0"
        >
          <RotateCcw className="w-4 h-4" />
        </Button>
      </div>
    </div>
  );
}

/**
 * Format a date as relative time (e.g., "2 hours ago")
 */
function formatRelativeTime(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSeconds = Math.floor(diffMs / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSeconds < 60) {
    return 'just now';
  } else if (diffMinutes < 60) {
    return `${diffMinutes} ${diffMinutes === 1 ? 'minute' : 'minutes'} ago`;
  } else if (diffHours < 24) {
    return `${diffHours} ${diffHours === 1 ? 'hour' : 'hours'} ago`;
  } else if (diffDays < 30) {
    return `${diffDays} ${diffDays === 1 ? 'day' : 'days'} ago`;
  } else {
    return date.toLocaleDateString();
  }
}
