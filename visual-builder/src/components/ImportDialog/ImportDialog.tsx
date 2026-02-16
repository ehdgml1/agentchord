/**
 * ImportDialog component for Visual Builder
 *
 * Dialog for importing workflows from JSON files with
 * drag & drop support and validation.
 */

import { useState, useCallback, useRef } from 'react';
import { Upload, FileJson, AlertCircle, Check } from 'lucide-react';
import { Button } from '../ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '../ui/dialog';
import { parseWorkflowImport } from '../../lib/workflowExport';
import type { WorkflowExport } from '../../types';

interface ImportDialogProps {
  /** Dialog open state */
  open: boolean;
  /** Dialog state change handler */
  onOpenChange: (open: boolean) => void;
  /** Callback when workflow is imported */
  onImport: (workflowData: WorkflowExport) => void;
}

export function ImportDialog({ open, onOpenChange, onImport }: ImportDialogProps) {
  const [importData, setImportData] = useState<WorkflowExport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Reset state when dialog closes
  const handleOpenChange = useCallback((newOpen: boolean) => {
    if (!newOpen) {
      setImportData(null);
      setError(null);
      setIsDragging(false);
    }
    onOpenChange(newOpen);
  }, [onOpenChange]);

  // Handle file content
  const handleFileContent = useCallback((content: string) => {
    setError(null);
    const parsed = parseWorkflowImport(content);

    if (!parsed) {
      setError('Invalid workflow file format. Please select a valid JSON export.');
      setImportData(null);
      return;
    }

    setImportData(parsed);
  }, []);

  // Handle file selection
  const handleFileSelect = useCallback((file: File) => {
    if (!file.name.endsWith('.json')) {
      setError('Please select a JSON file.');
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      const content = e.target?.result as string;
      handleFileContent(content);
    };
    reader.onerror = () => {
      setError('Failed to read file. Please try again.');
    };
    reader.readAsText(file);
  }, [handleFileContent]);

  // Handle file input change
  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFileSelect(file);
    }
  }, [handleFileSelect]);

  // Handle drag and drop
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const file = e.dataTransfer.files[0];
    if (file) {
      handleFileSelect(file);
    }
  }, [handleFileSelect]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragging(false);
  }, []);

  // Handle import
  const handleImport = useCallback(() => {
    if (importData) {
      onImport(importData);
      handleOpenChange(false);
    }
  }, [importData, onImport, handleOpenChange]);

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Import Workflow</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* File Input Area */}
          <div
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              isDragging
                ? 'border-indigo-500 bg-indigo-50'
                : 'border-gray-300 hover:border-gray-400'
            }`}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".json"
              onChange={handleInputChange}
              className="hidden"
            />

            <FileJson className="w-12 h-12 mx-auto mb-3 text-muted-foreground" />

            {importData ? (
              <div className="space-y-2">
                <div className="flex items-center justify-center gap-2 text-green-600">
                  <Check className="w-5 h-5" />
                  <span className="font-medium">File loaded successfully</span>
                </div>
                <p className="text-sm text-muted-foreground">
                  Ready to import
                </p>
              </div>
            ) : (
              <>
                <p className="text-sm text-muted-foreground mb-3">
                  Drag and drop a workflow JSON file here, or click to browse
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <Upload className="w-4 h-4 mr-2" />
                  Select File
                </Button>
              </>
            )}
          </div>

          {/* Error Display */}
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-md flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
              <span className="text-sm text-red-700">{error}</span>
            </div>
          )}

          {/* Preview */}
          {importData && (
            <div className="border rounded-md p-4 bg-gray-50 space-y-2">
              <h4 className="text-sm font-medium">Workflow Preview</h4>
              <div className="space-y-1 text-sm">
                <div>
                  <span className="text-muted-foreground">Name:</span>{' '}
                  <span className="font-medium">{importData.workflow.name}</span>
                </div>
                {importData.workflow.description && (
                  <div>
                    <span className="text-muted-foreground">Description:</span>{' '}
                    {importData.workflow.description}
                  </div>
                )}
                <div>
                  <span className="text-muted-foreground">Nodes:</span>{' '}
                  {importData.workflow.nodes.length}
                </div>
                <div>
                  <span className="text-muted-foreground">Connections:</span>{' '}
                  {importData.workflow.edges.length}
                </div>
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => handleOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleImport}
            disabled={!importData}
          >
            Import Workflow
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
