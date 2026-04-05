import { buildApiUrl, API_CONFIG } from '@/config/api';
import { fetchAuthSession } from 'aws-amplify/auth';
import { getSurveyStatus } from './surveyService';

export interface ProgressData {
  completed: number;
  total: number;
  percentage: number;
}

export async function getTotalValidQuestions(): Promise<number> {
  try {
    const authSession = await fetchAuthSession();
    const idToken = authSession.tokens?.idToken?.toString();
    
    if (!idToken) {
      console.error('No auth token available');
      return 0;
    }
    
    const response = await fetch(
      buildApiUrl(API_CONFIG.ENDPOINTS.TOTAL_VALID_QUESTIONS),
      {
        headers: {
          'Authorization': `Bearer ${idToken}`
        }
      }
    );
    
    if (!response.ok) {
      console.error('Failed to fetch total questions:', response.status);
      return 0;
    }
    
    const data = await response.json();
    return data.count || 0;
  } catch (error) {
    console.error('Error fetching total questions:', error);
    return 0;
  }
}

export async function getUserCompletedCount(userId: string): Promise<number> {
  try {
    const authSession = await fetchAuthSession();
    const idToken = authSession.tokens?.idToken?.toString();
    
    if (!idToken) {
      console.error('No auth token available');
      return 0;
    }
    
    const response = await fetch(
      buildApiUrl(API_CONFIG.ENDPOINTS.USER_COMPLETED_COUNT, { userId }),
      {
        headers: {
          'Authorization': `Bearer ${idToken}`
        }
      }
    );
    
    if (!response.ok) {
      console.error('Failed to fetch completed count:', response.status);
      return 0;
    }
    
    const data = await response.json();
    return data.count || 0;
  } catch (error) {
    console.error('Error fetching completed count:', error);
    return 0;
  }
}

export async function getUserProgress(userId: string): Promise<ProgressData> {
  const [completed, defaultTotal, surveyStatus] = await Promise.all([
    getUserCompletedCount(userId),
    getTotalValidQuestions(),
    getSurveyStatus().catch(() => null),
  ]);
  
  // Use assigned question count from survey if available (includes instanced copies)
  const total = surveyStatus?.assignedQuestionCount ?? defaultTotal;
  
  const percentage = total > 0 ? Math.round((completed / total) * 100) : 0;
  
  return { completed, total, percentage };
}
