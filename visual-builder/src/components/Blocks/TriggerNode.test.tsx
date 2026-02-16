import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TriggerNode } from './TriggerNode';

// Mock @xyflow/react
vi.mock('@xyflow/react', () => ({
  Handle: ({ type, position }: any) => <div data-testid={`handle-${type}`} />,
  Position: { Left: 'left', Right: 'right', Top: 'top', Bottom: 'bottom' },
}));

// Mock BaseNode
vi.mock('./BaseNode', () => ({
  BaseNode: ({ children, selected, hasInput, hasOutput }: any) => (
    <div
      data-testid="base-node"
      data-selected={selected}
      data-has-input={hasInput}
      data-has-output={hasOutput}
    >
      {children}
    </div>
  ),
}));

// Mock cronUtils
vi.mock('../../lib/cronUtils', () => ({
  cronToHuman: (expr: string) => `Human: ${expr}`,
  formatNextRun: (date: Date) => `Next: ${date.toISOString()}`,
}));

describe('TriggerNode', () => {
  const defaultCronProps = {
    id: 'test-node',
    type: 'trigger',
    selected: false,
    isConnectable: true,
    xPos: 0,
    yPos: 0,
    data: {
      triggerType: 'cron' as const,
      cronExpression: '0 9 * * *',
      nextRunAt: '2026-02-12T09:00:00Z',
    },
    dragging: false,
    zIndex: 0,
  };

  const defaultWebhookProps = {
    ...defaultCronProps,
    data: {
      triggerType: 'webhook' as const,
      webhookPath: 'webhook-123',
    },
  };

  describe('Cron Trigger', () => {
    it('renders "Schedule" title for cron type', () => {
      render(<TriggerNode {...defaultCronProps} />);
      expect(screen.getByText('Schedule')).toBeInTheDocument();
    });

    it('renders "Cron Trigger" subtitle', () => {
      render(<TriggerNode {...defaultCronProps} />);
      expect(screen.getByText('Cron Trigger')).toBeInTheDocument();
    });

    it('renders Clock icon for cron type', () => {
      const { container } = render(<TriggerNode {...defaultCronProps} />);
      const svg = container.querySelector('svg');
      expect(svg).toBeInTheDocument();
    });

    it('displays human-readable cron expression', () => {
      render(<TriggerNode {...defaultCronProps} />);
      expect(screen.getByText('Human: 0 9 * * *')).toBeInTheDocument();
    });

    it('displays raw cron expression in code block', () => {
      render(<TriggerNode {...defaultCronProps} />);
      const codeBlock = screen.getByText('0 9 * * *');
      expect(codeBlock.tagName).toBe('CODE');
    });

    it('displays next run time when provided', () => {
      render(<TriggerNode {...defaultCronProps} />);
      expect(screen.getByText(/Next:/)).toBeInTheDocument();
    });

    it('does not display next run when not provided', () => {
      const props = {
        ...defaultCronProps,
        data: {
          ...defaultCronProps.data,
          nextRunAt: undefined,
        },
      };
      const { queryByText } = render(<TriggerNode {...props} />);
      expect(queryByText(/Next:/)).not.toBeInTheDocument();
    });

    it('does not display cron expression when not provided', () => {
      const props = {
        ...defaultCronProps,
        data: {
          triggerType: 'cron' as const,
        },
      };
      const { container } = render(<TriggerNode {...props} />);
      const codeBlock = container.querySelector('code');
      expect(codeBlock).not.toBeInTheDocument();
    });
  });

  describe('Webhook Trigger', () => {
    it('renders "Webhook" title for webhook type', () => {
      render(<TriggerNode {...defaultWebhookProps} />);
      expect(screen.getByText('Webhook')).toBeInTheDocument();
    });

    it('renders "HTTP Trigger" subtitle', () => {
      render(<TriggerNode {...defaultWebhookProps} />);
      expect(screen.getByText('HTTP Trigger')).toBeInTheDocument();
    });

    it('renders Globe icon for webhook type', () => {
      const { container } = render(<TriggerNode {...defaultWebhookProps} />);
      const svg = container.querySelector('svg');
      expect(svg).toBeInTheDocument();
    });

    it('displays webhook URL when webhookPath provided', () => {
      render(<TriggerNode {...defaultWebhookProps} />);
      expect(screen.getByText('/api/webhooks/webhook-123')).toBeInTheDocument();
    });

    it('does not display webhook URL when webhookPath not provided', () => {
      const props = {
        ...defaultWebhookProps,
        data: {
          triggerType: 'webhook' as const,
        },
      };
      const { queryByText } = render(<TriggerNode {...props} />);
      expect(queryByText(/\/api\/webhooks\//)).not.toBeInTheDocument();
    });
  });

  describe('Common behavior', () => {
    it('passes hasInput=false to BaseNode', () => {
      render(<TriggerNode {...defaultCronProps} />);
      const baseNode = screen.getByTestId('base-node');
      expect(baseNode).toHaveAttribute('data-has-input', 'false');
    });

    it('passes hasOutput=true to BaseNode', () => {
      render(<TriggerNode {...defaultCronProps} />);
      const baseNode = screen.getByTestId('base-node');
      expect(baseNode).toHaveAttribute('data-has-output', 'true');
    });

    it('passes selected prop to BaseNode', () => {
      render(<TriggerNode {...defaultCronProps} selected={true} />);
      const baseNode = screen.getByTestId('base-node');
      expect(baseNode).toHaveAttribute('data-selected', 'true');
    });
  });
});
