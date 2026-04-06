import React from "react";
import { ProgressBar } from "@/components/ProgressBar";
import { InfoTooltip } from "@/components/InfoTooltip";

interface OverallProgressSectionProps {
  completed: number;
  total: number;
}

/**
 * OVERALL PROGRESS SECTION
 *
 * Shared component displaying the user's overall question completion progress.
 * Renders a white card with heading, info tooltip, and the existing ProgressBar.
 * Reused on Dashboard, Life Story Reflections, Life Events, and Personal Insights pages.
 */
export const OverallProgressSection: React.FC<OverallProgressSectionProps> = ({
  completed,
  total,
}) => {
  return (
    <div className="bg-white rounded-lg shadow p-6 mb-6">
      <div className="flex items-center gap-2 mb-4">
        <h3 className="text-xl font-semibold">Your Overall Progress</h3>
        <InfoTooltip content="This shows your total progress across all question types. Keep recording to increase your completion percentage!" />
      </div>
      <ProgressBar completed={completed} total={total} />
    </div>
  );
};
