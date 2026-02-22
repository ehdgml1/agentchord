/**
 * Tests for DocumentUploader component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DocumentUploader } from './DocumentUploader';
import type { DocumentFileInfo } from '../../types/blocks';

const mockFiles: DocumentFileInfo[] = [
  { id: 'abc123', filename: 'test.txt', size: 1024, mimeType: 'text/plain' },
  { id: 'def456', filename: 'data.pdf', size: 2 * 1024 * 1024, mimeType: 'application/pdf' },
];

describe('DocumentUploader', () => {
  const mockOnUpload = vi.fn();
  const mockOnDelete = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Empty State', () => {
    it('renders drop zone with upload icon and text', () => {
      render(
        <DocumentUploader
          files={[]}
          onUpload={mockOnUpload}
          onDelete={mockOnDelete}
        />
      );

      const dropZone = screen.getByTestId('drop-zone');
      expect(dropZone).toBeInTheDocument();

      // Upload icon should be visible (not loader)
      const uploadIcon = dropZone.querySelector('svg');
      expect(uploadIcon).toBeInTheDocument();

      expect(screen.getByText(/파일을 드래그하거나 클릭하여 선택/i)).toBeInTheDocument();
    });

    it('renders empty when no files', () => {
      render(
        <DocumentUploader
          files={[]}
          onUpload={mockOnUpload}
          onDelete={mockOnDelete}
        />
      );

      const fileList = screen.queryByTestId('file-list');
      expect(fileList).not.toBeInTheDocument();
    });

    it('shows allowed extensions and max size in helper text', () => {
      render(
        <DocumentUploader
          files={[]}
          onUpload={mockOnUpload}
          onDelete={mockOnDelete}
        />
      );

      expect(screen.getByText(/\.txt, \.md, \.csv, \.pdf, \.log, \.json/i)).toBeInTheDocument();
      expect(screen.getByText(/최대 10MB/i)).toBeInTheDocument();
    });
  });

  describe('File List Rendering', () => {
    it('renders file list when files provided', () => {
      render(
        <DocumentUploader
          files={mockFiles}
          onUpload={mockOnUpload}
          onDelete={mockOnDelete}
        />
      );

      const fileList = screen.getByTestId('file-list');
      expect(fileList).toBeInTheDocument();
    });

    it('shows file sizes formatted as bytes', () => {
      const files: DocumentFileInfo[] = [
        { id: '1', filename: 'tiny.txt', size: 512, mimeType: 'text/plain' },
      ];

      render(
        <DocumentUploader
          files={files}
          onUpload={mockOnUpload}
          onDelete={mockOnDelete}
        />
      );

      expect(screen.getByText('512 B')).toBeInTheDocument();
    });

    it('shows file sizes formatted as KB', () => {
      const files: DocumentFileInfo[] = [
        { id: '1', filename: 'test.txt', size: 1024, mimeType: 'text/plain' },
      ];

      render(
        <DocumentUploader
          files={files}
          onUpload={mockOnUpload}
          onDelete={mockOnDelete}
        />
      );

      expect(screen.getByText('1.0 KB')).toBeInTheDocument();
    });

    it('shows file sizes formatted as MB', () => {
      const files: DocumentFileInfo[] = [
        { id: '1', filename: 'data.pdf', size: 2 * 1024 * 1024, mimeType: 'application/pdf' },
      ];

      render(
        <DocumentUploader
          files={files}
          onUpload={mockOnUpload}
          onDelete={mockOnDelete}
        />
      );

      expect(screen.getByText('2.0 MB')).toBeInTheDocument();
    });

    it('shows file sizes formatted with decimal precision', () => {
      const files: DocumentFileInfo[] = [
        { id: '1', filename: 'medium.csv', size: 1536, mimeType: 'text/csv' },
      ];

      render(
        <DocumentUploader
          files={files}
          onUpload={mockOnUpload}
          onDelete={mockOnDelete}
        />
      );

      expect(screen.getByText('1.5 KB')).toBeInTheDocument();
    });

    it('renders multiple files correctly', () => {
      render(
        <DocumentUploader
          files={mockFiles}
          onUpload={mockOnUpload}
          onDelete={mockOnDelete}
        />
      );

      expect(screen.getByText('test.txt')).toBeInTheDocument();
      expect(screen.getByText('data.pdf')).toBeInTheDocument();
      expect(screen.getByText('1.0 KB')).toBeInTheDocument();
      expect(screen.getByText('2.0 MB')).toBeInTheDocument();
    });

    it('shows file icon emoji for each file', () => {
      const files: DocumentFileInfo[] = [
        { id: '1', filename: 'doc.pdf', size: 1024, mimeType: 'application/pdf' },
        { id: '2', filename: 'data.csv', size: 1024, mimeType: 'text/csv' },
        { id: '3', filename: 'notes.md', size: 1024, mimeType: 'text/markdown' },
        { id: '4', filename: 'config.json', size: 1024, mimeType: 'application/json' },
        { id: '5', filename: 'plain.txt', size: 1024, mimeType: 'text/plain' },
      ];

      render(
        <DocumentUploader
          files={files}
          onUpload={mockOnUpload}
          onDelete={mockOnDelete}
        />
      );

      const fileList = screen.getByTestId('file-list');
      // Each file should have an emoji icon (rendered as text)
      expect(fileList.textContent).toContain('📄'); // PDF
      expect(fileList.textContent).toContain('📊'); // CSV
      expect(fileList.textContent).toContain('📝'); // MD
      expect(fileList.textContent).toContain('{}'); // JSON
      expect(fileList.textContent).toContain('📃'); // Default
    });

    it('shows delete button for each file', () => {
      render(
        <DocumentUploader
          files={mockFiles}
          onUpload={mockOnUpload}
          onDelete={mockOnDelete}
        />
      );

      expect(screen.getByTestId('delete-abc123')).toBeInTheDocument();
      expect(screen.getByTestId('delete-def456')).toBeInTheDocument();
    });
  });

  describe('File Upload via Input', () => {
    it('calls onUpload when file selected via input', async () => {
      render(
        <DocumentUploader
          files={[]}
          onUpload={mockOnUpload}
          onDelete={mockOnDelete}
        />
      );

      const input = screen.getByTestId('file-input') as HTMLInputElement;
      const file = new File(['content'], 'test.txt', { type: 'text/plain' });

      await userEvent.upload(input, file);

      expect(mockOnUpload).toHaveBeenCalledTimes(1);
      expect(mockOnUpload).toHaveBeenCalledWith(file);
    });

    it('calls onUpload for multiple files selected', async () => {
      render(
        <DocumentUploader
          files={[]}
          onUpload={mockOnUpload}
          onDelete={mockOnDelete}
        />
      );

      const input = screen.getByTestId('file-input') as HTMLInputElement;
      const file1 = new File(['content1'], 'test1.txt', { type: 'text/plain' });
      const file2 = new File(['content2'], 'test2.txt', { type: 'text/plain' });

      // Use fireEvent instead of userEvent for multi-file upload
      Object.defineProperty(input, 'files', {
        value: [file1, file2],
        configurable: true,
      });
      fireEvent.change(input);

      expect(mockOnUpload).toHaveBeenCalledTimes(2);
      expect(mockOnUpload).toHaveBeenNthCalledWith(1, file1);
      expect(mockOnUpload).toHaveBeenNthCalledWith(2, file2);
    });

    it('file input has correct accept attribute', () => {
      render(
        <DocumentUploader
          files={[]}
          onUpload={mockOnUpload}
          onDelete={mockOnDelete}
        />
      );

      const input = screen.getByTestId('file-input') as HTMLInputElement;
      expect(input).toHaveAttribute('accept', '.txt,.md,.csv,.pdf,.log,.json');
    });

    it('resets input value after file selection', async () => {
      render(
        <DocumentUploader
          files={[]}
          onUpload={mockOnUpload}
          onDelete={mockOnDelete}
        />
      );

      const input = screen.getByTestId('file-input') as HTMLInputElement;
      const file = new File(['content'], 'test.txt', { type: 'text/plain' });

      await userEvent.upload(input, file);

      // Input should be reset so same file can be selected again
      expect(input.value).toBe('');
    });

    it('does not call onUpload for disallowed file extension', async () => {
      render(
        <DocumentUploader
          files={[]}
          onUpload={mockOnUpload}
          onDelete={mockOnDelete}
        />
      );

      const input = screen.getByTestId('file-input') as HTMLInputElement;
      const file = new File(['content'], 'test.exe', { type: 'application/x-msdownload' });

      await userEvent.upload(input, file);

      expect(mockOnUpload).not.toHaveBeenCalled();
    });

    it('does not call onUpload for file exceeding max size', async () => {
      render(
        <DocumentUploader
          files={[]}
          onUpload={mockOnUpload}
          onDelete={mockOnDelete}
        />
      );

      const input = screen.getByTestId('file-input') as HTMLInputElement;
      // Create a file larger than 10MB
      const largeContent = new Array(11 * 1024 * 1024).fill('a').join('');
      const file = new File([largeContent], 'large.txt', { type: 'text/plain' });

      await userEvent.upload(input, file);

      expect(mockOnUpload).not.toHaveBeenCalled();
    });
  });

  describe('Click Interaction', () => {
    it('click on drop zone triggers file input', async () => {
      render(
        <DocumentUploader
          files={[]}
          onUpload={mockOnUpload}
          onDelete={mockOnDelete}
        />
      );

      const dropZone = screen.getByTestId('drop-zone');
      const input = screen.getByTestId('file-input') as HTMLInputElement;

      const clickSpy = vi.spyOn(input, 'click');

      await userEvent.click(dropZone);

      expect(clickSpy).toHaveBeenCalled();
      expect(clickSpy.mock.calls.length).toBeGreaterThanOrEqual(1);
    });

    it('Enter key on drop zone triggers file input', async () => {
      render(
        <DocumentUploader
          files={[]}
          onUpload={mockOnUpload}
          onDelete={mockOnDelete}
        />
      );

      const dropZone = screen.getByTestId('drop-zone');
      const input = screen.getByTestId('file-input') as HTMLInputElement;

      const clickSpy = vi.spyOn(input, 'click');

      dropZone.focus();
      fireEvent.keyDown(dropZone, { key: 'Enter' });

      expect(clickSpy).toHaveBeenCalled();
      expect(clickSpy.mock.calls.length).toBeGreaterThanOrEqual(1);
    });

    it('Space key on drop zone triggers file input', async () => {
      render(
        <DocumentUploader
          files={[]}
          onUpload={mockOnUpload}
          onDelete={mockOnDelete}
        />
      );

      const dropZone = screen.getByTestId('drop-zone');
      const input = screen.getByTestId('file-input') as HTMLInputElement;

      const clickSpy = vi.spyOn(input, 'click');

      dropZone.focus();
      fireEvent.keyDown(dropZone, { key: ' ' });

      expect(clickSpy).toHaveBeenCalled();
      expect(clickSpy.mock.calls.length).toBeGreaterThanOrEqual(1);
    });
  });

  describe('Delete Interaction', () => {
    it('calls onDelete when delete button clicked', async () => {
      render(
        <DocumentUploader
          files={mockFiles}
          onUpload={mockOnUpload}
          onDelete={mockOnDelete}
        />
      );

      const deleteButton = screen.getByTestId('delete-abc123');
      await userEvent.click(deleteButton);

      expect(mockOnDelete).toHaveBeenCalledTimes(1);
      expect(mockOnDelete).toHaveBeenCalledWith('abc123');
    });

    it('calls onDelete with correct ID for each file', async () => {
      render(
        <DocumentUploader
          files={mockFiles}
          onUpload={mockOnUpload}
          onDelete={mockOnDelete}
        />
      );

      await userEvent.click(screen.getByTestId('delete-abc123'));
      expect(mockOnDelete).toHaveBeenCalledWith('abc123');

      await userEvent.click(screen.getByTestId('delete-def456'));
      expect(mockOnDelete).toHaveBeenCalledWith('def456');
    });

    it('delete button click does not propagate to drop zone', async () => {
      const dropZoneClickSpy = vi.fn();

      render(
        <DocumentUploader
          files={mockFiles}
          onUpload={mockOnUpload}
          onDelete={mockOnDelete}
        />
      );

      const dropZone = screen.getByTestId('drop-zone');
      dropZone.onclick = dropZoneClickSpy;

      const deleteButton = screen.getByTestId('delete-abc123');
      await userEvent.click(deleteButton);

      expect(mockOnDelete).toHaveBeenCalledTimes(1);
      // Drop zone click handler should not have been called
      expect(dropZoneClickSpy).not.toHaveBeenCalled();
    });
  });

  describe('Uploading State', () => {
    it('shows uploading state with spinner', () => {
      render(
        <DocumentUploader
          files={[]}
          onUpload={mockOnUpload}
          onDelete={mockOnDelete}
          isUploading={true}
        />
      );

      const dropZone = screen.getByTestId('drop-zone');
      // Loader2 icon should be visible with animate-spin class
      const loader = dropZone.querySelector('.animate-spin');
      expect(loader).toBeInTheDocument();
    });

    it('shows uploading text when isUploading is true', () => {
      render(
        <DocumentUploader
          files={[]}
          onUpload={mockOnUpload}
          onDelete={mockOnDelete}
          isUploading={true}
        />
      );

      expect(screen.getByText('업로드 중...')).toBeInTheDocument();
      expect(screen.queryByText(/파일을 드래그하거나 클릭하여 선택/i)).not.toBeInTheDocument();
    });

    it('disables drop zone interaction when uploading', () => {
      render(
        <DocumentUploader
          files={[]}
          onUpload={mockOnUpload}
          onDelete={mockOnDelete}
          isUploading={true}
        />
      );

      const dropZone = screen.getByTestId('drop-zone');
      expect(dropZone.className).toContain('pointer-events-none');
      expect(dropZone.className).toContain('opacity-60');
    });

    it('shows normal state when not uploading', () => {
      render(
        <DocumentUploader
          files={[]}
          onUpload={mockOnUpload}
          onDelete={mockOnDelete}
          isUploading={false}
        />
      );

      expect(screen.getByText(/파일을 드래그하거나 클릭하여 선택/i)).toBeInTheDocument();
      expect(screen.queryByText('업로드 중...')).not.toBeInTheDocument();
    });
  });

  describe('Error Display', () => {
    it('shows error message when error prop is set', () => {
      render(
        <DocumentUploader
          files={[]}
          onUpload={mockOnUpload}
          onDelete={mockOnDelete}
          error="Upload failed: network error"
        />
      );

      const errorEl = screen.getByTestId('upload-error');
      expect(errorEl).toBeInTheDocument();
      expect(errorEl).toHaveTextContent('Upload failed: network error');
    });

    it('shows AlertCircle icon with error message', () => {
      render(
        <DocumentUploader
          files={[]}
          onUpload={mockOnUpload}
          onDelete={mockOnDelete}
          error="Upload failed"
        />
      );

      const errorEl = screen.getByTestId('upload-error');
      const icon = errorEl.querySelector('svg');
      expect(icon).toBeInTheDocument();
    });

    it('does not show error when error prop is undefined', () => {
      render(
        <DocumentUploader
          files={[]}
          onUpload={mockOnUpload}
          onDelete={mockOnDelete}
        />
      );

      const errorEl = screen.queryByTestId('upload-error');
      expect(errorEl).not.toBeInTheDocument();
    });

    it('does not show error when error prop is empty string', () => {
      render(
        <DocumentUploader
          files={[]}
          onUpload={mockOnUpload}
          onDelete={mockOnDelete}
          error=""
        />
      );

      const errorEl = screen.queryByTestId('upload-error');
      expect(errorEl).not.toBeInTheDocument();
    });
  });

  describe('Drag and Drop', () => {
    it('handles drag-over visual state', () => {
      render(
        <DocumentUploader
          files={[]}
          onUpload={mockOnUpload}
          onDelete={mockOnDelete}
        />
      );

      const dropZone = screen.getByTestId('drop-zone');

      // Initially not in drag-over state
      expect(dropZone.className).not.toContain('border-blue-500');
      expect(dropZone.className).not.toContain('bg-blue-50');

      // Trigger drag over
      fireEvent.dragOver(dropZone);

      // Now should have drag-over styles
      expect(dropZone.className).toContain('border-blue-500');
      expect(dropZone.className).toContain('bg-blue-50');
    });

    it('handles drag-leave to remove visual state', () => {
      render(
        <DocumentUploader
          files={[]}
          onUpload={mockOnUpload}
          onDelete={mockOnDelete}
        />
      );

      const dropZone = screen.getByTestId('drop-zone');

      // Enter drag state
      fireEvent.dragOver(dropZone);
      expect(dropZone.className).toContain('border-blue-500');

      // Leave drag state
      fireEvent.dragLeave(dropZone);
      expect(dropZone.className).not.toContain('border-blue-500');
      expect(dropZone.className).not.toContain('bg-blue-50');
    });

    it('handles drop event with files', () => {
      render(
        <DocumentUploader
          files={[]}
          onUpload={mockOnUpload}
          onDelete={mockOnDelete}
        />
      );

      const dropZone = screen.getByTestId('drop-zone');
      const file = new File(['content'], 'test.txt', { type: 'text/plain' });

      fireEvent.drop(dropZone, {
        dataTransfer: {
          files: [file],
        },
      });

      expect(mockOnUpload).toHaveBeenCalledTimes(1);
      expect(mockOnUpload).toHaveBeenCalledWith(file);
    });

    it('handles drop event with multiple files', () => {
      render(
        <DocumentUploader
          files={[]}
          onUpload={mockOnUpload}
          onDelete={mockOnDelete}
        />
      );

      const dropZone = screen.getByTestId('drop-zone');
      const file1 = new File(['content1'], 'test1.txt', { type: 'text/plain' });
      const file2 = new File(['content2'], 'test2.txt', { type: 'text/plain' });

      fireEvent.drop(dropZone, {
        dataTransfer: {
          files: [file1, file2],
        },
      });

      expect(mockOnUpload).toHaveBeenCalledTimes(2);
      expect(mockOnUpload).toHaveBeenNthCalledWith(1, file1);
      expect(mockOnUpload).toHaveBeenNthCalledWith(2, file2);
    });

    it('clears drag-over state after drop', () => {
      render(
        <DocumentUploader
          files={[]}
          onUpload={mockOnUpload}
          onDelete={mockOnDelete}
        />
      );

      const dropZone = screen.getByTestId('drop-zone');

      // Enter drag state
      fireEvent.dragOver(dropZone);
      expect(dropZone.className).toContain('border-blue-500');

      // Drop files
      const file = new File(['content'], 'test.txt', { type: 'text/plain' });
      fireEvent.drop(dropZone, {
        dataTransfer: {
          files: [file],
        },
      });

      // Drag-over state should be cleared
      expect(dropZone.className).not.toContain('border-blue-500');
      expect(dropZone.className).not.toContain('bg-blue-50');
    });

    it('validates dropped files by extension', () => {
      render(
        <DocumentUploader
          files={[]}
          onUpload={mockOnUpload}
          onDelete={mockOnDelete}
        />
      );

      const dropZone = screen.getByTestId('drop-zone');
      const validFile = new File(['content'], 'valid.txt', { type: 'text/plain' });
      const invalidFile = new File(['content'], 'invalid.exe', { type: 'application/x-msdownload' });

      fireEvent.drop(dropZone, {
        dataTransfer: {
          files: [validFile, invalidFile],
        },
      });

      // Only valid file should trigger onUpload
      expect(mockOnUpload).toHaveBeenCalledTimes(1);
      expect(mockOnUpload).toHaveBeenCalledWith(validFile);
    });

    it('validates dropped files by size', () => {
      render(
        <DocumentUploader
          files={[]}
          onUpload={mockOnUpload}
          onDelete={mockOnDelete}
        />
      );

      const dropZone = screen.getByTestId('drop-zone');
      const validFile = new File(['small content'], 'small.txt', { type: 'text/plain' });

      // Manually set size property (File constructor doesn't respect size in test env)
      Object.defineProperty(validFile, 'size', { value: 1024 });

      const largeContent = new Array(11 * 1024 * 1024).fill('a').join('');
      const invalidFile = new File([largeContent], 'large.txt', { type: 'text/plain' });
      Object.defineProperty(invalidFile, 'size', { value: 11 * 1024 * 1024 });

      fireEvent.drop(dropZone, {
        dataTransfer: {
          files: [validFile, invalidFile],
        },
      });

      // Only small file should trigger onUpload
      expect(mockOnUpload).toHaveBeenCalledTimes(1);
      expect(mockOnUpload).toHaveBeenCalledWith(validFile);
    });
  });

  describe('Accessibility', () => {
    it('drop zone has role="button"', () => {
      render(
        <DocumentUploader
          files={[]}
          onUpload={mockOnUpload}
          onDelete={mockOnDelete}
        />
      );

      const dropZone = screen.getByTestId('drop-zone');
      expect(dropZone).toHaveAttribute('role', 'button');
    });

    it('drop zone has tabIndex for keyboard navigation', () => {
      render(
        <DocumentUploader
          files={[]}
          onUpload={mockOnUpload}
          onDelete={mockOnDelete}
        />
      );

      const dropZone = screen.getByTestId('drop-zone');
      expect(dropZone).toHaveAttribute('tabIndex', '0');
    });

    it('file input is hidden from screen readers', () => {
      render(
        <DocumentUploader
          files={[]}
          onUpload={mockOnUpload}
          onDelete={mockOnDelete}
        />
      );

      const input = screen.getByTestId('file-input');
      expect(input.className).toContain('hidden');
    });

    it('filenames have title attribute for truncated text', () => {
      render(
        <DocumentUploader
          files={mockFiles}
          onUpload={mockOnUpload}
          onDelete={mockOnDelete}
        />
      );

      const filename = screen.getByText('test.txt');
      expect(filename).toHaveAttribute('title', 'test.txt');
    });
  });
});
