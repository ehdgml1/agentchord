# Execution Panel Components

A comprehensive set of React components for visualizing and controlling workflow execution in the Visual Builder.

## Components Overview

### 1. ExecutionPanel
Main panel component that displays execution history and logs.

**Location**: `ExecutionPanel.tsx`

**Features**:
- Lists execution history with timestamps and status
- Displays node logs for selected execution
- Auto-refreshes execution list
- Click to view detailed execution

**Props**:
```tsx
interface ExecutionPanelProps {
  className?: string;
}
```

**Usage**:
```tsx
import { ExecutionPanel } from './components/ExecutionPanel';

<ExecutionPanel className="w-80" />
```

### 2. ExecutionControls
Interactive controls for running, stopping, and managing workflow executions.

**Location**: `ExecutionControls.tsx`

**Features**:
- Run workflow with mode selection (mock/full/debug)
- JSON input editor
- Stop/Resume execution buttons
- Real-time status and duration display
- Output and error display

**Usage**:
```tsx
import { ExecutionControls } from './components/ExecutionPanel';

<ExecutionControls />
```

### 3. ExecutionProgress
Progress indicator showing node execution status.

**Location**: `ExecutionProgress.tsx`

**Features**:
- Visual progress bar
- Node-by-node status with icons
- Duration display per node
- Status badges with color coding

**Props**:
```tsx
interface ExecutionProgressProps {
  execution: Execution;
}
```

**Status Colors**:
- **pending/queued**: Gray
- **running**: Blue with pulse animation
- **completed**: Green
- **failed**: Red
- **paused**: Yellow
- **timed_out**: Orange
- **cancelled**: Gray
- **retrying**: Orange with rotate icon

**Usage**:
```tsx
import { ExecutionProgress } from './components/ExecutionPanel';

{currentExecution && (
  <ExecutionProgress execution={currentExecution} />
)}
```

### 4. NodeResultPopup
Modal dialog displaying detailed node execution results.

**Location**: `NodeResultPopup.tsx`

**Features**:
- Full node execution details
- Input/Output JSON viewer
- Error display
- Timestamps and duration
- Retry count
- Scrollable JSON sections

**Props**:
```tsx
interface NodeResultPopupProps {
  nodeExecution: NodeExecution | null;
  onClose: () => void;
}
```

**Usage**:
```tsx
import { NodeResultPopup } from './components/ExecutionPanel';

const [selectedNode, setSelectedNode] = useState<NodeExecution | null>(null);

<NodeResultPopup
  nodeExecution={selectedNode}
  onClose={() => setSelectedNode(null)}
/>
```

### 5. LogViewer
Displays node execution logs with expandable details.

**Location**: `LogViewer.tsx`

**Features**:
- Chronological node execution list
- Color-coded status indicators
- Input/Output preview
- Error highlighting
- Retry indicators

**Props**:
```tsx
interface LogViewerProps {
  nodeExecutions: NodeExecution[];
  className?: string;
}
```

**Usage**:
```tsx
import { LogViewer } from './components/ExecutionPanel';

{execution && (
  <LogViewer nodeExecutions={execution.nodeExecutions} />
)}
```

### 6. DebugControls
Debug mode controls for stepping through execution.

**Location**: `DebugControls.tsx`

**Features**:
- Continue/Pause execution
- Step through nodes
- Stop debugging
- Current node indicator

**Props**:
```tsx
interface DebugControlsProps {
  isDebugging: boolean;
  isPaused: boolean;
  currentNode: string | null;
  onContinue: () => void;
  onStep: () => void;
  onStop: () => void;
}
```

**Usage**:
```tsx
import { DebugControls } from './components/ExecutionPanel';

<DebugControls
  isDebugging={mode === 'debug'}
  isPaused={execution?.status === 'paused'}
  currentNode={currentNodeId}
  onContinue={handleContinue}
  onStep={handleStep}
  onStop={handleStop}
/>
```

## Hooks

### useExecutionUpdates
WebSocket hook for real-time execution updates.

**Location**: `src/hooks/useExecutionUpdates.ts`

**Features**:
- Connects to debug WebSocket endpoint
- Receives live execution updates
- Auto-reconnects on connection loss
- Handles node-level updates
- Error handling

**Returns**:
```tsx
{
  execution: Execution | null;
  isConnected: boolean;
  error: string | null;
}
```

**Usage**:
```tsx
import { useExecutionUpdates } from '../hooks/useExecutionUpdates';

function MyComponent() {
  const [executionId, setExecutionId] = useState<string | null>(null);
  const { execution, isConnected, error } = useExecutionUpdates(executionId);

  return (
    <div>
      {isConnected && <Badge>Live</Badge>}
      {error && <div>Error: {error}</div>}
      {execution && <ExecutionProgress execution={execution} />}
    </div>
  );
}
```

## Store Integration

All components integrate with Zustand stores:

### useExecutionStore
```tsx
import { useExecutionStore } from '../../stores/executionStore';

const {
  executions,          // Execution[]
  currentExecution,    // Execution | null
  isLoading,           // boolean
  error,               // string | null
  runWorkflow,         // (workflowId, input, mode) => Promise<Execution>
  stopExecution,       // (id) => Promise<void>
  resumeExecution,     // (id) => Promise<void>
  fetchExecutions,     // (workflowId?) => Promise<void>
  fetchExecution,      // (id) => Promise<void>
} = useExecutionStore();
```

### useWorkflowStore
```tsx
import { useWorkflowStore } from '../../stores/workflowStore';

const { workflowId, workflowName, nodes, edges } = useWorkflowStore();
```

