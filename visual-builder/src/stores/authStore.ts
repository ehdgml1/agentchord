/**
 * Zustand store for authentication state
 *
 * Manages user authentication, login/register, and token persistence.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { setAuthToken } from '../services/api';

interface AuthUser {
  id: string;
  email: string;
  role: string;
}

interface AuthState {
  // SECURITY NOTE: Token stored in localStorage for SPA compatibility.
  // localStorage is accessible to XSS attacks. Mitigated by:
  // 1. CSP headers preventing inline script execution
  // 2. Short token expiry (configured in backend JWT_EXPIRE_MINUTES)
  // 3. Content sanitization in user-facing components
  // TODO: Consider httpOnly cookie auth for enhanced security (requires backend changes)
  token: string | null;
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      login: async (email, password) => {
        set({ isLoading: true, error: null });
        try {
          const res = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password }),
          });
          if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err?.error?.message || 'Login failed');
          }
          const data = await res.json();
          setAuthToken(data.token);
          set({
            token: data.token,
            user: { id: data.user_id, email: data.email, role: data.role },
            isAuthenticated: true,
            isLoading: false,
          });
        } catch (e) {
          set({ isLoading: false, error: e instanceof Error ? e.message : 'Login failed' });
        }
      },

      register: async (email, password) => {
        set({ isLoading: true, error: null });
        try {
          const res = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password }),
          });
          if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err?.error?.message || 'Registration failed');
          }
          const data = await res.json();
          setAuthToken(data.token);
          set({
            token: data.token,
            user: { id: data.user_id, email: data.email, role: data.role },
            isAuthenticated: true,
            isLoading: false,
          });
        } catch (e) {
          set({ isLoading: false, error: e instanceof Error ? e.message : 'Registration failed' });
        }
      },

      logout: () => {
        setAuthToken(null);
        set({ token: null, user: null, isAuthenticated: false, error: null });
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ token: state.token, user: state.user, isAuthenticated: state.isAuthenticated }),
      onRehydrateStorage: () => {
        return (state) => {
          if (state?.token) {
            // Check if token is expired by decoding JWT payload
            try {
              const payload = JSON.parse(atob(state.token.split('.')[1]));
              if (payload.exp && payload.exp * 1000 < Date.now()) {
                // Token expired, clear auth state
                state.logout();
                return;
              }
            } catch {
              // Invalid token format, clear auth
              state.logout();
              return;
            }
            setAuthToken(state.token);
          }
        };
      },
    }
  )
);
