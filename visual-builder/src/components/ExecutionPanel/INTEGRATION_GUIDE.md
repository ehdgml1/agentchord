# Integration Guide

This guide shows how to integrate the execution visualization components into your Visual Builder application.

## Quick Start

### 1. Import Components

```tsx
import {
  ExecutionPanel,
  ExecutionControls,
  ExecutionProgress,
  NodeResultPopup,
  DebugControls,
} from '@/components/ExecutionPanel';
import { useExecutionUpdates } from '@/hooks/useExecutionUpdates';
```

### 2. Basic Integration

Add to your workflow canvas layout:

```tsx
// In your main Layout component
function WorkflowBuilderLayout() {
  return (
    <div className="flex h-screen">
      {/* Sidebar with blocks */}
      <Sidebar />

      {/* Main canvas */}
      <div className="flex-1 flex flex-col">
        <Header />
        <Canvas />
      </div>

      {/* Add Execution Panel on the right */}
      <ExecutionPanel className="w-96 border-l" />
    </div>
  );
}
```

### 3. Add Execution Controls

Create a dedicated execution view:

```tsx
function ExecutionView() {
  const { currentExecution } = useExecutionStore();
  const { execution, isConnected } = useExecutionUpdates(currentExecution?.id);

  return (
    <div className="h-full flex flex-col">
      {/* Controls at the top */}
      <ExecutionControls />

      {/* Progress in the middle */}
      {execution && (
        <div className="p-4 border-b">
          <div className="flex items-center gap-2 mb-2">
            <h3 className="font-semibold">Execution Progress</h3>
            {isConnected && (
              <Badge variant="success" className="gap-1">
                <span className="w-2 h-2 bg-green-500 rounded-full" />
                Live
              </Badge>
            )}
          </div>
          <ExecutionProgress execution={execution} />
        </div>
      )}

      {/* Logs at the bottom */}
      {execution && (
        <div className="flex-1 overflow-auto p-4">
          <LogViewer nodeExecutions={execution.nodeExecutions} />
        </div>
      )}
    </div>
  );
}
```

### 4. Add to Existing Layout

If you have a Layout component, integrate like this:

```tsx
// src/components/Layout/Layout.tsx
import { useState } from 'react';
import { ExecutionPanel } from '../ExecutionPanel';

export function Layout() {
  const [showExecutionPanel, setShowExecutionPanel] = useState(true);

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Left Sidebar */}
      <Sidebar />

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        <Header
          onToggleExecutionPanel={() => setShowExecutionPanel(!showExecutionPanel)}
        />
        <div className="flex-1 flex overflow-hidden">
          <Canvas />
          <PropertiesPanel />
        </div>
      </div>

      {/* Right Execution Panel */}
      {showExecutionPanel && (
        <ExecutionPanel className="w-96 flex-shrink-0" />
      )}
    </div>
  );
}
```

## Advanced Integration

### Modal-Based Execution

Show execution in a modal instead of a sidebar:

```tsx
function WorkflowCanvas() {
  const [showExecution, setShowExecution] = useState(false);
  const { currentExecution } = useExecutionStore();

  return (
    <>
      <Canvas />

      {/* Floating execution button */}
      {currentExecution && (
        <Button
          className="fixed bottom-4 right-4"
          onClick={() => setShowExecution(true)}
        >
          View Execution
        </Button>
      )}

      {/* Execution Modal */}
      <Dialog open={showExecution} onOpenChange={setShowExecution}>
        <DialogContent className="max-w-4xl max-h-[80vh]">
          <DialogHeader>
            <DialogTitle>Workflow Execution</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {currentExecution && (
              <>
                <ExecutionProgress execution={currentExecution} />
                <Separator />
                <LogViewer nodeExecutions={currentExecution.nodeExecutions} />
              </>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
```

### Bottom Panel Layout

Show execution panel at the bottom:

```tsx
function BottomPanelLayout() {
  const [panelHeight, setPanelHeight] = useState(300);
  const { currentExecution } = useExecutionStore();

  return (
    <div className="flex flex-col h-screen">
      {/* Top: Canvas */}
      <div className="flex-1 flex overflow-hidden">
        <Sidebar />
        <Canvas />
        <PropertiesPanel />
      </div>

      {/* Bottom: Execution Panel */}
      {currentExecution && (
        <div
          className="border-t"
          style={{ height: `${panelHeight}px` }}
        >
          <div className="h-full flex">
            <div className="flex-1 overflow-auto">
              <ExecutionControls />
              <div className="p-4">
                <ExecutionProgress execution={currentExecution} />
              </div>
            </div>
            <div className="w-96 border-l overflow-auto">
              <LogViewer nodeExecutions={currentExecution.nodeExecutions} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
```

