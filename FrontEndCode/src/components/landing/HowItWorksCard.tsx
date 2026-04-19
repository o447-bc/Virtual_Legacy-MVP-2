import React from "react";
import { STEP_NUMBER_CLASSES } from "./colorConfig";

interface HowItWorksCardProps {
  stepNumber: number;
  icon: React.ReactNode;
  title: string;
  description: string;
}

const HowItWorksCard: React.FC<HowItWorksCardProps> = ({
  stepNumber,
  icon,
  title,
  description,
}) => {
  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <span className={STEP_NUMBER_CLASSES}>{stepNumber}</span>
      <div className="w-12 h-12 bg-legacy-purple text-white rounded-full flex items-center justify-center mb-4 mt-2">
        {icon}
      </div>
      <h3 className="text-xl font-semibold mb-3">{title}</h3>
      <p className="text-gray-600">{description}</p>
    </div>
  );
};

export default HowItWorksCard;
