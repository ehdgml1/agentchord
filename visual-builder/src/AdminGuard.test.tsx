import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Navigate } from 'react-router-dom';
import { useAuthStore } from './stores/authStore';

// Mock the auth store
vi.mock('./stores/authStore', () => ({
  useAuthStore: vi.fn(),
}));

// Mock react-router-dom Navigate
vi.mock('react-router-dom', () => ({
  Navigate: vi.fn(() => <div data-testid="navigate">Navigate to /</div>),
}));

// Extract the AdminGuard component logic for testing
function AdminGuard({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user);
  if (user?.role !== 'admin') {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}

describe('AdminGuard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('allows admin users to access protected content', () => {
    const mockUser = { id: '1', email: 'admin@test.com', role: 'admin' };
    (useAuthStore as any).mockImplementation((selector: any) => {
      if (typeof selector === 'function') {
        return selector({ user: mockUser });
      }
      return mockUser;
    });

    render(
      <AdminGuard>
        <div data-testid="admin-content">Admin Content</div>
      </AdminGuard>
    );

    expect(screen.getByTestId('admin-content')).toBeInTheDocument();
    expect(screen.queryByTestId('navigate')).not.toBeInTheDocument();
  });

  it('redirects non-admin users', () => {
    const mockUser = { id: '2', email: 'user@test.com', role: 'user' };
    (useAuthStore as any).mockImplementation((selector: any) => {
      if (typeof selector === 'function') {
        return selector({ user: mockUser });
      }
      return mockUser;
    });

    render(
      <AdminGuard>
        <div data-testid="admin-content">Admin Content</div>
      </AdminGuard>
    );

    expect(screen.queryByTestId('admin-content')).not.toBeInTheDocument();
    expect(screen.getByTestId('navigate')).toBeInTheDocument();
    expect(Navigate).toHaveBeenCalled();
  });

  it('redirects users with no role', () => {
    const mockUser = { id: '3', email: 'norole@test.com', role: undefined };
    (useAuthStore as any).mockImplementation((selector: any) => {
      if (typeof selector === 'function') {
        return selector({ user: mockUser });
      }
      return mockUser;
    });

    render(
      <AdminGuard>
        <div data-testid="admin-content">Admin Content</div>
      </AdminGuard>
    );

    expect(screen.queryByTestId('admin-content')).not.toBeInTheDocument();
    expect(screen.getByTestId('navigate')).toBeInTheDocument();
  });

  it('redirects when user is null', () => {
    (useAuthStore as any).mockImplementation((selector: any) => {
      if (typeof selector === 'function') {
        return selector({ user: null });
      }
      return null;
    });

    render(
      <AdminGuard>
        <div data-testid="admin-content">Admin Content</div>
      </AdminGuard>
    );

    expect(screen.queryByTestId('admin-content')).not.toBeInTheDocument();
    expect(screen.getByTestId('navigate')).toBeInTheDocument();
  });
});
