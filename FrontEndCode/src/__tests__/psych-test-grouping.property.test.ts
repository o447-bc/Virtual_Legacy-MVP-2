import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import { groupQuestionsByFacet } from '@/components/psych-tests/testUtils';
import type { Question } from '@/types/psychTests';

/**
 * Feature: psych-test-framework, Property 15: Question facet grouping
 *
 * **Validates: Requirements 10.5**
 *
 * For any array of questions, grouping by groupByFacet produces groups where
 * every question in a group shares the same groupByFacet value, and the total
 * count across groups equals the original array length.
 */

const facetArb = fc.constantFrom(
  'imagination',
  'artistic_interests',
  'emotionality',
  'adventurousness',
  'intellect',
  'liberalism',
  'self_efficacy',
  'orderliness',
);

const questionArb: fc.Arbitrary<Question> = fc.record({
  questionId: fc.stringMatching(/^q\d{1,4}$/),
  text: fc.string({ minLength: 1, maxLength: 50 }),
  responseType: fc.constantFrom('likert5' as const, 'bipolar5' as const, 'multipleChoice' as const),
  options: fc.array(fc.string({ minLength: 1, maxLength: 20 }), { minLength: 2, maxLength: 5 }),
  reverseScored: fc.boolean(),
  scoringKey: fc.string({ minLength: 1, maxLength: 20 }),
  groupByFacet: facetArb,
  pageBreakAfter: fc.boolean(),
  accessibilityHint: fc.string({ minLength: 0, maxLength: 40 }),
});

describe('Feature: psych-test-framework, Property 15: Question facet grouping', () => {
  it('all questions in a group share the same facet and total count is preserved', () => {
    fc.assert(
      fc.property(
        fc.array(questionArb, { minLength: 0, maxLength: 60 }),
        (questions) => {
          const groups = groupQuestionsByFacet(questions);

          // Every question in a group shares the same groupByFacet value
          for (const group of groups) {
            for (const q of group.questions) {
              expect(q.groupByFacet).toBe(group.facet);
            }
          }

          // Total count across all groups equals original array length
          const totalInGroups = groups.reduce(
            (sum, g) => sum + g.questions.length,
            0,
          );
          expect(totalInGroups).toBe(questions.length);
        },
      ),
      { numRuns: 100 },
    );
  });
});
