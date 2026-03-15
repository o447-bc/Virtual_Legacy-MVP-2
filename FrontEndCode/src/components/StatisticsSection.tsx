import React from "react";
import { Flame, CheckCircle, TrendingUp, BarChart3 } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";

export interface StatisticsData {
  longestStreak: number;
  totalQuestionsAnswered: number;
  currentLevel: number;
  overallProgress: number;
}

interface StatisticsSectionProps {
  data: StatisticsData | null;
  loading: boolean;
  error: string | null;
}

/**
 * StatisticsSection Component
 * 
 * Displays user statistics in the UserMenu dropdown.
 * Shows longest streak, total questions answered, current level, and overall progress.
 * 
 * Requirements covered:
 * - 3.1: Display statistics in menu
 * - 3.2: Display longest streak
 * - 3.3: Display total questions answered
 * - 3.4: Display current level
 * - 3.5: Display overall progress percentage
 * - 3.6: Show loading indicators
 * - 3.7: Handle errors with cached/placeholder data
 */
export const StatisticsSection: React.FC<StatisticsSectionProps> = ({
  data,
  loading,
  error,
}) => {
  // Format numbers with commas for readability
  const formatNumber = (num: number): string => {
    return num.toLocaleString();
  };

  // Show loading skeleton
  if (loading && !data) {
    return (
      <div className="px-2 py-3 space-y-3">
        <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
          Statistics
        </div>
        <div className="grid grid-cols-2 gap-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="space-y-1">
              <Skeleton className="h-4 w-16" />
              <Skeleton className="h-5 w-12" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Use data or fallback to placeholder values
  const stats = data || {
    longestStreak: 0,
    totalQuestionsAnswered: 0,
    currentLevel: 1,
    overallProgress: 0,
  };

  return (
    <div className="px-2 py-3 space-y-3">
      <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
        Statistics
      </div>
      
      <div className="grid grid-cols-2 gap-3">
        {/* Longest Streak */}
        <div className="flex items-start gap-2">
          <Flame className="h-4 w-4 text-orange-500 mt-0.5 flex-shrink-0" />
          <div className="flex flex-col min-w-0">
            <span className="text-xs text-gray-600">Longest Streak</span>
            <span className="text-base font-semibold text-legacy-navy">
              {formatNumber(stats.longestStreak)}
            </span>
          </div>
        </div>

        {/* Total Questions Answered */}
        <div className="flex items-start gap-2">
          <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
          <div className="flex flex-col min-w-0">
            <span className="text-xs text-gray-600">Questions</span>
            <span className="text-base font-semibold text-legacy-navy">
              {formatNumber(stats.totalQuestionsAnswered)}
            </span>
          </div>
        </div>

        {/* Current Level */}
        <div className="flex items-start gap-2">
          <TrendingUp className="h-4 w-4 text-blue-500 mt-0.5 flex-shrink-0" />
          <div className="flex flex-col min-w-0">
            <span className="text-xs text-gray-600">Level</span>
            <span className="text-base font-semibold text-legacy-navy">
              {formatNumber(stats.currentLevel)}
            </span>
          </div>
        </div>

        {/* Overall Progress */}
        <div className="flex items-start gap-2">
          <BarChart3 className="h-4 w-4 text-purple-500 mt-0.5 flex-shrink-0" />
          <div className="flex flex-col min-w-0">
            <span className="text-xs text-gray-600">Progress</span>
            <span className="text-base font-semibold text-legacy-navy">
              {stats.overallProgress}%
            </span>
          </div>
        </div>
      </div>

      {/* Show subtle error indicator if there was an error but we have cached data */}
      {error && data && (
        <div className="text-xs text-gray-500 italic">
          Showing cached data
        </div>
      )}
    </div>
  );
};
