import { memo, useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { Button } from '../ui/button';
import { Popover, PopoverTrigger, PopoverContent } from '../ui/popover';

interface TemplateVarSelectorProps {
  templateVars: { label: string; value: string }[];
  onSelect: (value: string) => void;
}

export const TemplateVarSelector = memo(function TemplateVarSelector({
  templateVars,
  onSelect,
}: TemplateVarSelectorProps) {
  const [open, setOpen] = useState(false);

  if (templateVars.length === 0) return null;

  const handleSelect = (value: string) => {
    onSelect(value);
    setOpen(false);
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="h-8 w-8 p-0 text-muted-foreground hover:text-foreground"
          aria-label="템플릿 변수 선택"
        >
          <ChevronDown className="h-4 w-4" />
        </Button>
      </PopoverTrigger>
      <PopoverContent side="bottom" align="end" sideOffset={4} className="w-56 p-0">
        <div className="text-xs font-medium text-muted-foreground px-2 py-1.5 border-b">
          템플릿 변수 선택
        </div>
        <div className="max-h-48 overflow-y-auto p-1">
          {templateVars.map((v) => (
            <button
              key={v.value}
              onClick={() => handleSelect(v.value)}
              className="w-full text-left px-2 py-1.5 text-sm font-mono rounded hover:bg-accent hover:text-accent-foreground transition-colors"
            >
              {v.label}
            </button>
          ))}
        </div>
      </PopoverContent>
    </Popover>
  );
});
