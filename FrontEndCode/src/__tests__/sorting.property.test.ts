import { describe, it, expect, vi } from 'vitest';
import fc from 'fast-check';

// Mock service modules to prevent API config validation from throwing during import
vi.mock('@/services/surveyService', () => ({
  getSurveyStatus: vi.fn(),
}));

import { sortGroups, type InstanceGroupProgress } from '@/hooks/useLifeEventsProgress';

/**
 * Feature: dashboard-content-hub, Property 5: Life event group sorting
 *
 * Validates: Requirements 7.3
 *
 * For any list of life event instance groups (each with a minDifficultyLevel
 * and eventKey), the sorted output should be ordered such that for any two
 * adjacent groups A and B (where A comes before B), either
 * A.minDifficultyLevel < B.minDifficultyLevel, or
 * A.minDifficultyLevel === B.minDifficultyLevel and A.eventKey <= B.eventKey.
 */

const instanceGroupProgressArb: fc.Arbitrary<InstanceGroupProgress> = fc.record({
  eventKey: fc.string({ minLength: 0, maxLength: 20 }),
  instanceName: fc.string({ minLength: 1, maxLength: 20 }),
  instanceOrdinal: fc.nat({ max: 10 }),
  questions: fc.constant([]),
  totalQuestions: fc.nat({ max: 50 }),
  completedQuestions: fc.nat({ max: 50 }),
  minDifficultyLevel: fc.nat({ max: 10 }),
  eventLabel: fc.string({ minLength: 1, maxLength: 30 }),
});

describe('Feature: dashboard-content-hub, Property 5: Life event group sorting', () => {
  it('should sort groups by minDifficultyLevel ascending, then by eventKey lexicographically', () => {
    fc.assert(
      fc.property(
        fc.array(instanceGroupProgressArb, { minLength: 0, maxLength: 50 }),
        (groups) => {
          const sorted = sortGroups(groups);

          // Length is preserved
          expect(sorted).toHaveLength(groups.length);

          // Sorting invariant: for every adjacent pair, the ordering holds
          for (let i = 0; i < sorted.length - 1; i++) {
            const a = sorted[i];
            const b = sorted[i + 1];

            if (a.minDifficultyLevel !== b.minDifficultyLevel) {
              expect(a.minDifficultyLevel).toBeLessThan(b.minDifficultyLevel);
            } else {
              // Same difficulty level — eventKey should be in lexicographic order
              expect(a.eventKey.localeCompare(b.eventKey)).toBeLessThanOrEqual(0);
            }
          }
        },
      ),
      { numRuns: 100 },
    );
  });
});
