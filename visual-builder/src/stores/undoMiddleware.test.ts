/**
 * Tests for undo/redo middleware
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { createUndoStore } from './undoMiddleware';

describe('createUndoStore', () => {
  let undoStore: ReturnType<typeof createUndoStore>;
  let state: Record<string, unknown>;
  const keys = ['nodes', 'edges'];

  beforeEach(() => {
    undoStore = createUndoStore();
    state = {
      nodes: [{ id: '1', type: 'agent' }],
      edges: [],
      other: 'value',
    };
  });

  it('should save snapshots', () => {
    expect(undoStore.canUndo()).toBe(false);
    undoStore.saveSnapshot(state, keys);
    expect(undoStore.canUndo()).toBe(true);
  });

  it('should undo to previous state', () => {
    const initialNodes = [{ id: '1', type: 'agent' }];
    undoStore.saveSnapshot(state, keys);

    // Change state
    state.nodes = [{ id: '1', type: 'agent' }, { id: '2', type: 'trigger' }];

    // Undo should restore to saved snapshot
    undoStore.undo(
      () => state,
      (patch) => Object.assign(state, patch),
      keys
    );

    expect(state.nodes).toEqual(initialNodes);
    expect(undoStore.canRedo()).toBe(true);
  });

  it('should redo to next state', () => {
    undoStore.saveSnapshot(state, keys);

    // Change and save
    const changedNodes = [{ id: '1', type: 'agent' }, { id: '2', type: 'trigger' }];
    state.nodes = changedNodes;
    undoStore.saveSnapshot(state, keys);

    // Undo
    let newState: Record<string, unknown> = {};
    undoStore.undo(
      () => state,
      (patch) => Object.assign(newState, patch),
      keys
    );

    // Redo
    undoStore.redo(
      () => newState,
      (patch) => Object.assign(newState, patch),
      keys
    );

    expect(newState.nodes).toEqual(changedNodes);
    expect(undoStore.canRedo()).toBe(false);
  });

  it('should clear redo stack on new change', () => {
    undoStore.saveSnapshot(state, keys);

    // Change and save
    state.nodes = [{ id: '2', type: 'trigger' }];
    undoStore.saveSnapshot(state, keys);

    // Undo
    undoStore.undo(
      () => state,
      (patch) => Object.assign(state, patch),
      keys
    );

    expect(undoStore.canRedo()).toBe(true);

    // New change should clear redo (after the ignored snapshot)
    state.nodes = [{ id: '3', type: 'condition' }];
    undoStore.saveSnapshot(state, keys); // This is ignored due to ignoreNext flag
    undoStore.saveSnapshot(state, keys); // This one actually saves and clears future
    expect(undoStore.canRedo()).toBe(false);
  });

  it('should limit history to MAX_HISTORY', () => {
    // Save 51 snapshots
    for (let i = 0; i < 51; i++) {
      state.nodes = [{ id: String(i) }];
      undoStore.saveSnapshot(state, keys);
    }

    // Count undos (should be limited to 50)
    let undoCount = 0;
    while (undoStore.canUndo()) {
      undoCount++;
      undoStore.undo(
        () => state,
        (patch) => Object.assign(state, patch),
        keys
      );
    }

    expect(undoCount).toBeLessThanOrEqual(50);
  });

  it('should clear history', () => {
    undoStore.saveSnapshot(state, keys);
    expect(undoStore.canUndo()).toBe(true);

    undoStore.clear();
    expect(undoStore.canUndo()).toBe(false);
    expect(undoStore.canRedo()).toBe(false);
  });
});
