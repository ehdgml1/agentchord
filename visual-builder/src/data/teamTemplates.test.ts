import { describe, it, expect } from 'vitest';
import { TEAM_TEMPLATES } from './teamTemplates';

describe('teamTemplates', () => {
  describe('All templates have required fields', () => {
    it('validates each template has id, name, icon, description, category, config', () => {
      TEAM_TEMPLATES.forEach((template) => {
        expect(template).toHaveProperty('id');
        expect(template).toHaveProperty('name');
        expect(template).toHaveProperty('icon');
        expect(template).toHaveProperty('description');
        expect(template).toHaveProperty('category');
        expect(template).toHaveProperty('config');

        expect(typeof template.id).toBe('string');
        expect(typeof template.name).toBe('string');
        expect(typeof template.icon).toBe('string');
        expect(typeof template.description).toBe('string');
        expect(typeof template.category).toBe('string');
        expect(typeof template.config).toBe('object');
      });
    });

    it('validates config has required fields', () => {
      TEAM_TEMPLATES.forEach((template) => {
        const { config } = template;
        expect(config).toHaveProperty('strategy');
        expect(config).toHaveProperty('maxRounds');
        expect(config).toHaveProperty('costBudget');
        expect(config).toHaveProperty('members');

        expect(typeof config.strategy).toBe('string');
        expect(typeof config.maxRounds).toBe('number');
        expect(typeof config.costBudget).toBe('number');
        expect(Array.isArray(config.members)).toBe(true);
      });
    });
  });

  describe('Template ID uniqueness', () => {
    it('ensures all template IDs are unique', () => {
      const ids = TEAM_TEMPLATES.map((t) => t.id);
      const uniqueIds = new Set(ids);
      expect(uniqueIds.size).toBe(ids.length);
    });

    it('validates no empty IDs', () => {
      TEAM_TEMPLATES.forEach((template) => {
        expect(template.id.trim()).toBeTruthy();
      });
    });
  });

  describe('Strategy validation', () => {
    const validStrategies = ['coordinator', 'round_robin', 'debate', 'map_reduce'];

    it('ensures all strategies are valid', () => {
      TEAM_TEMPLATES.forEach((template) => {
        expect(validStrategies).toContain(template.config.strategy);
      });
    });

    it('validates strategy is non-empty', () => {
      TEAM_TEMPLATES.forEach((template) => {
        expect(template.config.strategy.trim()).toBeTruthy();
      });
    });
  });

  describe('Team member validation', () => {
    it('ensures each template has at least 2 members', () => {
      TEAM_TEMPLATES.forEach((template) => {
        expect(template.config.members.length).toBeGreaterThanOrEqual(2);
      });
    });

    it('validates member IDs are unique within each template', () => {
      TEAM_TEMPLATES.forEach((template) => {
        const memberIds = template.config.members.map((m) => m.id);
        const uniqueMemberIds = new Set(memberIds);
        expect(uniqueMemberIds.size).toBe(memberIds.length);
      });
    });

    it('ensures all members have required fields', () => {
      TEAM_TEMPLATES.forEach((template) => {
        template.config.members.forEach((member) => {
          expect(member).toHaveProperty('id');
          expect(member).toHaveProperty('name');
          expect(member).toHaveProperty('role');
          expect(member).toHaveProperty('model');
          expect(member).toHaveProperty('systemPrompt');
          expect(member).toHaveProperty('temperature');

          expect(typeof member.id).toBe('string');
          expect(typeof member.name).toBe('string');
          expect(typeof member.role).toBe('string');
          expect(typeof member.model).toBe('string');
          expect(typeof member.systemPrompt).toBe('string');
          expect(typeof member.temperature).toBe('number');
        });
      });
    });

    it('validates member temperature is between 0 and 1', () => {
      TEAM_TEMPLATES.forEach((template) => {
        template.config.members.forEach((member) => {
          expect(member.temperature).toBeGreaterThanOrEqual(0);
          expect(member.temperature).toBeLessThanOrEqual(1);
        });
      });
    });

    it('validates member IDs are non-empty', () => {
      TEAM_TEMPLATES.forEach((template) => {
        template.config.members.forEach((member) => {
          expect(member.id.trim()).toBeTruthy();
        });
      });
    });

    it('validates member names are non-empty', () => {
      TEAM_TEMPLATES.forEach((template) => {
        template.config.members.forEach((member) => {
          expect(member.name.trim()).toBeTruthy();
        });
      });
    });

    it('validates member systemPrompts are non-empty', () => {
      TEAM_TEMPLATES.forEach((template) => {
        template.config.members.forEach((member) => {
          expect(member.systemPrompt.trim()).toBeTruthy();
        });
      });
    });
  });

  describe('Specific template validation', () => {
    it('validates research-team template', () => {
      const template = TEAM_TEMPLATES.find((t) => t.id === 'research-team');
      expect(template).toBeDefined();
      expect(template?.config.strategy).toBe('map_reduce');
      expect(template?.config.members.length).toBe(3);
    });

    it('validates content-team template', () => {
      const template = TEAM_TEMPLATES.find((t) => t.id === 'content-team');
      expect(template).toBeDefined();
      expect(template?.config.strategy).toBe('coordinator');
      expect(template?.config.members.length).toBe(3);
    });

    it('validates code-review-team template', () => {
      const template = TEAM_TEMPLATES.find((t) => t.id === 'code-review-team');
      expect(template).toBeDefined();
      expect(template?.config.strategy).toBe('debate');
      expect(template?.config.members.length).toBe(3);
    });

    it('validates data-analysis-team template', () => {
      const template = TEAM_TEMPLATES.find((t) => t.id === 'data-analysis-team');
      expect(template).toBeDefined();
      expect(template?.config.strategy).toBe('coordinator');
      expect(template?.config.members.length).toBe(3);
    });

    it('validates customer-support-team template', () => {
      const template = TEAM_TEMPLATES.find((t) => t.id === 'customer-support-team');
      expect(template).toBeDefined();
      expect(template?.config.strategy).toBe('coordinator');
      expect(template?.config.members.length).toBe(3);
    });

    it('validates news-briefing-team template', () => {
      const template = TEAM_TEMPLATES.find((t) => t.id === 'news-briefing-team');
      expect(template).toBeDefined();
      expect(template?.config.strategy).toBe('map_reduce');
      expect(template?.config.members.length).toBe(3);
    });
  });

  describe('Data quality', () => {
    it('validates maxRounds is positive', () => {
      TEAM_TEMPLATES.forEach((template) => {
        expect(template.config.maxRounds).toBeGreaterThan(0);
      });
    });

    it('validates costBudget is non-negative', () => {
      TEAM_TEMPLATES.forEach((template) => {
        expect(template.config.costBudget).toBeGreaterThanOrEqual(0);
      });
    });

    it('validates descriptions are meaningful', () => {
      TEAM_TEMPLATES.forEach((template) => {
        expect(template.description.length).toBeGreaterThan(10);
      });
    });

    it('validates icons are emojis', () => {
      TEAM_TEMPLATES.forEach((template) => {
        expect(template.icon.length).toBeGreaterThan(0);
        expect(template.icon.length).toBeLessThan(5); // Emojis are typically 1-2 chars
      });
    });
  });
});
