import { lazy, memo, Suspense, useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Save, Download, Play, Trash2, LogOut, Upload, CheckCircle, ArrowLeft, Undo2, Redo2 } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { useWorkflowStore } from '../../stores/workflowStore';
import { useAuthStore } from '../../stores/authStore';
import { generateCode } from '../../utils/codeGenerator';
import { LLMStatus } from '../LLMStatus/LLMStatus';
import { nanoid } from 'nanoid';
import { toast } from 'sonner';
import { api } from '../../services/api';
import { useConfirm } from '../ui/confirm-dialog';

const RunDialog = lazy(() => import('../RunDialog').then(m => ({ default: m.RunDialog })));
const ImportDialog = lazy(() => import('../ImportDialog/ImportDialog').then(m => ({ default: m.ImportDialog })));

export const Header = memo(function Header() {
  const [isEditing, setIsEditing] = useState(false);
  const [runDialogOpen, setRunDialogOpen] = useState(false);
  const [importDialogOpen, setImportDialogOpen] = useState(false);
  const navigate = useNavigate();
  const confirm = useConfirm();
  const workflowName = useWorkflowStore(s => s.workflowName);
  const setWorkflowName = useWorkflowStore(s => s.setWorkflowName);
  const getWorkflow = useWorkflowStore(s => s.getWorkflow);
  const clearWorkflow = useWorkflowStore(s => s.clearWorkflow);
  const saveWorkflow = useWorkflowStore(s => s.saveWorkflow);
  const loadWorkflow = useWorkflowStore(s => s.loadWorkflow);
  const isSaving = useWorkflowStore(s => s.isSaving);
  const isDirty = useWorkflowStore(s => s.isDirty);
  const undo = useWorkflowStore(s => s.undo);
  const redo = useWorkflowStore(s => s.redo);
  const canUndo = useWorkflowStore(s => s.canUndo);
  const canRedo = useWorkflowStore(s => s.canRedo);
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  const handleNameClick = useCallback(() => {
    setIsEditing(true);
  }, []);

  const handleNameBlur = useCallback(() => {
    setIsEditing(false);
  }, []);

  const handleNameChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setWorkflowName(e.target.value);
    },
    [setWorkflowName]
  );

  const handleNameKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter') {
        setIsEditing(false);
      }
    },
    []
  );

  const handleExportJSON = useCallback(() => {
    const workflow = getWorkflow();
    const json = JSON.stringify({ version: '1.0', workflow }, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${workflowName.replace(/\s+/g, '_')}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [getWorkflow, workflowName]);

  const handleExportPython = useCallback(() => {
    const { nodes, edges } = useWorkflowStore.getState();
    const code = generateCode(nodes, edges);
    const blob = new Blob([code], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${workflowName.replace(/\s+/g, '_')}.py`;
    a.click();
    URL.revokeObjectURL(url);
  }, [workflowName]);

  const handleClear = useCallback(async () => {
    const ok = await confirm({
      title: 'Clear Workflow',
      description: 'This will remove all nodes and edges. This action cannot be undone.',
      confirmText: 'Clear',
      variant: 'destructive',
    });
    if (ok) clearWorkflow();
  }, [clearWorkflow, confirm]);

  const handleRun = useCallback(() => {
    setRunDialogOpen(true);
  }, []);

  const handleSave = useCallback(async () => {
    try {
      await saveWorkflow();
      toast.success('Workflow saved');
    } catch (error) {
      toast.error('Failed to save workflow');
      if (import.meta.env.DEV) console.error('Failed to save workflow:', error);
    }
  }, [saveWorkflow]);

  const handleImport = useCallback((workflowData: any) => {
    loadWorkflow({
      id: workflowData.workflow?.id || nanoid(),
      name: workflowData.workflow?.name || 'Imported Workflow',
      nodes: workflowData.workflow?.nodes || [],
      edges: workflowData.workflow?.edges || [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    });
    setImportDialogOpen(false);
  }, [loadWorkflow]);

  const handleValidate = useCallback(async () => {
    const state = useWorkflowStore.getState();
    if (!state.backendId) {
      toast.warning('Save the workflow first before validating');
      return;
    }
    try {
      const result = await api.workflows.validate(state.backendId);
      if (result.errors && result.errors.length > 0) {
        result.errors.forEach((err: string) => toast.error(err));
      } else {
        toast.success('Workflow is valid');
      }
    } catch (error) {
      toast.error('Validation failed');
    }
  }, []);

  return (
    <>
      <header className="h-14 border-b bg-background flex items-center justify-between px-4">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => navigate('/')}>
          <ArrowLeft className="w-4 h-4" />
        </Button>
        <div className="font-bold text-lg text-primary">AgentWeave</div>
        <div className="h-6 w-px bg-border" />
        {isEditing ? (
          <Input
            value={workflowName}
            onChange={handleNameChange}
            onBlur={handleNameBlur}
            onKeyDown={handleNameKeyDown}
            className="h-8 w-48"
            autoFocus
          />
        ) : (
          <button
            onClick={handleNameClick}
            className="text-sm font-medium hover:text-primary transition-colors"
          >
            {workflowName}
          </button>
        )}
      </div>

      <div className="flex items-center gap-2">
        <LLMStatus />
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={undo}
          disabled={!canUndo()}
          title="Undo (Ctrl+Z)"
        >
          <Undo2 className="w-4 h-4" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={redo}
          disabled={!canRedo()}
          title="Redo (Ctrl+Shift+Z)"
        >
          <Redo2 className="w-4 h-4" />
        </Button>
        <Button
          variant={isDirty ? "default" : "outline"}
          size="sm"
          onClick={handleSave}
          disabled={isSaving}
        >
          <Save className="w-4 h-4 mr-2" />
          {isSaving ? 'Saving...' : isDirty ? 'Save*' : 'Save'}
        </Button>
        <Button variant="outline" size="sm" onClick={handleExportJSON}>
          <Download className="w-4 h-4 mr-2" />
          Save JSON
        </Button>
        <Button variant="outline" size="sm" onClick={() => setImportDialogOpen(true)}>
          <Upload className="w-4 h-4 mr-2" />
          Import JSON
        </Button>
        <Button variant="outline" size="sm" onClick={handleExportPython}>
          <Download className="w-4 h-4 mr-2" />
          Export Python
        </Button>
        <Button variant="outline" size="sm" onClick={handleClear}>
          <Trash2 className="w-4 h-4 mr-2" />
          Clear
        </Button>
        <Button variant="outline" size="sm" onClick={handleValidate}>
          <CheckCircle className="w-4 h-4 mr-2" />
          Validate
        </Button>
        <Button size="sm" onClick={handleRun}>
          <Play className="w-4 h-4 mr-2" />
          Run
        </Button>
        <div className="h-6 w-px bg-border ml-2" />
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">{user?.email}</span>
          <Button variant="ghost" size="sm" onClick={logout}>
            <LogOut className="w-4 h-4 mr-2" />
            Logout
          </Button>
        </div>
      </div>
    </header>

    <Suspense fallback={null}>
      <RunDialog open={runDialogOpen} onOpenChange={setRunDialogOpen} />
      <ImportDialog open={importDialogOpen} onOpenChange={setImportDialogOpen} onImport={handleImport} />
    </Suspense>
    </>
  );
});