### With Debug Mode

Full integration with debug controls:

```tsx
function DebugWorkflowView() {
  const { currentExecution, stopExecution, resumeExecution } = useExecutionStore();
  const { execution, isConnected } = useExecutionUpdates(currentExecution?.id);
  const [selectedNode, setSelectedNode] = useState<NodeExecution | null>(null);

  const isDebugMode = execution?.mode === 'debug';
  const isPaused = execution?.status === 'paused';
  const currentNode = execution?.nodeExecutions.find(n => n.status === 'running')?.nodeId;

  const handleContinue = async () => {
    if (execution) {
      await resumeExecution(execution.id);
    }
  };

  const handleStop = async () => {
    if (execution) {
      await stopExecution(execution.id);
    }
  };

  return (
    <div className="h-screen flex flex-col">
      {/* Debug Controls Bar */}
      {isDebugMode && (
        <DebugControls
          isDebugging={isDebugMode}
          isPaused={isPaused}
          currentNode={currentNode || null}
          onContinue={handleContinue}
          onStep={() => console.log('Step')}
          onStop={handleStop}
        />
      )}

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Canvas with node highlighting */}
        <div className="flex-1">
          <Canvas highlightedNode={currentNode} />
        </div>

        {/* Execution Panel */}
        <div className="w-96 border-l flex flex-col">
          <ExecutionControls />
          {execution && (
            <>
              <div className="p-4 border-b">
                <ExecutionProgress execution={execution} />
              </div>
              <div className="flex-1 overflow-auto p-4">
                <LogViewer
                  nodeExecutions={execution.nodeExecutions}
                  onNodeClick={setSelectedNode}
                />
              </div>
            </>
          )}
        </div>
      </div>

      {/* Node Result Popup */}
      <NodeResultPopup
        nodeExecution={selectedNode}
        onClose={() => setSelectedNode(null)}
      />
    </div>
  );
}
```

## State Management

### Using Store Selectors

For better performance, use specific selectors:

```tsx
import { useExecutionStore } from '@/stores/executionStore';

function MyComponent() {
  // Instead of:
  // const { currentExecution, isLoading } = useExecutionStore();

  // Use specific selectors:
  const currentExecution = useExecutionStore(state => state.currentExecution);
  const isLoading = useExecutionStore(state => state.isLoading);

  // This prevents re-renders when unrelated state changes
}
```

### Custom Hook for Execution State

Create a custom hook to encapsulate execution logic:

```tsx
// src/hooks/useWorkflowExecution.ts
import { useState, useCallback } from 'react';
import { useExecutionStore } from '@/stores/executionStore';
import { useWorkflowStore } from '@/stores/workflowStore';
import { useExecutionUpdates } from './useExecutionUpdates';

export function useWorkflowExecution() {
  const workflowId = useWorkflowStore(state => state.workflowId);
  const {
    currentExecution,
    isLoading,
    error,
    runWorkflow,
    stopExecution,
    resumeExecution,
  } = useExecutionStore();

  const { execution: liveExecution, isConnected } = useExecutionUpdates(
    currentExecution?.id || null
  );

  const execution = liveExecution || currentExecution;

  const run = useCallback(
    async (input: string, mode: ExecutionMode) => {
      try {
        await runWorkflow(workflowId, input, mode);
      } catch (err) {
        console.error('Execution failed:', err);
      }
    },
    [workflowId, runWorkflow]
  );

  const stop = useCallback(async () => {
    if (execution) {
      await stopExecution(execution.id);
    }
  }, [execution, stopExecution]);

  const resume = useCallback(async () => {
    if (execution) {
      await resumeExecution(execution.id);
    }
  }, [execution, resumeExecution]);

  return {
    execution,
    isLoading,
    error,
    isConnected,
    run,
    stop,
    resume,
    canRun: !isLoading && (!execution || ['completed', 'failed', 'cancelled'].includes(execution.status)),
    canStop: execution?.status === 'running',
    canResume: execution?.status === 'paused',
  };
}
```

Usage:

