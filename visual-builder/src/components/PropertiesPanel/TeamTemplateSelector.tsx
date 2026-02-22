/**
 * TeamTemplateSelector - Visual template picker for Multi-Agent Teams.
 * Shows pre-built team configurations as clickable cards.
 */
import { memo } from 'react';
import { Sparkles } from 'lucide-react';
import { TEAM_TEMPLATES, type TeamTemplate } from '../../data/teamTemplates';

interface TeamTemplateSelectorProps {
  onSelect: (template: TeamTemplate) => void;
}

export const TeamTemplateSelector = memo(function TeamTemplateSelector({
  onSelect,
}: TeamTemplateSelectorProps) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-1.5 text-sm font-medium">
        <Sparkles className="w-3.5 h-3.5 text-amber-500" />
        Quick Start Templates
      </div>
      <p className="text-xs text-muted-foreground">
        Choose a template to get started quickly. You can customize it later.
      </p>
      <div className="space-y-2">
        {TEAM_TEMPLATES.map((template) => (
          <button
            key={template.id}
            type="button"
            className="w-full text-left p-3 border rounded-lg hover:border-primary hover:bg-accent/50 transition-colors group"
            onClick={() => onSelect(template)}
          >
            <div className="flex items-start gap-2.5">
              <span className="text-xl leading-none mt-0.5">{template.icon}</span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium group-hover:text-primary transition-colors">
                    {template.name}
                  </span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-muted text-muted-foreground">
                    {template.config.members.length} agents
                  </span>
                </div>
                <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">
                  {template.description}
                </p>
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
});
