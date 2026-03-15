import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Info } from "lucide-react";

interface InfoTooltipProps {
  content: string;
  className?: string;
}

export const InfoTooltip = ({ content, className = "" }: InfoTooltipProps) => {
  return (
    <Tooltip delayDuration={300}>
      <TooltipTrigger asChild>
        <span 
          className={`inline-flex items-center justify-center cursor-help ${className}`}
          aria-label="More information"
        >
          <Info className="h-4 w-4 text-gray-400 hover:text-gray-600 transition-colors" />
        </span>
      </TooltipTrigger>
      <TooltipContent className="max-w-xs" side="top">
        <p className="text-sm">{content}</p>
      </TooltipContent>
    </Tooltip>
  );
};
