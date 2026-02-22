import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Layout } from './Layout';
import { usePlaygroundStore } from '../../stores/playgroundStore';

// Mock all child components
vi.mock('./Header', () => ({
  Header: () => <div data-testid="header">Header</div>,
}));

vi.mock('../Sidebar/Sidebar', () => ({
  Sidebar: () => <div data-testid="sidebar">Sidebar</div>,
}));

vi.mock('../PropertiesPanel/PropertiesPanel', () => ({
  PropertiesPanel: () => <div data-testid="properties-panel">PropertiesPanel</div>,
}));

vi.mock('../CodePanel/CodePanel', () => ({
  CodePanel: () => <div data-testid="code-panel">CodePanel</div>,
}));

vi.mock('../ExecutionPanel', () => ({
  ExecutionPanel: () => <div data-testid="execution-panel">ExecutionPanel</div>,
}));

vi.mock('../PlaygroundPanel/PlaygroundPanel', () => ({
  PlaygroundPanel: () => <div data-testid="playground-panel">PlaygroundPanel</div>,
}));

vi.mock('../SchedulePanel/SchedulePanel', () => ({
  SchedulePanel: () => <div data-testid="schedule-panel">SchedulePanel</div>,
}));

describe('Layout', () => {
  beforeEach(() => {
    // Reset playground state before each test
    usePlaygroundStore.setState({ isOpen: false });
  });

  it('renders children content', () => {
    render(
      <Layout>
        <div data-testid="test-child">Test Content</div>
      </Layout>
    );
    expect(screen.getByTestId('test-child')).toBeInTheDocument();
    expect(screen.getByText('Test Content')).toBeInTheDocument();
  });

  it('renders Header component', () => {
    render(<Layout><div /></Layout>);
    expect(screen.getByTestId('header')).toBeInTheDocument();
  });

  it('renders Sidebar component', () => {
    render(<Layout><div /></Layout>);
    expect(screen.getByTestId('sidebar')).toBeInTheDocument();
  });

  it('renders PropertiesPanel component', () => {
    render(<Layout><div /></Layout>);
    expect(screen.getByTestId('properties-panel')).toBeInTheDocument();
  });

  it('renders CodePanel component', () => {
    render(<Layout><div /></Layout>);
    expect(screen.getByTestId('code-panel')).toBeInTheDocument();
  });

  it('renders ExecutionPanel component', () => {
    render(<Layout><div /></Layout>);
    expect(screen.getByTestId('execution-panel')).toBeInTheDocument();
  });

  it('has correct layout structure with flex classes', () => {
    const { container } = render(<Layout><div /></Layout>);
    const rootDiv = container.firstChild as HTMLElement;
    expect(rootDiv).toHaveClass('h-screen', 'flex', 'flex-col');
  });

  it('renders main content area', () => {
    const { container } = render(
      <Layout>
        <div data-testid="canvas">Canvas</div>
      </Layout>
    );
    const main = container.querySelector('main');
    expect(main).toBeInTheDocument();
    expect(main).toHaveClass('flex-1');
  });

  it('renders playground toggle button', () => {
    render(<Layout><div /></Layout>);
    expect(screen.getByText('플레이그라운드')).toBeInTheDocument();
  });

  it('shows properties panel by default', () => {
    render(<Layout><div /></Layout>);
    expect(screen.getByTestId('properties-panel')).toBeInTheDocument();
    expect(screen.queryByTestId('playground-panel')).not.toBeInTheDocument();
  });

  it('shows playground panel when toggled', async () => {
    const user = userEvent.setup();
    render(<Layout><div /></Layout>);

    // Click playground toggle button
    const playgroundButton = screen.getByText('플레이그라운드');
    await user.click(playgroundButton);

    // Playground panel should be shown
    expect(screen.getByTestId('playground-panel')).toBeInTheDocument();
    // Properties panel should be hidden
    expect(screen.queryByTestId('properties-panel')).not.toBeInTheDocument();
  });

  it('toggles back to properties panel', async () => {
    const user = userEvent.setup();
    render(<Layout><div /></Layout>);

    // Open playground
    const playgroundButton = screen.getByText('플레이그라운드');
    await user.click(playgroundButton);
    expect(screen.getByTestId('playground-panel')).toBeInTheDocument();

    // Close playground
    await user.click(playgroundButton);
    expect(screen.getByTestId('properties-panel')).toBeInTheDocument();
    expect(screen.queryByTestId('playground-panel')).not.toBeInTheDocument();
  });
});
