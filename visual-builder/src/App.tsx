import { lazy, Suspense, useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'sonner';
import { useAuthStore } from './stores/authStore';
import { ErrorBoundary } from './components/ErrorBoundary/ErrorBoundary';
import { ConfirmProvider } from './components/ui/confirm-dialog';
import { Button } from './components/ui/button';

const AuthPage = lazy(() => import('./components/Auth/AuthPage').then(m => ({ default: m.AuthPage })));
const WorkflowList = lazy(() => import('./pages/WorkflowList').then(m => ({ default: m.WorkflowList })));
const WorkflowEditor = lazy(() => import('./pages/WorkflowEditor').then(m => ({ default: m.WorkflowEditor })));
const AdminLayout = lazy(() => import('./components/Admin/AdminLayout').then(m => ({ default: m.AdminLayout })));

const LoadingFallback = () => (
  <div className="h-screen w-full flex items-center justify-center">
    <div className="text-muted-foreground">Loading...</div>
  </div>
);

const AppHydrationLoader = () => (
  <div className="h-screen w-full flex items-center justify-center">
    <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full" />
  </div>
);

const RouteErrorFallback = () => (
  <div className="flex flex-col items-center justify-center h-screen gap-4">
    <h2 className="text-xl font-semibold">Something went wrong</h2>
    <p className="text-muted-foreground">This page encountered an error.</p>
    <div className="flex gap-2">
      <Button onClick={() => window.location.reload()}>Try Again</Button>
      <Button variant="outline" asChild>
        <a href="/">Go to Dashboard</a>
      </Button>
    </div>
  </div>
);

function AdminGuard({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user);
  if (user?.role !== 'admin') {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}

function AppRoutes() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  if (!isAuthenticated) {
    return (
      <Suspense fallback={<LoadingFallback />}>
        <AuthPage />
      </Suspense>
    );
  }

  return (
    <Suspense fallback={<LoadingFallback />}>
      <Routes>
        <Route
          path="/"
          element={
            <ErrorBoundary fallback={<RouteErrorFallback />}>
              <WorkflowList />
            </ErrorBoundary>
          }
        />
        <Route
          path="/workflows/new"
          element={
            <ErrorBoundary fallback={<RouteErrorFallback />}>
              <WorkflowEditor />
            </ErrorBoundary>
          }
        />
        <Route
          path="/workflows/:id"
          element={
            <ErrorBoundary fallback={<RouteErrorFallback />}>
              <WorkflowEditor />
            </ErrorBoundary>
          }
        />
        <Route
          path="/admin/*"
          element={
            <ErrorBoundary fallback={<RouteErrorFallback />}>
              <AdminGuard>
                <AdminLayout />
              </AdminGuard>
            </ErrorBoundary>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}

function App() {
  const [isHydrated, setIsHydrated] = useState(false);

  useEffect(() => {
    // Wait for Zustand persist to rehydrate
    const unsubFinishHydration = useAuthStore.persist.onFinishHydration(() => {
      setIsHydrated(true);
    });

    // If already hydrated (synchronous storage)
    if (useAuthStore.persist.hasHydrated()) {
      setIsHydrated(true);
    }

    return () => {
      unsubFinishHydration();
    };
  }, []);

  if (!isHydrated) {
    return <AppHydrationLoader />;
  }

  return (
    <ErrorBoundary>
      <BrowserRouter>
        <ConfirmProvider>
          <AppRoutes />
          <Toaster position="bottom-right" richColors />
        </ConfirmProvider>
      </BrowserRouter>
    </ErrorBoundary>
  );
}

export default App;