```tsx
function ExecutionToolbar() {
  const { execution, run, stop, resume, canRun, canStop, canResume } = useWorkflowExecution();

  return (
    <div className="flex gap-2">
      {canRun && <Button onClick={() => run('{}', 'mock')}>Run</Button>}
      {canStop && <Button onClick={stop} variant="destructive">Stop</Button>}
      {canResume && <Button onClick={resume} variant="secondary">Resume</Button>}
    </div>
  );
}
```

## Styling Customization

### Custom Colors

Override status colors:

```tsx
// In your component or global CSS
const customStatusColors = {
  running: 'text-purple-500 bg-purple-50',
  completed: 'text-emerald-500 bg-emerald-50',
  failed: 'text-rose-500 bg-rose-50',
};

<ExecutionProgress
  execution={execution}
  className="custom-colors"
/>
```

### Dark Mode

Components automatically support dark mode. Test with:

```tsx
// Toggle dark mode
<button onClick={() => document.documentElement.classList.toggle('dark')}>
  Toggle Dark Mode
</button>
```

## Performance Tips

1. **Use WebSocket selectively**: Only connect WebSocket for active executions
```tsx
const shouldConnect = execution?.status === 'running' || execution?.status === 'paused';
const { execution: live } = useExecutionUpdates(shouldConnect ? execution.id : null);
```

2. **Virtualize long lists**: For many node executions, use virtualization
```tsx
import { VirtualList } from '@/components/VirtualList';

<VirtualList
  items={execution.nodeExecutions}
  renderItem={(node) => <NodeExecutionItem node={node} />}
/>
```

3. **Memoize callbacks**: Prevent unnecessary re-renders
```tsx
const handleNodeClick = useCallback((node: NodeExecution) => {
  setSelectedNode(node);
}, []);
```

## Error Handling

### Global Error Boundary

Wrap execution components in an error boundary:

```tsx
import { ErrorBoundary } from 'react-error-boundary';

function ExecutionContainer() {
  return (
    <ErrorBoundary
      fallback={<div>Error loading execution panel</div>}
      onError={(error) => console.error('Execution panel error:', error)}
    >
      <ExecutionPanel />
    </ErrorBoundary>
  );
}
```

### WebSocket Error Handling

The `useExecutionUpdates` hook handles errors internally, but you can display them:

```tsx
function ExecutionView() {
  const { execution, error, isConnected } = useExecutionUpdates(executionId);

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Connection Error</AlertTitle>
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  if (!isConnected) {
    return <div>Connecting...</div>;
  }

  return <ExecutionProgress execution={execution} />;
}
```

## Testing Integration

### Mock Store for Tests

```tsx
import { render, screen } from '@testing-library/react';
import { ExecutionControls } from '@/components/ExecutionPanel';

// Mock the stores
jest.mock('@/stores/executionStore');
jest.mock('@/stores/workflowStore');

test('renders execution controls', () => {
  render(<ExecutionControls />);
  expect(screen.getByText(/run/i)).toBeInTheDocument();
});
```

### Test WebSocket Updates

```tsx
import { renderHook, waitFor } from '@testing-library/react';
import { useExecutionUpdates } from '@/hooks/useExecutionUpdates';

test('receives WebSocket updates', async () => {
  const { result } = renderHook(() => useExecutionUpdates('exec-123'));

  // Simulate WebSocket message
  const ws = (global as any).mockWebSocket;
  ws.onmessage({
    data: JSON.stringify({
      type: 'execution_update',
      execution: { id: 'exec-123', status: 'running' },
    }),
  });

  await waitFor(() => {
    expect(result.current.execution?.status).toBe('running');
  });
});
```

## Troubleshooting

### Components not rendering
- Check if stores are properly initialized
- Verify imports are correct
- Ensure TypeScript compilation succeeded

### WebSocket not connecting
- Verify backend WebSocket endpoint is running
- Check browser console for connection errors
- Ensure execution ID is valid

### State not updating
- Check if store actions are being called
- Verify Zustand store is configured correctly
- Look for console errors

### Styles not applying
- Ensure Tailwind CSS is configured
- Check if shadcn/ui components are installed
- Verify className props are being passed

## Next Steps

1. Integrate components into your main layout
2. Configure WebSocket endpoint in your API client
3. Test with a sample workflow execution
4. Add custom styling if needed
5. Implement error handling
6. Add analytics/logging for execution events
