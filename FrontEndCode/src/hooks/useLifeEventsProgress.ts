import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { getSurveyStatus } from '@/services/surveyService';
import type { InstanceGroup, QuestionDetail } from '@/services/surveyService';
import {
  INSTANCEABLE_KEY_TO_PLACEHOLDER,
  LIFE_EVENT_REGISTRY,
} from '@/constants/lifeEventRegistry';

// ── Types ────────────────────────────────────────────────────────────────────

export interface InstanceGroupProgress {
  eventKey: string;
  instanceName: string;
  instanceOrdinal: number;
  questions: Array<{
    questionId: string;
    questionText: string;
    isAnswered: boolean;
    difficulty: number;
  }>;
  totalQuestions: number;
  completedQuestions: number;
  minDifficultyLevel: number;
  eventLabel: string;
}

export interface LifeEventsProgressData {
  groups: InstanceGroupProgress[];
  totalQuestions: number;
  completedQuestions: number;
}

// ── Pure computation functions (exported for property testing) ────────────────

/**
 * Replace placeholder tokens in question text with the instance name.
 * E.g. "Tell us about {spouse_name}" → "Tell us about Sarah"
 */
export function replacePlaceholder(
  text: string,
  eventKey: string,
  instanceName: string,
  placeholderMap: Record<string, string> = INSTANCEABLE_KEY_TO_PLACEHOLDER,
): string {
  const placeholder = placeholderMap[eventKey];
  if (!placeholder) return text;
  return text.split(placeholder).join(instanceName);
}

/**
 * Sort life event groups: ascending by minDifficultyLevel,
 * then alphabetically by eventKey for ties.
 */
export function sortGroups(
  groups: InstanceGroupProgress[],
): InstanceGroupProgress[] {
  return [...groups].sort((a, b) => {
    if (a.minDifficultyLevel !== b.minDifficultyLevel) {
      return a.minDifficultyLevel - b.minDifficultyLevel;
    }
    return a.eventKey.localeCompare(b.eventKey);
  });
}

/**
 * Build an answered-key lookup set from the answeredKeys array.
 * Keys are in the format "questionId#eventKey:ordinal".
 */
export function buildAnsweredKeySet(answeredKeys: string[]): Set<string> {
  return new Set(answeredKeys);
}

/**
 * Build the composite key used to check if a question is answered.
 * Format: "questionId#eventKey:ordinal"
 */
export function buildCompositeKey(
  questionId: string,
  eventKey: string,
  ordinal: number,
): string {
  return `${questionId}#${eventKey}:${ordinal}`;
}

/**
 * Look up the human-readable label for an event key from the registry.
 */
export function getEventLabel(eventKey: string): string {
  const entry = LIFE_EVENT_REGISTRY.find((e) => e.key === eventKey);
  return entry?.label ?? eventKey;
}

/**
 * Build InstanceGroupProgress objects from raw API data.
 * This is the core computation — no N+1 queries, all data comes from a single API call.
 */
export function buildGroupsFromApiData(
  instanced: InstanceGroup[],
  questionDetails: Record<string, QuestionDetail>,
  answeredKeys: string[],
): InstanceGroupProgress[] {
  const answeredSet = buildAnsweredKeySet(answeredKeys);

  return instanced.map((group) => {
    const questions = group.questionIds.map((questionId) => {
      const detail = questionDetails[questionId];
      const rawText = detail?.text ?? '';
      const questionText = replacePlaceholder(
        rawText,
        group.eventKey,
        group.instanceName,
      );
      const compositeKey = buildCompositeKey(
        questionId,
        group.eventKey,
        group.instanceOrdinal,
      );
      const isAnswered = answeredSet.has(compositeKey);
      const difficulty = detail?.difficulty ?? 0;

      return { questionId, questionText, isAnswered, difficulty };
    });

    const totalQuestions = questions.length;
    const completedQuestions = questions.filter((q) => q.isAnswered).length;
    const minDifficultyLevel =
      questions.length > 0
        ? Math.min(...questions.map((q) => q.difficulty))
        : 0;
    const eventLabel = getEventLabel(group.eventKey);

    return {
      eventKey: group.eventKey,
      instanceName: group.instanceName,
      instanceOrdinal: group.instanceOrdinal,
      questions,
      totalQuestions,
      completedQuestions,
      minDifficultyLevel,
      eventLabel,
    };
  });
}

/**
 * Compute the full LifeEventsProgressData from raw API data.
 */
export function computeLifeEventsProgress(
  instanced: InstanceGroup[],
  questionDetails: Record<string, QuestionDetail>,
  answeredKeys: string[],
): LifeEventsProgressData {
  const rawGroups = buildGroupsFromApiData(
    instanced,
    questionDetails,
    answeredKeys,
  );
  const groups = sortGroups(rawGroups);

  const totalQuestions = groups.reduce((sum, g) => sum + g.totalQuestions, 0);
  const completedQuestions = groups.reduce(
    (sum, g) => sum + g.completedQuestions,
    0,
  );

  return { groups, totalQuestions, completedQuestions };
}

// ── Hook ─────────────────────────────────────────────────────────────────────

export function useLifeEventsProgress(
  userId: string | undefined,
): UseQueryResult<LifeEventsProgressData> {
  return useQuery({
    queryKey: ['lifeEventsProgress', userId],
    queryFn: async (): Promise<LifeEventsProgressData> => {
      const status = await getSurveyStatus();

      const instanced = status.assignedQuestions?.instanced ?? [];
      const questionDetails = status.questionDetails ?? {};
      const answeredKeys = status.instancedProgress?.answeredKeys ?? [];

      return computeLifeEventsProgress(instanced, questionDetails, answeredKeys);
    },
    enabled: !!userId,
    staleTime: 60_000,
  });
}
