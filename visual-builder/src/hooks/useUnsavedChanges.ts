import { useEffect } from 'react';
import { useWorkflowStore } from '../stores/workflowStore';

/**
 * Hook to warn users about unsaved changes before leaving.
 * Uses beforeunload to protect against browser close/refresh.
 *
 * Note: In-app navigation blocking via useBlocker requires a data router
 * (createBrowserRouter). The app currently uses BrowserRouter, so only
 * the beforeunload handler is active. Migrate to createBrowserRouter
 * to enable in-app navigation blocking.
 */
export function useUnsavedChanges() {
  const isDirty = useWorkflowStore((s) => s.isDirty);

  // Browser close/refresh protection
  useEffect(() => {
    if (!isDirty) return;

    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      // Modern browsers ignore custom messages, but setting returnValue is required
      e.returnValue = '';
    };

    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [isDirty]);
}
