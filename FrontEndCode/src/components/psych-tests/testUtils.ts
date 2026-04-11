import type { Question } from '@/types/psychTests';

/**
 * Pure utility functions for psych test UI logic.
 * Extracted to a dependency-free module for easy property testing.
 */

/** Calculate progress percentage: Math.round((answered / total) * 100) */
export function calculateProgress(answered: number, total: number): number {
  if (total <= 0) return 0;
  return Math.round((answered / total) * 100);
}

/** Group questions by their groupByFacet value, preserving order */
export function groupQuestionsByFacet(
  questions: Question[],
): { facet: string; questions: Question[] }[] {
  const map = new Map<string, Question[]>();
  for (const q of questions) {
    const existing = map.get(q.groupByFacet);
    if (existing) {
      existing.push(q);
    } else {
      map.set(q.groupByFacet, [q]);
    }
  }
  return Array.from(map.entries()).map(([facet, qs]) => ({ facet, questions: qs }));
}

/** Determine if a video prompt should show at a given question index */
export function shouldShowVideoPrompt(index: number, frequency: number): boolean {
  if (frequency <= 0) return false;
  return index % frequency === 0;
}

/** Map responseType to a control kind for rendering */
export function controlKindForResponseType(
  responseType: 'likert5' | 'bipolar5' | 'multipleChoice',
): 'likert' | 'bipolar' | 'radio' {
  switch (responseType) {
    case 'likert5':
      return 'likert';
    case 'bipolar5':
      return 'bipolar';
    case 'multipleChoice':
      return 'radio';
  }
}
