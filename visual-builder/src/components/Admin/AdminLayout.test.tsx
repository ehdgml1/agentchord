/**
 * Tests for AdminLayout component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AdminLayout } from './AdminLayout';

// Mock child components
vi.mock('./UserManagement', () => ({
  UserManagement: () => <div data-testid="user-management">UserManagement</div>,
}));
vi.mock('./AuditLogViewer', () => ({
  AuditLogViewer: () => <div data-testid="audit-log-viewer">AuditLogViewer</div>,
}));
vi.mock('./ABTestDashboard', () => ({
  ABTestDashboard: () => <div data-testid="ab-test-dashboard">ABTestDashboard</div>,
}));

describe('AdminLayout', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Access Control', () => {
    it('renders "Access Denied" for non-admin user', () => {
      render(<AdminLayout userRole="user" />);

      expect(screen.getByText('Access Denied')).toBeInTheDocument();
      expect(screen.queryByText('Admin Panel')).not.toBeInTheDocument();
    });

    it('non-admin message includes "admin privileges"', () => {
      render(<AdminLayout userRole="guest" />);

      expect(screen.getByText(/admin privileges/i)).toBeInTheDocument();
    });

    it('default userRole is "admin" (no prop = works)', () => {
      render(<AdminLayout />);

      expect(screen.getByText('Admin Panel')).toBeInTheDocument();
      expect(screen.queryByText('Access Denied')).not.toBeInTheDocument();
    });

    it('renders "Admin Panel" title for admin user', () => {
      render(<AdminLayout userRole="admin" />);

      expect(screen.getByText('Admin Panel')).toBeInTheDocument();
    });
  });

  describe('Navigation', () => {
    it('renders all 3 nav buttons', () => {
      render(<AdminLayout userRole="admin" />);

      expect(screen.getByRole('button', { name: /user management/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /audit logs/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /a\/b tests/i })).toBeInTheDocument();
    });
  });

  describe('Default Section', () => {
    it('shows UserManagement by default', () => {
      render(<AdminLayout userRole="admin" />);

      expect(screen.getByTestId('user-management')).toBeInTheDocument();
    });

    it('does NOT show AuditLogViewer by default', () => {
      render(<AdminLayout userRole="admin" />);

      expect(screen.queryByTestId('audit-log-viewer')).not.toBeInTheDocument();
    });

    it('does NOT show ABTestDashboard by default', () => {
      render(<AdminLayout userRole="admin" />);

      expect(screen.queryByTestId('ab-test-dashboard')).not.toBeInTheDocument();
    });
  });

  describe('Section Switching', () => {
    it('clicking "Audit Logs" shows AuditLogViewer', async () => {
      const user = userEvent.setup();
      render(<AdminLayout userRole="admin" />);

      const auditLogsButton = screen.getByRole('button', { name: /audit logs/i });
      await user.click(auditLogsButton);

      expect(screen.getByTestId('audit-log-viewer')).toBeInTheDocument();
      expect(screen.queryByTestId('user-management')).not.toBeInTheDocument();
    });

    it('clicking "A/B Tests" shows ABTestDashboard', async () => {
      const user = userEvent.setup();
      render(<AdminLayout userRole="admin" />);

      const abTestsButton = screen.getByRole('button', { name: /a\/b tests/i });
      await user.click(abTestsButton);

      expect(screen.getByTestId('ab-test-dashboard')).toBeInTheDocument();
      expect(screen.queryByTestId('user-management')).not.toBeInTheDocument();
    });

    it('clicking "User Management" switches back', async () => {
      const user = userEvent.setup();
      render(<AdminLayout userRole="admin" />);

      // First switch to Audit Logs
      const auditLogsButton = screen.getByRole('button', { name: /audit logs/i });
      await user.click(auditLogsButton);
      expect(screen.getByTestId('audit-log-viewer')).toBeInTheDocument();

      // Then switch back to User Management
      const userManagementButton = screen.getByRole('button', { name: /user management/i });
      await user.click(userManagementButton);

      expect(screen.getByTestId('user-management')).toBeInTheDocument();
      expect(screen.queryByTestId('audit-log-viewer')).not.toBeInTheDocument();
    });
  });

  describe('Breadcrumb', () => {
    it('shows breadcrumb with section name', () => {
      render(<AdminLayout userRole="admin" />);

      // Default section is 'users', which should be transformed to 'Users'
      expect(screen.getByText(/Admin \/ Users/i)).toBeInTheDocument();
    });

    it('updates breadcrumb when switching to Audit Logs', async () => {
      const user = userEvent.setup();
      render(<AdminLayout userRole="admin" />);

      const auditLogsButton = screen.getByRole('button', { name: /audit logs/i });
      await user.click(auditLogsButton);

      expect(screen.getByText(/Admin \/ Audit/i)).toBeInTheDocument();
    });

    it('updates breadcrumb when switching to A/B Tests', async () => {
      const user = userEvent.setup();
      render(<AdminLayout userRole="admin" />);

      const abTestsButton = screen.getByRole('button', { name: /a\/b tests/i });
      await user.click(abTestsButton);

      expect(screen.getByText(/Admin \/ Ab Tests/i)).toBeInTheDocument();
    });
  });
});
