import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useAuthStore } from './authStore';

// Mock fetch and setAuthToken
const mockFetch = vi.fn();
global.fetch = mockFetch;

vi.mock('../services/api', () => ({
  setAuthToken: vi.fn(),
}));

import { setAuthToken } from '../services/api';

describe('authStore', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    useAuthStore.setState({
      token: null,
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
    });
  });

  describe('login', () => {
    it('authenticates successfully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ token: 'jwt-token', user_id: 'u1', email: 'test@test.com', role: 'admin' }),
      });

      await useAuthStore.getState().login('test@test.com', 'password');

      const state = useAuthStore.getState();
      expect(state.isAuthenticated).toBe(true);
      expect(state.token).toBe('jwt-token');
      expect(state.user?.email).toBe('test@test.com');
      expect(state.user?.role).toBe('admin');
      expect(setAuthToken).toHaveBeenCalledWith('jwt-token');
    });

    it('handles login failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ error: { message: 'Invalid credentials' } }),
      });

      await useAuthStore.getState().login('wrong@test.com', 'bad');

      const state = useAuthStore.getState();
      expect(state.isAuthenticated).toBe(false);
      expect(state.error).toBe('Invalid credentials');
      expect(state.token).toBeNull();
    });

    it('handles network error', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network failed'));

      await useAuthStore.getState().login('test@test.com', 'pass');

      expect(useAuthStore.getState().error).toBe('Network failed');
      expect(useAuthStore.getState().isAuthenticated).toBe(false);
    });

    it('sends correct request payload', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ token: 'jwt-token', user_id: 'u1', email: 'test@test.com', role: 'admin' }),
      });

      await useAuthStore.getState().login('test@test.com', 'password123');

      expect(mockFetch).toHaveBeenCalledWith('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: 'test@test.com', password: 'password123' }),
      });
    });

    it('sets loading state during login', async () => {
      let resolvePromise: (value: Response) => void;
      const promise = new Promise<Response>((resolve) => { resolvePromise = resolve; });
      mockFetch.mockReturnValueOnce(promise);

      const loginPromise = useAuthStore.getState().login('test@test.com', 'pass');
      expect(useAuthStore.getState().isLoading).toBe(true);

      resolvePromise!({ ok: true, json: async () => ({ token: 'jwt', user_id: 'u1', email: 'test@test.com', role: 'admin' }) } as Response);
      await loginPromise;
      expect(useAuthStore.getState().isLoading).toBe(false);
    });
  });

  describe('register', () => {
    it('registers successfully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ token: 'new-token', user_id: 'u2', email: 'new@test.com', role: 'viewer' }),
      });

      await useAuthStore.getState().register('new@test.com', 'password');

      const state = useAuthStore.getState();
      expect(state.isAuthenticated).toBe(true);
      expect(state.user?.role).toBe('viewer');
      expect(state.user?.email).toBe('new@test.com');
      expect(setAuthToken).toHaveBeenCalledWith('new-token');
    });

    it('handles registration failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ error: { message: 'Email already exists' } }),
      });

      await useAuthStore.getState().register('existing@test.com', 'pass');

      expect(useAuthStore.getState().error).toBe('Email already exists');
      expect(useAuthStore.getState().isAuthenticated).toBe(false);
    });

    it('sends correct request payload', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ token: 'jwt', user_id: 'u1', email: 'test@test.com', role: 'viewer' }),
      });

      await useAuthStore.getState().register('new@test.com', 'securepass');

      expect(mockFetch).toHaveBeenCalledWith('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: 'new@test.com', password: 'securepass' }),
      });
    });
  });

  describe('logout', () => {
    it('clears authentication state', () => {
      useAuthStore.setState({
        token: 'jwt-token',
        user: { id: 'u1', email: 'test@test.com', role: 'admin' },
        isAuthenticated: true,
      });

      useAuthStore.getState().logout();

      const state = useAuthStore.getState();
      expect(state.token).toBeNull();
      expect(state.user).toBeNull();
      expect(state.isAuthenticated).toBe(false);
      expect(setAuthToken).toHaveBeenCalledWith(null);
    });

    it('clears errors on logout', () => {
      useAuthStore.setState({
        token: 'jwt-token',
        user: { id: 'u1', email: 'test@test.com', role: 'admin' },
        isAuthenticated: true,
        error: 'Some error',
      });

      useAuthStore.getState().logout();

      expect(useAuthStore.getState().error).toBeNull();
    });
  });

  describe('clearError', () => {
    it('clears error state', () => {
      useAuthStore.setState({ error: 'Some error' });
      useAuthStore.getState().clearError();
      expect(useAuthStore.getState().error).toBeNull();
    });

    it('preserves other state when clearing error', () => {
      useAuthStore.setState({
        token: 'jwt-token',
        user: { id: 'u1', email: 'test@test.com', role: 'admin' },
        isAuthenticated: true,
        error: 'Some error',
      });

      useAuthStore.getState().clearError();

      const state = useAuthStore.getState();
      expect(state.error).toBeNull();
      expect(state.token).toBe('jwt-token');
      expect(state.isAuthenticated).toBe(true);
    });
  });
});
