/**
 * Admin Layout component
 * Provides navigation and role-based access control for admin features
 */

import { useState } from 'react';
import { UserManagement } from './UserManagement';
import { AuditLogViewer } from './AuditLogViewer';
import { ABTestDashboard } from './ABTestDashboard';
import { Button } from '../ui/button';

type AdminSection = 'users' | 'audit' | 'ab-tests';

interface AdminLayoutProps {
  userRole?: string;
}

export function AdminLayout({ userRole = 'admin' }: AdminLayoutProps) {
  const [activeSection, setActiveSection] = useState<AdminSection>('users');

  if (userRole !== 'admin') {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-2">Access Denied</h1>
          <p className="text-muted-foreground">
            You need admin privileges to access this section.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <aside className="w-64 border-r border-border bg-card">
        <div className="p-6 border-b border-border">
          <h1 className="text-2xl font-bold">Admin Panel</h1>
        </div>
        <nav className="p-4 space-y-2">
          <Button
            variant={activeSection === 'users' ? 'default' : 'ghost'}
            className="w-full justify-start"
            onClick={() => setActiveSection('users')}
          >
            User Management
          </Button>
          <Button
            variant={activeSection === 'audit' ? 'default' : 'ghost'}
            className="w-full justify-start"
            onClick={() => setActiveSection('audit')}
          >
            Audit Logs
          </Button>
          <Button
            variant={activeSection === 'ab-tests' ? 'default' : 'ghost'}
            className="w-full justify-start"
            onClick={() => setActiveSection('ab-tests')}
          >
            A/B Tests
          </Button>
        </nav>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        <div className="p-8">
          <div className="mb-6">
            <div className="text-sm text-muted-foreground">
              Admin / {activeSection.replace('-', ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
            </div>
          </div>

          {activeSection === 'users' && <UserManagement />}
          {activeSection === 'audit' && <AuditLogViewer />}
          {activeSection === 'ab-tests' && <ABTestDashboard />}
        </div>
      </main>
    </div>
  );
}
