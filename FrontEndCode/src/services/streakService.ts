import { API_CONFIG } from '@/config/api';
import { fetchAuthSession } from 'aws-amplify/auth';

export interface StreakData {
  streakCount: number;
  streakFreezeAvailable: boolean;
  lastVideoDate?: string;
  streakStatus?: 'active' | 'at_risk' | 'broken';
  daysSinceLastVideo?: number;
  freezeUsed?: boolean;
}

const CACHE_KEY_PREFIX = 'streak_';
const CACHE_DURATION = 3600000; // 1 hour in milliseconds

interface CachedStreak {
  data: StreakData;
  timestamp: number;
}

export const streakService = {
  /**
   * Get current streak data (simple, fast)
   */
  async getStreak(): Promise<StreakData> {
    const authSession = await fetchAuthSession();
    const idToken = authSession.tokens?.idToken?.toString();
    
    if (!idToken) throw new Error('No authentication token');

    const response = await fetch(
      `${API_CONFIG.BASE_URL}/streak`,
      {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${idToken}`,
          'Content-Type': 'application/json'
        }
      }
    );

    if (!response.ok) {
      throw new Error('Failed to fetch streak');
    }

    return await response.json();
  },

  /**
   * Check streak with status calculation (includes more details)
   */
  async checkStreak(): Promise<StreakData> {
    const authSession = await fetchAuthSession();
    const idToken = authSession.tokens?.idToken?.toString();
    
    if (!idToken) throw new Error('No authentication token');

    const response = await fetch(
      `${API_CONFIG.BASE_URL}/streak/check`,
      {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${idToken}`,
          'Content-Type': 'application/json'
        }
      }
    );

    if (!response.ok) {
      throw new Error('Failed to check streak');
    }

    return await response.json();
  },

  /**
   * Get streak with caching (use this for UI display)
   */
  async getCachedStreak(userId: string): Promise<StreakData> {
    const cacheKey = `${CACHE_KEY_PREFIX}${userId}`;
    const cached = localStorage.getItem(cacheKey);

    if (cached) {
      try {
        const cachedData: CachedStreak = JSON.parse(cached);
        const age = Date.now() - cachedData.timestamp;

        if (age < CACHE_DURATION) {
          return cachedData.data;
        }
      } catch (e) {
        console.error('Error parsing cached streak:', e);
      }
    }

    // Cache miss or expired - fetch fresh data
    const streakData = await this.getStreak();
    
    // Cache the result
    const cacheData: CachedStreak = {
      data: streakData,
      timestamp: Date.now()
    };
    localStorage.setItem(cacheKey, JSON.stringify(cacheData));

    return streakData;
  },

  /**
   * Invalidate streak cache (call after video upload)
   */
  invalidateCache(userId: string): void {
    const cacheKey = `${CACHE_KEY_PREFIX}${userId}`;
    localStorage.removeItem(cacheKey);
  },

  /**
   * Update cached streak data (call after video upload with response data)
   */
  updateCache(userId: string, streakData: StreakData): void {
    const cacheKey = `${CACHE_KEY_PREFIX}${userId}`;
    const cacheData: CachedStreak = {
      data: streakData,
      timestamp: Date.now()
    };
    localStorage.setItem(cacheKey, JSON.stringify(cacheData));
  }
};
