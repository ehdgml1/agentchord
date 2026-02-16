import { describe, it, expect, beforeEach } from 'vitest';
import { useDebugStore } from './debugStore';
import type { DebugEvent } from '../types/debug';

describe('debugStore', () => {
  beforeEach(() => {
    useDebugStore.setState({
      isDebugging: false,
      isPaused: false,
      currentNode: null,
      breakpoints: new Set<string>(),
      events: [],
    });
  });

  describe('Initial state', () => {
    it('should have correct initial state', () => {
      const state = useDebugStore.getState();
      expect(state.isDebugging).toBe(false);
      expect(state.isPaused).toBe(false);
      expect(state.currentNode).toBeNull();
      expect(state.breakpoints.size).toBe(0);
      expect(state.events).toEqual([]);
    });
  });

  describe('startDebug', () => {
    it('should set isDebugging=true and clear events', () => {
      useDebugStore.setState({
        events: [
          {
            id: 'evt1',
            type: 'node_execution',
            timestamp: '2024-01-01',
            data: {},
          },
        ],
      });

      useDebugStore.getState().startDebug('wf1', '{}');

      const state = useDebugStore.getState();
      expect(state.isDebugging).toBe(true);
      expect(state.isPaused).toBe(false);
      expect(state.currentNode).toBeNull();
      expect(state.events).toEqual([]);
    });
  });

  describe('stop', () => {
    it('should set isDebugging=false', () => {
      useDebugStore.setState({
        isDebugging: true,
        isPaused: true,
        currentNode: 'node1',
      });

      useDebugStore.getState().stop();

      const state = useDebugStore.getState();
      expect(state.isDebugging).toBe(false);
      expect(state.isPaused).toBe(false);
      expect(state.currentNode).toBeNull();
    });
  });

  describe('toggleBreakpoint', () => {
    it('should add a breakpoint', () => {
      useDebugStore.getState().toggleBreakpoint('node1');

      const state = useDebugStore.getState();
      expect(state.breakpoints.has('node1')).toBe(true);
    });

    it('should remove existing breakpoint', () => {
      useDebugStore.setState({
        breakpoints: new Set(['node1', 'node2']),
      });

      useDebugStore.getState().toggleBreakpoint('node1');

      const state = useDebugStore.getState();
      expect(state.breakpoints.has('node1')).toBe(false);
      expect(state.breakpoints.has('node2')).toBe(true);
    });

    it('should toggle breakpoint multiple times', () => {
      const { toggleBreakpoint } = useDebugStore.getState();

      toggleBreakpoint('node1');
      expect(useDebugStore.getState().breakpoints.has('node1')).toBe(true);

      toggleBreakpoint('node1');
      expect(useDebugStore.getState().breakpoints.has('node1')).toBe(false);

      toggleBreakpoint('node1');
      expect(useDebugStore.getState().breakpoints.has('node1')).toBe(true);
    });
  });

  describe('addEvent', () => {
    it('should append to events array', () => {
      const event1: DebugEvent = {
        id: 'evt1',
        type: 'node_execution',
        timestamp: '2024-01-01',
        data: {},
      };

      const event2: DebugEvent = {
        id: 'evt2',
        type: 'error',
        timestamp: '2024-01-02',
        data: {},
      };

      useDebugStore.getState().addEvent(event1);
      expect(useDebugStore.getState().events).toEqual([event1]);

      useDebugStore.getState().addEvent(event2);
      expect(useDebugStore.getState().events).toEqual([event1, event2]);
    });
  });

  describe('setPaused', () => {
    it('should set paused with nodeId', () => {
      useDebugStore.getState().setPaused(true, 'node1');

      const state = useDebugStore.getState();
      expect(state.isPaused).toBe(true);
      expect(state.currentNode).toBe('node1');
    });

    it('should set paused without nodeId', () => {
      useDebugStore.setState({ currentNode: 'node1' });

      useDebugStore.getState().setPaused(false);

      const state = useDebugStore.getState();
      expect(state.isPaused).toBe(false);
      expect(state.currentNode).toBeNull();
    });
  });

  describe('continueExecution', () => {
    it('should clear paused state', () => {
      useDebugStore.setState({
        isPaused: true,
        currentNode: 'node1',
      });

      useDebugStore.getState().continueExecution();

      const state = useDebugStore.getState();
      expect(state.isPaused).toBe(false);
      expect(state.currentNode).toBeNull();
    });
  });

  describe('step', () => {
    it('should set isPaused=false', () => {
      useDebugStore.setState({ isPaused: true });

      useDebugStore.getState().step();

      expect(useDebugStore.getState().isPaused).toBe(false);
    });
  });

  describe('reset', () => {
    it('should clear all state', () => {
      useDebugStore.setState({
        isDebugging: true,
        isPaused: true,
        currentNode: 'node1',
        events: [
          {
            id: 'evt1',
            type: 'node_execution',
            timestamp: '2024-01-01',
            data: {},
          },
        ],
      });

      useDebugStore.getState().reset();

      const state = useDebugStore.getState();
      expect(state.isDebugging).toBe(false);
      expect(state.isPaused).toBe(false);
      expect(state.currentNode).toBeNull();
      expect(state.events).toEqual([]);
    });
  });
});
