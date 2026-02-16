import { useEffect, useRef, useCallback } from 'react';
import { useWorkflowStore } from '../stores/workflowStore';

const AUTO_SAVE_DELAY = 30000; // 30 seconds

/**
 * Hook that auto-saves the workflow after a period of inactivity.
 * Only saves if isDirty and backendId exists (workflow was previously saved).
 */
export function useAutoSave() {
  const isDirty = useWorkflowStore((s) => s.isDirty);
  const backendId = useWorkflowStore((s) => s.backendId);
  const saveWorkflow = useWorkflowStore((s) => s.saveWorkflow);
  const isSaving = useWorkflowStore((s) => s.isSaving);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const doAutoSave = useCallback(async () => {
    try {
      await saveWorkflow();
    } catch {
      // Silent fail for auto-save - user can manually save
      if (import.meta.env.DEV) console.warn('Auto-save failed');
    }
  }, [saveWorkflow]);

  useEffect(() => {
    // Only auto-save if dirty, has a backend ID, and not currently saving
    if (!isDirty || !backendId || isSaving) {
      return;
    }

    timerRef.current = setTimeout(doAutoSave, AUTO_SAVE_DELAY);

    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [isDirty, backendId, isSaving, doAutoSave]);
}
