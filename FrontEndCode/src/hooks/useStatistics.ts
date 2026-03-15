import { useQuery, useQueryClient } from "@tanstack/react-query";
import { streakService } from "@/services/streakService";
import { getUserProgress } from "@/services/progressService";
import { StatisticsData } from "@/components/StatisticsSection";

function calculateLevel(progressData: { percentage: number }): number {
  if (progressData.percentage >= 90) return 10;
  if (progressData.percentage >= 80) return 9;
  if (progressData.percentage >= 70) return 8;
  if (progressData.percentage >= 60) return 7;
  if (progressData.percentage >= 50) return 6;
  if (progressData.percentage >= 40) return 5;
  if (progressData.percentage >= 30) return 4;
  if (progressData.percentage >= 20) return 3;
  if (progressData.percentage >= 10) return 2;
  return 1;
}

async function fetchStatistics(userId: string): Promise<StatisticsData> {
  const [streakData, progressData] = await Promise.all([
    streakService.getStreak(),
    getUserProgress(userId),
  ]);
  return {
    longestStreak: streakData.streakCount || 0,
    totalQuestionsAnswered: progressData.completed,
    currentLevel: calculateLevel(progressData),
    overallProgress: progressData.percentage,
  };
}

export function useStatistics(userId: string | undefined) {
  const { data, isLoading: loading, error } = useQuery({
    queryKey: ["statistics", userId ?? ""],
    queryFn: () => fetchStatistics(userId!),
    enabled: !!userId,
    staleTime: 5 * 60_000,
    placeholderData: { longestStreak: 0, totalQuestionsAnswered: 0, currentLevel: 1, overallProgress: 0 },
  });

  return {
    data: data ?? null,
    loading,
    error: error?.message ?? null,
  };
}

export function useInvalidateStatistics() {
  const queryClient = useQueryClient();
  return (userId: string) => queryClient.invalidateQueries({ queryKey: ["statistics", userId] });
}
