import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AuthPage } from './AuthPage';
import { useAuthStore } from '../../stores/authStore';

const mockLogin = vi.fn();
const mockRegister = vi.fn();
const mockClearError = vi.fn();

vi.mock('../../stores/authStore', () => ({
  useAuthStore: vi.fn(() => ({
    login: mockLogin,
    register: mockRegister,
    isLoading: false,
    error: null,
    clearError: mockClearError,
  })),
}));

describe('AuthPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders AgentChord title', () => {
    render(<AuthPage />);
    expect(screen.getByText('AgentChord')).toBeInTheDocument();
  });

  it('renders Sign In button in login mode', () => {
    render(<AuthPage />);
    expect(screen.getByRole('button', { name: 'Sign In' })).toBeInTheDocument();
  });

  it('renders email and password fields', () => {
    render(<AuthPage />);
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });

  it('renders "Don\'t have an account? Sign up" link', () => {
    render(<AuthPage />);
    expect(screen.getByText("Don't have an account? Sign up")).toBeInTheDocument();
  });

  it('switches to register mode when toggle clicked', async () => {
    const user = userEvent.setup();
    render(<AuthPage />);

    const toggleButton = screen.getByText("Don't have an account? Sign up");
    await user.click(toggleButton);

    expect(screen.getByRole('button', { name: 'Create Account' })).toBeInTheDocument();
  });

  it('shows "Create Account" in register mode', async () => {
    const user = userEvent.setup();
    render(<AuthPage />);

    await user.click(screen.getByText("Don't have an account? Sign up"));

    expect(screen.getByRole('button', { name: 'Create Account' })).toBeInTheDocument();
  });

  it('shows "Already have an account? Sign in" in register mode', async () => {
    const user = userEvent.setup();
    render(<AuthPage />);

    await user.click(screen.getByText("Don't have an account? Sign up"));

    expect(screen.getByText('Already have an account? Sign in')).toBeInTheDocument();
  });

  it('calls login on form submit in login mode', async () => {
    const user = userEvent.setup();
    render(<AuthPage />);

    const emailInput = screen.getByLabelText(/email/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const submitButton = screen.getByRole('button', { name: 'Sign In' });

    await user.type(emailInput, 'test@example.com');
    await user.type(passwordInput, 'password123');
    await user.click(submitButton);

    expect(mockLogin).toHaveBeenCalledWith('test@example.com', 'password123');
  });

  it('calls register on form submit in register mode', async () => {
    const user = userEvent.setup();
    render(<AuthPage />);

    const emailInput = screen.getByLabelText(/email/i);
    const passwordInput = screen.getByLabelText(/password/i);

    await user.click(screen.getByText("Don't have an account? Sign up"));

    await user.type(emailInput, 'test@example.com');
    await user.type(passwordInput, 'password123');
    await user.click(screen.getByRole('button', { name: 'Create Account' }));

    expect(mockRegister).toHaveBeenCalledWith('test@example.com', 'password123');
  });

  it('shows "Please wait..." when loading', () => {
    vi.mocked(useAuthStore).mockReturnValue({
      login: mockLogin,
      register: mockRegister,
      isLoading: true,
      error: null,
      clearError: mockClearError,
    });

    render(<AuthPage />);

    expect(screen.getByRole('button', { name: 'Please wait...' })).toBeInTheDocument();
  });

  it('disables inputs when loading', () => {
    vi.mocked(useAuthStore).mockReturnValue({
      login: mockLogin,
      register: mockRegister,
      isLoading: true,
      error: null,
      clearError: mockClearError,
    });

    render(<AuthPage />);

    expect(screen.getByLabelText(/email/i)).toBeDisabled();
    expect(screen.getByLabelText(/password/i)).toBeDisabled();
  });

  it('shows error message when error is set', () => {
    vi.mocked(useAuthStore).mockReturnValue({
      login: mockLogin,
      register: mockRegister,
      isLoading: false,
      error: 'Invalid credentials',
      clearError: mockClearError,
    });

    render(<AuthPage />);

    expect(screen.getByText('Invalid credentials')).toBeInTheDocument();
  });

  it('clears error when mode toggled', async () => {
    const user = userEvent.setup();
    render(<AuthPage />);

    await user.click(screen.getByText("Don't have an account? Sign up"));

    expect(mockClearError).toHaveBeenCalled();
  });

  it('submit button disabled when email empty', () => {
    render(<AuthPage />);

    const submitButton = screen.getByRole('button', { name: 'Sign In' });

    expect(submitButton).toBeDisabled();
  });

  it('submit button disabled when password empty', async () => {
    const user = userEvent.setup();
    render(<AuthPage />);

    const emailInput = screen.getByLabelText(/email/i);
    await user.type(emailInput, 'test@example.com');

    const submitButton = screen.getByRole('button', { name: 'Sign In' });

    expect(submitButton).toBeDisabled();
  });

  it('renders sign-in description text', () => {
    render(<AuthPage />);
    expect(screen.getByText('Sign in to your account to continue')).toBeInTheDocument();
  });
});
