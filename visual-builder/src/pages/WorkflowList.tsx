import { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Trash2, Clock, GitBranch, Search, Copy } from 'lucide-react';
import { Button } from '../components/ui/button';
import { WorkflowListSkeleton } from '../components/ui/skeleton';
import { api } from '../services/api';
import { useWorkflowStore } from '../stores/workflowStore';
import { useAuthStore } from '../stores/authStore';
import { LogOut } from 'lucide-react';
import { toast } from 'sonner';
import type { Workflow } from '../types/workflow';
import { useConfirm } from '../components/ui/confirm-dialog';

interface WorkflowSummary {
  id: string;
  name: string;
  description?: string;
  nodeCount: number;
  updatedAt?: string;
  createdAt?: string;
}

function toSummary(w: Workflow): WorkflowSummary {
  return {
    id: w.id,
    name: w.name || 'Untitled',
    description: w.description || '',
    nodeCount: w.nodes?.length || 0,
    updatedAt: w.updatedAt,
    createdAt: w.createdAt,
  };
}

export function WorkflowList() {
  const [workflows, setWorkflows] = useState<WorkflowSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<'name-asc' | 'name-desc' | 'date-new' | 'date-old' | 'nodes'>('date-new');
  const navigate = useNavigate();
  const confirm = useConfirm();
  const clearWorkflow = useWorkflowStore(s => s.clearWorkflow);
  const user = useAuthStore(s => s.user);
  const logout = useAuthStore(s => s.logout);

  const fetchWorkflows = useCallback(async () => {
    setIsLoading(true);
    try {
      const list = await api.workflows.list();
      setWorkflows(list.map(toSummary));
    } catch {
      toast.error('Failed to load workflows');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => { fetchWorkflows(); }, [fetchWorkflows]);

  const handleOpen = useCallback((id: string) => {
    navigate(`/workflows/${id}`);
  }, [navigate]);

  const handleNew = useCallback(() => {
    clearWorkflow();
    navigate('/workflows/new');
  }, [navigate, clearWorkflow]);

  const handleDelete = useCallback(async (id: string, name: string) => {
    const ok = await confirm({
      title: 'Delete Workflow',
      description: `Are you sure you want to delete "${name}"? This action cannot be undone.`,
      confirmText: 'Delete',
      variant: 'destructive',
    });
    if (!ok) return;
    try {
      await api.workflows.delete(id);
      setWorkflows(prev => prev.filter(w => w.id !== id));
      toast.success('Workflow deleted');
    } catch {
      toast.error('Failed to delete workflow');
    }
  }, [confirm]);

  const handleClone = useCallback(async (workflow: WorkflowSummary) => {
    try {
      const original = await api.workflows.get(workflow.id);
      await api.workflows.create({
        name: `${original.name} (Copy)`,
        nodes: original.nodes,
        edges: original.edges,
      });
      toast.success('Workflow duplicated');
      fetchWorkflows();
    } catch {
      toast.error('Failed to duplicate workflow');
    }
  }, [fetchWorkflows]);

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
    });
  };

  const filteredWorkflows = useMemo(() => {
    let result = workflows;

    // Filter by search
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(w =>
        w.name.toLowerCase().includes(q) ||
        (w.description || '').toLowerCase().includes(q)
      );
    }

    // Sort
    result = [...result].sort((a, b) => {
      switch (sortBy) {
        case 'name-asc': return a.name.localeCompare(b.name);
        case 'name-desc': return b.name.localeCompare(a.name);
        case 'date-new': return (b.updatedAt || '').localeCompare(a.updatedAt || '');
        case 'date-old': return (a.updatedAt || '').localeCompare(b.updatedAt || '');
        case 'nodes': return b.nodeCount - a.nodeCount;
        default: return 0;
      }
    });

    return result;
  }, [workflows, searchQuery, sortBy]);

  return (
    <div className="min-h-screen bg-background">
      <header className="h-14 border-b bg-background flex items-center justify-between px-6">
        <div className="font-bold text-lg text-primary">AgentChord</div>
        <div className="flex items-center gap-2">
          <Button size="sm" onClick={handleNew}>
            <Plus className="w-4 h-4 mr-2" />
            New Workflow
          </Button>
          <div className="h-6 w-px bg-border ml-2" />
          <span className="text-sm text-muted-foreground">{user?.email}</span>
          <Button variant="ghost" size="sm" onClick={logout}>
            <LogOut className="w-4 h-4 mr-2" />
            Logout
          </Button>
        </div>
      </header>

      <main className="max-w-5xl mx-auto p-6">
        <h1 className="text-2xl font-bold mb-6">Workflows</h1>

        <div className="flex items-center gap-3 mb-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search workflows..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2 text-sm border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            className="text-sm border rounded-md px-3 py-2 bg-background"
          >
            <option value="date-new">Newest first</option>
            <option value="date-old">Oldest first</option>
            <option value="name-asc">Name A-Z</option>
            <option value="name-desc">Name Z-A</option>
            <option value="nodes">Most nodes</option>
          </select>
        </div>

        {isLoading ? (
          <WorkflowListSkeleton />
        ) : workflows.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-muted-foreground mb-4">No workflows yet</p>
            <Button onClick={handleNew}>
              <Plus className="w-4 h-4 mr-2" />
              Create your first workflow
            </Button>
          </div>
        ) : filteredWorkflows.length === 0 && searchQuery ? (
          <div className="text-center py-8 text-muted-foreground">
            No workflows matching "{searchQuery}"
          </div>
        ) : (
          <div className="grid gap-3">
            {filteredWorkflows.map(w => (
              <div
                key={w.id}
                className="border rounded-lg p-4 hover:bg-accent/50 transition-colors cursor-pointer flex items-center justify-between group"
                onClick={() => handleOpen(w.id)}
              >
                <div className="flex-1 min-w-0">
                  <h3 className="font-medium truncate">{w.name}</h3>
                  {w.description && (
                    <p className="text-sm text-muted-foreground truncate mt-0.5">{w.description}</p>
                  )}
                  <div className="flex items-center gap-4 mt-1.5 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <GitBranch className="w-3 h-3" />
                      {w.nodeCount} nodes
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {formatDate(w.updatedAt)}
                    </span>
                  </div>
                </div>
                <div
                  className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity"
                  onClick={e => e.stopPropagation()}
                >
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8"
                    onClick={() => handleClone(w)}
                    title="Duplicate workflow"
                  >
                    <Copy className="w-4 h-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8"
                    onClick={() => handleDelete(w.id, w.name)}
                  >
                    <Trash2 className="w-4 h-4 text-destructive" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
