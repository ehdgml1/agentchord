import { memo, type ReactNode } from 'react';
import { Header } from './Header';
import { Sidebar } from '../Sidebar/Sidebar';
import { PropertiesPanel } from '../PropertiesPanel/PropertiesPanel';
import { CodePanel } from '../CodePanel/CodePanel';
import { ExecutionPanel } from '../ExecutionPanel';

interface LayoutProps {
  children: ReactNode;
}

export const Layout = memo(function Layout({ children }: LayoutProps) {
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
        <div className="flex flex-col">
          <PropertiesPanel />
          <ExecutionPanel />
        </div>
      </div>
    </div>
  );
});
