import { memo, useState, type ReactNode } from 'react';
import { useShallow } from 'zustand/react/shallow';
import { Clock, MessageSquare } from 'lucide-react';
import { Header } from './Header';
import { Sidebar } from '../Sidebar/Sidebar';
import { PropertiesPanel } from '../PropertiesPanel/PropertiesPanel';
import { CodePanel } from '../CodePanel/CodePanel';
import { ExecutionPanel } from '../ExecutionPanel';
import { SchedulePanel } from '../SchedulePanel/SchedulePanel';
import { PlaygroundPanel } from '../PlaygroundPanel/PlaygroundPanel';
import { Button } from '../ui/button';
import { useWorkflowStore } from '../../stores/workflowStore';
import { usePlaygroundStore } from '../../stores/playgroundStore';
import { cn } from '../../lib/utils';

interface LayoutProps {
  children: ReactNode;
}

export const Layout = memo(function Layout({ children }: LayoutProps) {
  const [showSchedules, setShowSchedules] = useState(false);
  const backendId = useWorkflowStore(s => s.backendId);
  const { isOpen: showPlayground, toggle: togglePlayground } = usePlaygroundStore(
    useShallow((s) => ({ isOpen: s.isOpen, toggle: s.toggle }))
  );

  return (
    <div className="h-screen flex flex-col">
      <Header />
      <div className="flex-1 flex overflow-hidden">
        <Sidebar />
        <main className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-hidden">
            {children}
          </div>
          <CodePanel />
        </main>
        <aside className={cn(
          'flex flex-col border-l bg-background overflow-hidden',
          showPlayground ? 'w-96' : 'w-80'
        )}>
          {showPlayground ? (
            <PlaygroundPanel />
          ) : (
            <>
              <PropertiesPanel />
              <ExecutionPanel />
              {showSchedules && (
                <div className="border-t max-h-64 overflow-auto shrink-0">
                  {backendId ? (
                    <SchedulePanel workflowId={backendId} />
                  ) : (
                    <div className="p-4 text-center text-sm text-muted-foreground">
                      Save the workflow first to manage schedules.
                    </div>
                  )}
                </div>
              )}
            </>
          )}
          <div className="mt-auto border-t shrink-0">
            {!showPlayground && (
              <Button
                variant={showSchedules ? "secondary" : "ghost"}
                size="sm"
                className="w-full justify-start gap-2 rounded-none h-9"
                onClick={() => setShowSchedules(!showSchedules)}
              >
                <Clock className="w-4 h-4" />
                Schedules
              </Button>
            )}
            <Button
              variant={showPlayground ? "secondary" : "ghost"}
              size="sm"
              className="w-full justify-start gap-2 rounded-none h-9 border-t"
              onClick={togglePlayground}
            >
              <MessageSquare className="w-4 h-4" />
              플레이그라운드
            </Button>
          </div>
        </aside>
      </div>
    </div>
  );
});
