import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Layout } from './Layout';

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

describe('Layout', () => {
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
});
