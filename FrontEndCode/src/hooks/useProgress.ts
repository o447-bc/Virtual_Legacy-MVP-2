import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getCurrentUser, fetchAuthSession } from 'aws-amplify/auth';
import { buildApiUrl, API_CONFIG } from '@/config/api';
import { toast } from '@/hooks/use-toast';

// ── Types ────────────────────────────────────────────────────────────────────

export interface ProgressItem {
  questionType: string;
  friendlyName: string;
  totalQuestAtCurrLevel: number;
  remainQuestAtCurrLevel: string[];
  remainQuestTextAtCurrLevel: string[];
  currentQuestLevel: number;
  [key: string]: unknown;
}

export interface ProgressData {
  questionTypes: string[];
  friendlyNames: string[];
  numValidQuestions: number[];
  progressDataMap: Record<string, number>;
  unansweredQuestionsMap: Record<string, string[]>;
  unansweredQuestionTextsMap: Record<string, string[]>;
  progressItems: ProgressItem[];
}

// ── Helpers ──────────────────────────────────────────────────────────────────

async function getIdToken(): Promise<string> {
  const session = await fetchAuthSession();
  const token = session.tokens?.idToken?.toString();
  if (!token) throw new Error('No authentication token available. Please log in again.');
  return token;
}

function processItems(items: ProgressItem[]): ProgressData {
  const questionTypes: string[] = [];
  const friendlyNames: string[] = [];
  const numValidQuestions: number[] = [];
  const progressDataMap: Record<string, number> = {};
  const unansweredQuestionsMap: Record<string, string[]> = {};
  const unansweredQuestionTextsMap: Record<string, string[]> = {};

  items.forEach((item) => {
    questionTypes.push(item.questionType);
    friendlyNames.push(item.friendlyName);
    numValidQuestions.push(item.totalQuestAtCurrLevel);
    progressDataMap[item.questionType] = item.remainQuestAtCurrLevel.length;
    unansweredQuestionsMap[item.questionType] = item.remainQuestAtCurrLevel;
    unansweredQuestionTextsMap[item.questionType] = item.remainQuestTextAtCurrLevel || [];
  });

  return { questionTypes, friendlyNames, numValidQuestions, progressDataMap, unansweredQuestionsMap, unansweredQuestionTextsMap, progressItems: items };
}

async function fetchProgress(userId: string, updatedItem?: ProgressItem): Promise<ProgressData> {
  const idToken = await getIdToken();
  const response = await fetch(
    buildApiUrl(API_CONFIG.ENDPOINTS.PROGRESS_SUMMARY_2, { userId }),
    { headers: { Authorization: `Bearer ${idToken}` } }
  );
  if (!response.ok) throw new Error('Failed to fetch progress data');

  const json = await response.json();
  let items: ProgressItem[] = json.progressItems || [];

  // Merge in any navigation-state updated item
  if (updatedItem) {
    items = items.map(item => item.questionType === updatedItem.questionType ? updatedItem : item);
  }

  return processItems(items);
}

async function incrementLevel(questionType: string): Promise<{ levelComplete: boolean; newGlobalLevel: number; updatedProgressItems: ProgressItem[] }> {
  const idToken = await getIdToken();
  const response = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.INCREMENT_LEVEL_2), {
    method: 'POST',
    headers: { Authorization: `Bearer ${idToken}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ questionType }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({ error: 'Server error' }));
    throw new Error(err.error || 'Failed to advance level');
  }
  return response.json();
}

// ── Pure computation helpers ─────────────────────────────────────────────────

/**
 * Compute Life Story progress totals from ProgressData.
 * Extracted as a pure function for testability.
 */
export function computeLifeStoryProgress(progressData: ProgressData): { total: number; completed: number } {
  const total = progressData.numValidQuestions.reduce((sum, n) => sum + n, 0);
  const completed = progressData.numValidQuestions.reduce((sum, n, i) => {
    const unanswered = progressData.progressDataMap[progressData.questionTypes[i]] ?? 0;
    return sum + (n - unanswered);
  }, 0);
  return { total, completed };
}

// ── Hooks ────────────────────────────────────────────────────────────────────

export function useProgress(userId: string | undefined, updatedItem?: ProgressItem) {
  return useQuery({
    queryKey: ['progress', userId],
    queryFn: () => fetchProgress(userId!, updatedItem),
    enabled: !!userId,
    staleTime: 60_000,
    placeholderData: (prev) => prev,
  });
}

export function useIncrementLevel() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (questionType: string) => incrementLevel(questionType),
    onSuccess: (result, _vars, _ctx) => {
      if (result.levelComplete && result.updatedProgressItems) {
        // Directly update the cache with the new level data
        queryClient.setQueriesData<ProgressData>({ queryKey: ['progress'] }, () =>
          processItems(result.updatedProgressItems)
        );
        toast({
          title: 'Level Complete!',
          description: `Congratulations! You completed Level ${result.newGlobalLevel - 1}. Level ${result.newGlobalLevel} is now unlocked!`,
        });
      }
    },
    onError: (error: Error) => {
      toast({
        title: 'Level Advancement Failed',
        description: error.message,
        variant: 'destructive',
      });
    },
  });
}
