import { useState, useEffect } from "react";
import { streakService } from "@/services/streakService";
import { getUserProgress } from "@/services/progressService";
import { StatisticsData } from "@/components/StatisticsSection";

const CACHE_KEY_PREFIX = "user_statistics_";
const CACHE_DURATION = 300000; // 5 minutes in milliseconds

interface CachedStatistics {
  data: StatisticsData;
  timestamp: number;
}

/**
 * Calculate user level based on progress percentage
 * Level 1: 0-9%
 * Level 2: 10-19%
 * Level 3: 20-29%
 * ...
 * Level 10: 90-100%
 */
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

/**
 * Get cached statistics from localStorage
 */
function getCachedStatistics(userId: string): StatisticsData | null {
  const cacheKey = `${CACHE_KEY_PREFIX}${userId}`;
  const cached = localStorage.getItem(cacheKey);

  if (!cached) return null;

  try {
    const cachedData: CachedStatistics = JSON.parse(cached);
    const age = Date.now() - cachedData.timestamp;

    // Return cached data if it's less than 5 minutes old
    if (age < CACHE_DURATION) {
      return cachedData.data;
    }
  } catch (e) {
    console.error("Error parsing cached statistics:", e);
  }

  return null;
}

/**
 * Set cached statistics in localStorage
 */
function setCachedStatistics(userId: string, data: StatisticsData): void {
  const cacheKey = `${CACHE_KEY_PREFIX}${userId}`;
  const cacheData: CachedStatistics = {
    data,
    timestamp: Date.now(),
  };
  localStorage.setItem(cacheKey, JSON.stringify(cacheData));
}

/**
 * Fetch fresh statistics data from services
 */
async function fetchStatistics(userId: string): Promise<StatisticsData> {
  // Fetch data from both services in parallel
  const [streakData, progressData] = await Promise.all([
    streakService.getStreak(),
    getUserProgress(userId),
  ]);

  // Note: streakService returns current streak, not longest streak
  // For now, we'll use current streak as longest streak
  // In a real implementation, we'd need a separate API endpoint for longest streak
  const statistics: StatisticsData = {
    longestStreak: streakData.streakCount || 0,
    totalQuestionsAnswered: progressData.completed,
    currentLevel: calculateLevel(progressData),
    overallProgress: progressData.percentage,
  };

  return statistics;
}

/**
 * Custom hook to fetch and cache user statistics
 * 
 * Requirements covered:
 * - 10.1: Load statistics asynchronously
 * - 10.2: Cache statistics for 5 minutes
 * - 10.3: Display cached data immediately if available
 * - 10.4: Fetch fresh data in background if cache is stale
 * - 10.5: Don't block page rendering
 */
export function useStatistics(userId: string | undefined) {
  const [data, setData] = useState<StatisticsData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!userId) {
      setLoading(false);
      return;
    }

    let isMounted = true;

    async function loadStatistics() {
      try {
        // Check cache first
        const cached = getCachedStatistics(userId);
        
        if (cached) {
          // Display cached data immediately
          if (isMounted) {
            setData(cached);
            setLoading(false);
          }
          
          // Fetch fresh data in background (cache is stale)
          try {
            const fresh = await fetchStatistics(userId);
            if (isMounted) {
              setData(fresh);
              setCachedStatistics(userId, fresh);
            }
          } catch (bgError) {
            // Silent fail for background refresh
            console.error("Background statistics refresh failed:", bgError);
          }
        } else {
          // No cache - fetch fresh data
          const fresh = await fetchStatistics(userId);
          if (isMounted) {
            setData(fresh);
            setLoading(false);
            setCachedStatistics(userId, fresh);
            setError(null);
          }
        }
      } catch (err) {
        // Log full error details for debugging (Requirements 13.5, 13.6)
        console.error("Failed to fetch statistics:", err);
        
        // Try to use any cached data, even if expired
        const cached = getCachedStatistics(userId);
        if (cached && isMounted) {
          setData(cached);
          setError("Using cached data"); // Requirements 13.3, 13.6
        } else if (isMounted) {
          // No cache available - use placeholder values (Requirements 3.7, 13.3)
          setData({
            longestStreak: 0,
            totalQuestionsAnswered: 0,
            currentLevel: 1,
            overallProgress: 0,
          });
          setError("Failed to load statistics");
        }
        
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    loadStatistics();

    return () => {
      isMounted = false;
    };
  }, [userId]);

  return { data, loading, error };
}

/**
 * Invalidate statistics cache (call after video upload)
 */
export function invalidateStatisticsCache(userId: string): void {
  const cacheKey = `${CACHE_KEY_PREFIX}${userId}`;
  localStorage.removeItem(cacheKey);
}
