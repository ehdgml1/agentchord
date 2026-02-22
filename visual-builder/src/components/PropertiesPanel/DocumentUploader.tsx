/**
 * Document file upload component for RAG nodes
 *
 * Provides drag-and-drop and click-to-select file upload with
 * uploaded file list management.
 */

import { memo, useCallback, useRef, useState } from 'react';
import { Upload, FileText, Trash2, Loader2, AlertCircle } from 'lucide-react';
import { Button } from '../ui/button';
import type { DocumentFileInfo } from '../../types/blocks';

interface DocumentUploaderProps {
  /** Currently uploaded files */
  files: DocumentFileInfo[];
  /** Called when a file is selected for upload */
  onUpload: (file: File) => void;
  /** Called when a file should be deleted */
  onDelete: (fileId: string) => void;
  /** Whether an upload is in progress */
  isUploading?: boolean;
  /** Error message to display */
  error?: string;
}

const ALLOWED_EXTENSIONS = ['.txt', '.md', '.csv', '.pdf', '.log', '.json'];
const MAX_SIZE_MB = 10;

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getFileIcon(filename: string): string {
  const ext = filename.split('.').pop()?.toLowerCase();
  switch (ext) {
    case 'pdf':
      return '📄';
    case 'csv':
      return '📊';
    case 'json':
      return '{}';
    case 'md':
      return '📝';
    default:
      return '📃';
  }
}

export const DocumentUploader = memo(function DocumentUploader({
  files,
  onUpload,
  onDelete,
  isUploading = false,
  error,
}: DocumentUploaderProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const validateAndUpload = useCallback(
    (file: File) => {
      const ext = '.' + (file.name.split('.').pop()?.toLowerCase() || '');
      if (!ALLOWED_EXTENSIONS.includes(ext)) {
        return;
      }
      if (file.size > MAX_SIZE_MB * 1024 * 1024) {
        return;
      }
      onUpload(file);
    },
    [onUpload]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragOver(false);

      const droppedFiles = Array.from(e.dataTransfer.files);
      for (const file of droppedFiles) {
        validateAndUpload(file);
      }
    },
    [validateAndUpload]
  );

  const handleClick = useCallback(() => {
    inputRef.current?.click();
  }, []);

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const selectedFiles = Array.from(e.target.files || []);
      for (const file of selectedFiles) {
        validateAndUpload(file);
      }
      // Reset input so same file can be selected again
      if (inputRef.current) {
        inputRef.current.value = '';
      }
    },
    [validateAndUpload]
  );

  return (
    <div className="space-y-2">
      {/* Drop zone */}
      <div
        role="button"
        tabIndex={0}
        className={`
          relative flex flex-col items-center justify-center gap-2 rounded-md border-2 border-dashed p-4
          cursor-pointer transition-colors
          ${isDragOver
            ? 'border-blue-500 bg-blue-50 dark:bg-blue-950'
            : 'border-muted-foreground/25 hover:border-muted-foreground/50'
          }
          ${isUploading ? 'pointer-events-none opacity-60' : ''}
        `}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleClick}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            handleClick();
          }
        }}
        data-testid="drop-zone"
      >
        {isUploading ? (
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        ) : (
          <Upload className="h-6 w-6 text-muted-foreground" />
        )}
        <div className="text-center">
          <p className="text-sm text-muted-foreground">
            {isUploading ? '업로드 중...' : '파일을 드래그하거나 클릭하여 선택'}
          </p>
          <p className="text-xs text-muted-foreground/70 mt-1">
            {ALLOWED_EXTENSIONS.join(', ')} (최대 {MAX_SIZE_MB}MB)
          </p>
        </div>
        <input
          ref={inputRef}
          type="file"
          className="hidden"
          accept={ALLOWED_EXTENSIONS.join(',')}
          onChange={handleFileChange}
          data-testid="file-input"
        />
      </div>

      {/* Error message */}
      {error && (
        <div className="flex items-center gap-1.5 text-xs text-red-600" data-testid="upload-error">
          <AlertCircle className="h-3.5 w-3.5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Uploaded files list */}
      {files.length > 0 && (
        <div className="space-y-1" data-testid="file-list">
          {files.map((file) => (
            <div
              key={file.id}
              className="flex items-center gap-2 rounded-md border px-2 py-1.5 text-sm"
            >
              <span className="flex-shrink-0">{getFileIcon(file.filename)}</span>
              <FileText className="h-3.5 w-3.5 flex-shrink-0 text-muted-foreground" />
              <span className="flex-1 truncate" title={file.filename}>
                {file.filename}
              </span>
              <span className="flex-shrink-0 text-xs text-muted-foreground">
                {formatFileSize(file.size)}
              </span>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 flex-shrink-0"
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(file.id);
                }}
                data-testid={`delete-${file.id}`}
              >
                <Trash2 className="h-3.5 w-3.5 text-muted-foreground hover:text-red-500" />
              </Button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
});
