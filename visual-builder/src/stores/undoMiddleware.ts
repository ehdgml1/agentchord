/**
 * Undo/Redo middleware for Zustand
 *
 * Provides temporal state management with undo/redo capabilities.
 * Tracks snapshots of specified state keys and enables time-travel through state changes.
 */

const MAX_HISTORY = 50;

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export interface UndoStore {
  saveSnapshot: (state: any, keys: string[]) => void;
  undo: (get: () => any, set: (s: any) => void, keys: string[]) => void;
  redo: (get: () => any, set: (s: any) => void, keys: string[]) => void;
  canUndo: () => boolean;
  canRedo: () => boolean;
  clear: () => void;
}

export function createUndoStore(): UndoStore {
  let past: Record<string, unknown>[] = [];
  let future: Record<string, unknown>[] = [];
  let ignoreNext = false;

  return {
    /**
     * Save a snapshot of the current state before changes
     * @param state Current state object
     * @param keys Keys to include in the snapshot
     */
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    saveSnapshot: (state: any, keys: string[]) => {
      if (ignoreNext) {
        ignoreNext = false;
        return;
      }
      const snapshot: Record<string, unknown> = {};
      for (const key of keys) {
        // Deep clone arrays and objects to prevent mutation issues
        const value = state[key];
        snapshot[key] = Array.isArray(value)
          ? JSON.parse(JSON.stringify(value))
          : value;
      }
      past.push(snapshot);
      if (past.length > MAX_HISTORY) past.shift();
      future = []; // Clear redo stack on new change
    },

    /**
     * Undo to the previous state
     * @param get Zustand get function
     * @param set Zustand set function
     * @param keys Keys to restore from snapshot
     */
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    undo: (get: () => any, set: (s: any) => void, keys: string[]) => {
      if (past.length === 0) return;
      const current: Record<string, unknown> = {};
      const state = get();
      for (const key of keys) {
        current[key] = state[key];
      }
      future.push(current);
      const prev = past.pop()!;
      ignoreNext = true;
      set({ ...prev, isDirty: true });
    },

    /**
     * Redo to the next state
     * @param get Zustand get function
     * @param set Zustand set function
     * @param keys Keys to restore from snapshot
     */
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    redo: (get: () => any, set: (s: any) => void, keys: string[]) => {
      if (future.length === 0) return;
      const current: Record<string, unknown> = {};
      const state = get();
      for (const key of keys) {
        current[key] = state[key];
      }
      past.push(current);
      const next = future.pop()!;
      ignoreNext = true;
      set({ ...next, isDirty: true });
    },

    /**
     * Check if undo is available
     */
    canUndo: () => past.length > 0,

    /**
     * Check if redo is available
     */
    canRedo: () => future.length > 0,

    /**
     * Clear all undo/redo history
     */
    clear: () => {
      past = [];
      future = [];
    },
  };
}
