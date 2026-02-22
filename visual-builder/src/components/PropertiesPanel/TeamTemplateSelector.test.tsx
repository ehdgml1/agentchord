import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TeamTemplateSelector } from './TeamTemplateSelector';
import { TEAM_TEMPLATES } from '../../data/teamTemplates';

describe('TeamTemplateSelector', () => {
  it('renders Quick Start Templates header', () => {
    const onSelect = vi.fn();
    render(<TeamTemplateSelector onSelect={onSelect} />);

    expect(screen.getByText('Quick Start Templates')).toBeInTheDocument();
  });

  it('renders helper text', () => {
    const onSelect = vi.fn();
    render(<TeamTemplateSelector onSelect={onSelect} />);

    expect(
      screen.getByText('Choose a template to get started quickly. You can customize it later.')
    ).toBeInTheDocument();
  });

  it('renders all templates from TEAM_TEMPLATES', () => {
    const onSelect = vi.fn();
    render(<TeamTemplateSelector onSelect={onSelect} />);

    TEAM_TEMPLATES.forEach((template) => {
      expect(screen.getByText(template.name)).toBeInTheDocument();
    });
  });

  it('displays template descriptions', () => {
    const onSelect = vi.fn();
    render(<TeamTemplateSelector onSelect={onSelect} />);

    TEAM_TEMPLATES.forEach((template) => {
      expect(screen.getByText(template.description)).toBeInTheDocument();
    });
  });

  it('displays agent count for each template', () => {
    const onSelect = vi.fn();
    render(<TeamTemplateSelector onSelect={onSelect} />);

    const agentBadges = screen.getAllByText(/\d+ agents/);
    expect(agentBadges).toHaveLength(TEAM_TEMPLATES.length);

    TEAM_TEMPLATES.forEach((template) => {
      const agentCount = template.config.members.length;
      const badgeText = `${agentCount} agents`;
      expect(agentBadges.some((badge) => badge.textContent === badgeText)).toBe(true);
    });
  });

  it('displays template icons', () => {
    const onSelect = vi.fn();
    render(<TeamTemplateSelector onSelect={onSelect} />);

    TEAM_TEMPLATES.forEach((template) => {
      expect(screen.getByText(template.icon)).toBeInTheDocument();
    });
  });

  it('calls onSelect with correct template when clicked', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<TeamTemplateSelector onSelect={onSelect} />);

    const firstTemplate = TEAM_TEMPLATES[0];
    const button = screen.getByRole('button', { name: new RegExp(firstTemplate.name) });

    await user.click(button);

    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith(firstTemplate);
  });

  it('calls onSelect with correct template for each button', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<TeamTemplateSelector onSelect={onSelect} />);

    for (const template of TEAM_TEMPLATES) {
      onSelect.mockClear();
      const button = screen.getByRole('button', { name: new RegExp(template.name) });
      await user.click(button);

      expect(onSelect).toHaveBeenCalledTimes(1);
      expect(onSelect).toHaveBeenCalledWith(template);
    }
  });

  it('renders correct number of template buttons', () => {
    const onSelect = vi.fn();
    render(<TeamTemplateSelector onSelect={onSelect} />);

    const buttons = screen.getAllByRole('button');
    expect(buttons).toHaveLength(TEAM_TEMPLATES.length);
  });

  it('renders buttons with proper type="button"', () => {
    const onSelect = vi.fn();
    render(<TeamTemplateSelector onSelect={onSelect} />);

    const buttons = screen.getAllByRole('button');
    buttons.forEach((button) => {
      expect(button).toHaveAttribute('type', 'button');
    });
  });

  describe('Specific templates', () => {
    it('renders research-team template correctly', () => {
      const onSelect = vi.fn();
      render(<TeamTemplateSelector onSelect={onSelect} />);

      expect(screen.getByText('리서치 팀')).toBeInTheDocument();
      expect(screen.getByText('🔍')).toBeInTheDocument();
      expect(
        screen.getByText('기업, 시장, 기술 트렌드를 조사하고 분석 보고서를 작성합니다')
      ).toBeInTheDocument();
    });

    it('renders content-team template correctly', () => {
      const onSelect = vi.fn();
      render(<TeamTemplateSelector onSelect={onSelect} />);

      expect(screen.getByText('콘텐츠 팀')).toBeInTheDocument();
      expect(screen.getByText('✍️')).toBeInTheDocument();
      expect(
        screen.getByText('블로그, SNS, 마케팅 콘텐츠를 기획하고 작성합니다')
      ).toBeInTheDocument();
    });

    it('renders code-review-team template correctly', () => {
      const onSelect = vi.fn();
      render(<TeamTemplateSelector onSelect={onSelect} />);

      expect(screen.getByText('코드 리뷰 팀')).toBeInTheDocument();
      expect(screen.getByText('🛡️')).toBeInTheDocument();
      expect(
        screen.getByText('코드 품질, 보안, 성능을 다각도로 리뷰합니다')
      ).toBeInTheDocument();
    });

    it('renders data-analysis-team template correctly', () => {
      const onSelect = vi.fn();
      render(<TeamTemplateSelector onSelect={onSelect} />);

      expect(screen.getByText('데이터 분석 팀')).toBeInTheDocument();
      expect(screen.getByText('📊')).toBeInTheDocument();
      expect(
        screen.getByText('데이터를 수집, 분석하고 인사이트를 도출합니다')
      ).toBeInTheDocument();
    });

    it('renders customer-support-team template correctly', () => {
      const onSelect = vi.fn();
      render(<TeamTemplateSelector onSelect={onSelect} />);

      expect(screen.getByText('고객 지원 팀')).toBeInTheDocument();
      expect(screen.getByText('💬')).toBeInTheDocument();
      expect(
        screen.getByText('고객 문의를 분류하고 적절한 답변을 생성합니다')
      ).toBeInTheDocument();
    });

    it('renders news-briefing-team template correctly', () => {
      const onSelect = vi.fn();
      render(<TeamTemplateSelector onSelect={onSelect} />);

      expect(screen.getByText('뉴스 브리핑 팀')).toBeInTheDocument();
      expect(screen.getByText('📰')).toBeInTheDocument();
      expect(
        screen.getByText('실시간 뉴스를 수집하고 요약 브리핑을 생성합니다')
      ).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('renders all template buttons as focusable', () => {
      const onSelect = vi.fn();
      render(<TeamTemplateSelector onSelect={onSelect} />);

      const buttons = screen.getAllByRole('button');
      buttons.forEach((button) => {
        expect(button).toBeVisible();
      });
    });
  });
});
