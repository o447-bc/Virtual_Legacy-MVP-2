import React, { useCallback } from "react";
import { ChevronRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface ContentPathCardProps {
  title: string;
  subtitle: string;
  icon: React.ReactNode;
  progressLabel: string;
  levelLabel?: string;
  accentColor: string;
  disabled?: boolean;
  badge?: string;
  onClick: () => void;
}

/**
 * CONTENT PATH CARD
 *
 * A large, interactive navigation card used on the Dashboard content hub.
 * Each card represents one of the three content paths (Life Story, Life Events, Values & Emotions).
 * Supports keyboard navigation, hover/active states, and a disabled "Coming Soon" mode.
 */
export const ContentPathCard: React.FC<ContentPathCardProps> = ({
  title,
  subtitle,
  icon,
  progressLabel,
  levelLabel,
  accentColor,
  disabled = false,
  badge,
  onClick,
}) => {
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (disabled) return;
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        onClick();
      }
    },
    [disabled, onClick]
  );

  const handleClick = useCallback(() => {
    if (disabled) return;
    onClick();
  }, [disabled, onClick]);

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      className={cn(
        "bg-white rounded-xl p-6 border-l-4 min-h-[120px] flex items-center gap-4 transition-all duration-200 outline-none",
        accentColor,
        disabled
          ? "opacity-60 cursor-default"
          : "cursor-pointer shadow hover:shadow-lg hover:scale-[1.01] active:scale-[0.99] focus-visible:ring-2 focus-visible:ring-legacy-purple focus-visible:ring-offset-2"
      )}
      aria-disabled={disabled || undefined}
    >
      {/* Icon circle */}
      <div className="flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center bg-gray-100">
        {icon}
      </div>

      {/* Text content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <h3 className="text-xl font-semibold text-legacy-navy">{title}</h3>
          {badge && (
            <Badge variant="secondary" className="text-xs">
              {badge}
            </Badge>
          )}
          {levelLabel && (
            <Badge className="bg-legacy-purple text-white text-xs">
              {levelLabel}
            </Badge>
          )}
        </div>
        <p className="text-sm text-gray-500 mt-0.5">{subtitle}</p>
        <p className="text-sm font-medium text-gray-700 mt-1">{progressLabel}</p>
      </div>

      {/* Chevron */}
      <ChevronRight className="flex-shrink-0 w-5 h-5 text-gray-400" />
    </div>
  );
};