## Type Definitions

### Execution
```tsx
interface Execution {
  id: string;
  workflowId: string;
  status: ExecutionStatus;
  mode: ExecutionMode;
  triggerType: TriggerType;
  triggerId: string | null;
  input: string;
  output: unknown | null;
  error: string | null;
  nodeExecutions: NodeExecution[];
  startedAt: string;
  completedAt: string | null;
  durationMs: number | null;
}
```

### NodeExecution
```tsx
interface NodeExecution {
  nodeId: string;
  status: ExecutionStatus;
  input: unknown;
  output: unknown | null;
  error: string | null;
  startedAt: string;
  completedAt: string | null;
  durationMs: number | null;
  retryCount: number;
}
```

### ExecutionStatus
```tsx
type ExecutionStatus =
  | 'pending'
  | 'queued'
  | 'running'
  | 'paused'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'retrying'
  | 'timed_out';
```

### ExecutionMode
```tsx
type ExecutionMode = 'full' | 'mock' | 'debug';
```

## Complete Example

```tsx
import { useState } from 'react';
import {
  ExecutionPanel,
  ExecutionControls,
  ExecutionProgress,
  NodeResultPopup,
  DebugControls,
} from './components/ExecutionPanel';
import { useExecutionStore } from './stores/executionStore';
import { useExecutionUpdates } from './hooks/useExecutionUpdates';

export function WorkflowExecutionView() {
  const { currentExecution } = useExecutionStore();
  const [selectedNode, setSelectedNode] = useState<NodeExecution | null>(null);

  // Real-time updates via WebSocket
  const { execution: liveExecution, isConnected } = useExecutionUpdates(
    currentExecution?.id || null
  );

  const execution = liveExecution || currentExecution;
  const isDebugMode = execution?.mode === 'debug';
  const isPaused = execution?.status === 'paused';

  return (
    <div className="flex h-screen">
      {/* Main content area */}
      <div className="flex-1 flex flex-col">
        {/* Debug controls bar */}
        {isDebugMode && (
          <DebugControls
            isDebugging={isDebugMode}
            isPaused={isPaused}
            currentNode={execution?.nodeExecutions.find(n => n.status === 'running')?.nodeId || null}
            onContinue={() => console.log('Continue')}
            onStep={() => console.log('Step')}
            onStop={() => console.log('Stop')}
          />
        )}

        {/* Execution controls */}
        <ExecutionControls />

        {/* Progress display */}
        {execution && (
          <div className="p-4 border-b">
            <ExecutionProgress execution={execution} />
          </div>
        )}
      </div>

      {/* Side panel with execution history and logs */}
      <ExecutionPanel className="w-80" />

      {/* Node result popup */}
      <NodeResultPopup
        nodeExecution={selectedNode}
        onClose={() => setSelectedNode(null)}
      />
    </div>
  );
}
```

## Styling

All components use Tailwind CSS and the shadcn/ui design system. They support dark mode automatically.

### Color Scheme
- **Primary**: Blue for running/active states
- **Success**: Green for completed states
- **Destructive**: Red for failed states
- **Warning**: Yellow/Orange for paused/timeout states
- **Secondary**: Gray for pending/cancelled states

### Animations
- Pulse animation on running nodes
- Spin animation on loading indicators
- Smooth transitions for progress bars
- Fade in/out for dialogs

## API Endpoints

Components expect these backend endpoints:

- `GET /api/executions?workflowId={id}` - List executions
- `GET /api/executions/{id}` - Get execution details
- `POST /api/workflows/{id}/run` - Run workflow
- `POST /api/executions/{id}/stop` - Stop execution
- `POST /api/executions/{id}/resume` - Resume execution
- `WS /ws/debug/{executionId}` - WebSocket for live updates

## WebSocket Protocol

### Connection
```
ws://host/ws/debug/{executionId}
```

### Messages Received
```json
{
  "type": "execution_update",
  "execution": { /* Execution object */ }
}
```

```json
{
  "type": "node_update",
  "nodeExecution": { /* NodeExecution object */ }
}
```

```json
{
  "type": "error",
  "message": "Error message"
}
```

## Testing

Example test setup:

```tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ExecutionControls } from './ExecutionControls';

// Mock stores
jest.mock('../../stores/executionStore');
jest.mock('../../stores/workflowStore');

test('runs workflow on button click', async () => {
  const mockRunWorkflow = jest.fn();

  useExecutionStore.mockReturnValue({
    currentExecution: null,
    isLoading: false,
    error: null,
    runWorkflow: mockRunWorkflow,
  });

  render(<ExecutionControls />);

  const runButton = screen.getByRole('button', { name: /run/i });
  fireEvent.click(runButton);

  await waitFor(() => {
    expect(mockRunWorkflow).toHaveBeenCalled();
  });
});
```

## Troubleshooting

### WebSocket not connecting
- Verify backend WebSocket endpoint is running
- Check CORS and WebSocket upgrade headers
- Ensure execution ID is valid

### Progress not updating
- Check if currentExecution is null
- Verify nodeExecutions array is populated
- Ensure store is receiving updates

### Styles not applying
- Verify Tailwind CSS is configured
- Check if dark mode classes are correct
- Ensure UI components are properly imported

## Future Enhancements

- [ ] Export execution results to JSON/CSV
- [ ] Execution comparison view
- [ ] Performance metrics and charts
- [ ] Execution search and filtering
- [ ] Batch execution management
- [ ] Execution replay/time-travel debugging
