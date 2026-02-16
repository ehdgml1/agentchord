import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BaseNode } from './BaseNode';

vi.mock('@xyflow/react', () => ({
  Handle: ({ type, position }: { type: string; position: string }) => (
    <div data-testid={`handle-${type}`} data-position={position}>
      Handle
    </div>
  ),
  Position: {
    Left: 'left',
    Right: 'right',
    Top: 'top',
    Bottom: 'bottom',
  },
}));

describe('BaseNode', () => {
  it('renders children content', () => {
    render(
      <BaseNode color="#3B82F6">
        <div>Test Content</div>
      </BaseNode>
    );
    expect(screen.getByText('Test Content')).toBeInTheDocument();
  });

  it('renders with border color from prop', () => {
    const { container } = render(
      <BaseNode color="#3B82F6">
        <div>Content</div>
      </BaseNode>
    );
    const node = container.querySelector('.border-2');
    expect(node).toHaveStyle({ borderColor: '#3B82F6' });
  });

  it('renders input handle by default', () => {
    render(
      <BaseNode color="#3B82F6">
        <div>Content</div>
      </BaseNode>
    );
    expect(screen.getByTestId('handle-target')).toBeInTheDocument();
  });

  it('renders output handle by default', () => {
    render(
      <BaseNode color="#3B82F6">
        <div>Content</div>
      </BaseNode>
    );
    expect(screen.getByTestId('handle-source')).toBeInTheDocument();
  });

  it('hides input handle when hasInput=false', () => {
    render(
      <BaseNode color="#3B82F6" hasInput={false}>
        <div>Content</div>
      </BaseNode>
    );
    expect(screen.queryByTestId('handle-target')).not.toBeInTheDocument();
  });

  it('hides output handle when hasOutput=false', () => {
    render(
      <BaseNode color="#3B82F6" hasOutput={false}>
        <div>Content</div>
      </BaseNode>
    );
    expect(screen.queryByTestId('handle-source')).not.toBeInTheDocument();
  });

  it('adds ring classes when selected=true', () => {
    const { container } = render(
      <BaseNode color="#3B82F6" selected={true}>
        <div>Content</div>
      </BaseNode>
    );
    const node = container.querySelector('.ring-2');
    expect(node).toBeInTheDocument();
    expect(node).toHaveClass('ring-primary');
    expect(node).toHaveClass('ring-offset-2');
  });

  it('has no ring classes when selected=false by default', () => {
    const { container } = render(
      <BaseNode color="#3B82F6">
        <div>Content</div>
      </BaseNode>
    );
    const node = container.querySelector('.border-2');
    expect(node).not.toHaveClass('ring-2');
    expect(node).not.toHaveClass('ring-primary');
  });

  it('input handle has position left', () => {
    render(
      <BaseNode color="#3B82F6">
        <div>Content</div>
      </BaseNode>
    );
    const inputHandle = screen.getByTestId('handle-target');
    expect(inputHandle).toHaveAttribute('data-position', 'left');
  });

  it('output handle has position right', () => {
    render(
      <BaseNode color="#3B82F6">
        <div>Content</div>
      </BaseNode>
    );
    const outputHandle = screen.getByTestId('handle-source');
    expect(outputHandle).toHaveAttribute('data-position', 'right');
  });

  it('renders with min-w-[180px] class', () => {
    const { container } = render(
      <BaseNode color="#3B82F6">
        <div>Content</div>
      </BaseNode>
    );
    const node = container.querySelector('.min-w-\\[180px\\]');
    expect(node).toBeInTheDocument();
  });

  it('renders with rounded-lg class', () => {
    const { container } = render(
      <BaseNode color="#3B82F6">
        <div>Content</div>
      </BaseNode>
    );
    const node = container.querySelector('.rounded-lg');
    expect(node).toBeInTheDocument();
  });

  it('renders with bg-card class', () => {
    const { container } = render(
      <BaseNode color="#3B82F6">
        <div>Content</div>
      </BaseNode>
    );
    const node = container.querySelector('.bg-card');
    expect(node).toBeInTheDocument();
  });

  it('renders with shadow-md class', () => {
    const { container } = render(
      <BaseNode color="#3B82F6">
        <div>Content</div>
      </BaseNode>
    );
    const node = container.querySelector('.shadow-md');
    expect(node).toBeInTheDocument();
  });

  it('can hide both handles', () => {
    render(
      <BaseNode color="#3B82F6" hasInput={false} hasOutput={false}>
        <div>Content</div>
      </BaseNode>
    );
    expect(screen.queryByTestId('handle-target')).not.toBeInTheDocument();
    expect(screen.queryByTestId('handle-source')).not.toBeInTheDocument();
  });
});
