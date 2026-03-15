import React from 'react';
import { StreakData } from '@/services/streakService';

interface StreakCounterProps {
  streakData: StreakData | null;
  loading?: boolean;
  showFreeze?: boolean;
  className?: string;
}

export const StreakCounter: React.FC<StreakCounterProps> = ({
  streakData,
  loading = false,
  showFreeze = true,
  className = ''
}) => {
  if (loading) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <span className="text-2xl">🔥</span>
        <span className="text-sm text-gray-500">Loading...</span>
      </div>
    );
  }

  if (!streakData || streakData.streakCount === 0) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <span className="text-2xl opacity-50">🔥</span>
        <span className="text-sm text-gray-500">Start your streak!</span>
      </div>
    );
  }

  const { streakCount, streakFreezeAvailable } = streakData;

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <span className="text-2xl animate-pulse">🔥</span>
      <div className="flex flex-col">
        <span className="text-lg font-bold">
          {streakCount}-day streak
        </span>
        {showFreeze && streakFreezeAvailable && (
          <span className="text-xs text-blue-500 flex items-center gap-1">
            <span>❄️</span>
            <span>Freeze available</span>
          </span>
        )}
      </div>
    </div>
  );
};
