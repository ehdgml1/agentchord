/**
 * Custom hook for undo/redo keyboard shortcuts
 *
 * Provides keyboard shortcuts for undo (Ctrl/Cmd+Z) and redo (Ctrl/Cmd+Shift+Z or Ctrl/Cmd+Y)
 */

import { useEffect } from 'react';
import { useWorkflowStore } from '../stores/workflowStore';

export function useUndoRedo() {
  const undo = useWorkflowStore(s => s.undo);
  const redo = useWorkflowStore(s => s.redo);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // Check if we're in an input field - don't intercept undo/redo there
      const target = e.target as HTMLElement;
      const isInputField = target.tagName === 'INPUT' ||
                          target.tagName === 'TEXTAREA' ||
                          target.isContentEditable;

      if (isInputField) return;

      if ((e.metaKey || e.ctrlKey) && e.key === 'z') {
        e.preventDefault();
        if (e.shiftKey) {
          redo();
        } else {
          undo();
        }
      }

      if ((e.metaKey || e.ctrlKey) && e.key === 'y') {
        e.preventDefault();
        redo();
      }
    };

    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [undo, redo]);
}
