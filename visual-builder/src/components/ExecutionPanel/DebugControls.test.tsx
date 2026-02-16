import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { DebugControls } from './DebugControls';

// Mock UI components
vi.mock('../ui/button', () => ({
  Button: ({ children, onClick, disabled, variant, size, title }: any) => (
    <button
      onClick={onClick}
      disabled={disabled}
      data-variant={variant}
      data-size={size}
      title={title}
    >
      {children}
    </button>
  ),
}));

vi.mock('../ui/badge', () => ({
  Badge: ({ children, variant, className }: any) => (
    <span data-testid="badge" data-variant={variant} className={className}>
      {children}
    </span>
  ),
}));

describe('DebugControls', () => {
  const mockOnContinue = vi.fn();
  const mockOnStep = vi.fn();
  const mockOnStop = vi.fn();

  const defaultProps = {
    isDebugging: true,
    isPaused: true,
    currentNode: 'node-1',
    isConnected: true,
    onContinue: mockOnContinue,
    onStep: mockOnStep,
    onStop: mockOnStop,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns null when not debugging', () => {
    const { container } = render(
      <DebugControls {...defaultProps} isDebugging={false} />
    );

    expect(container.firstChild).toBeNull();
  });

  it('renders debug controls when debugging', () => {
    render(<DebugControls {...defaultProps} />);

    expect(screen.getByTestId('badge')).toBeInTheDocument();
  });

  it('shows connected status when connected', () => {
    render(<DebugControls {...defaultProps} />);

    const badge = screen.getByTestId('badge');
    expect(badge).toHaveTextContent('Debug Active');
    expect(badge).toHaveAttribute('data-variant', 'default');
  });

  it('shows disconnected status when not connected', () => {
    render(<DebugControls {...defaultProps} isConnected={false} />);

    const badge = screen.getByTestId('badge');
    expect(badge).toHaveTextContent('Disconnected');
    expect(badge).toHaveAttribute('data-variant', 'secondary');
  });

  it('displays current node when paused', () => {
    render(<DebugControls {...defaultProps} />);

    expect(screen.getByText(/Paused at:/i)).toBeInTheDocument();
    expect(screen.getByText('node-1')).toBeInTheDocument();
  });

  it('does not display current node when not paused', () => {
    render(<DebugControls {...defaultProps} isPaused={false} currentNode={null} />);

    expect(screen.queryByText(/Paused at:/i)).not.toBeInTheDocument();
  });

  it('renders continue button', () => {
    render(<DebugControls {...defaultProps} />);

    const continueButton = screen.getByTitle('Continue execution');
    expect(continueButton).toBeInTheDocument();
    expect(continueButton).not.toBeDisabled();
  });

  it('renders step button', () => {
    render(<DebugControls {...defaultProps} />);

    const stepButton = screen.getByTitle('Step to next node');
    expect(stepButton).toBeInTheDocument();
    expect(stepButton).not.toBeDisabled();
  });

  it('renders stop button', () => {
    render(<DebugControls {...defaultProps} />);

    const stopButton = screen.getByTitle('Stop debugging');
    expect(stopButton).toBeInTheDocument();
    expect(stopButton).not.toBeDisabled();
  });

  it('calls onContinue when continue button is clicked', () => {
    render(<DebugControls {...defaultProps} />);

    const continueButton = screen.getByTitle('Continue execution');
    fireEvent.click(continueButton);

    expect(mockOnContinue).toHaveBeenCalledTimes(1);
  });

  it('calls onStep when step button is clicked', () => {
    render(<DebugControls {...defaultProps} />);

    const stepButton = screen.getByTitle('Step to next node');
    fireEvent.click(stepButton);

    expect(mockOnStep).toHaveBeenCalledTimes(1);
  });

  it('calls onStop when stop button is clicked', () => {
    render(<DebugControls {...defaultProps} />);

    const stopButton = screen.getByTitle('Stop debugging');
    fireEvent.click(stopButton);

    expect(mockOnStop).toHaveBeenCalledTimes(1);
  });

  it('disables continue and step buttons when not paused', () => {
    render(<DebugControls {...defaultProps} isPaused={false} />);

    const continueButton = screen.getByTitle('Continue execution');
    const stepButton = screen.getByTitle('Step to next node');

    expect(continueButton).toBeDisabled();
    expect(stepButton).toBeDisabled();
  });

  it('disables all buttons when not connected', () => {
    render(<DebugControls {...defaultProps} isConnected={false} />);

    const continueButton = screen.getByTitle('Continue execution');
    const stepButton = screen.getByTitle('Step to next node');
    const stopButton = screen.getByTitle('Stop debugging');

    expect(continueButton).toBeDisabled();
    expect(stepButton).toBeDisabled();
    expect(stopButton).toBeDisabled();
  });

  it('applies correct button variants', () => {
    render(<DebugControls {...defaultProps} />);

    const stopButton = screen.getByTitle('Stop debugging');
    expect(stopButton).toHaveAttribute('data-variant', 'destructive');
  });
});
