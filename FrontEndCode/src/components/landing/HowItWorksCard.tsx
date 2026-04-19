import React from "react";
import { Link } from "react-router-dom";
import { ChevronDown } from "lucide-react";
import { STEP_NUMBER_CLASSES } from "./colorConfig";

interface HowItWorksCardProps {
  stepNumber: number;
  icon: React.ReactNode;
  title: string;
  description: string;
  expandedDescription: string;
  isExpanded: boolean;
  onToggle: () => void;
}

const HowItWorksCard: React.FC<HowItWorksCardProps> = ({
  stepNumber,
  icon,
  title,
  description,
  expandedDescription,
  isExpanded,
  onToggle,
}) => {
  return (
    <div
      className="bg-white p-6 rounded-lg shadow-md cursor-pointer transition-all duration-300"
      onClick={onToggle}
    >
      <span className={STEP_NUMBER_CLASSES}>{stepNumber}</span>
      <div className="w-12 h-12 bg-legacy-purple text-white rounded-full flex items-center justify-center mb-4 mt-2">
        {icon}
      </div>
      <h3 className="text-xl font-semibold mb-3">{title}</h3>
      <p className="text-gray-600">{description}</p>

      <div className={`overflow-hidden transition-all duration-300 ease-in-out ${isExpanded ? 'max-h-[500px] opacity-100' : 'max-h-0 opacity-0'}`}>
        <div className="aspect-video rounded-lg bg-gradient-to-br from-legacy-lightPurple to-legacy-purple flex items-center justify-center mt-4 mb-3">
          <span className="text-white text-sm">Screenshot coming soon</span>
        </div>
        <p className="text-gray-600 text-sm mb-3">{expandedDescription}</p>
        <Link
          to="/legacy-create-choice"
          className="text-legacy-purple hover:underline text-sm font-medium"
          onClick={(e) => e.stopPropagation()}
        >
          Preserve your first memory →
        </Link>
      </div>

      <div className="flex items-center gap-1 mt-3 text-legacy-purple text-sm">
        <span>Learn more</span>
        <ChevronDown className={`w-4 h-4 transition-transform duration-300 ${isExpanded ? 'rotate-180' : ''}`} />
      </div>
    </div>
  );
};

export default HowItWorksCard;
