import React, { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { InfoTooltip } from "@/components/InfoTooltip";
import { ChevronRight } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { useProgress, useIncrementLevel, ProgressItem } from "@/hooks/useProgress";

interface ProgressSectionProps {
  user: { id: string; personaType: string };
  navigationState?: any;
}

/**
 * PROGRESS SECTION COMPONENT
 *
 * Displays user's progress across all question categories with interactive
 * progress bars that allow direct navigation to category-specific recording.
 *
 * Extracted from Dashboard.tsx for reuse on the LifeStoryReflections page.
 *
 * KEY FEATURES:
 * - Fetches progress data from optimized batch API endpoint
 * - Displays progress bars for each question category
 * - Enables category-specific recording via progress bar clicks
 * - Auto-advances level when all categories at current level are complete
 * - Handles loading states and error conditions gracefully
 */
export const ProgressSection: React.FC<ProgressSectionProps> = ({ user, navigationState }) => {
  const navigate = useNavigate();
  const updatedItem = navigationState?.updatedProgressItem as ProgressItem | undefined;

  const { data, isLoading, isError, error, refetch } = useProgress(user?.id, updatedItem);
  const incrementLevel = useIncrementLevel();

  // Auto-advance level when all categories are complete
  useEffect(() => {
    if (!data) return;
    const allComplete = data.progressItems.length > 0 &&
      data.progressItems.every(item => item.remainQuestAtCurrLevel.length === 0);
    if (allComplete && !incrementLevel.isPending) {
      incrementLevel.mutate(data.progressItems[0]?.questionType || 'auto');
    }
  }, [data]);

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center gap-2 mb-6">
          <Skeleton className="h-6 w-40" />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 sm:gap-x-8">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="space-y-2">
              <div className="flex justify-between items-center">
                <Skeleton className="h-4 w-48" />
                <Skeleton className="h-4 w-28" />
              </div>
              <div className="flex items-center space-x-3">
                <Skeleton className="flex-1 h-3 rounded-full" />
                <Skeleton className="h-4 w-10" />
              </div>
              <Skeleton className="h-3 w-24" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-xl font-semibold mb-4">Your Progress</h3>
        <p className="text-red-600">Error loading progress: {(error as Error).message}</p>
        <Button onClick={() => refetch()} className="mt-4 bg-legacy-purple hover:bg-legacy-navy">
          Retry
        </Button>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-xl font-semibold mb-4">Your Progress</h3>
        <p className="text-gray-600">No question data available.</p>
      </div>
    );
  }

  const hasIncompleteCategories = data.questionTypes.some((qt, i) => {
    const total = data.numValidQuestions[i];
    const unanswered = data.progressDataMap[qt] || 0;
    return total > 0 ? Math.round(((total - unanswered) / total) * 100) < 100 : false;
  });

  return (
    <>
      {!hasIncompleteCategories && (
        <div className="mb-6 bg-green-50 border border-green-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-green-800 mb-2">
            🎉 Congratulations! Current Level Complete!
          </h3>
          <p className="text-green-700">
            You've completed all categories at your current level. Great work!
          </p>
        </div>
      )}

      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center gap-2 mb-6">
          <h3 className="text-xl font-semibold">Your Progress</h3>
          <InfoTooltip content="Click any progress bar to record responses for that category. Complete all categories to advance to the next level" />
        </div>

        <div className="relative grid grid-cols-1 sm:grid-cols-2 gap-6 sm:gap-x-8">
          <div className="hidden sm:block absolute left-1/2 top-0 bottom-0 w-px bg-gray-200 -translate-x-1/2" />

          {data.questionTypes.map((questionType, index) => {
            const progressItem = data.progressItems.find(item => item.questionType === questionType);
            const friendlyName = data.friendlyNames[index];
            const totalQuestions = data.numValidQuestions[index];
            const unansweredCount = data.progressDataMap[questionType] || 0;
            const answeredCount = totalQuestions - unansweredCount;
            const percentage = totalQuestions > 0 ? Math.round((answeredCount / totalQuestions) * 100) : 0;
            const currentLevel = progressItem?.currentQuestLevel || 1;

            const handleProgressBarClick = () => {
              if (percentage === 100) return;
              navigate('/record-conversation', {
                state: {
                  ...progressItem,
                  percentage,
                  unansweredQuestionIds: data.unansweredQuestionsMap[questionType] || [],
                  unansweredQuestionTexts: data.unansweredQuestionTextsMap[questionType] || [],
                },
              });
            };

            return (
              <div key={questionType} className="space-y-2">
                <div className="flex justify-between items-center">
                  <h4 className="font-medium text-gray-900">Level {currentLevel} - {friendlyName}</h4>
                  <span className="text-sm text-gray-600">{answeredCount} of {totalQuestions} completed</span>
                </div>
                <div
                  className={`flex items-center space-x-3 transition-all ${
                    percentage === 100 ? 'cursor-default opacity-75' : 'cursor-pointer hover:opacity-80 focus-visible:ring-2 focus-visible:ring-legacy-purple focus-visible:ring-offset-2 focus-visible:rounded-md'
                  }`}
                  onClick={handleProgressBarClick}
                  role={percentage < 100 ? "button" : undefined}
                  tabIndex={percentage < 100 ? 0 : undefined}
                  onKeyDown={(e) => {
                    if ((e.key === 'Enter' || e.key === ' ') && percentage < 100) {
                      e.preventDefault();
                      handleProgressBarClick();
                    }
                  }}
                  aria-label={percentage === 100 ? `${friendlyName} — level completed` : `Record responses for ${friendlyName}, ${percentage}% complete`}
                  title={percentage === 100 ? 'Level completed!' : `Click to record responses for ${friendlyName}`}
                >
                  <Progress value={percentage} className="flex-1 h-3" />
                  <span className="text-sm font-medium text-gray-700 min-w-[3rem]">{percentage}%</span>
                  {percentage < 100 && (
                    <ChevronRight className="h-4 w-4 text-gray-400 hover:text-legacy-purple transition-colors" />
                  )}
                </div>
                <div className="text-xs text-gray-500">
                  {percentage === 100 ? (
                    <span className="text-green-600 font-medium">✓ Congratulations finished!</span>
                  ) : (
                    `${totalQuestions} total questions`
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </>
  );
};
